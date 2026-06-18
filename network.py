"""Отправка промтов в API нейросетей."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import httpx

import db
from models import ModelConfig, get_api_key

DEFAULT_TIMEOUT = 60.0


@dataclass
class PromptResult:
    model_name: str
    model_id: int
    response_text: str
    error: str | None = None

    @property
    def is_success(self) -> bool:
        return self.error is None


def _get_timeout() -> float:
    raw = db.get_setting("request_timeout", str(int(DEFAULT_TIMEOUT)))
    try:
        return float(raw)
    except ValueError:
        return DEFAULT_TIMEOUT


def _build_headers(model: ModelConfig) -> dict[str, str]:
    api_key = get_api_key(model.env_key)
    if not api_key:
        raise ValueError(f"Ключ {model.env_key} не найден")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _build_payload(model: ModelConfig, prompt: str) -> dict:
    return {
        "model": model.api_id,
        "messages": [{"role": "user", "content": prompt}],
    }


def _parse_openai_compatible_response(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        raise ValueError("API вернул пустой список choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not content or not str(content).strip():
        raise ValueError("API вернул пустой ответ")
    return str(content).strip()


def _send_openai_compatible(model: ModelConfig, prompt: str, timeout: float) -> str:
    response = httpx.post(
        model.api_url,
        headers=_build_headers(model),
        json=_build_payload(model, prompt),
        timeout=timeout,
    )
    if response.status_code == 401:
        raise ValueError("Неверный API-ключ")
    if response.status_code >= 400:
        detail = response.text.strip() or response.reason_phrase
        raise ValueError(f"HTTP {response.status_code}: {detail}")
    return _parse_openai_compatible_response(response.json())


PROVIDERS = {
    "openai": _send_openai_compatible,
    "deepseek": _send_openai_compatible,
    "groq": _send_openai_compatible,
}


def send_prompt(model: ModelConfig, prompt: str, timeout: float | None = None) -> PromptResult:
    timeout_value = timeout if timeout is not None else _get_timeout()
    sender = PROVIDERS.get(model.provider, _send_openai_compatible)
    try:
        response_text = sender(model, prompt, timeout_value)
        return PromptResult(
            model_name=model.name,
            model_id=model.id,
            response_text=response_text,
        )
    except httpx.TimeoutException:
        return PromptResult(
            model_name=model.name,
            model_id=model.id,
            response_text="",
            error="Превышено время ожидания ответа",
        )
    except httpx.HTTPError as exc:
        return PromptResult(
            model_name=model.name,
            model_id=model.id,
            response_text="",
            error=f"Ошибка сети: {exc}",
        )
    except ValueError as exc:
        return PromptResult(
            model_name=model.name,
            model_id=model.id,
            response_text="",
            error=str(exc),
        )
    except Exception as exc:
        return PromptResult(
            model_name=model.name,
            model_id=model.id,
            response_text="",
            error=f"Неожиданная ошибка: {exc}",
        )


def send_prompt_parallel(
    models: list[ModelConfig],
    prompt: str,
    timeout: float | None = None,
) -> list[PromptResult]:
    if not models:
        return []
    timeout_value = timeout if timeout is not None else _get_timeout()
    results: list[PromptResult] = []
    with ThreadPoolExecutor(max_workers=len(models)) as executor:
        futures = {
            executor.submit(send_prompt, model, prompt, timeout_value): model
            for model in models
        }
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: item.model_name.lower())
    return results
