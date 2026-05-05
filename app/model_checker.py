import csv
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional

from .openrouter_client import OpenRouterError, chat_completion, fetch_models


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATUS_CSV_PATH = PROJECT_ROOT / "data" / "openrouter_free_model_status.csv"
STATUS_COLUMNS = [
    "checked_at_utc",
    "model_id",
    "model_name",
    "context_length",
    "working",
    "status_code",
    "latency_s",
    "output",
    "error",
]
TEST_PROMPT = "Reply with exactly one word: OK"


def _is_zero_price(value: Any) -> bool:
    try:
        return Decimal(str(value)) == Decimal("0")
    except (InvalidOperation, TypeError, ValueError):
        return False


def _is_free_model(model: Dict[str, Any]) -> bool:
    model_id = str(model.get("id", ""))
    pricing = model.get("pricing") or {}
    return model_id.endswith(":free") or (
        _is_zero_price(pricing.get("prompt"))
        and _is_zero_price(pricing.get("completion"))
    )


def _matches_contains(model: Dict[str, Any], contains: Optional[str]) -> bool:
    if not contains:
        return True
    needle = contains.lower()
    model_id = str(model.get("id", "")).lower()
    model_name = str(model.get("name", "")).lower()
    return needle in model_id or needle in model_name


def _write_status_csv(rows: List[Dict[str, Any]]) -> None:
    STATUS_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STATUS_CSV_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=STATUS_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _parse_working(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def load_latest_status_rows() -> List[Dict[str, Any]]:
    if not STATUS_CSV_PATH.exists():
        return []

    with STATUS_CSV_PATH.open("r", newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def load_working_models() -> List[str]:
    rows = load_latest_status_rows()
    return [row["model_id"] for row in rows if _parse_working(row.get("working"))]


def check_free_models(limit: Optional[int] = None, contains: Optional[str] = None) -> List[Dict[str, Any]]:
    models = fetch_models()
    free_models = [
        model
        for model in models
        if _is_free_model(model) and _matches_contains(model, contains)
    ]

    if limit is not None:
        free_models = free_models[:limit]

    checked_at = datetime.now(timezone.utc).isoformat()
    rows: List[Dict[str, Any]] = []

    for model in free_models:
        model_id = str(model.get("id", ""))
        model_name = str(model.get("name", ""))
        context_length = model.get("context_length", "")

        start = time.perf_counter()
        working = False
        status_code = ""
        output = ""
        error = ""

        try:
            output = chat_completion(
                model=model_id,
                messages=[{"role": "user", "content": TEST_PROMPT}],
                temperature=0,
                max_tokens=5,
                timeout=45,
            )
            status_code = 200
            working = bool(output)
        except OpenRouterError as exc:
            status_code = exc.status_code or ""
            error = exc.message
            logger.warning("Model check failed for %s: %s", model_id, exc.message)
        except Exception as exc:
            error = str(exc)
            logger.exception("Unexpected model check failure for %s", model_id)

        latency_s = round(time.perf_counter() - start, 3)
        rows.append(
            {
                "checked_at_utc": checked_at,
                "model_id": model_id,
                "model_name": model_name,
                "context_length": context_length,
                "working": working,
                "status_code": status_code,
                "latency_s": latency_s,
                "output": output,
                "error": error,
            }
        )

    _write_status_csv(rows)
    return rows

