"""Экспорт результатов в Markdown и JSON."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass
class ExportRow:
    model_name: str
    response_text: str
    error: str | None = None


def export_markdown(prompt: str, rows: list[ExportRow]) -> str:
    lines = [
        "# ChatList — экспорт результатов",
        "",
        f"**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Промт",
        "",
        prompt,
        "",
        "## Ответы",
        "",
    ]
    for index, row in enumerate(rows, start=1):
        lines.append(f"### {index}. {row.model_name}")
        lines.append("")
        if row.error:
            lines.append(f"*Ошибка:* {row.error}")
        else:
            lines.append(row.response_text)
        lines.append("")
    return "\n".join(lines)


def export_json(prompt: str, rows: list[ExportRow]) -> str:
    payload = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "prompt": prompt,
        "results": [asdict(row) for row in rows],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
