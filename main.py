import subprocess
import sys
import shutil
from dataclasses import dataclass
from pathlib import Path

import env_config

env_config.load_environment()

from PyQt6.QtCore import QEvent, Qt, QTimer
from PyQt6.QtGui import QAction, QBrush, QColor, QFontMetrics, QGuiApplication
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QDialog,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import db
from dialogs import (
    AboutDialog,
    MarkdownViewDialog,
    ModelsDialog,
    PreferencesDialog,
    PromptImproveDialog,
    PromptsDialog,
    SettingsDialog,
    _configure_readable_table,
    _table_cell,
    apply_table_row_heights,
)
from app_icon import apply_app_icon
from export_utils import ExportRow, export_json, export_markdown
from models import bootstrap_models, load_active_models, load_models, load_ready_models
from network import PromptResult, setup_request_logging
from themes import THEME_DARK, THEME_LIGHT, apply_appearance
from prompt_assistant import PromptImprovement
from prompt_search_ui import PromptSearchPanel, format_prompt_label
from workers import PromptImproveWorker, PromptSendWorker, wait_for_worker

PROMPT_VISIBLE_LINES = 3
RESULT_ROW_LINES = 6
RESULT_ROW_MAX_LINES = 10
TEXT_FRAME_PADDING = 12
CHECK_COLUMN_WIDTH = 56


@dataclass
class TempResult:
    model_name: str
    model_id: int
    response_text: str
    selected: bool = False
    error: str | None = None
    created_at: str = ""
    prompt_text: str = ""
    result_id: int | None = None


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ChatList")
        self.setMinimumSize(960, 720)

        self.prompts: list[db.Prompt] = []
        self.models = load_models()
        self.temp_results: list[TempResult] = []
        self._live_results: list[TempResult] = []
        self.history_mode = False
        self._selected_history: TempResult | None = None
        self.send_worker: PromptSendWorker | None = None
        self.improve_worker: PromptImproveWorker | None = None
        self._improve_dialog: PromptImproveDialog | None = None
        self._current_prompt_id: int | None = None
        self._selected_prompt_label: str = ""

        self._build_menu()
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        layout.addWidget(self._build_prompt_panel())
        layout.addWidget(self._build_actions_panel())
        layout.addWidget(self._build_results_panel(), stretch=1)
        layout.addWidget(self._build_save_panel())

        self.setStatusBar(QStatusBar())
        self._refresh_status()

    def _build_menu(self) -> None:
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        file_menu = QMenu("Файл", self)
        export_md = QAction("Экспорт в Markdown...", self)
        export_md.triggered.connect(lambda: self._export_results("md"))
        export_json = QAction("Экспорт в JSON...", self)
        export_json.triggered.connect(lambda: self._export_results("json"))
        file_menu.addAction(export_md)
        file_menu.addAction(export_json)
        menu_bar.addMenu(file_menu)

        settings_menu = QMenu("Настройки", self)
        preferences_action = QAction("Настройки...", self)
        preferences_action.triggered.connect(self._open_preferences_dialog)
        prompts_action = QAction("Промты...", self)
        prompts_action.triggered.connect(self._open_prompts_dialog)
        models_action = QAction("Модели...", self)
        models_action.triggered.connect(self._open_models_dialog)
        app_settings_action = QAction("Расширенные параметры...", self)
        app_settings_action.triggered.connect(self._open_settings_dialog)
        history_action = QAction("История результатов", self)
        history_action.triggered.connect(self._toggle_history_mode)
        db_viewer_action = QAction("Просмотр базы данных...", self)
        db_viewer_action.triggered.connect(self._launch_test_db)
        settings_menu.addAction(preferences_action)
        settings_menu.addSeparator()
        settings_menu.addAction(prompts_action)
        settings_menu.addAction(models_action)
        settings_menu.addAction(app_settings_action)
        settings_menu.addAction(history_action)
        settings_menu.addSeparator()
        settings_menu.addAction(db_viewer_action)
        menu_bar.addMenu(settings_menu)

        help_menu = QMenu("Справка", self)
        about_action = QAction("О программе...", self)
        about_action.triggered.connect(self._open_about_dialog)
        help_menu.addAction(about_action)
        menu_bar.addMenu(help_menu)

    def _update_font_metrics(self) -> None:
        prompt_line = QFontMetrics(self.prompt_input.font()).lineSpacing()
        self.prompt_input.setFixedHeight(
            prompt_line * PROMPT_VISIBLE_LINES + TEXT_FRAME_PADDING
        )
        self._result_row_height = (
            QFontMetrics(self.results_table.font()).lineSpacing() * RESULT_ROW_LINES
        )
        self._result_row_max_height = (
            QFontMetrics(self.results_table.font()).lineSpacing() * RESULT_ROW_MAX_LINES
        )
        if self.temp_results:
            self._render_results_table()

    def _open_preferences_dialog(self) -> None:
        dialog = PreferencesDialog(self)
        dialog.appearance_changed.connect(self._on_appearance_changed)
        dialog.exec()

    def _on_appearance_changed(self, theme: str, font_size: int) -> None:
        app = QApplication.instance()
        if isinstance(app, QApplication):
            apply_appearance(app, theme=theme, font_size=font_size)
            self._update_font_metrics()
        theme_label = "Светлая" if theme == THEME_LIGHT else "Тёмная"
        self.statusBar().showMessage(
            f"Настройки сохранены: {theme_label} тема, шрифт {font_size} pt",
            4000,
        )

    def _open_about_dialog(self) -> None:
        AboutDialog(self).exec()

    def _style_button(
        self, button: QPushButton, role: str, tooltip: str = ""
    ) -> QPushButton:
        button.setObjectName(f"{role}Button")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            button.setToolTip(tooltip)
        return button

    def _step_group(self, title: str, hint: str) -> tuple[QGroupBox, QVBoxLayout]:
        group = QGroupBox(title)
        group.setObjectName("stepGroup")
        layout = QVBoxLayout(group)
        hint_label = QLabel(hint)
        hint_label.setObjectName("hintLabel")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)
        return group, layout

    def _build_prompt_panel(self) -> QWidget:
        group, layout = self._step_group(
            "1. Запрос",
            "Новый запрос — введите текст в поле ниже. Сохранённый промт — "
            "начните ввод в «Поиск»: откроется список совпадений, кликните по строке для выбора. "
            "Кнопка «Улучшить промт» отправит текст в одну модель и предложит варианты.",
        )

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Поиск:"))
        self.prompt_filter = QLineEdit()
        self.prompt_filter.setPlaceholderText(
            "Слова из текста или тега — список откроется автоматически…"
        )
        self.prompt_filter.setClearButtonEnabled(True)
        self.prompt_filter.textChanged.connect(self._on_prompt_filter_changed)
        search_row.addWidget(self.prompt_filter, stretch=1)
        layout.addLayout(search_row)

        self.prompt_match_label = QLabel("")
        self.prompt_match_label.setObjectName("hintLabel")
        layout.addWidget(self.prompt_match_label)

        self.prompt_search_panel = PromptSearchPanel()
        self.prompt_search_panel.prompt_selected.connect(
            self._on_prompt_search_selected
        )
        layout.addWidget(self.prompt_search_panel)

        prompt_buttons = QHBoxLayout()
        self.prompts_button = self._style_button(
            QPushButton("Промты…"),
            "secondary",
            "Таблица сохранённых промтов: добавление, изменение, удаление",
        )
        self.prompts_button.clicked.connect(self._open_prompts_dialog)
        prompt_buttons.addWidget(self.prompts_button)

        self.db_viewer_button = self._style_button(
            QPushButton("База данных…"),
            "secondary",
            "Открыть test-db.py для просмотра SQLite",
        )
        self.db_viewer_button.clicked.connect(self._launch_test_db)
        prompt_buttons.addWidget(self.db_viewer_button)
        prompt_buttons.addStretch()
        layout.addLayout(prompt_buttons)

        self.prompt_filter.installEventFilter(self)

        tags_row = QHBoxLayout()
        tags_row.addWidget(QLabel("Теги:"))
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("python, api, refactor")
        tags_row.addWidget(self.tags_input)
        layout.addLayout(tags_row)

        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("Введите текст запроса...")
        prompt_line = QFontMetrics(self.prompt_input.font()).lineSpacing()
        self.prompt_input.setFixedHeight(
            prompt_line * PROMPT_VISIBLE_LINES + TEXT_FRAME_PADDING
        )
        layout.addWidget(self.prompt_input)

        improve_row = QHBoxLayout()
        self.improve_prompt_button = self._style_button(
            QPushButton("Улучшить промт"),
            "primary",
            "Отправить промт в модель для улучшения и переформулировки",
        )
        self.improve_prompt_button.clicked.connect(self._on_improve_prompt)
        improve_row.addWidget(self.improve_prompt_button)
        improve_row.addStretch()
        layout.addLayout(improve_row)

        return group

    def _build_actions_panel(self) -> QWidget:
        group, layout = self._step_group(
            "2. Отправка",
            "Проверьте и настройте модели, затем отправьте запрос — "
            "ответы появятся в таблице ниже.",
        )

        buttons = QHBoxLayout()
        self.models_button = self._style_button(
            QPushButton("Модели…"),
            "secondary",
            "Выбор активных нейросетей и проверка API-ключей",
        )
        self.models_button.clicked.connect(self._open_models_dialog)
        buttons.addWidget(self.models_button)

        self.send_button = self._style_button(
            QPushButton("Отправить"),
            "primary",
            "Отправить промт во все активные модели",
        )
        self.send_button.clicked.connect(self._on_send_clicked)
        buttons.addWidget(self.send_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        buttons.addWidget(self.progress_bar, stretch=1)

        buttons.addStretch()
        layout.addLayout(buttons)

        return group

    def _build_results_panel(self) -> QWidget:
        group, layout = self._step_group(
            "3. Ответы",
            "Сравните ответы моделей. Длинный текст обрезается по высоте — "
            "двойной клик откроет полный ответ. «История» — сохранённые результаты из базы.",
        )

        header = QHBoxLayout()
        self.results_title = QLabel("Таблица результатов")
        self.results_title.setObjectName("stepLabel")
        header.addWidget(self.results_title)

        self.history_button = self._style_button(
            QPushButton("История"),
            "toggle",
            "Показать сохранённые ответы из базы (повторное нажатие — вернуться к текущим)",
        )
        self.history_button.setCheckable(True)
        self.history_button.clicked.connect(self._toggle_history_mode)
        header.addWidget(self.history_button)

        self.results_filter = QLineEdit()
        self.results_filter.setPlaceholderText("Поиск в результатах...")
        self.results_filter.textChanged.connect(self._apply_results_filter)
        header.addWidget(self.results_filter, stretch=1)

        self.open_result_button = self._style_button(
            QPushButton("Открыть"),
            "secondary",
            "Просмотр полного ответа в формате Markdown",
        )
        self.open_result_button.clicked.connect(self._open_selected_result)
        header.addWidget(self.open_result_button)
        layout.addLayout(header)

        self.results_table = QTableWidget(0, 3)
        self.results_table.setHorizontalHeaderLabels(["Модель", "Ответ", "Выбрать"])
        self._result_row_height = (
            QFontMetrics(self.results_table.font()).lineSpacing() * RESULT_ROW_LINES
        )
        self._result_row_max_height = (
            QFontMetrics(self.results_table.font()).lineSpacing() * RESULT_ROW_MAX_LINES
        )
        _configure_readable_table(self.results_table, self._result_row_height)
        results_header = self.results_table.horizontalHeader()
        results_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        results_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        results_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.results_table.setColumnWidth(1, 520)
        self.results_table.setColumnWidth(2, CHECK_COLUMN_WIDTH)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.results_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(
            self._results_context_menu
        )
        self.results_table.itemSelectionChanged.connect(self._on_result_row_selected)
        self.results_table.doubleClicked.connect(self._open_selected_result)
        layout.addWidget(self.results_table, stretch=1)

        return group

    def _build_save_panel(self) -> QWidget:
        group, layout = self._step_group(
            "4. Сохранение",
            "Отметьте галочками нужные ответы, сохраните в базу или экспортируйте в файл.",
        )

        buttons = QHBoxLayout()
        self.save_button = self._style_button(
            QPushButton("Сохранить"),
            "primary",
            "Сохранить отмеченные ответы в базу данных",
        )
        self.save_button.clicked.connect(self._on_save_clicked)
        buttons.addWidget(self.save_button)

        export_md_btn = self._style_button(
            QPushButton("Экспорт MD"),
            "secondary",
            "Экспорт выбранных ответов в Markdown-файл",
        )
        export_md_btn.clicked.connect(lambda: self._export_results("md"))
        buttons.addWidget(export_md_btn)

        export_json_btn = self._style_button(
            QPushButton("Экспорт JSON"),
            "secondary",
            "Экспорт выбранных ответов в JSON-файл",
        )
        export_json_btn.clicked.connect(lambda: self._export_results("json"))
        buttons.addWidget(export_json_btn)

        buttons.addStretch()
        layout.addLayout(buttons)

        return group

    def _on_prompt_filter_changed(self) -> None:
        self.load_prompts(show_panel=True)

    def eventFilter(self, watched, event) -> bool:
        if watched is self.prompt_filter:
            if event.type() == QEvent.Type.FocusIn:
                self.load_prompts(show_panel=True)
            elif (
                event.type() == QEvent.Type.KeyPress
                and self.prompt_search_panel.isVisible()
            ):
                key = event.key()
                if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                    self.prompt_search_panel.focus_list()
                    return True
                if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    self.prompt_search_panel.select_current()
                    return True
                if key == Qt.Key.Key_Escape:
                    self.prompt_search_panel.hide_results()
                    return True
        return super().eventFilter(watched, event)

    def _show_prompt_search_panel(self) -> None:
        filter_text = self.prompt_filter.text().strip()
        if not self.prompts:
            self.prompt_search_panel.hide_results()
            return
        self.prompt_search_panel.show_results(
            self.prompts,
            filter_text,
            self.prompt_filter.width(),
        )

    def load_prompts(self, *, show_panel: bool = False) -> None:
        filter_text = self.prompt_filter.text().strip()
        self.prompts = db.list_prompts(
            search=filter_text,
            sort_by="created_at",
            sort_dir="desc",
        )
        total_count = (
            len(db.list_prompts()) if filter_text else len(self.prompts)
        )
        self._update_prompt_filter_hint(filter_text, total_count)
        self._refresh_status(total_count)

        if show_panel and filter_text:
            if self.prompts:
                self._show_prompt_search_panel()
            else:
                self.prompt_search_panel.hide_results()
        elif show_panel and not filter_text and self.prompt_filter.hasFocus():
            if self.prompts:
                self._show_prompt_search_panel()
            else:
                self.prompt_search_panel.hide_results()
        elif not filter_text and not self.prompt_filter.hasFocus():
            self.prompt_search_panel.hide_results()

    def _update_prompt_filter_hint(
        self, filter_text: str, total_count: int
    ) -> None:
        if not filter_text:
            if self._selected_prompt_label:
                self.prompt_match_label.setText(
                    f"Выбран: {self._selected_prompt_label}"
                )
            elif total_count:
                self.prompt_match_label.setText(
                    f"В базе {total_count} сохранённых промтов. "
                    "Кликните «Поиск» — откроется список для выбора."
                )
            else:
                self.prompt_match_label.setText(
                    "Сохранённых промтов пока нет — введите новый текст ниже."
                )
            return
        found = len(self.prompts)
        if found == 0:
            self.prompt_match_label.setText(
                f"По запросу «{filter_text}» ничего не найдено "
                f"(в базе {total_count} промтов)."
            )
        else:
            self.prompt_match_label.setText(
                f"Найдено {found} — совпадения подсвечены, кликните по строке в списке."
            )

    def load_models(self) -> None:
        self.models = load_models()
        self._refresh_status()

    def _refresh_status(self, total_prompts: int | None = None) -> None:
        active = load_active_models()
        ready, _ = load_ready_models()
        filter_text = self.prompt_filter.text().strip()
        if total_prompts is None:
            total_prompts = len(db.list_prompts())
        if filter_text:
            prompt_part = (
                f"Промтов: {len(self.prompts)} из {total_prompts} (поиск)"
            )
        else:
            prompt_part = f"Промтов: {total_prompts}"
        self.statusBar().showMessage(
            f"{prompt_part} | Моделей: {len(self.models)} | "
            f"Активных: {len(active)} | Готовых: {len(ready)}"
        )

    def _apply_prompt(self, prompt: db.Prompt) -> None:
        self._current_prompt_id = prompt.id
        self._selected_prompt_label = format_prompt_label(prompt)
        self.prompt_input.setPlainText(prompt.text)
        self.tags_input.setText(prompt.tags)
        self.prompt_match_label.setText(f"Выбран: {self._selected_prompt_label}")

    def _on_prompt_search_selected(self, prompt_id: int) -> None:
        prompt = db.get_prompt(prompt_id)
        if prompt is None:
            return
        self._apply_prompt(prompt)
        self.prompt_filter.blockSignals(True)
        self.prompt_filter.clear()
        self.prompt_filter.blockSignals(False)
        self.prompt_search_panel.hide_results()
        self.load_prompts()
        self.prompt_input.setFocus()

    def _on_send_clicked(self) -> None:
        prompt_text = self.prompt_input.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "Промт", "Введите текст запроса")
            return

        ready_models, errors = load_ready_models()
        if not ready_models:
            env_config.load_environment()
            ready_models, errors = load_ready_models()
        if not ready_models:
            message = "Нет активных моделей с валидными ключами API."
            if env_config.LOADED_ENV_PATH:
                message += f"\n\nЗагружен .env:\n{env_config.LOADED_ENV_PATH}"
            else:
                message += "\n\nФайл .env не найден. Положите его рядом с программой:"
                for path in env_config.env_file_candidates():
                    message += f"\n  • {path}"
            if errors:
                message += "\n\n" + "\n".join(errors)
            QMessageBox.warning(self, "Модели", message)
            return

        self._exit_history_mode()
        self._clear_temp_results()
        self._live_results.clear()
        self.send_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.progress_bar.show()
        self.statusBar().showMessage(f"Отправка в {len(ready_models)} моделей...")

        self.send_worker = PromptSendWorker(ready_models, prompt_text, parent=self)
        self.send_worker.finished.connect(self._on_send_finished)
        self.send_worker.failed.connect(self._on_send_failed)
        self.send_worker.start()

    def _on_send_finished(self, results: list) -> None:
        self.progress_bar.hide()
        self.send_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.send_worker = None

        for item in results:
            assert isinstance(item, PromptResult)
            text = item.response_text if item.is_success else f"[{item.error}]"
            self.temp_results.append(
                TempResult(
                    model_name=item.model_name,
                    model_id=item.model_id,
                    response_text=text,
                    error=item.error,
                )
            )
        self._render_results_table()
        success_count = sum(1 for row in self.temp_results if row.error is None)
        self.statusBar().showMessage(
            f"Получено ответов: {success_count}/{len(self.temp_results)}"
        )

    def _on_send_failed(self, message: str) -> None:
        self.progress_bar.hide()
        self.send_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.send_worker = None
        QMessageBox.critical(self, "Ошибка отправки", message)

    def _on_save_clicked(self) -> None:
        selected = [row for row in self.temp_results if row.selected]
        if not selected:
            QMessageBox.information(
                self, "Сохранение", "Отметьте хотя бы один результат"
            )
            return

        prompt_text = self.prompt_input.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "Сохранение", "Промт не может быть пустым")
            return

        tags = self.tags_input.text().strip()
        prompt_id = self._resolve_prompt_id(prompt_text, tags)

        saved = 0
        for row in selected:
            if row.error is not None:
                continue
            db.add_result(row.model_id, row.response_text, prompt_id=prompt_id)
            saved += 1

        if saved == 0:
            QMessageBox.warning(
                self, "Сохранение", "Нет успешных ответов для сохранения"
            )
            return

        self._clear_temp_results()
        self._live_results.clear()
        self._exit_history_mode()
        self.load_prompts()
        if self.history_mode:
            self._load_history_into_results()
        QMessageBox.information(
            self, "Сохранение", f"Сохранено результатов: {saved}"
        )
        self._refresh_status()

    def _resolve_prompt_id(self, prompt_text: str, tags: str) -> int:
        if self._current_prompt_id is not None:
            existing = db.get_prompt(self._current_prompt_id)
            if existing and existing.text == prompt_text:
                if tags != existing.tags:
                    db.update_prompt_tags(self._current_prompt_id, tags)
                return self._current_prompt_id
        return db.add_prompt(prompt_text, tags)

    def _clear_temp_results(self) -> None:
        self.temp_results.clear()
        self.results_table.setRowCount(0)

    def _render_results_table(self) -> None:
        search = self.results_filter.text().strip().lower()
        rows = self.temp_results
        if search:
            rows = [
                row
                for row in rows
                if search in row.model_name.lower()
                or search in row.response_text.lower()
                or search in row.created_at.lower()
                or search in row.prompt_text.lower()
            ]

        self.results_table.blockSignals(True)
        if self.history_mode:
            self._setup_history_columns()
            self.results_table.setRowCount(len(rows))
            for row_index, row in enumerate(rows):
                date_item = _table_cell(row.created_at)
                date_item.setData(Qt.ItemDataRole.UserRole, row.result_id)
                self.results_table.setItem(row_index, 0, date_item)

                model_item = _table_cell(row.model_name)
                model_item.setData(Qt.ItemDataRole.UserRole, row.model_id)
                self.results_table.setItem(row_index, 1, model_item)

                answer_item = _table_cell(row.response_text)
                self.results_table.setItem(row_index, 2, answer_item)

                self._set_result_checkbox(
                    row_index, 3, row.result_id, row.selected
                )
        else:
            self._setup_live_columns()
            self.results_table.setRowCount(len(rows))
            for row_index, row in enumerate(rows):
                model_item = _table_cell(row.model_name)
                model_item.setData(Qt.ItemDataRole.UserRole, row.model_id)
                self.results_table.setItem(row_index, 0, model_item)
                answer_item = _table_cell(row.response_text)
                if row.error:
                    answer_item.setForeground(QBrush(QColor("#C0392B")))
                self.results_table.setItem(row_index, 1, answer_item)

                self._set_result_checkbox(
                    row_index, 2, row.model_id, row.selected
                )

        check_col = 3 if self.history_mode else 2
        self.results_table.setColumnWidth(check_col, CHECK_COLUMN_WIDTH)

        apply_table_row_heights(
            self.results_table,
            self._result_row_height,
            self._result_row_max_height,
        )
        self.results_table.blockSignals(False)

    def _set_result_checkbox(
        self,
        row_index: int,
        column: int,
        result_key: int,
        selected: bool,
    ) -> None:
        checkbox = QCheckBox()
        checkbox.setChecked(selected)
        checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        checkbox.setProperty("result_key", result_key)
        checkbox.stateChanged.connect(self._on_result_checkbox_changed)

        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(4, 6, 4, 4)
        layout.setSpacing(0)
        layout.addWidget(
            checkbox,
            alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        )
        layout.addStretch()
        self.results_table.setCellWidget(row_index, column, wrapper)

    def _on_result_checkbox_changed(self, state: int) -> None:
        checkbox = self.sender()
        if not isinstance(checkbox, QCheckBox):
            return
        key = checkbox.property("result_key")
        if key is None:
            return
        selected = Qt.CheckState(state) == Qt.CheckState.Checked
        key = int(key)
        for row in self.temp_results:
            if self.history_mode:
                if row.result_id == key:
                    row.selected = selected
                    break
            elif row.model_id == key:
                row.selected = selected
                break

    def _setup_live_columns(self) -> None:
        if self.results_table.columnCount() == 3:
            return
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Модель", "Ответ", "Выбрать"])
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.results_table.setColumnWidth(2, CHECK_COLUMN_WIDTH)

    def _setup_history_columns(self) -> None:
        if self.results_table.columnCount() == 4:
            return
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(
            ["Дата", "Модель", "Ответ", "Выбрать"]
        )
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.results_table.setColumnWidth(3, CHECK_COLUMN_WIDTH)

    def _apply_results_filter(self) -> None:
        if self.history_mode:
            self._load_history_into_results()
        elif self.temp_results:
            self._render_results_table()

    def _results_context_menu(self, position) -> None:
        row = self.results_table.rowAt(position.y())
        if row < 0:
            return
        model_col = 1 if self.history_mode else 0
        model_item = self.results_table.item(row, model_col)
        if model_item is None:
            return
        model_id = model_item.data(Qt.ItemDataRole.UserRole)
        model_name = model_item.text()
        if model_id is None:
            return

        menu = QMenu(self)
        open_action = menu.addAction("Открыть ответ")
        copy_action = menu.addAction("Копировать ответ")
        deactivate_action = None
        if not self.history_mode:
            menu.addSeparator()
            deactivate_action = menu.addAction("Снять активность модели")
        chosen = menu.exec(self.results_table.viewport().mapToGlobal(position))
        if chosen == open_action:
            self._open_result_row(row)
        elif chosen == copy_action:
            self._copy_result_text(row)
        elif deactivate_action is not None and chosen == deactivate_action:
            db.update_model(int(model_id), is_active=False)
            self.load_models()
            self.statusBar().showMessage(f"Модель «{model_name}» отключена", 4000)

    def _open_selected_result(self) -> None:
        row = self.results_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Открыть", "Выберите строку с ответом")
            return
        self._open_result_row(row)

    def _toggle_history_mode(self) -> None:
        if self.history_mode:
            self._exit_history_mode()
            self.temp_results = list(self._live_results)
            self._render_results_table()
            self.save_button.setEnabled(bool(self._live_results))
            self.statusBar().showMessage("Текущие результаты", 3000)
            return
        self._live_results = list(self.temp_results)
        self.history_mode = True
        self.history_button.setChecked(True)
        self.history_button.setText("История ✓")
        self.results_title.setText("Сохранённые ответы")
        self.results_filter.setPlaceholderText("Поиск по сохранённым...")
        self.save_button.setEnabled(False)
        self._load_history_into_results()
        self.statusBar().showMessage(
            f"Сохранённых результатов: {len(self.temp_results)}"
        )

    def _exit_history_mode(self) -> None:
        if not self.history_mode:
            self.history_button.setChecked(False)
            return
        self.history_mode = False
        self.history_button.setChecked(False)
        self.history_button.setText("История")
        self.results_title.setText("Таблица результатов")
        self.results_filter.setPlaceholderText("Поиск в результатах...")
        self._selected_history = None

    def _load_history_into_results(self) -> None:
        records = db.list_results(
            search=self.results_filter.text(),
            sort_by="created_at",
            sort_dir="desc",
        )
        self.temp_results = [
            TempResult(
                model_name=result.model_name or "—",
                model_id=result.model_id,
                response_text=result.response_text,
                created_at=result.created_at,
                prompt_text=result.prompt_text or "",
                result_id=result.id,
            )
            for result in records
        ]
        self._render_results_table()

    def _result_by_table_row(self, row: int) -> TempResult | None:
        search = self.results_filter.text().strip().lower()
        rows = self.temp_results
        if search:
            rows = [
                item
                for item in rows
                if search in item.model_name.lower()
                or search in item.response_text.lower()
                or search in item.created_at.lower()
                or search in item.prompt_text.lower()
            ]
        if row < 0 or row >= len(rows):
            return None
        return rows[row]

    def _on_result_row_selected(self) -> None:
        if not self.history_mode:
            return
        row = self.results_table.currentRow()
        result = self._result_by_table_row(row)
        if result is None:
            return
        self._selected_history = result
        if result.prompt_text:
            self.prompt_input.setPlainText(result.prompt_text)

    def _open_markdown(
        self, title: str, prompt_text: str, answer_text: str
    ) -> None:
        markdown = (
            f"# {title}\n\n"
            f"## Промт\n\n{prompt_text or '—'}\n\n"
            f"## Ответ\n\n{answer_text}"
        )
        dialog = MarkdownViewDialog(title, markdown, self)
        dialog.exec()

    def _open_result_row(self, row: int) -> None:
        if self.history_mode:
            result = self._result_by_table_row(row)
            if result is None:
                return
            self._open_markdown(
                result.model_name,
                result.prompt_text,
                result.response_text,
            )
            return
        model_item = self.results_table.item(row, 0)
        answer_item = self.results_table.item(row, 1)
        if model_item is None or answer_item is None:
            return
        model_name = model_item.text()
        answer_text = answer_item.text()
        prompt_text = self.prompt_input.toPlainText().strip()
        self._open_markdown(model_name, prompt_text, answer_text)

    def _copy_result_text(self, row: int | None = None) -> None:
        if row is None:
            row = self.results_table.currentRow()
        if row < 0:
            return
        answer_col = 2 if self.history_mode else 1
        item = self.results_table.item(row, answer_col)
        if item is None:
            return
        QGuiApplication.clipboard().setText(item.text())
        self.statusBar().showMessage("Ответ скопирован в буфер обмена", 3000)

    def _selected_export_rows(self) -> list[ExportRow]:
        rows = [row for row in self.temp_results if row.selected] or self.temp_results
        return [
            ExportRow(
                model_name=row.model_name,
                response_text=row.response_text,
                error=row.error,
            )
            for row in rows
        ]

    def _export_results(self, fmt: str) -> None:
        if not self.temp_results:
            QMessageBox.information(self, "Экспорт", "Нет результатов для экспорта")
            return
        prompt_text = self.prompt_input.toPlainText().strip()
        rows = self._selected_export_rows()
        if fmt == "md":
            content = export_markdown(prompt_text, rows)
            default_name = "chatlist-export.md"
            filter_str = "Markdown (*.md)"
        else:
            content = export_json(prompt_text, rows)
            default_name = "chatlist-export.json"
            filter_str = "JSON (*.json)"

        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт", default_name, filter_str
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as file:
            file.write(content)
        self.statusBar().showMessage(f"Экспортировано: {path}", 5000)

    def _open_models_dialog(self) -> None:
        dialog = ModelsDialog(self)
        dialog.exec()
        self.load_models()

    def _open_prompts_dialog(self) -> None:
        dialog = PromptsDialog(self)
        dialog.exec()
        self.load_prompts()

    def _improve_worker_busy(self) -> bool:
        return self.improve_worker is not None and self.improve_worker.isRunning()

    def _stop_improve_worker(self) -> None:
        if self.improve_worker is None:
            return
        worker = self.improve_worker
        self.improve_worker = None
        try:
            worker.finished.disconnect()
        except TypeError:
            pass
        try:
            worker.failed.disconnect()
        except TypeError:
            pass
        wait_for_worker(worker)
        worker.deleteLater()

    def _start_improve_worker(
        self,
        dialog: PromptImproveDialog,
        model,
        prompt_text: str,
    ) -> None:
        if self._improve_worker_busy():
            return
        self._stop_improve_worker()
        self.improve_worker = PromptImproveWorker(model, prompt_text, parent=self)
        self.improve_worker.finished.connect(
            lambda result: self._on_improve_worker_finished(dialog, result)
        )
        self.improve_worker.failed.connect(
            lambda message: self._on_improve_worker_failed(dialog, message)
        )
        self.improve_worker.start()

    def _on_improve_worker_finished(
        self, dialog: PromptImproveDialog, result: object
    ) -> None:
        if self.improve_worker is not None:
            wait_for_worker(self.improve_worker, 5000)
            self.improve_worker.deleteLater()
            self.improve_worker = None
        if dialog is not self._improve_dialog:
            return
        assert isinstance(result, PromptImprovement)
        dialog.show_result(result)

    def _on_improve_worker_failed(
        self, dialog: PromptImproveDialog, message: str
    ) -> None:
        if self.improve_worker is not None:
            wait_for_worker(self.improve_worker, 5000)
            self.improve_worker.deleteLater()
            self.improve_worker = None
        if dialog is not self._improve_dialog:
            return
        dialog.show_error(message)

    def _on_improve_prompt(self) -> None:
        prompt_text = self.prompt_input.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(
                self, "Улучшить промт", "Введите текст запроса для улучшения"
            )
            return

        ready_models, errors = load_ready_models()
        if not ready_models:
            env_config.load_environment()
            ready_models, errors = load_ready_models()
        if not ready_models:
            message = "Нет активных моделей с валидными ключами API."
            if errors:
                message += "\n\n" + "\n".join(errors)
            QMessageBox.warning(self, "Модели", message)
            return

        self._stop_improve_worker()
        dialog = PromptImproveDialog(
            prompt_text,
            ready_models,
            self,
            busy_checker=self._improve_worker_busy,
        )
        self._improve_dialog = dialog
        dialog.improve_requested.connect(
            lambda model: self._start_improve_worker(dialog, model, prompt_text)
        )
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        self._improve_dialog = None
        self._stop_improve_worker()
        if not accepted:
            return
        if dialog.selected_text:
            self.prompt_input.setPlainText(dialog.selected_text)
            self.statusBar().showMessage("Промт подставлен из AI-ассистента", 3000)

    def _launch_test_db(self) -> None:
        db_path = db.get_db_path()
        if not db_path.is_file():
            db.init_db(db_path)

        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).resolve().parent
            python = shutil.which("python") or shutil.which("python3")
        else:
            base_dir = Path(__file__).resolve().parent
            python = sys.executable

        script = base_dir / "test-db.py"
        if not script.is_file():
            QMessageBox.warning(
                self,
                "База данных",
                f"Не найден файл test-db.py:\n{script}",
            )
            return
        if python is None:
            QMessageBox.warning(
                self,
                "База данных",
                "Не найден интерпретатор Python для запуска test-db.py",
            )
            return

        try:
            subprocess.Popen(
                [python, str(script), str(db_path.resolve())],
                cwd=str(base_dir),
            )
        except OSError as exc:
            QMessageBox.critical(
                self,
                "База данных",
                f"Не удалось запустить test-db.py:\n{exc}",
            )
            return
        self.statusBar().showMessage(f"Запущен просмотр базы: {db_path.name}", 4000)

    def _open_settings_dialog(self) -> None:
        dialog = SettingsDialog(self)
        dialog.exec()

    def closeEvent(self, event) -> None:
        if self.send_worker is not None and self.send_worker.isRunning():
            self.statusBar().showMessage(
                "Дождитесь завершения отправки промта…",
                5000,
            )
            event.ignore()
            return
        if self._improve_worker_busy():
            self.statusBar().showMessage(
                "Дождитесь завершения улучшения промта…",
                5000,
            )
            event.ignore()
            return
        if self.send_worker is not None:
            wait_for_worker(self.send_worker)
            self.send_worker.deleteLater()
            self.send_worker = None
        self._stop_improve_worker()
        super().closeEvent(event)


def main() -> None:
    env_config.load_environment()
    db.init_db()
    setup_request_logging()
    bootstrap_messages = bootstrap_models()
    if not db.get_setting("request_timeout"):
        db.set_setting("request_timeout", "60")
    if not db.get_setting("theme"):
        db.set_setting("theme", THEME_LIGHT)
    if not db.get_setting("font_size"):
        db.set_setting("font_size", "10")

    app = QApplication(sys.argv)
    apply_appearance(app)
    window = MainWindow()
    apply_app_icon(app, window)
    window._update_font_metrics()
    window.load_prompts()
    window.load_models()
    window.show()
    QTimer.singleShot(0, window.prompt_input.setFocus)
    if bootstrap_messages:
        window.statusBar().showMessage(
            "Отключены модели без ключей: "
            + "; ".join(bootstrap_messages[:3])
            + ("..." if len(bootstrap_messages) > 3 else ""),
            10000,
        )
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
