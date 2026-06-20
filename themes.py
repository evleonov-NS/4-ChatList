"""Тёплые светлая и тёмная темы для ChatList."""

from __future__ import annotations

from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import QApplication

import db

THEME_LIGHT = "light"
THEME_DARK = "dark"

DEFAULT_FONT_SIZE = 10
MIN_FONT_SIZE = 8
MAX_FONT_SIZE = 20

COLORS = {
    "light": {
        "bg": "#FFF8F3",
        "surface": "#FFFFFF",
        "surface_alt": "#FFEEDD",
        "text": "#4A3728",
        "text_muted": "#7D6B5D",
        "accent": "#F4A261",
        "accent_hover": "#E76F51",
        "accent_soft": "#FFD8A8",
        "border": "#F0D4B8",
        "header": "#FFE8D6",
        "inactive_row": "#ECE6E0",
        "selection": "#FFDDB8",
    },
    "dark": {
        "bg": "#2A211C",
        "surface": "#3A2F28",
        "surface_alt": "#4A3C33",
        "text": "#FFF5EB",
        "text_muted": "#D4C4B5",
        "accent": "#F4A261",
        "accent_hover": "#FFB86C",
        "accent_soft": "#5C4030",
        "border": "#5A4A40",
        "header": "#4A3C33",
        "inactive_row": "#3A3530",
        "selection": "#6B4E3D",
    },
}


def get_theme() -> str:
    theme = db.get_setting("theme", THEME_LIGHT)
    return theme if theme in (THEME_LIGHT, THEME_DARK) else THEME_LIGHT


def set_theme(theme: str) -> None:
    db.set_setting("theme", theme if theme in (THEME_LIGHT, THEME_DARK) else THEME_LIGHT)


def get_font_size() -> int:
    raw = db.get_setting("font_size", str(DEFAULT_FONT_SIZE))
    try:
        size = int(raw)
    except ValueError:
        return DEFAULT_FONT_SIZE
    return max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, size))


def set_font_size(size: int) -> None:
    clamped = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, int(size)))
    db.set_setting("font_size", str(clamped))


def inactive_row_brush(theme: str | None = None) -> QBrush:
    name = theme or get_theme()
    color = COLORS[name]["inactive_row"]
    return QBrush(QColor(color))


def _build_stylesheet(theme: str, font_size: int) -> str:
    c = COLORS[theme]
    hint_size = max(MIN_FONT_SIZE, font_size - 1)
    header_size = font_size + 1
    return f"""
    QMainWindow, QDialog, QWidget {{
        background-color: {c["bg"]};
        color: {c["text"]};
        font-size: {font_size}pt;
    }}
    QLabel {{
        color: {c["text"]};
        font-size: {font_size}pt;
    }}
    QLabel#hintLabel {{
        color: {c["text_muted"]};
        font-size: {hint_size}pt;
        padding: 0 2px 4px 2px;
    }}
    QLabel#stepLabel {{
        font-weight: 600;
        color: {c["text"]};
        font-size: {header_size}pt;
    }}
    QGroupBox {{
        font-size: {font_size}pt;
    }}
    QGroupBox#stepGroup {{
        background-color: {c["surface"]};
        border: 1px solid {c["border"]};
        border-radius: 10px;
        margin-top: 10px;
        padding: 12px 12px 10px 12px;
        font-weight: 600;
        font-size: {header_size}pt;
    }}
    QGroupBox#stepGroup::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 0 6px;
        color: {c["text"]};
    }}
    QFrame#promptSearchPanel {{
        background-color: {c["surface"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        margin-top: 2px;
    }}
    QListWidget#promptSearchList {{
        background-color: {c["surface"]};
        color: {c["text"]};
        border: none;
        outline: none;
        padding: 2px;
        font-size: {font_size}pt;
    }}
    QListWidget#promptSearchList::item {{
        padding: 4px 6px;
        border-radius: 4px;
    }}
    QListWidget#promptSearchList::item:selected {{
        background-color: {c["selection"]};
    }}
    QListWidget#promptSearchList::item:hover {{
        background-color: {c["surface_alt"]};
    }}
    QLineEdit, QTextEdit, QComboBox, QTableWidget, QListWidget, QSpinBox {{
        background-color: {c["surface"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        border-radius: 6px;
        padding: 4px;
        selection-background-color: {c["selection"]};
        font-size: {font_size}pt;
    }}
    QComboBox::drop-down {{
        border: none;
    }}
    QTableWidget {{
        gridline-color: {c["border"]};
        alternate-background-color: {c["surface_alt"]};
        font-size: {font_size}pt;
    }}
    QTableWidget::indicator {{
        width: 18px;
        height: 18px;
    }}
    QHeaderView::section {{
        background-color: {c["header"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        padding: 6px;
        font-weight: bold;
        font-size: {font_size}pt;
    }}
    QPushButton {{
        background-color: {c["surface"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 600;
        min-height: 20px;
        font-size: {font_size}pt;
    }}
    QPushButton:hover {{
        background-color: {c["surface_alt"]};
        border-color: {c["accent"]};
    }}
    QPushButton:pressed {{
        background-color: {c["accent_soft"]};
    }}
    QPushButton:disabled {{
        background-color: {c["surface_alt"]};
        color: {c["text_muted"]};
        border-color: {c["border"]};
    }}
    QPushButton#primaryButton {{
        background-color: {c["accent"]};
        color: {c["text"] if theme == THEME_LIGHT else "#2A211C"};
        border: none;
        padding: 9px 20px;
    }}
    QPushButton#primaryButton:hover {{
        background-color: {c["accent_hover"]};
        border: none;
    }}
    QPushButton#primaryButton:pressed {{
        background-color: {c["accent_soft"]};
    }}
    QPushButton#primaryButton:disabled {{
        background-color: {c["border"]};
        color: {c["text_muted"]};
    }}
    QPushButton#secondaryButton {{
        background-color: {c["surface"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
    }}
    QPushButton#secondaryButton:hover {{
        background-color: {c["surface_alt"]};
        border-color: {c["accent"]};
        color: {c["text"]};
    }}
    QPushButton#toggleButton {{
        background-color: {c["surface"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        padding: 8px 14px;
    }}
    QPushButton#toggleButton:hover {{
        border-color: {c["accent"]};
        background-color: {c["surface_alt"]};
    }}
    QPushButton#toggleButton:checked {{
        background-color: {c["accent_soft"]};
        border: 2px solid {c["accent"]};
        color: {c["text"]};
        padding: 7px 13px;
    }}
    QPushButton#toggleButton:checked:hover {{
        background-color: {c["selection"]};
    }}
    QMenuBar {{
        background-color: {c["surface"]};
        color: {c["text"]};
        font-size: {font_size}pt;
    }}
    QMenuBar::item:selected {{
        background-color: {c["accent_soft"]};
    }}
    QMenu {{
        background-color: {c["surface"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        font-size: {font_size}pt;
    }}
    QMenu::item:selected {{
        background-color: {c["selection"]};
    }}
    QStatusBar {{
        background-color: {c["surface_alt"]};
        color: {c["text_muted"]};
        font-size: {hint_size}pt;
    }}
    QProgressBar {{
        border: 1px solid {c["border"]};
        border-radius: 6px;
        background-color: {c["surface"]};
        text-align: center;
        font-size: {hint_size}pt;
    }}
    QProgressBar::chunk {{
        background-color: {c["accent"]};
        border-radius: 5px;
    }}
    QCheckBox {{
        color: {c["text"]};
        font-size: {font_size}pt;
    }}
    QTextBrowser {{
        background-color: {c["surface"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 12px;
        font-size: {font_size}pt;
    }}
    """


def apply_appearance(
    app: QApplication,
    theme: str | None = None,
    font_size: int | None = None,
) -> tuple[str, int]:
    name = theme or get_theme()
    if name not in COLORS:
        name = THEME_LIGHT
    size = font_size if font_size is not None else get_font_size()
    size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, size))

    font = QFont(app.font())
    font.setPointSize(size)
    app.setFont(font)
    app.setStyleSheet(_build_stylesheet(name, size))
    set_theme(name)
    set_font_size(size)
    return name, size


def apply_theme(app: QApplication, theme: str | None = None) -> str:
    name, _ = apply_appearance(app, theme=theme)
    return name
