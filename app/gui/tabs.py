# -*- coding: utf-8 -*-
"""Вкладки со списками справочников.

Все вкладки наследуются от BaseTab — общая логика (таблица, кнопки,
reload, обработка ошибок, показ фото) описана один раз.
"""

import logging
from pathlib import Path

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


class BaseTab(QWidget):
    """Общая логика вкладок-справочников.

    Наследнику нужно задать:
        HEADERS          — заголовки столбцов таблицы
        DIALOG_CLASS     — класс диалога создания/редактирования
        NOT_FOUND_ERROR  — исключение "запись не найдена"
        PHOTO_COLUMN     — индекс столбца с фото (опционально)
        _repo()          — репозиторий, с которым работает вкладка
        _row_values()    — список строковых значений для строки таблицы
        _delete_prompt() — текст вопроса при удалении
        _photo_path()    — путь к фото (если задан PHOTO_COLUMN)
    """

    HEADERS: list[str] = []
    DIALOG_CLASS: type | None = None
    NOT_FOUND_ERROR: type | None = None
    PHOTO_COLUMN: int | None = None
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

    def _row_values(self, item) -> list[str]:
        """Значения для строки таблицы. Переопределяется в наследниках."""
        raise NotImplementedError

    def _delete_prompt(self, item) -> str:
        """Текст подтверждения удаления. Переопределяется в наследниках."""
        raise NotImplementedError

    def _photo_path(self, item) -> str | None:
        """Путь к фото элемента. Переопределяется во вкладках с фото."""
        return None

    def reload(self) -> None:
        """Перечитывает данные из БД и перерисовывает таблицу."""
        self._items = self._repo().list_all()
        self._fill_table()
        if self.PHOTO_COLUMN is not None:
            self._fill_photos()

    def _fill_table(self) -> None:
        """Заполняет таблицу текстовыми значениями."""
        table = self.ui.base_table
        table.setColumnCount(len(self.HEADERS))
        table.setHorizontalHeaderLabels(self.HEADERS)
        table.setRowCount(len(self._items))

        for row, item in enumerate(self._items):
            for col, value in enumerate(self._row_values(item)):
                table.setItem(row, col, QTableWidgetItem(value))

    def _fill_photos(self) -> None:
        """Ставит QLabel с фото в PHOTO_COLUMN каждой строки."""
        table = self.ui.base_table
        for row, item in enumerate(self._items):
            if self.PHOTO_COLUMN:
                table.setCellWidget(row, self.PHOTO_COLUMN, self._build_photo_label(item))

    def _build_photo_label(self, item) -> QLabel:
        """QLabel с картинкой или заглушкой, если файла нет."""
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Клик по картинке не перехватываем — пусть выделяется строка таблицы.
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        pixmap = self._load_pixmap(self._photo_path(item))
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

    HEADERS = ["Название"]
    DIALOG_CLASS = MaintenanceTypeDialog
    NOT_FOUND_ERROR = MaintenanceTypeNotFoundError

    def _repo(self):
        return self.services.maintenance_types

    def _row_values(self, item) -> list[str]:
        return [item.name]

    def _delete_prompt(self, item) -> str:
        return f"Удалить тип обслуживания «{item.name}»?\nДействие нельзя отменить."


class ManufacturersTab(BaseTab):
    """Вкладка «Производители»."""

    HEADERS = ["Название"]
    DIALOG_CLASS = ManufacturerDialog
    NOT_FOUND_ERROR = ManufacturerNotFoundError

    def _repo(self):
        return self.services.manufacturers

    def _row_values(self, item) -> list[str]:
        return [item.name]

    def _delete_prompt(self, item) -> str:
        return f"Удалить производителя «{item.name}»?\nДействие нельзя отменить."


class LocomotiveModelsTab(BaseTab):
    """Вкладка «Модели локомотивов»."""

    HEADERS = ["Фото", "Производитель", "Артикул", "Модель"]
    DIALOG_CLASS = LocomotiveModelDialog
    NOT_FOUND_ERROR = LocomotiveModelNotFoundError
    PHOTO_COLUMN = 1

    def _repo(self):
        return self.services.locomotive_models

    def _photo_path(self, item) -> str | None:
        return item.image_path

    def _row_values(self, item) -> list[str]:
        return [
            item.manufacturer.name,
            str(item.code),
            "",  # фото ставится виджетом в reload()
            item.name,
        ]

    def _delete_prompt(self, item) -> str:
        return (
            f"Удалить локомотив {item.manufacturer.name} {item.code}?\n"
            f"Действие нельзя отменить."
        )


class LocomotivesTab(BaseTab):
    """Вкладка «Локомотивы».

    Фото живёт в модели, а не в локомотиве — берём через связь.
    """

    HEADERS = ["Система", "Номер", "Фото", "Производитель", "Артикул", "Модель"]
    DIALOG_CLASS = LocomotiveDialog
    NOT_FOUND_ERROR = LocomotiveNotFoundError
    PHOTO_COLUMN = 1

    def _repo(self):
        return self.services.locomotives

    def _photo_path(self, item) -> str | None:
        return item.model.image_path if item.model else None

    def _row_values(self, item) -> list[str]:
        model = item.model
        manufacturer = (
            model.manufacturer.name if model and model.manufacturer else NO_DATA
        )
        return [
            str(item.system),
            str(item.number),
            "",  # фото ставится виджетом в reload()
            manufacturer,
            str(model.code) if model else NO_DATA,
            model.name if model else NO_DATA,
        ]

    def _delete_prompt(self, item) -> str:
        return (
            f"Удалить локомотив {item.number} с системы {item.system}?\n"
            f"Действие нельзя отменить."
        )


class DetailsTab(BaseTab):
    """Вкладка «Детали»."""

    HEADERS = ["Производитель", "Артикул", "Наименование", "Остаток"]
    DIALOG_CLASS = DetailDialog
    NOT_FOUND_ERROR = DetailNotFoundError

    def _repo(self):
        return self.services.details

    def _row_values(self, item) -> list[str]:
        manufacturer = item.manufacturer.name if item.manufacturer else NO_DATA
        return [
            manufacturer,
            str(item.code),
            item.name,
            str(item.quantity_in_stock),
        ]

    def _delete_prompt(self, item) -> str:
        return f"Удалить деталь «{item.name}»?\nДействие нельзя отменить."


class MaintenancesTab(BaseTab):
    """Вкладка «Листы обслуживания»."""

    HEADERS = ["Локомотив", "Тип", "Комментарий", "Автор"]
    DIALOG_CLASS = MaintenanceDialog
    NOT_FOUND_ERROR = MaintenanceNotFoundError
    DELETE_LABEL = "Пометить на удаление"

    def _repo(self):
        return self.services.maintenances

    def _row_values(self, item) -> list[str]:
        locomotive_text = (
            f"{item.locomotive.system} {item.locomotive.number}"
            if item.locomotive else NO_DATA
        )
        type_text = item.maintenance_type.name if item.maintenance_type else NO_DATA
        author_text = f"{item.user.first_name} {item.user.last_name}" if item.user else NO_DATA
        return [
            locomotive_text,
            type_text,
            item.description or "",
            author_text,
        ]

    def _delete_prompt(self, item) -> str:
        return f"Пометить на удаление лист обслуживания {item.id}?"


class SuppliesTab(BaseTab):
    """Вкладка «Приход».

    В БД каждая деталь — отдельная запись Supply, но объединены они
    номером supply_number. Поэтому таблица показывает партии: одна строка =
    один номер прихода, а не одна запись.
    """

    HEADERS = ["Номер", "Дата", "Деталей", "Всего", "Автор"]
    ADD_LABEL = "Создать приход"
    EDIT_LABEL = "Изменить"
    DELETE_LABEL = "Удалить"

    def _delete_prompt(self, item) -> str:
        return (
            f"Удалить приход №{item['number']}?\n"
            f"Остатки деталей вернутся на склад."
        )

    def reload(self) -> None:
        """Перечитывает партии приходов и рисует таблицу.

        Переопределяем метод, потому что BaseTab рассчитан на «одна запись
        таблицы = одна запись БД», а здесь нужна группировка по supply_number.
        """
        # self._items — список «партий» в виде словарей, чтобы дальше
        # работать и с таблицей, и с _selected_item единообразно.
        self._items = self.services.supplies.list_batches()

        table = self.ui.base_table
        table.setColumnCount(len(self.HEADERS))
        table.setHorizontalHeaderLabels(self.HEADERS)
        table.setRowCount(len(self._items))

        for row, batch in enumerate(self._items):
            values = [
                str(batch["number"]),
                batch["created_at"].strftime("%d.%m.%Y %H:%M"),
                str(batch["positions"]),
                str(batch["total_quantity"]),
                batch["user_login"] or NO_DATA,
            ]
            for col, value in enumerate(values):
                table.setItem(row, col, QTableWidgetItem(value))

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
