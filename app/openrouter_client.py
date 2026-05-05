import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

APP_REFERER = "http://localhost"
APP_TITLE = "My Personal LLM Website"

# Optional temporary fallback for simple public demos.
# Leave this empty when using .env locally or Render environment variables.
HARDCODED_OPENROUTER_API_KEY = "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"


class OpenRouterError(Exception):
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body


def get_api_key() -> str:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key or api_key == "...":
        api_key = HARDCODED_OPENROUTER_API_KEY.strip()

    if not api_key or api_key == "...":
        raise OpenRouterError(
            "OPENROUTER_API_KEY is missing. Set it in .env, set it as a Render "
            "environment variable, or fill HARDCODED_OPENROUTER_API_KEY in "
            "app/openrouter_client.py."
        )
    return api_key


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {get_api_key()}",
        "Content-Type": "application/json",
        "HTTP-Referer": APP_REFERER,
        "X-Title": APP_TITLE,
    }


def _extract_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:500] or response.reason

    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        return str(error.get("message") or error.get("code") or payload)
    if error:
        return str(error)
    return str(payload)


def _raise_for_http_error(response: requests.Response) -> None:
    if response.status_code < 400:
        return

    message = _extract_error_message(response)
    raise OpenRouterError(
        f"OpenRouter request failed with HTTP {response.status_code}: {message}",
        status_code=response.status_code,
        response_body=response.text[:1000],
    )


def fetch_models(timeout: int = 30) -> List[Dict[str, Any]]:
    try:
        response = requests.get(
            OPENROUTER_MODELS_URL,
            headers=_headers(),
            timeout=timeout,
        )
        _raise_for_http_error(response)
        payload = response.json()
    except requests.RequestException as exc:
        raise OpenRouterError(f"Could not fetch OpenRouter models: {exc}") from exc
    except ValueError as exc:
        raise OpenRouterError("OpenRouter returned invalid JSON for model list.") from exc

    models = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(models, list):
        raise OpenRouterError("OpenRouter model list response did not contain a model array.")
    return models


def chat_completion(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 500,
    timeout: int = 60,
) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        response = requests.post(
            OPENROUTER_CHAT_URL,
            headers=_headers(),
            json=payload,
            timeout=timeout,
        )
        _raise_for_http_error(response)
        data = response.json()
    except requests.RequestException as exc:
        raise OpenRouterError(f"OpenRouter chat request failed for {model}: {exc}") from exc
    except ValueError as exc:
        raise OpenRouterError(f"OpenRouter returned invalid JSON for {model}.") from exc

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise OpenRouterError(f"OpenRouter returned no completion text for {model}.") from exc

    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text_parts.append(str(part.get("text", "")))
            elif isinstance(part, str):
                text_parts.append(part)
        content = "".join(text_parts)

    text = str(content).strip()
    if not text:
        raise OpenRouterError(f"OpenRouter returned an empty completion for {model}.")
    return text

