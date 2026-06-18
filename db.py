"""Доступ к SQLite для ChatList."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal

DEFAULT_DB_PATH = Path("chatlist.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS prompts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    text       TEXT    NOT NULL,
    tags       TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS models (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT    NOT NULL UNIQUE,
    api_url   TEXT    NOT NULL,
    api_id    TEXT    NOT NULL,
    env_key   TEXT    NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    provider  TEXT    NOT NULL DEFAULT 'openai'
);

CREATE TABLE IF NOT EXISTS results (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id     INTEGER REFERENCES prompts(id) ON DELETE SET NULL,
    model_id      INTEGER NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    response_text TEXT    NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_prompts_created_at ON prompts(created_at);
CREATE INDEX IF NOT EXISTS idx_models_is_active ON models(is_active);
CREATE INDEX IF NOT EXISTS idx_results_prompt_id ON results(prompt_id);
CREATE INDEX IF NOT EXISTS idx_results_model_id ON results(model_id);
CREATE INDEX IF NOT EXISTS idx_results_created_at ON results(created_at);
"""

PromptSortField = Literal["created_at", "text", "tags"]
ModelSortField = Literal["name", "provider", "is_active"]
ResultSortField = Literal["created_at", "model_name"]
SortDirection = Literal["asc", "desc"]


@dataclass
class Prompt:
    id: int
    created_at: str
    text: str
    tags: str


@dataclass
class Model:
    id: int
    name: str
    api_url: str
    api_id: str
    env_key: str
    is_active: bool
    provider: str


@dataclass
class Result:
    id: int
    prompt_id: int | None
    model_id: int
    response_text: str
    created_at: str
    model_name: str | None = None
    prompt_text: str | None = None


def get_db_path() -> Path:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = 'db_path'"
        ).fetchone()
    if row and row["value"]:
        return Path(row["value"])
    return DEFAULT_DB_PATH


@contextmanager
def get_connection(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path | None = None) -> None:
    path = db_path or DEFAULT_DB_PATH
    with get_connection(path) as conn:
        conn.executescript(SCHEMA_SQL)


def _prompt_from_row(row: sqlite3.Row) -> Prompt:
    return Prompt(
        id=row["id"],
        created_at=row["created_at"],
        text=row["text"],
        tags=row["tags"],
    )


def _model_from_row(row: sqlite3.Row) -> Model:
    return Model(
        id=row["id"],
        name=row["name"],
        api_url=row["api_url"],
        api_id=row["api_id"],
        env_key=row["env_key"],
        is_active=bool(row["is_active"]),
        provider=row["provider"],
    )


def _result_from_row(row: sqlite3.Row) -> Result:
    keys = row.keys()
    return Result(
        id=row["id"],
        prompt_id=row["prompt_id"],
        model_id=row["model_id"],
        response_text=row["response_text"],
        created_at=row["created_at"],
        model_name=row["model_name"] if "model_name" in keys else None,
        prompt_text=row["prompt_text"] if "prompt_text" in keys else None,
    )


# --- prompts ---


def add_prompt(text: str, tags: str = "") -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO prompts (text, tags) VALUES (?, ?)",
            (text.strip(), tags.strip()),
        )
        return int(cursor.lastrowid)


def get_prompt(prompt_id: int) -> Prompt | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM prompts WHERE id = ?", (prompt_id,)
        ).fetchone()
    return _prompt_from_row(row) if row else None


def list_prompts(
    search: str = "",
    sort_by: PromptSortField = "created_at",
    sort_dir: SortDirection = "desc",
) -> list[Prompt]:
    allowed = {"created_at", "text", "tags"}
    column = sort_by if sort_by in allowed else "created_at"
    direction = "DESC" if sort_dir.lower() == "desc" else "ASC"
    query = f"SELECT * FROM prompts WHERE 1=1"
    params: list[str] = []
    if search.strip():
        query += " AND (text LIKE ? OR tags LIKE ?)"
        pattern = f"%{search.strip()}%"
        params.extend([pattern, pattern])
    query += f" ORDER BY {column} {direction}"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_prompt_from_row(row) for row in rows]


# --- models ---


def add_model(
    name: str,
    api_url: str,
    api_id: str,
    env_key: str,
    *,
    is_active: bool = True,
    provider: str = "openai",
) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO models (name, api_url, api_id, env_key, is_active, provider)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, api_url, api_id, env_key, int(is_active), provider),
        )
        return int(cursor.lastrowid)


def update_model(
    model_id: int,
    *,
    name: str | None = None,
    api_url: str | None = None,
    api_id: str | None = None,
    env_key: str | None = None,
    is_active: bool | None = None,
    provider: str | None = None,
) -> None:
    fields: dict[str, object] = {}
    if name is not None:
        fields["name"] = name
    if api_url is not None:
        fields["api_url"] = api_url
    if api_id is not None:
        fields["api_id"] = api_id
    if env_key is not None:
        fields["env_key"] = env_key
    if is_active is not None:
        fields["is_active"] = int(is_active)
    if provider is not None:
        fields["provider"] = provider
    if not fields:
        return
    assignments = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [model_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE models SET {assignments} WHERE id = ?", values)


def get_model(model_id: int) -> Model | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM models WHERE id = ?", (model_id,)
        ).fetchone()
    return _model_from_row(row) if row else None


def list_models(
    search: str = "",
    sort_by: ModelSortField = "name",
    sort_dir: SortDirection = "asc",
    *,
    active_only: bool = False,
) -> list[Model]:
    allowed = {"name", "provider", "is_active"}
    column = sort_by if sort_by in allowed else "name"
    direction = "DESC" if sort_dir.lower() == "desc" else "ASC"
    query = "SELECT * FROM models WHERE 1=1"
    params: list[object] = []
    if active_only:
        query += " AND is_active = 1"
    if search.strip():
        query += " AND (name LIKE ? OR provider LIKE ? OR api_id LIKE ?)"
        pattern = f"%{search.strip()}%"
        params.extend([pattern, pattern, pattern])
    query += f" ORDER BY {column} {direction}"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_model_from_row(row) for row in rows]


def get_active_models() -> list[Model]:
    return list_models(active_only=True)


def count_models() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM models").fetchone()
    return int(row["cnt"]) if row else 0


# --- results ---


def add_result(
    model_id: int,
    response_text: str,
    prompt_id: int | None = None,
) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO results (prompt_id, model_id, response_text)
            VALUES (?, ?, ?)
            """,
            (prompt_id, model_id, response_text),
        )
        return int(cursor.lastrowid)


def list_results(
    search: str = "",
    sort_by: ResultSortField = "created_at",
    sort_dir: SortDirection = "desc",
) -> list[Result]:
    allowed = {"created_at", "model_name"}
    column = "r.created_at" if sort_by == "created_at" else "m.name"
    direction = "DESC" if sort_dir.lower() == "desc" else "ASC"
    query = """
        SELECT
            r.id,
            r.prompt_id,
            r.model_id,
            r.response_text,
            r.created_at,
            m.name AS model_name,
            p.text AS prompt_text
        FROM results r
        JOIN models m ON m.id = r.model_id
        LEFT JOIN prompts p ON p.id = r.prompt_id
        WHERE 1=1
    """
    params: list[str] = []
    if search.strip():
        query += " AND (r.response_text LIKE ? OR m.name LIKE ? OR p.text LIKE ?)"
        pattern = f"%{search.strip()}%"
        params.extend([pattern, pattern, pattern])
    query += f" ORDER BY {column} {direction}"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_result_from_row(row) for row in rows]


# --- settings ---


def get_setting(key: str, default: str = "") -> str:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )


def _self_test() -> None:
    test_path = Path("chatlist_test.db")
    if test_path.exists():
        test_path.unlink()

    global DEFAULT_DB_PATH
    original_path = DEFAULT_DB_PATH
    DEFAULT_DB_PATH = test_path
    try:
        init_db()
        prompt_id = add_prompt("Тестовый промт", tags="test,demo")
        model_id = add_model(
            "Test Model",
            "https://api.example.com/v1/chat/completions",
            "test-model",
            "TEST_API_KEY",
            provider="openai",
        )
        add_result(model_id, "Тестовый ответ", prompt_id=prompt_id)
        set_setting("request_timeout", "60")
        prompts = list_prompts(search="Тест")
        models = get_active_models()
        results = list_results()
        assert len(prompts) == 1
        assert len(models) == 1
        assert len(results) == 1
        assert get_setting("request_timeout") == "60"
        print("db.py: все проверки пройдены")
    finally:
        DEFAULT_DB_PATH = original_path
        if test_path.exists():
            test_path.unlink()


if __name__ == "__main__":
    _self_test()
