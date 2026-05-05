from typing import Iterable, List


PREFERRED_MODELS = [
    "google/gemma-4-31b-it:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "z-ai/glm-4.5-air:free",
    "google/gemma-3-27b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]


def _model_id(value) -> str:
    if isinstance(value, dict):
        return str(value.get("model_id") or value.get("id") or "")
    return str(value)


def select_best_working_model(working_models: Iterable) -> str:
    model_ids: List[str] = []
    for item in working_models:
        model_id = _model_id(item).strip()
        if model_id and model_id not in model_ids:
            model_ids.append(model_id)

    if not model_ids:
        raise RuntimeError(
            "No working free OpenRouter models are available. Run /api/models/check "
            "and try again after at least one model passes."
        )

    model_set = set(model_ids)
    for preferred_model in PREFERRED_MODELS:
        if preferred_model in model_set:
            return preferred_model

    return model_ids[0]

