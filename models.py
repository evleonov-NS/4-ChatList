"""Конфигурация нейросетей и работа с API-ключами."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import db
import env_config

PROJECT_DIR = Path(__file__).resolve().parent
env_config.load_environment()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def get_openrouter_chat_url() -> str:
    base = os.getenv("OPENAI_BASE_URL", OPENROUTER_BASE_URL).strip().rstrip("/")
    return f"{base}/chat/completions"


def _build_default_models() -> list[dict[str, str | bool]]:
    """Бесплатные модели OpenRouter (актуальный список с openrouter.ai/api/v1/models)."""
    chat_url = get_openrouter_chat_url()
    return [
        {
            "name": "OpenRouter Free (авто)",
            "api_url": chat_url,
            "api_id": "openrouter/free",
            "env_key": "OPENROUTER_API_KEY",
            "is_active": True,
            "provider": "openrouter",
        },
        {
            "name": "Gemma 4 26B (free)",
            "api_url": chat_url,
            "api_id": "google/gemma-4-26b-a4b-it:free",
            "env_key": "OPENROUTER_API_KEY",
            "is_active": True,
            "provider": "openrouter",
        },
        {
            "name": "GPT-OSS 20B (free)",
            "api_url": chat_url,
            "api_id": "openai/gpt-oss-20b:free",
            "env_key": "OPENROUTER_API_KEY",
            "is_active": True,
            "provider": "openrouter",
        },
    ]


# Платные api_id → бесплатный api_id
PAID_TO_FREE: dict[str, str] = {
    "deepseek/deepseek-chat": "openrouter/free",
    "openai/gpt-4o-mini": "google/gemma-4-26b-a4b-it:free",
    "openai/gpt-4o": "openai/gpt-oss-20b:free",
    "meta-llama/llama-3.3-70b-instruct": "openai/gpt-oss-20b:free",
    "llama-3.3-70b-versatile": "openai/gpt-oss-20b:free",
}

# Устаревшие или нестабильные :free → актуальные
STALE_FREE: dict[str, tuple[str, str]] = {
    "deepseek/deepseek-r1:free": ("OpenRouter Free (авто)", "openrouter/free"),
    "meta-llama/llama-3.2-3b-instruct:free": ("Gemma 4 26B (free)", "google/gemma-4-26b-a4b-it:free"),
    "meta-llama/llama-3.3-70b-instruct:free": ("GPT-OSS 20B (free)", "openai/gpt-oss-20b:free"),
}


@dataclass
class ModelConfig:
    id: int
    name: str
    api_url: str
    api_id: str
    env_key: str
    is_active: bool
    provider: str

    @classmethod
    def from_db(cls, model: db.Model) -> ModelConfig:
        return cls(
            id=model.id,
            name=model.name,
            api_url=model.api_url,
            api_id=model.api_id,
            env_key=model.env_key,
            is_active=model.is_active,
            provider=model.provider,
        )


def get_api_key(env_key: str) -> str | None:
    return env_config.get_env(env_key)


def validate_model(model: ModelConfig) -> list[str]:
    errors: list[str] = []
    if not model.is_active:
        return errors
    if not model.api_url.strip():
        errors.append(f"{model.name}: не указан api_url")
    if not model.api_id.strip():
        errors.append(f"{model.name}: не указан api_id")
    if not get_api_key(model.env_key):
        errors.append(f"{model.name}: ключ {model.env_key} не найден в .env")
    return errors


def load_models(*, active_only: bool = False) -> list[ModelConfig]:
    rows = db.list_models(active_only=active_only)
    return [ModelConfig.from_db(row) for row in rows]


def load_active_models() -> list[ModelConfig]:
    return load_models(active_only=True)


def load_ready_models() -> tuple[list[ModelConfig], list[str]]:
    active = load_active_models()
    ready: list[ModelConfig] = []
    errors: list[str] = []
    for model in active:
        model_errors = validate_model(model)
        if model_errors:
            errors.extend(model_errors)
        else:
            ready.append(model)
    return ready, errors


def ensure_default_models() -> None:
    existing = {model.name for model in db.list_models()}
    for item in _build_default_models():
        if item["name"] in existing:
            continue
        db.add_model(
            name=str(item["name"]),
            api_url=str(item["api_url"]),
            api_id=str(item["api_id"]),
            env_key=str(item["env_key"]),
            is_active=bool(item["is_active"]),
            provider=str(item["provider"]),
        )


def deactivate_invalid_models() -> list[str]:
    """Отключает активные модели без валидной конфигурации."""
    if not env_config.LOADED_ENV_PATH:
        return [
            f"Файл .env не найден. Ожидается один из путей:\n"
            + "\n".join(f"  • {path}" for path in env_config.env_file_candidates())
        ]
    messages: list[str] = []
    for model in load_active_models():
        errors = validate_model(model)
        if errors:
            db.update_model(model.id, is_active=False)
            messages.extend(errors)
    return messages


def migrate_named_models_to_openrouter() -> None:
    """Обновляет известные модели на OpenRouter, если ключ доступен."""
    if not get_api_key("OPENROUTER_API_KEY"):
        return
    defaults = {str(item["name"]): item for item in _build_default_models()}
    chat_url = get_openrouter_chat_url()
    for model in db.list_models():
        spec = defaults.get(model.name)
        if not spec:
            continue
        db.update_model(
            model.id,
            api_url=chat_url,
            api_id=str(spec["api_id"]),
            env_key="OPENROUTER_API_KEY",
            provider="openrouter",
            is_active=True,
        )


def activate_openrouter_models() -> None:
    if not get_api_key("OPENROUTER_API_KEY"):
        return
    chat_url = get_openrouter_chat_url()
    for model in db.list_models():
        if model.env_key == "OPENROUTER_API_KEY":
            db.update_model(
                model.id,
                is_active=True,
                api_url=chat_url,
                provider="openrouter",
            )


def prefer_openrouter_over_legacy() -> None:
    """Если настроен OpenRouter, оставляем только модели с OPENROUTER_API_KEY."""
    if not get_api_key("OPENROUTER_API_KEY"):
        return
    for model in db.list_models():
        if model.env_key != "OPENROUTER_API_KEY" and model.is_active:
            db.update_model(model.id, is_active=False)


def migrate_stale_free_models() -> None:
    """Заменяет снятые с бесплатного тарифа или нестабильные модели."""
    if not get_api_key("OPENROUTER_API_KEY"):
        return
    chat_url = get_openrouter_chat_url()
    for model in db.list_models():
        if model.env_key != "OPENROUTER_API_KEY":
            continue
        stale = STALE_FREE.get(model.api_id)
        if not stale:
            continue
        _, new_api_id = stale
        db.update_model(
            model.id,
            api_url=chat_url,
            api_id=new_api_id,
            env_key="OPENROUTER_API_KEY",
            provider="openrouter",
            is_active=True,
        )


def migrate_paid_to_free_models() -> None:
    """Переводит платные OpenRouter-модели на бесплатные варианты (:free)."""
    if not get_api_key("OPENROUTER_API_KEY"):
        return
    chat_url = get_openrouter_chat_url()
    for model in db.list_models():
        if model.env_key != "OPENROUTER_API_KEY":
            continue
        if model.api_id.endswith(":free") or model.api_id == "openrouter/free":
            db.update_model(
                model.id,
                api_url=chat_url,
                provider="openrouter",
                is_active=True,
            )
            continue
        free_api_id = PAID_TO_FREE.get(model.api_id)
        if free_api_id:
            db.update_model(
                model.id,
                api_url=chat_url,
                api_id=free_api_id,
                env_key="OPENROUTER_API_KEY",
                provider="openrouter",
                is_active=True,
            )
        elif model.is_active:
            db.update_model(model.id, is_active=False)


def dedupe_active_models() -> None:
    """Оставляет одну активную модель на каждый api_id (предпочитает имена с «free»)."""
    by_api_id: dict[str, list[db.Model]] = {}
    for model in db.list_models():
        if not model.is_active:
            continue
        by_api_id.setdefault(model.api_id, []).append(model)
    for group in by_api_id.values():
        if len(group) <= 1:
            continue
        group.sort(key=lambda item: ("(free)" not in item.name, item.name))
        keeper = group[0]
        for model in group[1:]:
            if model.id != keeper.id:
                db.update_model(model.id, is_active=False)


def migrate_legacy_models_to_openrouter() -> None:
    """Переводит старые модели с другими именами на OpenRouter."""
    if not get_api_key("OPENROUTER_API_KEY"):
        return
    chat_url = get_openrouter_chat_url()
    legacy_map = {
        "GPT-4o": "openai/gpt-oss-20b:free",
        "GPT-4o Mini": "google/gemma-4-26b-a4b-it:free",
        "DeepSeek Chat": "openrouter/free",
        "DeepSeek R1 (free)": "openrouter/free",
        "Groq Llama 3.3 70B": "openai/gpt-oss-20b:free",
        "Llama 3.3 70B": "openai/gpt-oss-20b:free",
        "Llama 3.3 70B (free)": "openai/gpt-oss-20b:free",
        "Llama 3.2 3B (free)": "google/gemma-4-26b-a4b-it:free",
    }
    for model in db.list_models():
        free_api_id = legacy_map.get(model.name)
        if free_api_id is None:
            continue
        db.update_model(
            model.id,
            api_url=chat_url,
            api_id=free_api_id,
            env_key="OPENROUTER_API_KEY",
            provider="openrouter",
            is_active=True,
        )


def bootstrap_models() -> list[str]:
    ensure_default_models()
    migrate_stale_free_models()
    migrate_named_models_to_openrouter()
    migrate_legacy_models_to_openrouter()
    migrate_paid_to_free_models()
    activate_openrouter_models()
    dedupe_active_models()
    prefer_openrouter_over_legacy()
    return deactivate_invalid_models()


def seed_default_models() -> None:
    """Совместимость: первичное заполнение и синхронизация моделей."""
    bootstrap_models()
