# -*- coding: utf-8 -*-

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, ClassVar, Protocol

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHeaderView,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from app.db.exceptions import (
    DetailNotFoundError,
    EntityInUseError,
    LocomotiveModelNotFoundError,
    LocomotiveNotFoundError,
    MaintenanceNotFoundError,
    MaintenanceTypeNotFoundError,
    ManufacturerNotFoundError,
    SupplyNotFoundError,
)
from app.gui.dialogs import (
    DetailDialog,
    LocomotiveDialog,
    LocomotiveModelDialog,
    MaintenanceDialog,
    MaintenanceTypeDialog,
    ManufacturerDialog,
    SupplyDialog,
)
from app.services import Services
from app.utils.image_storage import PROJECT_ROOT, load_oriented_image
from app.widgets.ui_base_tab_widget import Ui_baseTab_widget

logger = logging.getLogger(__name__)

NO_DATA = "—"
PHOTO_HEIGHT = 64
PHOTO_MAX_WIDTH = 128
ROW_HEIGHT_WITH_PHOTO = PHOTO_HEIGHT + 8
ROW_HEIGHT_TEXT_ONLY = 28

WARNING_TITLE = "Внимание"
ERROR_TITLE = "Ошибка"
CONFIRM_TITLE = "Подтверждение"


class CellRenderer(Protocol):
    def ensure_cell(self, table: QTableWidget, row: int, col: int) -> Any: ...
    def apply(self, cell: Any, value: Any) -> None: ...


class TextCellRenderer:
    def ensure_cell(self, table: QTableWidget, row: int, col: int) -> QTableWidgetItem:
        cell = table.item(row, col)
        if cell is None:
            cell = QTableWidgetItem()
            table.setItem(row, col, cell)
        return cell

    def apply(self, cell: QTableWidgetItem, value: Any) -> None:
        cell.setText(NO_DATA if value is None else str(value))


class PhotoCellRenderer:
    """Ячейка-превью с кэшем пиксмапов и переиспользованием QLabel.

    Переиспользование важно для отзывчивости: при сортировке таблица
    не создаёт QLabel заново, а обновляет pixmap в существующем. Кэш
    избавляет от повторного чтения файла с диска — пути уникальны
    (UUID-суффикс при сохранении), поэтому кэш не может отдать старое
    фото вместо нового.
    """

    def __init__(self, height: int = PHOTO_HEIGHT, max_width: int = PHOTO_MAX_WIDTH):
        self._height = height
        self._max_width = max_width
        self._cache: dict[str | None, QPixmap | None] = {}

    def clear_cache(self) -> None:
        self._cache.clear()

    def ensure_cell(self, table: QTableWidget, row: int, col: int) -> QLabel:
        cell = table.cellWidget(row, col)
        if cell is None:
            cell = self._create_label()
            table.setCellWidget(row, col, cell)
        return cell

    def apply(self, cell: QLabel, value: Any) -> None:
        pixmap = self._cached_pixmap(value)
        if pixmap is None:
            cell.clear()
            cell.setText(NO_DATA)
        else:
            cell.setText("")
            cell.setPixmap(pixmap)

    def _create_label(self) -> QLabel:
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Клик по картинке не перехватываем — пусть выделяется строка таблицы.
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        return label

    def _cached_pixmap(self, path: str | None) -> QPixmap | None:
        if path in self._cache:
            return self._cache[path]
        pixmap = self._load_pixmap(path)
        self._cache[path] = pixmap
        return pixmap

    def _load_pixmap(self, path: str | None) -> QPixmap | None:
        file_path = self._resolve_path(path)
        if file_path is None:
            return None

        image = load_oriented_image(file_path)
        if image is None:
            logger.warning(f"Не удалось прочитать изображение: {file_path}")
            return None

        pixmap = self._make_thumbnail(image)
        if pixmap.isNull():
            logger.warning(f"Не удалось масштабировать изображение: {file_path}")
            return None
        return pixmap

    def _resolve_path(self, path: str | None) -> Path | None:
        """Возвращает абсолютный путь к существующему файлу или None.

        Относительные пути в БД строятся от корня проекта, чтобы
        отображение не зависело от текущей рабочей директории процесса.
        """
        if not path:
            return None

        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = PROJECT_ROOT / file_path

        if not file_path.exists():
            logger.warning(f"Файл изображения не найден: {file_path}")
            return None

        return file_path

    def _make_thumbnail(self, image: QImage) -> QPixmap:
        """Масштабирует фото под ячейку: фиксированная высота, ширина по пропорции.

        Высота всегда self._height, ширина ограничена self._max_width:
        широкие кадры остаются крупными, панорамы не расползаются на всю таблицу.
        """
        if image.isNull() or image.height() == 0:
            return QPixmap()

        aspect = image.width() / image.height()
        width = round(self._height * aspect)
        height = self._height

        if width > self._max_width:
            width = self._max_width
            height = max(1, round(width / aspect))

        # Пропорции учтены в width/height — IgnoreAspectRatio не искажает.
        scaled = image.scaled(
            width,
            height,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        return QPixmap.fromImage(scaled)


@dataclass(frozen=True)
class Column:
    """Заголовок, рендерер ячейки, getter значения и параметры сортировки.

    getter возвращает значение для отображения (может быть None).
    sort_key — ключ сортировки; если None, используется getter (подходит,
    когда getter уже возвращает сравнимое значение без None). Если типы
    для отображения и сортировки различаются (артикул как «1234» vs 1234),
    задаётся явный sort_key. sortable=False отключает сортировку по колонке.
    """

    title: str
    renderer: CellRenderer
    getter: Callable[[Any], Any]
    sort_key: Callable[[Any], Any] | None = None
    sortable: bool = True

    def effective_sort_key(self) -> Callable[[Any], Any] | None:
        if not self.sortable:
            return None
        return self.sort_key if self.sort_key is not None else self.getter


class TableRenderer:
    """Рисует таблицу по списку Column и списку записей.

    Переиспользует ячейки между вызовами (ensure_cell + apply) и
    группирует перерисовку через setUpdatesEnabled — это делает
    сортировку быстрой: при повторном рендере не уничтожаются QLabel
    и QTableWidgetItem, не пересчитываются высоты строк.
    """

    def __init__(self, columns: list[Column]):
        self._columns = columns

    def render(self, table: QTableWidget, items: list) -> None:
        table.setUpdatesEnabled(False)
        try:
            self._ensure_structure(table, len(items))
            for row, item in enumerate(items):
                self._render_row(table, row, item)
        finally:
            table.setUpdatesEnabled(True)

    def _ensure_structure(self, table: QTableWidget, row_count: int) -> None:
        if table.columnCount() != len(self._columns):
            table.setColumnCount(len(self._columns))
            table.setHorizontalHeaderLabels([c.title for c in self._columns])
        if table.rowCount() != row_count:
            table.setRowCount(row_count)

    def _render_row(self, table: QTableWidget, row: int, item: Any) -> None:
        for col, column in enumerate(self._columns):
            cell = column.renderer.ensure_cell(table, row, col)
            column.renderer.apply(cell, column.getter(item))


_TEXT_RENDERER = TextCellRenderer()
_PHOTO_RENDERER = PhotoCellRenderer()


def _sorted_by(getter: Callable[[Any], Any], default: Any) -> Callable[[Any], Any]:
    """None-безопасный ключ сортировки: default, если getter вернул None.

    Нужен, когда getter возвращает None (для NO_DATA), а Python 3 не
    умеет сравнивать None со str/int/datetime. default должен быть
    того же типа, что непустые значения getter-а.
    """
    def sort_key(item):
        value = getter(item)
        return default if value is None else value
    return sort_key


def _locomotive_manufacturer_name(item) -> str | None:
    model = item.model
    if model is None or model.manufacturer is None:
        return None
    return model.manufacturer.name


def _locomotive_model_image_path(item) -> str | None:
    return item.model.image_path if item.model else None


def _locomotive_model_code(item) -> str | None:
    return str(item.model.code) if item.model else None


def _locomotive_model_code_int(item) -> int | None:
    return item.model.code if item.model else None


def _locomotive_model_name(item) -> str | None:
    return item.model.name if item.model else None


def _detail_manufacturer_name(item) -> str | None:
    return item.manufacturer.name if item.manufacturer else None

def _detail_code_sort_key(item) -> tuple[int, str]:
    """Натуральная сортировка артикула: «9999» < «10000» < «10000-1»"""
    code = str(item.code)
    prefix, _, suffix = code.partition("-")
    try:
        numeric = int(prefix)
    except ValueError:
        numeric = 0
    return (numeric, suffix)

def _maintenance_locomotive_label(item) -> str | None:
    loco = item.locomotive
    return f"{loco.system} {loco.number}" if loco else None


def _maintenance_type_name(item) -> str | None:
    return item.maintenance_type.name if item.maintenance_type else None


def _maintenance_author_name(item) -> str | None:
    user = item.user
    return f"{user.first_name} {user.last_name}" if user else None


def _maintenance_date(item) -> str | None:
    return item.date.strftime("%d.%m.%Y") if item.date else None


def _batch_number(item) -> str:
    return str(item["number"])


def _batch_created_at(item) -> str:
    return item["created_at"].strftime("%d.%m.%Y %H:%M")


class _TabBase(QWidget):
    """Каркас вкладки-справочника: таблица, кнопки, выбор, reload, сортировка.

    Наследнику обязательно задать:
        COLUMN_CONFIG      — список Column
        DIALOG_CLASS       — класс диалога создания/редактирования
        _reload_items()    — как получить строки таблицы
        _open_dialog_for_edit(item) — как открыть диалог редактирования
        _delete(item)      — как удалить запись (с обработкой ошибок)
        _delete_prompt(item) — текст вопроса при удалении
    """

    COLUMN_CONFIG: ClassVar[list[Column]]
    DIALOG_CLASS: ClassVar[type[QDialog]]

    ADD_LABEL = "Добавить"
    EDIT_LABEL = "Изменить"
    DELETE_LABEL = "Удалить"
    EMPTY_SELECTION_MESSAGE = "Выберите запись"

    def __init__(self, services: Services, current_user, parent=None):
        super().__init__(parent)
        self.services = services
        self.current_user = current_user

        self.ui = Ui_baseTab_widget()
        self.ui.setupUi(self)

        self._table_renderer = TableRenderer(self.COLUMN_CONFIG)
        self._items: list = []
        self._sorted_column: int | None = None
        self._sort_descending = False

        self._sort_timer = QTimer(self)
        self._sort_timer.setSingleShot(True)
        self._sort_timer.timeout.connect(self._apply_sort_and_redraw)

        self._configure_table()
        self._setup_buttons()
        self.reload()

    def _configure_table(self) -> None:
        table = self.ui.base_table
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        header.sectionClicked.connect(self._on_header_clicked)

        # Фиксированная высота строки убирает resizeRowsToContents из
        # горячего пути: пересчёт высот на каждый клик по заголовку —
        # самая дорогая операция QTableWidget.
        vheader = table.verticalHeader()
        vheader.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        vheader.setDefaultSectionSize(self._row_height())

    def _row_height(self) -> int:
        has_photo = any(
            isinstance(c.renderer, PhotoCellRenderer) for c in self.COLUMN_CONFIG
        )
        return ROW_HEIGHT_WITH_PHOTO if has_photo else ROW_HEIGHT_TEXT_ONLY

    def _setup_buttons(self) -> None:
        self.ui.addBase_button.setText(self.ADD_LABEL)
        self.ui.editBase_button.setText(self.EDIT_LABEL)
        self.ui.deleteBase_button.setText(self.DELETE_LABEL)

        self.ui.addBase_button.clicked.connect(self._on_add_clicked)
        self.ui.editBase_button.clicked.connect(self._on_edit_clicked)
        self.ui.deleteBase_button.clicked.connect(self._on_delete_clicked)

    def reload(self) -> None:
        self._items = self._reload_items()
        _PHOTO_RENDERER.clear_cache()
        self._apply_sort()
        self._table_renderer.render(self.ui.base_table, self._items)

    def _on_header_clicked(self, column: int) -> None:
        if self.COLUMN_CONFIG[column].effective_sort_key() is None:
            return
        if self._sorted_column == column:
            self._sort_descending = not self._sort_descending
        else:
            self._sorted_column = column
            self._sort_descending = False
        # Клики в серии коалесцируются: несколько нажатий подряд
        # сливаются в один рендер после последнего.
        self._sort_timer.start(0)

    def _apply_sort_and_redraw(self) -> None:
        self._apply_sort()
        self._table_renderer.render(self.ui.base_table, self._items)
        self.ui.base_table.clearSelection()
        self._update_sort_indicator()

    def _apply_sort(self) -> None:
        if self._sorted_column is None:
            return
        sort_key = self.COLUMN_CONFIG[self._sorted_column].effective_sort_key()
        if sort_key is None:
            return
        self._items.sort(key=sort_key, reverse=self._sort_descending)

    def _update_sort_indicator(self) -> None:
        if self._sorted_column is None:
            return
        order = (Qt.SortOrder.DescendingOrder if self._sort_descending
                 else Qt.SortOrder.AscendingOrder)
        self.ui.base_table.horizontalHeader().setSortIndicator(
            self._sorted_column, order
        )

    def _selected_item(self):
        row = self.ui.base_table.currentRow()
        if row < 0 or row >= len(self._items):
            return None
        return self._items[row]

    def _require_selection(self):
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, WARNING_TITLE, self.EMPTY_SELECTION_MESSAGE)
        return item

    def _on_add_clicked(self) -> None:
        dialog = self.DIALOG_CLASS(self.services, self.current_user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _on_edit_clicked(self) -> None:
        item = self._require_selection()
        if item is not None:
            self._open_dialog_for_edit(item)

    def _on_delete_clicked(self) -> None:
        item = self._require_selection()
        if item is not None and self._confirm_delete(item):
            self._delete(item)

    def _confirm_delete(self, item) -> bool:
        reply = QMessageBox.question(
            self,
            CONFIRM_TITLE,
            self._delete_prompt(item),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def _reload_items(self) -> list:
        raise NotImplementedError

    def _open_dialog_for_edit(self, item) -> None:
        raise NotImplementedError

    def _delete(self, item) -> None:
        raise NotImplementedError

    def _delete_prompt(self, item) -> str:
        raise NotImplementedError


class BaseTab(_TabBase):
    """Вкладка справочника, строки — ORM-объекты из репозитория."""

    NOT_FOUND_ERROR: ClassVar[type[BaseException]]

    def _repo(self):
        raise NotImplementedError

    def _reload_items(self) -> list:
        return self._repo().list_all()

    def _open_dialog_for_edit(self, item) -> None:
        dialog = self.DIALOG_CLASS(
            self.services, self.current_user, item, parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _delete(self, item) -> None:
        not_found = self.NOT_FOUND_ERROR
        try:
            self._repo().delete(item.id)
        except EntityInUseError as exc:
            QMessageBox.warning(self, WARNING_TITLE, str(exc))
            return
        except not_found:
            QMessageBox.critical(self, ERROR_TITLE, "Запись уже удалена")
            return
        self.reload()


class BatchTab(_TabBase):
    """Вкладка, строки — словари партий (групп записей)."""


class MaintenanceTypesTab(BaseTab):
    """Вкладка «Типы обслуживания»."""

    DIALOG_CLASS = MaintenanceTypeDialog
    NOT_FOUND_ERROR = MaintenanceTypeNotFoundError

    COLUMN_CONFIG = [
        Column("Название", _TEXT_RENDERER, lambda item: item.name),
    ]

    def _repo(self):
        return self.services.maintenance_types

    def _delete_prompt(self, item) -> str:
        return f"Удалить тип обслуживания «{item.name}»?\nДействие нельзя отменить."


class ManufacturersTab(BaseTab):
    """Вкладка «Производители»."""

    DIALOG_CLASS = ManufacturerDialog
    NOT_FOUND_ERROR = ManufacturerNotFoundError

    COLUMN_CONFIG = [
        Column("Название", _TEXT_RENDERER, lambda item: item.name),
    ]

    def _repo(self):
        return self.services.manufacturers

    def _delete_prompt(self, item) -> str:
        return f"Удалить производителя «{item.name}»?\nДействие нельзя отменить."


class LocomotiveModelsTab(BaseTab):
    """Вкладка «Модели локомотивов»."""

    DIALOG_CLASS = LocomotiveModelDialog
    NOT_FOUND_ERROR = LocomotiveModelNotFoundError

    COLUMN_CONFIG = [
        Column("Фото",          _PHOTO_RENDERER, lambda item: item.image_path,
                                                 sortable=False),
        Column("Производитель", _TEXT_RENDERER,  lambda item: item.manufacturer.name),
        Column("Артикул",       _TEXT_RENDERER,  lambda item: str(item.code),
                                                 lambda item: item.code),
        Column("Модель",        _TEXT_RENDERER,  lambda item: item.name),
    ]

    def _repo(self):
        return self.services.locomotive_models

    def _delete_prompt(self, item) -> str:
        return (
            f"Удалить локомотив {item.manufacturer.name} {item.code}?\n"
            f"Действие нельзя отменить."
        )


class LocomotivesTab(BaseTab):
    """Вкладка «Локомотивы». Фото живёт в модели, а не в локомотиве."""

    DIALOG_CLASS = LocomotiveDialog
    NOT_FOUND_ERROR = LocomotiveNotFoundError

    COLUMN_CONFIG = [
        Column("Система",       _TEXT_RENDERER,  lambda item: str(item.system),
                                                 lambda item: item.system),
        Column("Номер",         _TEXT_RENDERER,  lambda item: str(item.number),
                                                 lambda item: item.number),
        Column("Фото",          _PHOTO_RENDERER, _locomotive_model_image_path,
                                                 sortable=False),
        Column("Производитель", _TEXT_RENDERER,  _locomotive_manufacturer_name,
                                                 _sorted_by(_locomotive_manufacturer_name, "")),
        Column("Артикул",       _TEXT_RENDERER,  _locomotive_model_code,
                                                 _sorted_by(_locomotive_model_code_int, 0)),
        Column("Модель",        _TEXT_RENDERER,  _locomotive_model_name,
                                                 _sorted_by(_locomotive_model_name, "")),
    ]

    def _repo(self):
        return self.services.locomotives

    def _delete_prompt(self, item) -> str:
        return (
            f"Удалить локомотив {item.number} с системы {item.system}?\n"
            f"Действие нельзя отменить."
        )


class DetailsTab(BaseTab):
    """Вкладка «Детали»."""

    DIALOG_CLASS = DetailDialog
    NOT_FOUND_ERROR = DetailNotFoundError

    COLUMN_CONFIG = [
        Column("Производитель", _TEXT_RENDERER, _detail_manufacturer_name,
                                                _sorted_by(_detail_manufacturer_name, "")),
        Column("Артикул",       _TEXT_RENDERER, lambda item: str(item.code),
                                                _detail_code_sort_key),
        Column("Наименование",  _TEXT_RENDERER, lambda item: item.name),
        Column("Остаток",       _TEXT_RENDERER, lambda item: str(item.quantity_in_stock),
                                                lambda item: item.quantity_in_stock),
    ]

    def _repo(self):
        return self.services.details

    def _delete_prompt(self, item) -> str:
        return f"Удалить деталь «{item.name}»?\nДействие нельзя отменить."

class MaintenancesTab(BaseTab):
    """Вкладка «Листы обслуживания»."""

    DIALOG_CLASS = MaintenanceDialog
    NOT_FOUND_ERROR = MaintenanceNotFoundError
    DELETE_LABEL = "Пометить на удаление"

    COLUMN_CONFIG = [
        Column("Локомотив",   _TEXT_RENDERER, _maintenance_locomotive_label,
                                              _sorted_by(_maintenance_locomotive_label, "")),
        Column("Тип",         _TEXT_RENDERER, _maintenance_type_name,
                                              _sorted_by(_maintenance_type_name, "")),
        Column("Комментарий", _TEXT_RENDERER, lambda item: item.description or ""),
        Column("Автор",       _TEXT_RENDERER, _maintenance_author_name,
                                              _sorted_by(_maintenance_author_name, "")),
        Column("Дата",        _TEXT_RENDERER, _maintenance_date,
                                              _sorted_by(lambda item: item.date,
                                                         datetime.min)),
    ]

    def _repo(self):
        return self.services.maintenances

    def _delete_prompt(self, item) -> str:
        return f"Пометить на удаление лист обслуживания {item.id}?"


class SuppliesTab(BatchTab):
    """Вкладка «Приход».

    В БД каждая деталь — отдельная запись Supply, объединённая номером
    supply_number. Таблица показывает партии: одна строка = один приход.
    """

    DIALOG_CLASS = SupplyDialog
    ADD_LABEL = "Создать приход"
    EDIT_LABEL = "Изменить"
    DELETE_LABEL = "Удалить"
    EMPTY_SELECTION_MESSAGE = "Выберите приход"

    COLUMN_CONFIG = [
        Column("Номер",   _TEXT_RENDERER, _batch_number,
                                          lambda item: item["number"]),
        Column("Дата",    _TEXT_RENDERER, _batch_created_at,
                                          lambda item: item["created_at"]),
        Column("Деталей", _TEXT_RENDERER, lambda item: str(item["positions"]),
                                          lambda item: item["positions"]),
        Column("Всего",   _TEXT_RENDERER, lambda item: str(item["total_quantity"]),
                                          lambda item: item["total_quantity"]),
        Column("Автор",   _TEXT_RENDERER, lambda item: item["user_login"]),
    ]

    def _reload_items(self) -> list:
        return self.services.supplies.list_batches()

    def _open_dialog_for_edit(self, item) -> None:
        dialog = SupplyDialog(
            self.services, self.current_user,
            supply_number=item["number"], parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _delete(self, item) -> None:
        try:
            self.services.supplies.delete_batch(item["number"])
        except SupplyNotFoundError:
            QMessageBox.critical(self, ERROR_TITLE, "Приход уже удалён")
            return
        self.reload()

    def _delete_prompt(self, item) -> str:
        return (
            f"Удалить приход №{item['number']}?\n"
            f"Остатки деталей вернутся на склад."
        )


__all__ = [
    "BaseTab",
    "BatchTab",
    "MaintenanceTypesTab",
    "ManufacturersTab",
    "LocomotiveModelsTab",
    "LocomotivesTab",
    "DetailsTab",
    "MaintenancesTab",
    "SuppliesTab",
]
