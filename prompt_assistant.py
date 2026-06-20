"""AI-ассистент для улучшения промтов через OpenRouter."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from models import ModelConfig
from network import send_prompt

IMPROVE_INSTRUCTION = """Ты — ассистент по улучшению промтов. Пользователь пришлёт исходный текст запроса.

Верни ТОЛЬКО валидный JSON (без markdown-ограждений) такой структуры:
{
  "improved": "улучшенная версия промта",
  "alternatives": ["вариант 1", "вариант 2", "вариант 3"],
  "adaptations": {
    "code": "адаптация для задач программирования",
    "analysis": "адаптация для аналитических задач",
    "creative": "адаптация для творческих задач"
  }
}

Требования:
- Сохраняй язык исходного промта (русский или английский).
- alternatives — ровно 2 или 3 переформулировки.
- Улучшай ясность, структуру и конкретность, не меняя смысл без необходимости.
- adaptations — краткие специализированные версии того же запроса."""


@dataclass
class PromptImprovement:
    original: str
    improved: str
    alternatives: list[str] = field(default_factory=list)
    adaptations: dict[str, str] = field(default_factory=dict)
    model_name: str = ""
    raw_response: str = ""
    error: str | None = None

    @property
    def is_success(self) -> bool:
        return self.error is None and bool(self.improved.strip())


def build_improve_request(user_prompt: str) -> str:
    return f"{IMPROVE_INSTRUCTION}\n\n---\n\nИсходный промт:\n{user_prompt.strip()}"


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _extract_json_object(text: str) -> dict:
    cleaned = _strip_code_fence(text)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        data = json.loads(match.group())
        if isinstance(data, dict):
            return data
    raise ValueError("Ответ модели не содержит JSON с улучшениями")


def parse_improvement_response(
    response_text: str,
    original: str,
    model_name: str,
) -> PromptImprovement:
    data = _extract_json_object(response_text)
    improved = str(data.get("improved", "")).strip()
    if not improved:
        raise ValueError("JSON не содержит поле improved")

    alternatives_raw = data.get("alternatives") or []
    alternatives: list[str] = []
    if isinstance(alternatives_raw, list):
        for item in alternatives_raw[:3]:
            text = str(item).strip()
            if text:
                alternatives.append(text)

    adaptations_raw = data.get("adaptations") or {}
    adaptations: dict[str, str] = {}
    if isinstance(adaptations_raw, dict):
        for key in ("code", "analysis", "creative"):
            value = adaptations_raw.get(key)
            if value is not None and str(value).strip():
                adaptations[key] = str(value).strip()

    return PromptImprovement(
        original=original,
        improved=improved,
        alternatives=alternatives,
        adaptations=adaptations,
        model_name=model_name,
        raw_response=response_text,
    )


def improve_prompt(model: ModelConfig, user_prompt: str) -> PromptImprovement:
    request_text = build_improve_request(user_prompt)
    result = send_prompt(model, request_text)
    if result.error:
        return PromptImprovement(
            original=user_prompt,
            improved="",
            model_name=model.name,
            error=result.error,
        )
    try:
        return parse_improvement_response(
            result.response_text,
            user_prompt,
            model.name,
        )
    except (ValueError, json.JSONDecodeError) as exc:
        return PromptImprovement(
            original=user_prompt,
            improved=result.response_text.strip(),
            model_name=model.name,
            raw_response=result.response_text,
            error=f"Не удалось разобрать ответ: {exc}. Показан сырой текст.",
        )
