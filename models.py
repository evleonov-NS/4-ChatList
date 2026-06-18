"""Конфигурация нейросетей и работа с API-ключами."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

import db

load_dotenv()

DEFAULT_MODELS: list[dict[str, str | bool]] = [
    {
        "name": "GPT-4o",
        "api_url": "https://api.openai.com/v1/chat/completions",
        "api_id": "gpt-4o",
        "env_key": "OPENAI_API_KEY",
        "is_active": True,
        "provider": "openai",
    },
    {
        "name": "DeepSeek Chat",
        "api_url": "https://api.deepseek.com/chat/completions",
        "api_id": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
        "is_active": True,
        "provider": "deepseek",
    },
    {
        "name": "Groq Llama 3.3 70B",
        "api_url": "https://api.groq.com/openai/v1/chat/completions",
        "api_id": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
        "is_active": True,
        "provider": "groq",
    },
]


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
    value = os.getenv(env_key, "").strip()
    return value or None


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
    """Активные модели с валидной конфигурацией и список ошибок."""
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


def seed_default_models() -> None:
    if db.count_models() > 0:
        return
    for item in DEFAULT_MODELS:
        db.add_model(
            name=str(item["name"]),
            api_url=str(item["api_url"]),
            api_id=str(item["api_id"]),
            env_key=str(item["env_key"]),
            is_active=bool(item["is_active"]),
            provider=str(item["provider"]),
        )
