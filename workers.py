"""Фоновая отправка промтов без блокировки UI."""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from models import ModelConfig
from network import PromptResult, send_prompt_parallel


class PromptSendWorker(QThread):
    finished = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, models: list[ModelConfig], prompt: str) -> None:
        super().__init__()
        self.models = models
        self.prompt = prompt

    def run(self) -> None:
        try:
            results: list[PromptResult] = send_prompt_parallel(self.models, self.prompt)
            self.finished.emit(results)
        except Exception as exc:
            self.failed.emit(str(exc))
