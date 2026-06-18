"""Загрузка переменных окружения из .env."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = get_app_dir()
LOADED_ENV_PATH: Path | None = None
ENV_ENCODINGS = ("utf-8-sig", "utf-8", "utf-16", "cp1251")


def env_file_candidates() -> list[Path]:
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in (
        APP_DIR / ".env",
        Path.cwd() / ".env",
        Path(__file__).resolve().parent / ".env",
    ):
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return unique


def _parse_env_manually(path: Path) -> bool:
    for encoding in ENV_ENCODINGS:
        try:
            text = path.read_text(encoding=encoding)
        except (UnicodeError, OSError):
            continue
        loaded = False
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                continue
            key, _, value = stripped.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ[key] = value
                loaded = True
        if loaded:
            return True
    return False


def _is_placeholder(value: str) -> bool:
    lowered = value.lower()
    return (
        not value
        or "your-" in lowered
        or lowered.endswith("-key")
        or "gsk_your" in lowered
        or "hf_your" in lowered
    )


def _load_env_file(path: Path) -> bool:
    loaded = False
    for encoding in ENV_ENCODINGS:
        try:
            load_dotenv(path, override=True, encoding=encoding)
            loaded = True
            break
        except (UnicodeError, OSError):
            continue
    if not loaded:
        loaded = _parse_env_manually(path)
    return loaded


def load_environment() -> Path | None:
    global LOADED_ENV_PATH
    for path in env_file_candidates():
        if not path.is_file():
            continue
        if _load_env_file(path):
            LOADED_ENV_PATH = path
            return path
    LOADED_ENV_PATH = None
    return None


def get_env(name: str, default: str = "") -> str | None:
    value = os.getenv(name, default).strip().strip('"').strip("'")
    if _is_placeholder(value):
        return None
    return value or None


load_environment()
