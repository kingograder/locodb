# -*- coding: utf-8 -*-
"""
Вкладки со списками справочников.
"""

import logging
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, ClassVar, Protocol

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap, QPixmapCache
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
PHOTO_HEIGHT = 64        # одинаковая высота превью — ровные строки таблицы
PHOTO_MAX_WIDTH = 128    # предел для панорам — не расползаться на всю таблицу

WARNING_TITLE = "Внимание"
ERROR_TITLE = "Ошибка"
CONFIRM_TITLE = "Подтверждение"


class CellRenderer(Protocol):
    """Способ отрисовать одну ячейку таблицы по её значению."""

    def render(self, table: QTableWidget, row: int, col: int, value: Any) -> None: ...


class TextCellRenderer:
    """Ячейка-текст: None превращается в NO_DATA."""

    def render(self, table: QTableWidget, row: int, col: int, value: Any) -> None:
        text = NO_DATA if value is None else str(value)
        table.setItem(row, col, QTableWidgetItem(text))


class PhotoCellRenderer:
    """Ячейка-превью: QLabel с картинкой или заглушкой NO_DATA.

    Отвечает только за загрузку файла и масштабирование. Структуры
    таблицы не знает — ей передают table/row/col как параметры.
    """

    def __init__(self, height: int = PHOTO_HEIGHT, max_width: int = PHOTO_MAX_WIDTH):
        self._height = height
        self._max_width = max_width

    def render(self, table: QTableWidget, row: int, col: int, value: Any) -> None:
        table.setCellWidget(row, col, self._build_label(value))

    def _build_label(self, path: str | None) -> QLabel:
        label = self._create_label()
        pixmap = self._load_pixmap(path)
        if pixmap is None:
            label.setText(NO_DATA)
        else:
            label.setPixmap(pixmap)
        return label

    def _create_label(self) -> QLabel:
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Клик по картинке не перехватываем — пусть выделяется строка таблицы.
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        return label

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
    """Заголовок, рендерер ячейки и getter значения для одной колонки."""

    title: str
    renderer: CellRenderer
    getter: Callable[[Any], Any]


class TableRenderer:
    """Рисует таблицу по списку Column и списку записей.

    Не знает, откуда пришли записи и что они собой представляют —
    только делегирует значение каждой ячейки её рендереру.
    """

    def __init__(self, columns: list[Column]):
        self._columns = columns

    def render(self, table: QTableWidget, items: list) -> None:
        self._configure(table, row_count=len(items))
        for row, item in enumerate(items):
            self._render_row(table, row, item)
        table.resizeRowsToContents()

    def _configure(self, table: QTableWidget, row_count: int) -> None:
        table.setColumnCount(len(self._columns))
        table.setHorizontalHeaderLabels([c.title for c in self._columns])
        table.setRowCount(row_count)

    def _render_row(self, table: QTableWidget, row: int, item: Any) -> None:
        for col, column in enumerate(self._columns):
            column.renderer.render(table, row, col, column.getter(item))


_TEXT_RENDERER = TextCellRenderer()
_PHOTO_RENDERER = PhotoCellRenderer()


def _locomotive_manufacturer_name(item) -> str | None:
    """Имя производителя модели локомотива; None, если связь не заполнена."""
    model = item.model
    if model is None or model.manufacturer is None:
        return None
    return model.manufacturer.name


def _locomotive_model_image_path(item) -> str | None:
    return item.model.image_path if item.model else None


def _locomotive_model_code(item) -> str | None:
    return str(item.model.code) if item.model else None


def _locomotive_model_name(item) -> str | None:
    return item.model.name if item.model else None


def _detail_manufacturer_name(item) -> str | None:
    return item.manufacturer.name if item.manufacturer else None


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


class _TabBaseMeta(type(QWidget), ABCMeta):
    """Метакласс-мост между Shiboken и ABC.

    QWidget из PySide6 использует Shiboken.ObjectType, ABC — ABCMeta.
    Оба наследуют type, но не друг друга, поэтому Python не может
    вывести общий метакласс и падает с TypeError. Пустой наследник
    обоих снимает конфликт, не добавляя поведения.
    """


class _TabBase(QWidget, metaclass=_TabBaseMeta):
    """Каркас вкладки-справочника: таблица, кнопки, выбор, reload.

    Не знает ни источника данных, ни типа строки — только то, что
    умеет показать таблицу по COLUMN_CONFIG и обработать клики.

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

        self._configure_table()
        self._setup_buttons()
        self.reload()

    def _configure_table(self) -> None:
        table = self.ui.base_table
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def _setup_buttons(self) -> None:
        self.ui.addBase_button.setText(self.ADD_LABEL)
        self.ui.editBase_button.setText(self.EDIT_LABEL)
        self.ui.deleteBase_button.setText(self.DELETE_LABEL)

        self.ui.addBase_button.clicked.connect(self._on_add_clicked)
        self.ui.editBase_button.clicked.connect(self._on_edit_clicked)
        self.ui.deleteBase_button.clicked.connect(self._on_delete_clicked)

    def reload(self) -> None:
        self._items = self._reload_items()
        QPixmapCache.clear()
        self._table_renderer.render(self.ui.base_table, self._items)

    def _selected_item(self):
        """Возвращает выбранную запись или None."""
        row = self.ui.base_table.currentRow()
        if row < 0 or row >= len(self._items):
            return None
        return self._items[row]

    def _require_selection(self):
        """Возвращает выбранную запись; при пустом выборе предупреждает и None."""
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

    @abstractmethod
    def _reload_items(self) -> list: ...

    @abstractmethod
    def _open_dialog_for_edit(self, item) -> None: ...

    @abstractmethod
    def _delete(self, item) -> None: ...

    @abstractmethod
    def _delete_prompt(self, item) -> str: ...


class BaseTab(_TabBase):
    """Вкладка справочника, строки — ORM-объекты из репозитория.

    Наследнику задать:
        DIALOG_CLASS       — класс диалога
        NOT_FOUND_ERROR    — исключение "запись не найдена"
        COLUMN_CONFIG      — колонки
        _repo()            — репозиторий вкладки
        _delete_prompt(item) — текст вопроса при удалении
    """

    NOT_FOUND_ERROR: ClassVar[type[BaseException]]

    def _repo(self):
        """Репозиторий вкладки. Переопределяется в наследниках."""
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
    """Вкладка, строки — словари партий (групп записей).

    Наследнику задать:
        DIALOG_CLASS       — класс диалога
        COLUMN_CONFIG      — колонки (getter принимает dict)
        _reload_items()    — как собрать партии
        _open_dialog_for_edit(item) — как открыть диалог по партии
        _delete(item)      — как удалить партию
        _delete_prompt(item) — текст вопроса при удалении
    """


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
        Column("Фото",          _PHOTO_RENDERER, lambda item: item.image_path),
        Column("Производитель", _TEXT_RENDERER,  lambda item: item.manufacturer.name),
        Column("Артикул",       _TEXT_RENDERER,  lambda item: str(item.code)),
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
    """Вкладка «Локомотивы».

    Фото живёт в модели, а не в локомотиве — берём через связь.
    """

    DIALOG_CLASS = LocomotiveDialog
    NOT_FOUND_ERROR = LocomotiveNotFoundError

    COLUMN_CONFIG = [
        Column("Система",       _TEXT_RENDERER,  lambda item: str(item.system)),
        Column("Номер",         _TEXT_RENDERER,  lambda item: str(item.number)),
        Column("Фото",          _PHOTO_RENDERER, _locomotive_model_image_path),
        Column("Производитель", _TEXT_RENDERER,  _locomotive_manufacturer_name),
        Column("Артикул",       _TEXT_RENDERER,  _locomotive_model_code),
        Column("Модель",        _TEXT_RENDERER,  _locomotive_model_name),
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
        Column("Производитель", _TEXT_RENDERER, _detail_manufacturer_name),
        Column("Артикул",       _TEXT_RENDERER, lambda item: str(item.code)),
        Column("Наименование",  _TEXT_RENDERER, lambda item: item.name),
        Column("Остаток",       _TEXT_RENDERER, lambda item: str(item.quantity_in_stock)),
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
        Column("Локомотив",   _TEXT_RENDERER, _maintenance_locomotive_label),
        Column("Тип",         _TEXT_RENDERER, _maintenance_type_name),
        Column("Комментарий", _TEXT_RENDERER, lambda item: item.description or ""),
        Column("Автор",       _TEXT_RENDERER, _maintenance_author_name),
        Column("Дата",        _TEXT_RENDERER, _maintenance_date),
    ]

    def _repo(self):
        return self.services.maintenances

    def _delete_prompt(self, item) -> str:
        return f"Пометить на удаление лист обслуживания {item.id}?"


class SuppliesTab(BatchTab):
    """Вкладка «Приход».

    В БД каждая деталь — отдельная запись Supply, объединённая номером
    supply_number. Таблица показывает партии: одна строка = один приход.
    Getter-ы COLUMN_CONFIG принимают словарь партии, а не ORM-объект.
    """

    DIALOG_CLASS = SupplyDialog
    ADD_LABEL = "Создать приход"
    EDIT_LABEL = "Изменить"
    DELETE_LABEL = "Удалить"
    EMPTY_SELECTION_MESSAGE = "Выберите приход"

    COLUMN_CONFIG = [
        Column("Номер",   _TEXT_RENDERER, _batch_number),
        Column("Дата",    _TEXT_RENDERER, _batch_created_at),
        Column("Деталей", _TEXT_RENDERER, lambda item: str(item["positions"])),
        Column("Всего",   _TEXT_RENDERER, lambda item: str(item["total_quantity"])),
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
