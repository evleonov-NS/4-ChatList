"""Список поиска сохранённых промтов с подсветкой совпадений."""

from __future__ import annotations

import html
import re

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import (
    QAbstractTextDocumentLayout,
    QPalette,
    QTextDocument,
)
from PyQt6.QtWidgets import (
    QFrame,
    QListWidget,
    QListWidgetItem,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
)

import db

HIGHLIGHT_BG = "#FFD8A8"
HIGHLIGHT_FG = "#4A3728"
PANEL_MAX_HEIGHT = 280


def search_tokens(query: str) -> list[str]:
    return [token for token in re.split(r"\s+", query.strip()) if token]


def format_prompt_label(prompt: db.Prompt, preview_len: int = 80) -> str:
    preview = prompt.text.replace("\n", " ")
    if len(preview) > preview_len:
        preview = preview[: preview_len - 3] + "..."
    label = f"{prompt.created_at[:10]} — {preview}"
    if prompt.tags:
        label += f" [{prompt.tags}]"
    return label


def highlight_html(text: str, query: str) -> str:
    safe = html.escape(text)
    tokens = sorted(search_tokens(query), key=len, reverse=True)
    for token in tokens:
        pattern = re.compile(re.escape(token), re.IGNORECASE)
        safe = pattern.sub(
            lambda match: (
                f'<span style="background-color:{HIGHLIGHT_BG}; '
                f'color:{HIGHLIGHT_FG}; font-weight:600;">'
                f"{html.escape(match.group(0))}</span>"
            ),
            safe,
        )
    return safe


class PromptSearchDelegate(QStyledItemDelegate):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._query = ""
        self._fallback_width = 320

    def set_query(self, query: str) -> None:
        self._query = query

    def set_fallback_width(self, width: int) -> None:
        self._fallback_width = max(width, 200)

    def _text_width(self, option: QStyleOptionViewItem) -> int:
        width = option.rect.width()
        if width > 0:
            return width
        widget = option.widget
        if widget is not None:
            viewport = getattr(widget, "viewport", lambda: widget)()
            if viewport is not None and viewport.width() > 0:
                return viewport.width() - 12
        return self._fallback_width

    def paint(
        self,
        painter,
        option: QStyleOptionViewItem,
        index,
    ) -> None:
        painter.save()
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        document = QTextDocument()
        plain = index.data(Qt.ItemDataRole.DisplayRole) or ""
        text_color = option.palette.text().color().name()
        document.setHtml(
            f'<div style="color:{text_color};">{highlight_html(plain, self._query)}</div>'
        )
        document.setTextWidth(self._text_width(option))

        context = QAbstractTextDocumentLayout.PaintContext()
        if option.state & QStyle.StateFlag.State_Selected:
            context.palette.setColor(
                QPalette.ColorRole.Text,
                option.palette.highlightedText().color(),
            )

        painter.translate(option.rect.topLeft())
        document.documentLayout().draw(painter, context)
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        document = QTextDocument()
        plain = index.data(Qt.ItemDataRole.DisplayRole) or ""
        document.setHtml(highlight_html(plain, self._query))
        document.setTextWidth(self._text_width(option))
        return QSize(
            int(document.idealWidth()),
            max(28, int(document.size().height()) + 8),
        )


class PromptSearchPanel(QFrame):
    prompt_selected = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("promptSearchPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.list = QListWidget()
        self.list.setObjectName("promptSearchList")
        self.list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._delegate = PromptSearchDelegate(self.list)
        self.list.setItemDelegate(self._delegate)
        self.list.itemClicked.connect(self._emit_selection)
        self.list.itemActivated.connect(self._emit_selection)
        layout.addWidget(self.list)
        self.hide()

    def show_results(
        self, prompts: list[db.Prompt], query: str, list_width: int
    ) -> None:
        if not prompts:
            self.hide()
            return

        self._delegate.set_query(query)
        self._delegate.set_fallback_width(list_width)
        self.list.clear()
        for prompt in prompts:
            item = QListWidgetItem(format_prompt_label(prompt))
            item.setData(Qt.ItemDataRole.UserRole, prompt.id)
            self.list.addItem(item)
        self.list.setCurrentRow(0)

        total_height = 8
        for row in range(self.list.count()):
            total_height += self.list.sizeHintForRow(row)
        self.list.setFixedHeight(min(PANEL_MAX_HEIGHT, total_height))

        self.show()

    def hide_results(self) -> None:
        self.list.clear()
        self.hide()

    def focus_list(self) -> None:
        if self.isVisible() and self.list.count():
            self.list.setFocus()

    def select_current(self) -> None:
        item = self.list.currentItem()
        if item is not None:
            self._emit_selection(item)

    def _emit_selection(self, item: QListWidgetItem) -> None:
        prompt_id = item.data(Qt.ItemDataRole.UserRole)
        if prompt_id is not None:
            self.prompt_selected.emit(int(prompt_id))


# Совместимость со старым именем
PromptSearchPopup = PromptSearchPanel
