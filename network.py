"""Отправка промтов в API нейросетей."""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import httpx

import db
from models import ModelConfig, get_api_key
from version import __version__

DEFAULT_TIMEOUT = 60.0
LOG_DIR = Path("logs")
logger = logging.getLogger("chatlist.network")


@dataclass
class PromptResult:
    model_name: str
    model_id: int
    response_text: str
    error: str | None = None

    @property
    def is_success(self) -> bool:
        return self.error is None


def setup_request_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    if logger.handlers:
        return
    handler = logging.FileHandler(LOG_DIR / "requests.log", encoding="utf-8")
    handler.setFormatter(
        logging.Formatter(
            f"%(asctime)s [ChatList {__version__}] [%(levelname)s] %(message)s"
        )
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.info("ChatList %s — логирование запросов включено", __version__)


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
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    referer = db.get_setting("http_referer", "")
    app_title = db.get_setting("app_title", "ChatList")
    if referer:
        headers["HTTP-Referer"] = referer
    if app_title:
        headers["X-Title"] = app_title
    return headers


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


def _format_api_error(status_code: int, body: str) -> str:
    message = ""
    try:
        data = json.loads(body)
        error = data.get("error")
        if isinstance(error, dict):
            message = str(error.get("message", "")).strip()
        elif error is not None:
            message = str(error).strip()
    except json.JSONDecodeError:
        message = body.strip()

    if status_code == 402:
        hint = "Пополните баланс: https://openrouter.ai/settings/credits"
        if message:
            return f"Недостаточно средств на OpenRouter — {message}. {hint}"
        return f"Недостаточно средств на OpenRouter. {hint}"
    if status_code == 429:
        return (
            f"Лимит запросов (HTTP 429): {message or 'слишком много запросов'}. "
            "Подождите минуту или отправьте в одну модель."
        )
    if status_code == 404:
        return (
            f"Модель недоступна (HTTP 404): {message or 'не найдена'}. "
            "Обновите api_id в Настройки → Модели."
        )
    if status_code == 401:
        return "Неверный API-ключ"
    if message:
        return f"HTTP {status_code}: {message}"
    return f"HTTP {status_code}: {body.strip() or 'нет описания'}"


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
        raise ValueError(_format_api_error(response.status_code, response.text))
    return _parse_openai_compatible_response(response.json())


PROVIDERS = {
    "openai": _send_openai_compatible,
    "deepseek": _send_openai_compatible,
    "groq": _send_openai_compatible,
    "openrouter": _send_openai_compatible,
}


def send_prompt(model: ModelConfig, prompt: str, timeout: float | None = None) -> PromptResult:
    timeout_value = timeout if timeout is not None else _get_timeout()
    sender = PROVIDERS.get(model.provider, _send_openai_compatible)
    logger.info(
        "Запрос к %s (%s), длина промта: %s",
        model.name,
        model.api_id,
        len(prompt),
    )
    try:
        response_text = sender(model, prompt, timeout_value)
        logger.info("Успешный ответ от %s, длина: %s", model.name, len(response_text))
        return PromptResult(
            model_name=model.name,
            model_id=model.id,
            response_text=response_text,
        )
    except httpx.TimeoutException:
        logger.warning("Таймаут для %s", model.name)
        return PromptResult(
            model_name=model.name,
            model_id=model.id,
            response_text="",
            error="Превышено время ожидания ответа",
        )
    except httpx.HTTPError as exc:
        logger.warning("Сеть для %s: %s", model.name, exc)
        return PromptResult(
            model_name=model.name,
            model_id=model.id,
            response_text="",
            error=f"Ошибка сети: {exc}",
        )
    except ValueError as exc:
        logger.warning("API для %s: %s", model.name, exc)
        return PromptResult(
            model_name=model.name,
            model_id=model.id,
            response_text="",
            error=str(exc),
        )
    except Exception as exc:
        logger.exception("Неожиданная ошибка для %s", model.name)
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
