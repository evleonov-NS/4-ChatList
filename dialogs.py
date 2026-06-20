"""Диалоги настроек моделей, программы и истории результатов."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import db
from models import ModelConfig
from prompt_assistant import PromptImprovement
from themes import (
    DEFAULT_FONT_SIZE,
    MAX_FONT_SIZE,
    MIN_FONT_SIZE,
    THEME_DARK,
    THEME_LIGHT,
    get_font_size,
    get_theme,
    inactive_row_brush,
    set_font_size,
    set_theme,
)

APP_NAME = "ChatList"
APP_VERSION = "1.1.0"
APP_DESCRIPTION = (
    "Приложение для отправки одного промта в несколько нейросетей, "
    "сравнения ответов и сохранения лучших результатов."
)

ADAPTATION_LABELS = {
    "code": "Для кода",
    "analysis": "Для анализа",
    "creative": "Для креатива",
}


def _table_cell(text: str) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setToolTip(text)
    return item


def _configure_readable_table(table: QTableWidget, min_row_height: int = 0) -> None:
    table.setWordWrap(True)
    table.setTextElideMode(Qt.TextElideMode.ElideNone)
    table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
    if min_row_height > 0:
        table.verticalHeader().setDefaultSectionSize(min_row_height)
        table.verticalHeader().setMinimumSectionSize(min_row_height)
    table.verticalHeader().setSectionResizeMode(
        QHeaderView.ResizeMode.ResizeToContents
    )


def apply_table_row_heights(
    table: QTableWidget,
    min_row_height: int,
    max_row_height: int | None = None,
) -> None:
    cap = max_row_height if max_row_height is not None else min_row_height
    table.resizeRowsToContents()
    for row_index in range(table.rowCount()):
        height = table.rowHeight(row_index)
        height = max(min_row_height, min(cap, height))
        table.setRowHeight(row_index, height)


def _paint_inactive_row(table: QTableWidget, row_index: int, inactive: QBrush) -> None:
    for col in range(table.columnCount()):
        item = table.item(row_index, col)
        if item is not None:
            item.setBackground(inactive)


class MarkdownViewDialog(QDialog):
    def __init__(self, title: str, markdown: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(720, 520)

        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setMarkdown(markdown)
        browser.setOpenExternalLinks(True)
        layout.addWidget(browser)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.reject)
        layout.addWidget(close_box)


class PromptImproveDialog(QDialog):
    """Панель улучшения промта с вариантами подстановки."""

    improve_requested = pyqtSignal(object)

    def __init__(
        self,
        original: str,
        models: list[ModelConfig],
        parent=None,
        *,
        busy_checker=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI-ассистент — улучшение промта")
        self.setMinimumSize(820, 640)
        self.resize(900, 720)

        self._original = original
        self._models = models
        self._busy_checker = busy_checker
        self._auto_started = False
        self.selected_text: str | None = None

        root = QVBoxLayout(self)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Модель:"))
        self.model_combo = QComboBox()
        for model in models:
            self.model_combo.addItem(model.name, model.id)
        self._select_saved_model()
        controls.addWidget(self.model_combo, stretch=1)
        self.retry_button = QPushButton("Повторить")
        self.retry_button.clicked.connect(self._request_improvement)
        controls.addWidget(self.retry_button)
        root.addLayout(controls)

        self.status_label = QLabel("")
        self.status_label.setObjectName("hintLabel")
        root.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        root.addWidget(self.progress)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        content = QWidget()
        self._content_layout = QVBoxLayout(content)

        self._original_box = self._make_variant_group(
            "Исходный промт",
            original,
            apply_enabled=False,
        )
        self._content_layout.addWidget(self._original_box)

        self._improved_box = self._make_variant_group("Улучшенный промт")
        self._content_layout.addWidget(self._improved_box)

        self._alternatives_container = QVBoxLayout()
        self._content_layout.addLayout(self._alternatives_container)

        self._adaptations_container = QVBoxLayout()
        self._content_layout.addLayout(self._adaptations_container)

        self._content_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.reject)
        root.addWidget(close_box)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._auto_started:
            self._auto_started = True
            self._request_improvement()

    def _select_saved_model(self) -> None:
        raw = db.get_setting("prompt_assistant_model_id", "")
        if not raw:
            return
        try:
            model_id = int(raw)
        except ValueError:
            return
        for index in range(self.model_combo.count()):
            if self.model_combo.itemData(index) == model_id:
                self.model_combo.setCurrentIndex(index)
                return

    def _selected_model(self) -> ModelConfig | None:
        model_id = self.model_combo.currentData()
        if model_id is None:
            return None
        for model in self._models:
            if model.id == int(model_id):
                return model
        return self._models[0] if self._models else None

    def _make_variant_group(
        self,
        title: str,
        text: str = "",
        *,
        apply_enabled: bool = True,
    ) -> QGroupBox:
        group = QGroupBox(title)
        group.setObjectName("stepGroup")
        layout = QVBoxLayout(group)
        editor = QTextEdit()
        editor.setReadOnly(True)
        editor.setPlainText(text)
        editor.setMinimumHeight(72)
        layout.addWidget(editor)

        if apply_enabled:
            apply_btn = QPushButton("Подставить в поле ввода")
            apply_btn.setObjectName("primaryButton")
            apply_btn.clicked.connect(lambda: self._apply_text(editor.toPlainText()))
            layout.addWidget(apply_btn)

        group._editor = editor  # type: ignore[attr-defined]
        return group

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _set_group_text(self, group: QGroupBox, text: str) -> None:
        group._editor.setPlainText(text)  # type: ignore[attr-defined]

    def _request_improvement(self) -> None:
        if self._block_if_busy():
            return
        model = self._selected_model()
        if model is None:
            QMessageBox.warning(self, "Модель", "Нет доступных моделей")
            return
        db.set_setting("prompt_assistant_model_id", str(model.id))
        self.begin_loading(model.name)
        self.improve_requested.emit(model)

    def begin_loading(self, model_name: str) -> None:
        self.progress.show()
        self.retry_button.setEnabled(False)
        self.model_combo.setEnabled(False)
        self.status_label.setText(f"Запрос к модели «{model_name}»…")
        self._set_group_text(self._improved_box, "")
        self._clear_layout(self._alternatives_container)
        self._clear_layout(self._adaptations_container)

    def show_result(self, result: PromptImprovement) -> None:
        self._finish_loading()
        if result.error:
            self.status_label.setText(result.error)
        else:
            self.status_label.setText(f"Готово — модель «{result.model_name}»")

        self._set_group_text(self._improved_box, result.improved)
        self._clear_layout(self._alternatives_container)
        for index, alt in enumerate(result.alternatives, start=1):
            box = self._make_variant_group(f"Вариант {index}")
            self._set_group_text(box, alt)
            self._alternatives_container.addWidget(box)

        self._clear_layout(self._adaptations_container)
        for key, label in ADAPTATION_LABELS.items():
            text = result.adaptations.get(key, "")
            if not text:
                continue
            box = self._make_variant_group(label)
            self._set_group_text(box, text)
            self._adaptations_container.addWidget(box)

    def show_error(self, message: str) -> None:
        self._finish_loading()
        self.status_label.setText(message)
        QMessageBox.warning(self, "Ошибка", message)

    def _finish_loading(self) -> None:
        self.progress.hide()
        self.retry_button.setEnabled(True)
        self.model_combo.setEnabled(True)

    def _worker_busy(self) -> bool:
        if self._busy_checker is None:
            return False
        return bool(self._busy_checker())

    def _block_if_busy(self) -> bool:
        if not self._worker_busy():
            return False
        self.status_label.setText(
            "Подождите завершения запроса к модели или дождитесь таймаута…"
        )
        return True

    def reject(self) -> None:
        if self._block_if_busy():
            return
        super().reject()

    def _apply_text(self, text: str) -> None:
        cleaned = text.strip()
        if not cleaned:
            return
        self.selected_text = cleaned
        self.accept()

    def closeEvent(self, event) -> None:
        if self._block_if_busy():
            event.ignore()
            return
        super().closeEvent(event)


class ModelsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Модели")
        self.setMinimumSize(1100, 520)
        self.resize(1200, 560)

        layout = QVBoxLayout(self)

        controls = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по имени, провайдеру, api_id...")
        self.search_input.textChanged.connect(self.reload)
        controls.addWidget(self.search_input)

        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Имя (А→Я)", ("name", "asc"))
        self.sort_combo.addItem("Имя (Я→А)", ("name", "desc"))
        self.sort_combo.addItem("Провайдер", ("provider", "asc"))
        self.sort_combo.currentIndexChanged.connect(self.reload)
        controls.addWidget(self.sort_combo)
        layout.addLayout(controls)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Имя", "API URL", "API ID", "ENV key", "Провайдер", "Активна"]
        )
        _configure_readable_table(self.table)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(1, 340)
        self.table.setColumnWidth(2, 280)
        self.table.setColumnWidth(3, 180)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._models_context_menu)
        self.table.doubleClicked.connect(self._edit_selected)
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self._add_model)
        edit_btn = QPushButton("Изменить")
        edit_btn.clicked.connect(self._edit_selected)
        delete_btn = QPushButton("Удалить")
        delete_btn.clicked.connect(self._delete_selected)
        buttons.addWidget(add_btn)
        buttons.addWidget(edit_btn)
        buttons.addWidget(delete_btn)
        buttons.addStretch()
        layout.addLayout(buttons)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.reject)
        close_box.accepted.connect(self.accept)
        layout.addWidget(close_box)

        self.reload()

    def reload(self) -> None:
        try:
            self.table.itemChanged.disconnect(self._on_active_toggled)
        except TypeError:
            pass

        sort_by, sort_dir = self.sort_combo.currentData()
        models = db.list_models(
            search=self.search_input.text(),
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        self.table.blockSignals(True)
        self.table.setRowCount(len(models))
        inactive = inactive_row_brush()
        for row_index, model in enumerate(models):
            self.table.setItem(row_index, 0, _table_cell(model.name))
            self.table.setItem(row_index, 1, _table_cell(model.api_url))
            self.table.setItem(row_index, 2, _table_cell(model.api_id))
            self.table.setItem(row_index, 3, _table_cell(model.env_key))
            self.table.setItem(row_index, 4, _table_cell(model.provider))
            active_item = QTableWidgetItem()
            active_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
            )
            active_item.setCheckState(
                Qt.CheckState.Checked if model.is_active else Qt.CheckState.Unchecked
            )
            active_item.setData(Qt.ItemDataRole.UserRole, model.id)
            self.table.setItem(row_index, 5, active_item)
            if not model.is_active:
                _paint_inactive_row(self.table, row_index, inactive)
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(1, max(340, self.table.columnWidth(1)))
        self.table.setColumnWidth(2, max(280, self.table.columnWidth(2)))
        self.table.setColumnWidth(3, max(180, self.table.columnWidth(3)))
        self.table.resizeRowsToContents()
        self.table.blockSignals(False)
        self.table.itemChanged.connect(self._on_active_toggled)

    def _on_active_toggled(self, item: QTableWidgetItem) -> None:
        if item.column() != 5:
            return
        model_id = item.data(Qt.ItemDataRole.UserRole)
        if model_id is None:
            return
        is_active = item.checkState() == Qt.CheckState.Checked
        db.update_model(int(model_id), is_active=is_active)
        self.reload()

    def _models_context_menu(self, position) -> None:
        row = self.table.rowAt(position.y())
        if row < 0:
            return
        item = self.table.item(row, 5)
        if item is None:
            return
        model_id = item.data(Qt.ItemDataRole.UserRole)
        if model_id is None:
            return
        model = db.get_model(int(model_id))
        if model is None:
            return

        menu = QMenu(self)
        if model.is_active:
            toggle = menu.addAction("Снять активность")
        else:
            toggle = menu.addAction("Включить модель")
        edit_action = menu.addAction("Изменить...")
        chosen = menu.exec(self.table.viewport().mapToGlobal(position))
        if chosen == toggle:
            db.update_model(model.id, is_active=not model.is_active)
            self.reload()
        elif chosen == edit_action:
            self.table.selectRow(row)
            self._edit_selected()

    def _selected_model_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 5)
        if item is None:
            return None
        model_id = item.data(Qt.ItemDataRole.UserRole)
        return int(model_id) if model_id is not None else None

    def _add_model(self) -> None:
        data = self._prompt_model_form()
        if not data:
            return
        try:
            is_active = data.pop("is_active")
            db.add_model(is_active=is_active, **data)
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        self.reload()

    def _edit_selected(self) -> None:
        model_id = self._selected_model_id()
        if model_id is None:
            return
        model = db.get_model(model_id)
        if model is None:
            return
        data = self._prompt_model_form(model)
        if not data:
            return
        is_active = data.pop("is_active")
        db.update_model(model_id, is_active=is_active, **data)
        self.reload()

    def _delete_selected(self) -> None:
        model_id = self._selected_model_id()
        if model_id is None:
            return
        answer = QMessageBox.question(
            self,
            "Удаление",
            "Удалить выбранную модель?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        db.delete_model(model_id)
        self.reload()

    def _prompt_model_form(self, model: db.Model | None = None) -> dict | None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Модель")
        dialog.setMinimumWidth(720)
        form = QFormLayout(dialog)
        name = QLineEdit(model.name if model else "")
        api_url = QLineEdit(model.api_url if model else "")
        api_id = QLineEdit(model.api_id if model else "")
        env_key = QLineEdit(model.env_key if model else "OPENROUTER_API_KEY")
        provider = QLineEdit(model.provider if model else "openrouter")
        for field in (name, api_url, api_id, env_key, provider):
            field.setMinimumWidth(540)
        active = QCheckBox("Активна")
        active.setChecked(model.is_active if model else True)
        form.addRow("Имя", name)
        form.addRow("API URL", api_url)
        form.addRow("API ID", api_id)
        form.addRow("ENV key", env_key)
        form.addRow("Провайдер", provider)
        form.addRow("", active)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        if not name.text().strip():
            QMessageBox.warning(self, "Ошибка", "Имя модели обязательно")
            return None
        return {
            "name": name.text().strip(),
            "api_url": api_url.text().strip(),
            "api_id": api_id.text().strip(),
            "env_key": env_key.text().strip(),
            "provider": provider.text().strip() or "openrouter",
            "is_active": active.isChecked(),
        }


class PromptsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Промты")
        self.setMinimumSize(900, 520)
        self.resize(960, 560)

        layout = QVBoxLayout(self)

        controls = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по тексту или тегам...")
        self.search_input.textChanged.connect(self.reload)
        controls.addWidget(self.search_input)

        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Дата (новые)", ("created_at", "desc"))
        self.sort_combo.addItem("Дата (старые)", ("created_at", "asc"))
        self.sort_combo.addItem("Текст (А→Я)", ("text", "asc"))
        self.sort_combo.addItem("Теги (А→Я)", ("tags", "asc"))
        self.sort_combo.currentIndexChanged.connect(self.reload)
        controls.addWidget(self.sort_combo)
        layout.addLayout(controls)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Дата", "Промт", "Теги"])
        _configure_readable_table(self.table)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(1, 480)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._edit_selected)
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self._add_prompt)
        edit_btn = QPushButton("Изменить")
        edit_btn.clicked.connect(self._edit_selected)
        delete_btn = QPushButton("Удалить")
        delete_btn.clicked.connect(self._delete_selected)
        buttons.addWidget(add_btn)
        buttons.addWidget(edit_btn)
        buttons.addWidget(delete_btn)
        buttons.addStretch()
        layout.addLayout(buttons)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.reject)
        close_box.accepted.connect(self.accept)
        layout.addWidget(close_box)

        self.reload()

    def reload(self) -> None:
        sort_by, sort_dir = self.sort_combo.currentData()
        prompts = db.list_prompts(
            search=self.search_input.text(),
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        self.table.setRowCount(len(prompts))
        for row_index, prompt in enumerate(prompts):
            date_item = _table_cell(prompt.created_at)
            date_item.setData(Qt.ItemDataRole.UserRole, prompt.id)
            self.table.setItem(row_index, 0, date_item)

            text_preview = prompt.text.replace("\n", " ")
            text_item = _table_cell(text_preview)
            text_item.setData(Qt.ItemDataRole.UserRole, prompt.id)
            self.table.setItem(row_index, 1, text_item)

            self.table.setItem(row_index, 2, _table_cell(prompt.tags))

        self.table.resizeRowsToContents()

    def _selected_prompt_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        prompt_id = item.data(Qt.ItemDataRole.UserRole)
        return int(prompt_id) if prompt_id is not None else None

    def _prompt_form(self, prompt: db.Prompt | None = None) -> dict | None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Промт")
        dialog.setMinimumWidth(640)
        form = QFormLayout(dialog)
        text = QTextEdit(prompt.text if prompt else "")
        text.setMinimumHeight(120)
        tags = QLineEdit(prompt.tags if prompt else "")
        tags.setMinimumWidth(480)
        form.addRow("Текст", text)
        form.addRow("Теги", tags)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        prompt_text = text.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "Ошибка", "Текст промта обязателен")
            return None
        return {"text": prompt_text, "tags": tags.text().strip()}

    def _add_prompt(self) -> None:
        data = self._prompt_form()
        if not data:
            return
        try:
            db.add_prompt(data["text"], data["tags"])
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        self.reload()

    def _edit_selected(self) -> None:
        prompt_id = self._selected_prompt_id()
        if prompt_id is None:
            QMessageBox.information(self, "Изменить", "Выберите промт")
            return
        prompt = db.get_prompt(prompt_id)
        if prompt is None:
            return
        data = self._prompt_form(prompt)
        if not data:
            return
        db.update_prompt(prompt_id, text=data["text"], tags=data["tags"])
        self.reload()

    def _delete_selected(self) -> None:
        prompt_id = self._selected_prompt_id()
        if prompt_id is None:
            QMessageBox.information(self, "Удалить", "Выберите промт")
            return
        answer = QMessageBox.question(
            self,
            "Удаление",
            "Удалить выбранный промт?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        db.delete_prompt(prompt_id)
        self.reload()


class SettingsDialog(QDialog):
    """Расширенный редактор всех пар key/value в таблице settings."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Расширенные параметры")
        self.setMinimumSize(560, 360)

        layout = QVBoxLayout(self)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по ключу или значению...")
        self.search_input.textChanged.connect(self.reload)
        layout.addWidget(self.search_input)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Ключ", "Значение"])
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self._add_setting)
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self._save_changes)
        delete_btn = QPushButton("Удалить")
        delete_btn.clicked.connect(self._delete_selected)
        buttons.addWidget(add_btn)
        buttons.addWidget(save_btn)
        buttons.addWidget(delete_btn)
        buttons.addStretch()
        layout.addLayout(buttons)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.reject)
        layout.addWidget(close_box)

        self.reload()

    def reload(self) -> None:
        search = self.search_input.text().strip().lower()
        settings = db.list_settings()
        if search:
            settings = [
                (key, value)
                for key, value in settings
                if search in key.lower() or search in value.lower()
            ]
        self.table.setRowCount(len(settings))
        for row_index, (key, value) in enumerate(settings):
            key_item = QTableWidgetItem(key)
            key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row_index, 0, key_item)
            self.table.setItem(row_index, 1, QTableWidgetItem(value))

    def _add_setting(self) -> None:
        key, ok = QInputDialog.getText(self, "Настройка", "Ключ:")
        if not ok or not key.strip():
            return
        value, ok = QInputDialog.getText(self, "Настройка", "Значение:")
        if not ok:
            return
        db.set_setting(key.strip(), value)
        self.reload()

    def _save_changes(self) -> None:
        for row in range(self.table.rowCount()):
            key_item = self.table.item(row, 0)
            value_item = self.table.item(row, 1)
            if key_item is None or value_item is None:
                continue
            db.set_setting(key_item.text(), value_item.text())
        QMessageBox.information(self, "Настройки", "Настройки сохранены")

    def _delete_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        key_item = self.table.item(row, 0)
        if key_item is None:
            return
        db.delete_setting(key_item.text())
        self.reload()


class PreferencesDialog(QDialog):
    """Настройки оформления: тема и размер шрифта."""

    appearance_changed = pyqtSignal(str, int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Светлая", THEME_LIGHT)
        self.theme_combo.addItem("Тёмная", THEME_DARK)
        current_theme = get_theme()
        index = self.theme_combo.findData(current_theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        form.addRow("Тема", self.theme_combo)

        self.font_spin = QSpinBox()
        self.font_spin.setRange(MIN_FONT_SIZE, MAX_FONT_SIZE)
        self.font_spin.setSuffix(" pt")
        self.font_spin.setValue(get_font_size())
        form.addRow("Размер шрифта панелей", self.font_spin)

        hint = QLabel(
            "Тема и размер шрифта сохраняются в базе данных (таблица settings) "
            "и применяются ко всем панелям главного окна."
        )
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)

        layout.addLayout(form)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Сохранить")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self) -> None:
        theme = self.theme_combo.currentData()
        font_size = self.font_spin.value()
        set_theme(str(theme))
        set_font_size(font_size)
        self.appearance_changed.emit(str(theme), font_size)
        self.accept()


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("О программе")
        self.setMinimumSize(520, 420)

        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setMarkdown(
            f"# {APP_NAME}\n\n"
            f"**Версия:** {APP_VERSION}\n\n"
            f"{APP_DESCRIPTION}\n\n"
            "## Возможности\n\n"
            "- отправка промта в несколько моделей OpenRouter;\n"
            "- сравнение ответов и сохранение в SQLite;\n"
            "- AI-ассистент для улучшения промтов;\n"
            "- история, экспорт MD/JSON, настройки темы и шрифта.\n\n"
            "## Стек\n\n"
            "Python · PyQt6 · SQLite · httpx · OpenRouter\n\n"
            "## База данных\n\n"
            "Настройки, промты, модели и результаты хранятся в `chatlist.db`."
        )
        layout.addWidget(browser)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.reject)
        layout.addWidget(close_box)


class ResultsHistoryDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("История результатов")
        self.setMinimumSize(900, 480)

        layout = QVBoxLayout(self)

        controls = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по ответу, модели, промту...")
        self.search_input.textChanged.connect(self.reload)
        controls.addWidget(self.search_input)

        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Дата (новые)", ("created_at", "desc"))
        self.sort_combo.addItem("Дата (старые)", ("created_at", "asc"))
        self.sort_combo.addItem("Модель (А→Я)", ("model_name", "asc"))
        self.sort_combo.currentIndexChanged.connect(self.reload)
        controls.addWidget(self.sort_combo)
        layout.addLayout(controls)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Дата", "Модель", "Промт", "Ответ"])
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        copy_btn = QPushButton("Копировать ответ")
        copy_btn.clicked.connect(self._copy_selected)
        layout.addWidget(copy_btn)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.reject)
        layout.addWidget(close_box)

        self.reload()

    def reload(self) -> None:
        sort_by, sort_dir = self.sort_combo.currentData()
        results = db.list_results(
            search=self.search_input.text(),
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        self.table.setRowCount(len(results))
        for row_index, result in enumerate(results):
            self.table.setItem(
                row_index, 0, QTableWidgetItem(result.created_at)
            )
            self.table.setItem(
                row_index, 1, QTableWidgetItem(result.model_name or "")
            )
            prompt_preview = (result.prompt_text or "").replace("\n", " ")
            if len(prompt_preview) > 100:
                prompt_preview = prompt_preview[:97] + "..."
            self.table.setItem(row_index, 2, QTableWidgetItem(prompt_preview))
            self.table.setItem(
                row_index, 3, QTableWidgetItem(result.response_text)
            )

    def _copy_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 3)
        if item is None:
            return
        from PyQt6.QtWidgets import QApplication

        QApplication.clipboard().setText(item.text())
        QMessageBox.information(self, "Буфер обмена", "Ответ скопирован")
