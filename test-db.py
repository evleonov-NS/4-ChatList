"""Тестовый просмотр SQLite: список таблиц и CRUD с пагинацией."""

from __future__ import annotations

import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app_icon import apply_app_icon
from dialogs import _configure_readable_table, _table_cell
from themes import DEFAULT_FONT_SIZE, THEME_LIGHT, _build_stylesheet

PAGE_SIZE = 50


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


@contextmanager
def open_database(path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_user_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name COLLATE NOCASE
        """
    ).fetchall()
    return [row["name"] for row in rows]


def table_columns(conn: sqlite3.Connection, table: str) -> list[sqlite3.Row]:
    return conn.execute(f"PRAGMA table_info({quote_ident(table)})").fetchall()


def primary_key_columns(columns: list[sqlite3.Row]) -> list[str]:
    return [col["name"] for col in columns if col["pk"]]


def _style_button(button: QPushButton, role: str, tooltip: str = "") -> QPushButton:
    button.setObjectName(f"{role}Button")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    if tooltip:
        button.setToolTip(tooltip)
    return button


def _step_group(title: str, hint: str) -> tuple[QGroupBox, QVBoxLayout]:
    group = QGroupBox(title)
    group.setObjectName("stepGroup")
    layout = QVBoxLayout(group)
    hint_label = QLabel(hint)
    hint_label.setObjectName("hintLabel")
    hint_label.setWordWrap(True)
    layout.addWidget(hint_label)
    return group, layout


class RowFormDialog(QDialog):
    """Форма добавления или редактирования строки таблицы."""

    def __init__(
        self,
        table: str,
        columns: list[sqlite3.Row],
        values: dict[str, object] | None = None,
        *,
        edit_mode: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{'Изменить' if edit_mode else 'Добавить'} — {table}")
        self.setMinimumWidth(560)
        self._columns = columns
        self._fields: dict[str, QWidget] = {}

        layout = QVBoxLayout(self)
        form = QFormLayout()
        pk_names = set(primary_key_columns(columns))

        for col in columns:
            name = col["name"]
            label = name
            if col["pk"]:
                label += " (PK)"
            if col["notnull"]:
                label += " *"

            if edit_mode and name in pk_names:
                field: QWidget = QLineEdit(str(values.get(name, "")) if values else "")
                field.setEnabled(False)
            elif not edit_mode and name in pk_names and _is_autoincrement_pk(col, columns):
                field = QLineEdit()
                field.setPlaceholderText("авто")
                field.setEnabled(False)
            elif _is_long_text_column(col):
                text_edit = QTextEdit()
                text_edit.setPlainText(str(values.get(name, "")) if values else "")
                text_edit.setFixedHeight(80)
                field = text_edit
            else:
                field = QLineEdit(str(values.get(name, "")) if values else "")

            field.setMinimumWidth(420)
            self._fields[name] = field
            form.addRow(label, field)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> dict[str, object | None]:
        result: dict[str, object | None] = {}
        pk_names = set(primary_key_columns(self._columns))
        for col in self._columns:
            name = col["name"]
            field = self._fields[name]
            if isinstance(field, QTextEdit):
                text = field.toPlainText()
            elif isinstance(field, QLineEdit) and not field.isEnabled():
                if not field.text().strip() and name in pk_names:
                    result[name] = None
                    continue
                text = field.text()
            else:
                assert isinstance(field, QLineEdit)
                text = field.text()

            if not text.strip():
                if col["notnull"] and not (
                    name in pk_names and _is_autoincrement_pk(col, self._columns)
                ):
                    raise ValueError(f"Поле «{name}» обязательно")
                result[name] = None
            else:
                result[name] = text.strip()
        return result


def _is_autoincrement_pk(col: sqlite3.Row, columns: list[sqlite3.Row]) -> bool:
    if not col["pk"]:
        return False
    type_name = (col["type"] or "").upper()
    if "INT" not in type_name:
        return False
    pk_cols = primary_key_columns(columns)
    return len(pk_cols) == 1 and pk_cols[0] == col["name"]


def _is_long_text_column(col: sqlite3.Row) -> bool:
    type_name = (col["type"] or "").upper()
    return "TEXT" in type_name or "BLOB" in type_name or type_name == ""


class TableBrowserDialog(QDialog):
    """Просмотр таблицы с пагинацией и CRUD."""

    def __init__(
        self,
        db_path: Path,
        table: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.db_path = db_path
        self.table = table
        self.page = 0
        self.total_rows = 0

        self.setWindowTitle(f"Таблица — {table}")
        self.setMinimumSize(960, 560)
        self.resize(1024, 620)

        layout = QVBoxLayout(self)

        info = QLabel(f"Файл: {db_path}  |  Таблица: {table}")
        info.setObjectName("hintLabel")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по текстовым колонкам...")
        self.search_input.textChanged.connect(self._reset_page_and_reload)
        layout.addWidget(self.search_input)

        self.table_widget = QTableWidget(0, 0)
        _configure_readable_table(self.table_widget)
        self.table_widget.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_widget.doubleClicked.connect(self._edit_selected)
        layout.addWidget(self.table_widget, stretch=1)

        pager = QHBoxLayout()
        self.prev_button = _style_button(
            QPushButton("← Назад"), "secondary", "Предыдущая страница"
        )
        self.prev_button.clicked.connect(self._prev_page)
        pager.addWidget(self.prev_button)

        self.page_label = QLabel("")
        self.page_label.setObjectName("stepLabel")
        pager.addWidget(self.page_label)

        self.next_button = _style_button(
            QPushButton("Вперёд →"), "secondary", "Следующая страница"
        )
        self.next_button.clicked.connect(self._next_page)
        pager.addWidget(self.next_button)
        pager.addStretch()
        layout.addLayout(pager)

        crud = QHBoxLayout()
        add_btn = _style_button(
            QPushButton("Добавить"), "primary", "Создать новую строку"
        )
        add_btn.clicked.connect(self._add_row)
        edit_btn = _style_button(
            QPushButton("Изменить"), "secondary", "Редактировать выбранную строку"
        )
        edit_btn.clicked.connect(self._edit_selected)
        delete_btn = _style_button(
            QPushButton("Удалить"), "secondary", "Удалить выбранную строку"
        )
        delete_btn.clicked.connect(self._delete_selected)
        crud.addWidget(add_btn)
        crud.addWidget(edit_btn)
        crud.addWidget(delete_btn)
        crud.addStretch()
        layout.addLayout(crud)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.reject)
        layout.addWidget(close_box)

        self._columns: list[sqlite3.Row] = []
        self._pk_columns: list[str] = []
        self._display_columns: list[str] = []
        self.reload()

    def _with_connection(self):
        return open_database(self.db_path)

    def _load_schema(self) -> None:
        with self._with_connection() as conn:
            self._columns = table_columns(conn, self.table)
        self._pk_columns = primary_key_columns(self._columns)
        self._display_columns = ["__rowid__", *[col["name"] for col in self._columns]]

    def reload(self) -> None:
        if not self._columns:
            self._load_schema()

        search = self.search_input.text().strip()
        offset = self.page * PAGE_SIZE

        with self._with_connection() as conn:
            where_sql, params = self._build_search_clause(search)
            table_sql = quote_ident(self.table)
            count_row = conn.execute(
                f"SELECT COUNT(*) AS cnt FROM {table_sql}{where_sql}",
                params,
            ).fetchone()
            self.total_rows = int(count_row["cnt"]) if count_row else 0

            order = self._order_clause()
            query = (
                f"SELECT rowid AS __rowid__, * FROM {table_sql}"
                f"{where_sql} ORDER BY {order} LIMIT ? OFFSET ?"
            )
            rows = conn.execute(query, [*params, PAGE_SIZE, offset]).fetchall()

        self._render_table(rows)
        self._update_pager()

    def _order_clause(self) -> str:
        if self._pk_columns:
            return ", ".join(quote_ident(name) for name in self._pk_columns)
        return "rowid"

    def _build_search_clause(self, search: str) -> tuple[str, list[str]]:
        if not search:
            return "", []
        text_columns = [
            col["name"]
            for col in self._columns
            if _is_long_text_column(col) or "CHAR" in (col["type"] or "").upper()
        ]
        if not text_columns:
            text_columns = [col["name"] for col in self._columns]
        if not text_columns:
            return "", []

        pattern = f"%{search}%"
        parts = [f"CAST({quote_ident(name)} AS TEXT) LIKE ?" for name in text_columns]
        params = [pattern] * len(text_columns)
        return f" WHERE ({' OR '.join(parts)})", params

    def _render_table(self, rows: list[sqlite3.Row]) -> None:
        col_names = [col["name"] for col in self._columns]
        self.table_widget.setColumnCount(len(col_names))
        self.table_widget.setHorizontalHeaderLabels(col_names)
        self.table_widget.setRowCount(len(rows))

        header = self.table_widget.horizontalHeader()
        for index in range(len(col_names)):
            if index == 0:
                header.setSectionResizeMode(index, QHeaderView.ResizeMode.ResizeToContents)
            elif index == len(col_names) - 1:
                header.setSectionResizeMode(index, QHeaderView.ResizeMode.Stretch)
            else:
                header.setSectionResizeMode(index, QHeaderView.ResizeMode.Interactive)

        for row_index, row in enumerate(rows):
            rowid = row["__rowid__"]
            for col_index, name in enumerate(col_names):
                value = row[name]
                text = "" if value is None else str(value)
                item = _table_cell(text)
                item.setData(Qt.ItemDataRole.UserRole, rowid)
                if col_index == 0:
                    item.setData(Qt.ItemDataRole.UserRole + 1, name)
                self.table_widget.setItem(row_index, col_index, item)

        self.table_widget.resizeColumnsToContents()
        if col_names:
            self.table_widget.setColumnWidth(
                len(col_names) - 1,
                max(240, self.table_widget.columnWidth(len(col_names) - 1)),
            )

    def _update_pager(self) -> None:
        total_pages = max(1, (self.total_rows + PAGE_SIZE - 1) // PAGE_SIZE)
        if self.page >= total_pages:
            self.page = max(0, total_pages - 1)
        shown_from = self.total_rows and self.page * PAGE_SIZE + 1
        shown_to = min((self.page + 1) * PAGE_SIZE, self.total_rows)
        self.page_label.setText(
            f"Страница {self.page + 1} из {total_pages}  "
            f"({shown_from}–{shown_to} из {self.total_rows})"
        )
        self.prev_button.setEnabled(self.page > 0)
        self.next_button.setEnabled((self.page + 1) * PAGE_SIZE < self.total_rows)

    def _reset_page_and_reload(self) -> None:
        self.page = 0
        self.reload()

    def _prev_page(self) -> None:
        if self.page > 0:
            self.page -= 1
            self.reload()

    def _next_page(self) -> None:
        if (self.page + 1) * PAGE_SIZE < self.total_rows:
            self.page += 1
            self.reload()

    def _selected_rowid(self) -> int | None:
        row = self.table_widget.currentRow()
        if row < 0:
            return None
        item = self.table_widget.item(row, 0)
        if item is None:
            return None
        rowid = item.data(Qt.ItemDataRole.UserRole)
        return int(rowid) if rowid is not None else None

    def _row_values_by_rowid(self, rowid: int) -> dict[str, object]:
        table_sql = quote_ident(self.table)
        with self._with_connection() as conn:
            row = conn.execute(
                f"SELECT * FROM {table_sql} WHERE rowid = ?",
                (rowid,),
            ).fetchone()
        if row is None:
            raise ValueError("Строка не найдена")
        return {col["name"]: row[col["name"]] for col in self._columns}

    def _add_row(self) -> None:
        dialog = RowFormDialog(self.table, self._columns, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            values = dialog.values()
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return

        columns = []
        placeholders = []
        insert_values = []
        pk_names = set(self._pk_columns)
        for col in self._columns:
            name = col["name"]
            value = values.get(name)
            if value is None:
                if name in pk_names and _is_autoincrement_pk(col, self._columns):
                    continue
                if value is None and not col["notnull"]:
                    columns.append(quote_ident(name))
                    placeholders.append("?")
                    insert_values.append(None)
                continue
            columns.append(quote_ident(name))
            placeholders.append("?")
            insert_values.append(value)

        if not columns:
            QMessageBox.warning(self, "Ошибка", "Нет данных для вставки")
            return

        table_sql = quote_ident(self.table)
        sql = (
            f"INSERT INTO {table_sql} ({', '.join(columns)}) "
            f"VALUES ({', '.join(placeholders)})"
        )
        try:
            with self._with_connection() as conn:
                conn.execute(sql, insert_values)
        except sqlite3.Error as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        self.reload()

    def _edit_selected(self) -> None:
        rowid = self._selected_rowid()
        if rowid is None:
            QMessageBox.information(self, "Изменить", "Выберите строку")
            return
        try:
            current = self._row_values_by_rowid(rowid)
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return

        dialog = RowFormDialog(
            self.table,
            self._columns,
            current,
            edit_mode=True,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            values = dialog.values()
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return

        assignments = []
        update_values = []
        pk_names = set(self._pk_columns)
        for col in self._columns:
            name = col["name"]
            if name in pk_names:
                continue
            assignments.append(f"{quote_ident(name)} = ?")
            update_values.append(values.get(name))

        if not assignments:
            QMessageBox.information(self, "Изменить", "Нет редактируемых полей")
            return

        table_sql = quote_ident(self.table)
        where_sql, where_values = self._where_clause(current, rowid)
        sql = f"UPDATE {table_sql} SET {', '.join(assignments)}{where_sql}"
        try:
            with self._with_connection() as conn:
                conn.execute(sql, [*update_values, *where_values])
        except sqlite3.Error as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        self.reload()

    def _delete_selected(self) -> None:
        rowid = self._selected_rowid()
        if rowid is None:
            QMessageBox.information(self, "Удалить", "Выберите строку")
            return
        answer = QMessageBox.question(
            self,
            "Удаление",
            "Удалить выбранную строку?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            current = self._row_values_by_rowid(rowid)
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return

        table_sql = quote_ident(self.table)
        where_sql, where_values = self._where_clause(current, rowid)
        sql = f"DELETE FROM {table_sql}{where_sql}"
        try:
            with self._with_connection() as conn:
                conn.execute(sql, where_values)
        except sqlite3.Error as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        if self.page > 0 and self.page * PAGE_SIZE >= self.total_rows - 1:
            self.page -= 1
        self.reload()

    def _where_clause(
        self, row_values: dict[str, object], rowid: int
    ) -> tuple[str, list[object]]:
        if self._pk_columns:
            parts = [f"{quote_ident(name)} = ?" for name in self._pk_columns]
            values = [row_values[name] for name in self._pk_columns]
            return f" WHERE {' AND '.join(parts)}", values
        return " WHERE rowid = ?", [rowid]


class MainWindow(QMainWindow):
    def __init__(self, initial_path: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Тест SQLite — просмотр таблиц")
        self.setMinimumSize(640, 480)
        self.db_path: Path | None = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        layout.addWidget(self._build_file_panel())
        layout.addWidget(self._build_tables_panel(), stretch=1)

        self.setStatusBar(QStatusBar())
        self._refresh_status()

        if initial_path and initial_path.is_file():
            self._load_database(initial_path)

    def _build_file_panel(self) -> QWidget:
        group, layout = _step_group(
            "1. База данных",
            "Выберите файл SQLite (.db). Список таблиц появится ниже.",
        )
        row = QHBoxLayout()
        self.path_label = QLineEdit()
        self.path_label.setReadOnly(True)
        self.path_label.setPlaceholderText("Файл не выбран")
        row.addWidget(self.path_label, stretch=1)

        browse_btn = _style_button(
            QPushButton("Обзор…"),
            "secondary",
            "Открыть файл SQLite",
        )
        browse_btn.clicked.connect(self._browse_database)
        row.addWidget(browse_btn)
        layout.addLayout(row)
        return group

    def _build_tables_panel(self) -> QWidget:
        group, layout = _step_group(
            "2. Таблицы",
            "Выберите таблицу и нажмите «Открыть» — откроется просмотр с пагинацией и CRUD.",
        )

        self.tables_list = QListWidget()
        self.tables_list.itemDoubleClicked.connect(self._open_selected_table)
        layout.addWidget(self.tables_list, stretch=1)

        buttons = QHBoxLayout()
        self.open_button = _style_button(
            QPushButton("Открыть"),
            "primary",
            "Открыть выбранную таблицу",
        )
        self.open_button.clicked.connect(self._open_selected_table)
        self.open_button.setEnabled(False)
        buttons.addWidget(self.open_button)
        buttons.addStretch()
        layout.addLayout(buttons)

        self.tables_list.currentItemChanged.connect(self._on_table_selection_changed)
        return group

    def _browse_database(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть SQLite",
            str(self.db_path.parent if self.db_path else Path.cwd()),
            "SQLite (*.db *.sqlite *.sqlite3);;Все файлы (*.*)",
        )
        if not path:
            return
        self._load_database(Path(path))

    def _load_database(self, path: Path) -> None:
        try:
            with open_database(path) as conn:
                tables = list_user_tables(conn)
        except sqlite3.Error as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть базу:\n{exc}")
            return

        self.db_path = path
        self.path_label.setText(str(path))
        self.tables_list.clear()
        for name in tables:
            self.tables_list.addItem(QListWidgetItem(name))
        self.open_button.setEnabled(bool(tables))
        self._refresh_status(len(tables))

    def _on_table_selection_changed(self) -> None:
        has_selection = self.tables_list.currentItem() is not None
        self.open_button.setEnabled(has_selection and self.db_path is not None)

    def _selected_table_name(self) -> str | None:
        item = self.tables_list.currentItem()
        return item.text() if item else None

    def _open_selected_table(self) -> None:
        if self.db_path is None:
            QMessageBox.warning(self, "Открыть", "Сначала выберите файл базы данных")
            return
        table = self._selected_table_name()
        if not table:
            QMessageBox.information(self, "Открыть", "Выберите таблицу из списка")
            return
        dialog = TableBrowserDialog(self.db_path, table, self)
        dialog.exec()

    def _refresh_status(self, table_count: int | None = None) -> None:
        if self.db_path is None:
            self.statusBar().showMessage("Файл базы данных не выбран")
            return
        if table_count is None:
            table_count = self.tables_list.count()
        self.statusBar().showMessage(
            f"{self.db_path.name} | Таблиц: {table_count}"
        )


def main() -> None:
    initial_path: Path | None = None
    if len(sys.argv) > 1:
        candidate = Path(sys.argv[1])
        if candidate.is_file():
            initial_path = candidate

    app = QApplication(sys.argv)
    app.setStyleSheet(_build_stylesheet(THEME_LIGHT, DEFAULT_FONT_SIZE))
    window = MainWindow(initial_path)
    apply_app_icon(app, window)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
