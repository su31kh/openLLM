import logging
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from .model_checker import check_free_models, load_working_models
from .model_registry import select_best_working_model
from .openrouter_client import (
    OpenRouterError,
    chat_completion,
    get_masked_api_key_info,
    validate_api_key,
)
from .schemas import ChatRequest, ChatResponse, ModelCheckResponse


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Local LLM Backend")
STATIC_DIR = Path(__file__).resolve().parent / "static"


def _is_recoverable_model_error(exc: OpenRouterError) -> bool:
    if exc.status_code is None:
        return True
    if exc.status_code in {400, 404, 408, 409, 429}:
        return True
    return 500 <= exc.status_code <= 599


def _ensure_working_models() -> List[str]:
    working_models = load_working_models()
    if working_models:
        return working_models

    logger.info("No model status CSV found or no working models listed. Running model check.")
    rows = check_free_models()
    return [row["model_id"] for row in rows if row.get("working")]


def _ordered_chat_candidates(requested_model: Optional[str], working_models: List[str]) -> List[str]:
    candidates: List[str] = []

    if requested_model:
        candidates.append(requested_model)
    else:
        candidates.append(select_best_working_model(working_models))

    for model_id in working_models:
        if model_id not in candidates:
            candidates.append(model_id)

    return candidates


@app.get("/")
def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def api_health():
    return {
        "status": "ok",
        "message": "Local LLM backend is running",
    }


@app.get("/api/key/debug")
def api_key_debug():
    return get_masked_api_key_info()


@app.get("/api/key/validate")
def api_key_validate():
    try:
        key_info = validate_api_key()
    except OpenRouterError as exc:
        raise HTTPException(status_code=401 if exc.status_code == 401 else 502, detail=exc.message) from exc

    return {
        "status": "ok",
        "key": key_info.get("data", {}),
    }


@app.get("/api/models/check", response_model=ModelCheckResponse)
def api_check_models(
    limit: Optional[int] = Query(default=None, ge=1),
    contains: Optional[str] = Query(default=None),
):
    try:
        rows = check_free_models(limit=limit, contains=contains)
    except OpenRouterError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc

    working_models = [row["model_id"] for row in rows if row.get("working")]
    return ModelCheckResponse(
        num_checked=len(rows),
        num_working=len(working_models),
        working_models=working_models,
    )


@app.get("/api/models/working")
def api_working_models():
    working_models = load_working_models()
    return {
        "num_working": len(working_models),
        "working_models": working_models,
    }


@app.post("/api/chat", response_model=ChatResponse)
def api_chat(chat_request: ChatRequest):
    try:
        working_models = _ensure_working_models()
        candidates = _ordered_chat_candidates(chat_request.model, working_models)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except OpenRouterError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc

    messages = [{"role": "user", "content": chat_request.prompt}]
    errors = []

    for index, model_id in enumerate(candidates):
        try:
            answer = chat_completion(
                model=model_id,
                messages=messages,
                temperature=chat_request.temperature,
                max_tokens=chat_request.max_tokens,
            )
            return ChatResponse(
                model_used=model_id,
                answer=answer,
                fallback_used=index > 0,
            )
        except OpenRouterError as exc:
            logger.warning("Chat failed for %s: %s", model_id, exc.message)
            errors.append(f"{model_id}: {exc.message}")
            if not _is_recoverable_model_error(exc):
                raise HTTPException(status_code=502, detail=exc.message) from exc

    raise HTTPException(
        status_code=503,
        detail="All candidate models failed. Last errors: " + " | ".join(errors[-3:]),
    )

