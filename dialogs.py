"""Диалоги настроек моделей, программы и истории результатов."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
)

import db
from themes import inactive_row_brush


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


def apply_table_row_heights(table: QTableWidget, min_row_height: int) -> None:
    table.resizeRowsToContents()
    for row_index in range(table.rowCount()):
        table.setRowHeight(
            row_index,
            max(min_row_height, table.rowHeight(row_index)),
        )


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


class SettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки программы")
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
