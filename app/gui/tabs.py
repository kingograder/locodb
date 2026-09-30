# -*- coding: utf-8 -*-
"""Вкладки со списками справочников.

Все вкладки наследуются от BaseTab — общая логика (таблица, кнопки,
reload, обработка ошибок, показ фото) описана один раз.

Колонки каждой вкладки описываются одним словарём COLUMN_CONFIG:

    COLUMN_CONFIG = {
        "Заголовок": ("text",  lambda item: значение_или_None),
        "Фото":      ("photo", lambda item: путь_к_картинке),
    }

Порядок ключей = порядок колонок в таблице. Тип "photo" кладёт в ячейку
QLabel с картинкой (или заглушкой), тип "text" — обычный QTableWidgetItem.
Если getter вернул None, в ячейку-текст попадёт NO_DATA.
"""

import logging
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHeaderView,
    QLabel,
    QMessageBox,
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
from app.utils.image_storage import PROJECT_ROOT
from app.widgets.ui_base_tab_widget import Ui_baseTab_widget

logger = logging.getLogger(__name__)

NO_DATA = "—"
PHOTO_WIDTH = 96
PHOTO_HEIGHT = 64

# (kind, getter) — kind сейчас "text" или "photo".
ColumnSpec = tuple[str, Callable[[Any], Any]]


class BaseTab(QWidget):
    """Общая логика вкладок-справочников.

    Наследнику нужно задать:
        COLUMN_CONFIG    — словарь колонок (см. модульный docstring)
        DIALOG_CLASS     — класс диалога создания/редактирования
        NOT_FOUND_ERROR  — исключение "запись не найдена"
        _repo()          — репозиторий, с которым работает вкладка
        _delete_prompt() — текст вопроса при удалении
    """

    COLUMN_CONFIG: dict[str, ColumnSpec] = {}
    DIALOG_CLASS: type | None = None
    NOT_FOUND_ERROR: type | None = None
    ADD_LABEL = "Добавить"
    EDIT_LABEL = "Изменить"
    DELETE_LABEL = "Удалить"

    def __init__(self, services: Services, current_user, parent=None):
        super().__init__(parent)
        self.services = services
        self.current_user = current_user

        self.ui = Ui_baseTab_widget()
        self.ui.setupUi(self)

        table = self.ui.base_table
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self._setup_buttons()
        self._items: list = []
        self.reload()

    def _setup_buttons(self) -> None:
        """Задаёт подписи кнопок и подключает обработчики."""
        self.ui.addBase_button.setText(self.ADD_LABEL)
        self.ui.editBase_button.setText(self.EDIT_LABEL)
        self.ui.deleteBase_button.setText(self.DELETE_LABEL)

        self.ui.addBase_button.clicked.connect(self._on_add_clicked)
        self.ui.editBase_button.clicked.connect(self._on_edit_clicked)
        self.ui.deleteBase_button.clicked.connect(self._on_delete_clicked)

    def _repo(self):
        """Репозиторий вкладки. Переопределяется в наследниках."""
        raise NotImplementedError

    def _delete_prompt(self, item) -> str:
        """Текст подтверждения удаления. Переопределяется в наследниках."""
        raise NotImplementedError

    def reload(self) -> None:
        """Перечитывает данные из БД и перерисовывает таблицу."""
        self._items = self._repo().list_all()
        self._fill_table()

    def _fill_table(self) -> None:
        """Рисует таблицу по COLUMN_CONFIG и self._items."""
        table = self.ui.base_table
        columns = list(self.COLUMN_CONFIG.items())

        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels([title for title, _ in columns])
        table.setRowCount(len(self._items))

        for row, item in enumerate(self._items):
            for col, (_title, (kind, getter)) in enumerate(columns):
                value = getter(item)
                if kind == "photo":
                    table.setCellWidget(
                        row, col, self._build_photo_label(value)
                    )
                else:
                    text = NO_DATA if value is None else str(value)
                    table.setItem(row, col, QTableWidgetItem(text))

    def _build_photo_label(self, path: str | None) -> QLabel:
        """QLabel с картинкой или заглушкой, если файла нет."""
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Клик по картинке не перехватываем — пусть выделяется строка таблицы.
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        pixmap = self._load_pixmap(path)
        if pixmap is None:
            label.setText(NO_DATA)
            return label

        label.setPixmap(pixmap)
        return label

    def _load_pixmap(self, path: str | None) -> QPixmap | None:
        """Загружает и масштабирует фото. None, если файла нет или он битый.

        Относительные пути (как хранятся в БД) строятся от корня проекта,
        чтобы работало независимо от текущей рабочей директории процесса.
        """
        if not path:
            return None

        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = PROJECT_ROOT / file_path

        if not file_path.exists():
            logger.warning(f"Файл изображения не найден: {file_path}")
            return None

        pixmap = QPixmap(str(file_path))
        if pixmap.isNull():
            logger.warning(f"Не удалось прочитать изображение: {file_path}")
            return None

        return pixmap.scaled(
            QSize(PHOTO_WIDTH, PHOTO_HEIGHT),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def _selected_item(self):
        """Возвращает выбранную запись или None."""
        row = self.ui.base_table.currentRow()
        if row < 0 or row >= len(self._items):
            return None
        return self._items[row]

    def _on_add_clicked(self) -> None:
        """Открывает диалог создания."""
        dialog = self.DIALOG_CLASS(self.services, self.current_user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _on_edit_clicked(self) -> None:
        """Открывает диалог редактирования."""
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "Внимание", "Выберите запись")
            return

        dialog = self.DIALOG_CLASS(
            self.services, self.current_user, item, parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _on_delete_clicked(self) -> None:
        """Удаляет выбранную запись после подтверждения."""
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "Внимание", "Выберите запись")
            return

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            self._delete_prompt(item),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self._repo().delete(item.id)
        except EntityInUseError as exc:
            QMessageBox.warning(self, "Внимание", str(exc))
            return
        except self.NOT_FOUND_ERROR:
            QMessageBox.critical(self, "Ошибка", "Запись уже удалена")
            return

        self.reload()


class MaintenanceTypesTab(BaseTab):
    """Вкладка «Типы обслуживания»."""

    DIALOG_CLASS = MaintenanceTypeDialog
    NOT_FOUND_ERROR = MaintenanceTypeNotFoundError

    COLUMN_CONFIG = {
        "Название": ("text", lambda it: it.name),
    }

    def _repo(self):
        return self.services.maintenance_types

    def _delete_prompt(self, item) -> str:
        return f"Удалить тип обслуживания «{item.name}»?\nДействие нельзя отменить."


class ManufacturersTab(BaseTab):
    """Вкладка «Производители»."""

    DIALOG_CLASS = ManufacturerDialog
    NOT_FOUND_ERROR = ManufacturerNotFoundError

    COLUMN_CONFIG = {
        "Название": ("text", lambda it: it.name),
    }

    def _repo(self):
        return self.services.manufacturers

    def _delete_prompt(self, item) -> str:
        return f"Удалить производителя «{item.name}»?\nДействие нельзя отменить."


class LocomotiveModelsTab(BaseTab):
    """Вкладка «Модели локомотивов»."""

    DIALOG_CLASS = LocomotiveModelDialog
    NOT_FOUND_ERROR = LocomotiveModelNotFoundError

    COLUMN_CONFIG = {
        "Фото":          ("photo", lambda it: it.image_path),
        "Производитель": ("text",  lambda it: it.manufacturer.name),
        "Артикул":       ("text",  lambda it: str(it.code)),
        "Модель":        ("text",  lambda it: it.name),
    }

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

    COLUMN_CONFIG = {
        "Система":       ("text",  lambda it: str(it.system)),
        "Номер":         ("text",  lambda it: str(it.number)),
        "Фото":          ("photo", lambda it: it.model.image_path if it.model else None),
        "Производитель": ("text",  lambda it: it.model.manufacturer.name
                                       if it.model and it.model.manufacturer else None),
        "Артикул":       ("text",  lambda it: str(it.model.code) if it.model else None),
        "Модель":        ("text",  lambda it: it.model.name if it.model else None),
    }

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

    COLUMN_CONFIG = {
        "Производитель": ("text", lambda it: it.manufacturer.name if it.manufacturer else None),
        "Артикул":       ("text", lambda it: str(it.code)),
        "Наименование":  ("text", lambda it: it.name),
        "Остаток":       ("text", lambda it: str(it.quantity_in_stock)),
    }

    def _repo(self):
        return self.services.details

    def _delete_prompt(self, item) -> str:
        return f"Удалить деталь «{item.name}»?\nДействие нельзя отменить."


class MaintenancesTab(BaseTab):
    """Вкладка «Листы обслуживания»."""

    DIALOG_CLASS = MaintenanceDialog
    NOT_FOUND_ERROR = MaintenanceNotFoundError
    DELETE_LABEL = "Пометить на удаление"

    COLUMN_CONFIG = {
        "Локомотив": ("text", lambda it: f"{it.locomotive.system} {it.locomotive.number}"
                                         if it.locomotive else None),
        "Тип":       ("text", lambda it: it.maintenance_type.name
                                         if it.maintenance_type else None),
        "Комментарий": ("text", lambda it: it.description or ""),
        "Автор":     ("text", lambda it: f"{it.user.first_name} {it.user.last_name}"
                                         if it.user else None),
    }

    def _repo(self):
        return self.services.maintenances

    def _delete_prompt(self, item) -> str:
        return f"Пометить на удаление лист обслуживания {item.id}?"


class SuppliesTab(BaseTab):
    """Вкладка «Приход».

    В БД каждая деталь — отдельная запись Supply, но объединены они
    номером supply_number. Поэтому таблица показывает партии: одна строка =
    один номер прихода, а не одна запись.

    Getter-ы COLUMN_CONFIG здесь принимают словарь партии (dict), а не
    ORM-объект — это видно по обращениям вида batch["number"].
    """

    ADD_LABEL = "Создать приход"
    EDIT_LABEL = "Изменить"
    DELETE_LABEL = "Удалить"

    COLUMN_CONFIG = {
        "Номер":   ("text", lambda b: str(b["number"])),
        "Дата":    ("text", lambda b: b["created_at"].strftime("%d.%m.%Y %H:%M")),
        "Деталей": ("text", lambda b: str(b["positions"])),
        "Всего":   ("text", lambda b: str(b["total_quantity"])),
        "Автор":   ("text", lambda b: b["user_login"]),
    }

    def reload(self) -> None:
        """Перечитывает партии приходов и рисует таблицу.

        Переопределяем метод, потому что BaseTab берёт данные из
        _repo().list_all(), а здесь нужна группировка по supply_number.
        Отрисовка остаётся общей — _fill_table() разберёт COLUMN_CONFIG.
        """
        self._items = self.services.supplies.list_batches()
        self._fill_table()

    def _delete_prompt(self, item) -> str:
        return (
            f"Удалить приход №{item['number']}?\n"
            f"Остатки деталей вернутся на склад."
        )

    def _on_add_clicked(self) -> None:
        """Открывает диалог создания нового прихода."""
        dialog = SupplyDialog(self.services, self.current_user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _on_edit_clicked(self) -> None:
        """Открывает диалог редактирования выбранной партии."""
        batch = self._selected_item()
        if batch is None:
            QMessageBox.information(self, "Внимание", "Выберите приход")
            return

        dialog = SupplyDialog(
            self.services, self.current_user,
            supply_number=batch["number"], parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _on_delete_clicked(self) -> None:
        """Удаляет выбранную партию после подтверждения."""
        batch = self._selected_item()
        if batch is None:
            QMessageBox.information(self, "Внимание", "Выберите приход")
            return

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            self._delete_prompt(batch),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self.services.supplies.delete_batch(batch["number"])
        except SupplyNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Приход уже удалён")
            return

        self.reload()


__all__ = [
    "BaseTab",
    "MaintenanceTypesTab",
    "ManufacturersTab",
    "LocomotiveModelsTab",
    "LocomotivesTab",
    "DetailsTab",
    "MaintenancesTab",
]
