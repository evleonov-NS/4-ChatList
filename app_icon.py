"""Иконка приложения ChatList."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QWidget


def _assets_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets"
    return Path(__file__).resolve().parent / "assets"


def get_app_icon() -> QIcon:
    assets = _assets_dir()
    ico = assets / "chatlist.ico"
    png = assets / "chatlist-icon.png"
    if ico.exists():
        return QIcon(str(ico))
    if png.exists():
        return QIcon(str(png))
    return QIcon()


def apply_app_icon(app: QApplication, window: QWidget | None = None) -> None:
    icon = get_app_icon()
    if icon.isNull():
        return
    app.setWindowIcon(icon)
    if window is not None:
        window.setWindowIcon(icon)
