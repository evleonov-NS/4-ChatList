import sys

from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import db
from models import load_active_models, load_models, seed_default_models


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ChatList")
        self.setMinimumSize(900, 600)

        self.prompts: list[db.Prompt] = []
        self.models = load_models()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        layout.addWidget(self._build_prompt_panel())
        layout.addWidget(self._build_actions_panel())
        layout.addWidget(self._build_results_panel(), stretch=1)
        layout.addWidget(self._build_save_panel())

        self.setStatusBar(QStatusBar())
        self._refresh_status()

    def _build_prompt_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Промт"))

        self.saved_prompts = QComboBox()
        self.saved_prompts.setPlaceholderText("Выберите сохранённый промт")
        self.saved_prompts.currentIndexChanged.connect(self._on_saved_prompt_selected)
        layout.addWidget(self.saved_prompts)

        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("Введите текст запроса...")
        self.prompt_input.setMinimumHeight(120)
        layout.addWidget(self.prompt_input)

        return panel

    def _build_actions_panel(self) -> QWidget:
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        self.send_button = QPushButton("Отправить")
        self.send_button.clicked.connect(self._on_send_clicked)
        layout.addWidget(self.send_button)
        layout.addStretch()

        return panel

    def _build_results_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Результаты"))

        self.results_table = QTableWidget(0, 3)
        self.results_table.setHorizontalHeaderLabels(["Модель", "Ответ", "Выбрать"])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.results_table)

        return panel

    def _build_save_panel(self) -> QWidget:
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        self.save_button = QPushButton("Сохранить")
        self.save_button.clicked.connect(self._on_save_clicked)
        layout.addWidget(self.save_button)
        layout.addStretch()

        return panel

    def load_prompts(self) -> None:
        self.prompts = db.list_prompts(sort_by="created_at", sort_dir="desc")
        self.saved_prompts.blockSignals(True)
        self.saved_prompts.clear()
        self.saved_prompts.addItem("— новый промт —", None)
        for prompt in self.prompts:
            preview = prompt.text.replace("\n", " ")
            if len(preview) > 80:
                preview = preview[:77] + "..."
            label = f"{prompt.created_at[:10]} — {preview}"
            self.saved_prompts.addItem(label, prompt.id)
        self.saved_prompts.blockSignals(False)

    def load_models(self) -> None:
        self.models = load_models()
        self._refresh_status()

    def _refresh_status(self) -> None:
        active = load_active_models()
        self.statusBar().showMessage(
            f"Промтов: {len(self.prompts)} | Моделей: {len(self.models)} | Активных: {len(active)}"
        )

    def _on_saved_prompt_selected(self, index: int) -> None:
        if index <= 0:
            return
        prompt_id = self.saved_prompts.currentData()
        if prompt_id is None:
            return
        prompt = db.get_prompt(int(prompt_id))
        if prompt:
            self.prompt_input.setPlainText(prompt.text)

    def _on_send_clicked(self) -> None:
        self.statusBar().showMessage("Отправка будет реализована на следующем этапе")

    def _on_save_clicked(self) -> None:
        self.statusBar().showMessage("Сохранение будет реализовано на следующем этапе")

    def _clear_results_table(self) -> None:
        self.results_table.setRowCount(0)


def main() -> None:
    db.init_db()
    seed_default_models()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.load_prompts()
    window.load_models()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
