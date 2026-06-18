"""Тёплые светлая и тёмная темы для ChatList."""

from __future__ import annotations

from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import QApplication

import db

THEME_LIGHT = "light"
THEME_DARK = "dark"

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


def inactive_row_brush(theme: str | None = None) -> QBrush:
    name = theme or get_theme()
    color = COLORS[name]["inactive_row"]
    return QBrush(QColor(color))


def _build_stylesheet(theme: str) -> str:
    c = COLORS[theme]
    return f"""
    QMainWindow, QDialog, QWidget {{
        background-color: {c["bg"]};
        color: {c["text"]};
    }}
    QLabel {{
        color: {c["text"]};
    }}
    QLabel#hintLabel {{
        color: {c["text_muted"]};
        font-size: 12px;
        padding: 0 2px 4px 2px;
    }}
    QLabel#stepLabel {{
        font-weight: 600;
        color: {c["text"]};
    }}
    QGroupBox#stepGroup {{
        background-color: {c["surface"]};
        border: 1px solid {c["border"]};
        border-radius: 10px;
        margin-top: 10px;
        padding: 12px 12px 10px 12px;
        font-weight: 600;
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
    QLineEdit, QTextEdit, QComboBox, QTableWidget, QListWidget {{
        background-color: {c["surface"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        border-radius: 6px;
        padding: 4px;
        selection-background-color: {c["selection"]};
    }}
    QComboBox::drop-down {{
        border: none;
    }}
    QTableWidget {{
        gridline-color: {c["border"]};
        alternate-background-color: {c["surface_alt"]};
    }}
    QHeaderView::section {{
        background-color: {c["header"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        padding: 6px;
        font-weight: bold;
    }}
    QPushButton {{
        background-color: {c["surface"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 600;
        min-height: 20px;
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
    }}
    QMenuBar::item:selected {{
        background-color: {c["accent_soft"]};
    }}
    QMenu {{
        background-color: {c["surface"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
    }}
    QMenu::item:selected {{
        background-color: {c["selection"]};
    }}
    QStatusBar {{
        background-color: {c["surface_alt"]};
        color: {c["text_muted"]};
    }}
    QProgressBar {{
        border: 1px solid {c["border"]};
        border-radius: 6px;
        background-color: {c["surface"]};
        text-align: center;
    }}
    QProgressBar::chunk {{
        background-color: {c["accent"]};
        border-radius: 5px;
    }}
    QCheckBox {{
        color: {c["text"]};
    }}
    QTextBrowser {{
        background-color: {c["surface"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 12px;
    }}
    """


def apply_theme(app: QApplication, theme: str | None = None) -> str:
    name = theme or get_theme()
    if name not in COLORS:
        name = THEME_LIGHT
    app.setStyleSheet(_build_stylesheet(name))
    set_theme(name)
    return name
