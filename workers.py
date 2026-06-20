"""Фоновая отправка промтов без блокировки UI."""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from models import ModelConfig
from network import PromptResult, send_prompt_parallel
from prompt_assistant import PromptImprovement, improve_prompt


def wait_for_worker(worker: QThread | None, timeout_ms: int = 120_000) -> bool:
    if worker is None or not worker.isRunning():
        return True
    return worker.wait(timeout_ms)


class PromptSendWorker(QThread):
    finished = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(
        self,
        models: list[ModelConfig],
        prompt: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.models = models
        self.prompt = prompt

    def run(self) -> None:
        try:
            results: list[PromptResult] = send_prompt_parallel(self.models, self.prompt)
            self.finished.emit(results)
        except Exception as exc:
            self.failed.emit(str(exc))


class PromptImproveWorker(QThread):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        model: ModelConfig,
        prompt: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.model = model
        self.prompt = prompt

    def run(self) -> None:
        try:
            result: PromptImprovement = improve_prompt(self.model, self.prompt)
            if result.error and not result.improved:
                self.failed.emit(result.error)
            else:
                self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
