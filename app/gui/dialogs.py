# -*- coding: utf-8 -*-
"""Диалоги создания и редактирования.

Каждый диалог принимает Services и работает только через репозитории.
Доменные исключения репозиториев показываются пользователю здесь.
"""

import logging
from datetime import UTC, datetime, time
from pathlib import Path

from PySide6.QtCore import QDate, QDateTime, QTime
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QFileDialog, QHeaderView,
    QMessageBox, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem,
)

from app.db.exceptions import (
    AlreadyAddedError,
    DetailNotFoundError,
    EntityInUseError,
    LastActiveAdminError,
    LocomotiveModelNotFoundError,
    LocomotiveNotFoundError,
    LoginAlreadyTakenError,
    MaintenanceNotFoundError,
    MaintenanceTypeNotFoundError,
    ManufacturerNotFoundError,
    SupplyNotFoundError,
    UserNotFoundError,
)
from app.db.models import Detail
from app.services import Services
from app.utils.image_storage import delete_image, save_model_image
from app.widgets.ui_detail_add_dialog import Ui_addDetail_dialog
from app.widgets.ui_locomotive_add_dialog import Ui_addLocomotive_dialog
from app.widgets.ui_locomotive_model_add_dialog import Ui_addLocomotiveModel_dialog
from app.widgets.ui_maintenance_add_dialog import Ui_addMaintenance_dialog
from app.widgets.ui_maintenance_type_add_dialog import Ui_addMaintenanceType_dialog
from app.widgets.ui_manufacturer_add_dialog import Ui_addManufacturer_dialog
from app.widgets.ui_supply_add_dialog import Ui_addSupply_dialog
from app.widgets.ui_user_edit_dialog import Ui_userEdit_dialog
from app.widgets.ui_user_management_dialog import Ui_usersManagement_dialog

logger = logging.getLogger(__name__)

IMAGE_FILTER = "Изображения (*.png *.jpg *.jpeg *.bmp)"
BOOL_YES = "Да"
BOOL_NO = "Нет"
NO_DATA = "—"

# Все доменные ошибки "запись не найдена". Используются в _try_save.
_NOT_FOUND = (
    DetailNotFoundError, LocomotiveModelNotFoundError, LocomotiveNotFoundError,
    MaintenanceNotFoundError, MaintenanceTypeNotFoundError, ManufacturerNotFoundError,
    UserNotFoundError, SupplyNotFoundError,
)


def _fill_combo(combo: QComboBox, items, label, data=lambda item: item.id) -> None:
    """Заполняет combo. label(item) даёт текст, data(item) значение."""
    combo.clear()
    for item in items:
        combo.addItem(label(item), data(item))


def _try_save(dialog: QDialog, action, not_found_msg: str = "Запись не найдена") -> bool:
    """Выполняет действие и переводит доменные ошибки в сообщения.

    Уникальность и валидацию проверяет репозиторий, здесь показываем
    готовый текст. Возвращает True при успехе.
    """
    try:
        action()
        return True
    except AlreadyAddedError as exc:
        QMessageBox.warning(dialog, "Внимание", str(exc))
    except _NOT_FOUND:
        QMessageBox.critical(dialog, "Ошибка", not_found_msg)
    return False


def _last_admin_message(will_be_admin: bool, will_be_active: bool) -> str:
    """Подбирает текст под то, что меняется у последнего админа."""
    if not will_be_admin and not will_be_active:
        return "Нельзя разжаловать и отключить последнего активного администратора"
    if not will_be_admin:
        return "Нельзя разжаловать последнего активного администратора"
    return "Нельзя отключить последнего активного администратора"


# Формат подписей в выпадающих списках. Префиксы короткие и однозначные:
# S system, N number, M manufacturer, Art article.
def _locomotive_label(loco) -> str:
    return f"S:{loco.system} N:{loco.number}"


def _model_label(model) -> str:
    man = model.manufacturer.name if model.manufacturer else NO_DATA
    return f"M:{man} Art:{model.code}"


def _detail_label(detail) -> str:
    man = detail.manufacturer.name if detail.manufacturer else NO_DATA
    return f"M:{man} Art:{detail.code} {detail.name}"


class DetailRowsEditor:
    """Управляет таблицей состава деталей.

    Одинаково используется в листах обслуживания и в приходах.
    Следит за настройкой таблицы, добавлением и удалением строк,
    чтением и записью состава.
    """

    def __init__(
        self, table: QTableWidget, add_button: QPushButton,
        remove_button: QPushButton, parent: QDialog, details: list[Detail],
    ) -> None:
        self.table = table
        self.parent = parent
        self.details = details

        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Деталь", "Количество"])
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        add_button.clicked.connect(lambda _=False: self.add_row())
        remove_button.clicked.connect(lambda _=False: self.remove_row())

    def add_row(self, detail_id: int | None = None, quantity: int = 1) -> None:
        """Добавляет строку выбора детали и количества."""
        if not self.details:
            QMessageBox.information(
                self.parent, "Нет деталей", "Сначала добавьте деталь в справочник."
            )
            return
        if detail_id is not None and all(d.id != detail_id for d in self.details):
            return

        row = self.table.rowCount()
        self.table.insertRow(row)

        combo = QComboBox(self.parent)
        for detail in self.details:
            combo.addItem(_detail_label(detail), detail.id)
        if detail_id is not None:
            combo.setCurrentIndex(combo.findData(detail_id))

        spin = QSpinBox(self.parent)
        spin.setRange(1, 9999)
        spin.setValue(max(1, quantity))
        self.table.setCellWidget(row, 0, combo)
        self.table.setCellWidget(row, 1, spin)

    def remove_row(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self.parent, "Внимание", "Выберите строку")
            return
        self.table.removeRow(row)

    def set_rows(self, rows: dict[int, int]) -> None:
        """Заменяет содержимое таблицы сохранённым составом."""
        self.table.setRowCount(0)
        for detail_id, quantity in rows.items():
            self.add_row(detail_id, quantity)

    def get_rows(self) -> dict[int, int]:
        """Собирает ID деталей и суммарные количества в словарь."""
        result: dict[int, int] = {}
        for row in range(self.table.rowCount()):
            combo = self.table.cellWidget(row, 0)
            spin = self.table.cellWidget(row, 1)
            if not isinstance(combo, QComboBox) or not isinstance(spin, QSpinBox):
                continue
            detail_id = combo.currentData()
            if detail_id is not None:
                result[detail_id] = result.get(detail_id, 0) + spin.value()
        return result


class MaintenanceTypeDialog(QDialog):
    """Создание и редактирование типа обслуживания."""

    def __init__(self, services: Services, current_user, item=None, parent=None):
        super().__init__(parent)
        self.services = services
        self.item = item

        self.ui = Ui_addMaintenanceType_dialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.accepted.connect(self._on_save)
        self.ui.buttonBox.rejected.connect(self.reject)

        if item is None:
            self.setWindowTitle("Новый тип обслуживания")
        else:
            self.setWindowTitle("Редактирование типа обслуживания")
            self.ui.maintenanceType_lineEdit.setText(item.name)

    def _on_save(self) -> None:
        name = self.ui.maintenanceType_lineEdit.text().strip()
        if not name:
            QMessageBox.warning(self, "Внимание", "Укажите название типа")
            return

        def action():
            if self.item is None:
                self.services.maintenance_types.create(name=name)
            else:
                self.services.maintenance_types.update(self.item.id, name=name)

        if _try_save(self, action):
            self.accept()


class ManufacturerDialog(QDialog):
    """Создание и редактирование производителя."""

    def __init__(self, services: Services, current_user, item=None, parent=None):
        super().__init__(parent)
        self.services = services
        self.item = item

        self.ui = Ui_addManufacturer_dialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.accepted.connect(self._on_save)
        self.ui.buttonBox.rejected.connect(self.reject)

        if item is None:
            self.setWindowTitle("Новый производитель")
        else:
            self.setWindowTitle("Редактирование производителя")
            self.ui.manufacturerName_lineEdit.setText(item.name)

    def _on_save(self) -> None:
        name = self.ui.manufacturerName_lineEdit.text().strip()
        if not name:
            QMessageBox.warning(self, "Внимание", "Укажите название производителя")
            return

        def action():
            if self.item is None:
                self.services.manufacturers.create(name=name)
            else:
                self.services.manufacturers.update(self.item.id, name=name)

        if _try_save(self, action):
            self.accept()


class LocomotiveModelDialog(QDialog):
    """Создание и редактирование модели локомотива."""

    def __init__(self, services: Services, current_user, item=None, parent=None):
        super().__init__(parent)
        self.services = services
        self.item = item
        # Путь файла, выбранного в этой сессии. None значит фото не менялось.
        self._picked_file: str | None = None

        self.ui = Ui_addLocomotiveModel_dialog()
        self.ui.setupUi(self)
        self.ui.addLocomotiveModel_buttonBox.accepted.connect(self._on_save)
        self.ui.addLocomotiveModel_buttonBox.rejected.connect(self.reject)
        self.ui.filepicker_toolButton.clicked.connect(self._on_pick_file)

        _fill_combo(
            self.ui.maufacturer_comboBox,
            self.services.manufacturers.list_all(),
            lambda man: man.name,
        )

        if item is None:
            self.setWindowTitle("Новая модель локомотива")
        else:
            self.setWindowTitle("Редактирование модели локомотива")
            self._load_data(item)

    def _load_data(self, item) -> None:
        self.ui.locomotiveCode_lineEdit.setText(str(item.code))
        self.ui.locomotiveModel_lineEdit.setText(item.name)
        index = self.ui.maufacturer_comboBox.findData(item.manufacturer_id)
        if index >= 0:
            self.ui.maufacturer_comboBox.setCurrentIndex(index)
        if item.image_path:
            # Показываем только имя файла, полный путь пользователю не нужен.
            self.ui.filepath_lineEdit.setText(Path(item.image_path).name)

    def _on_pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать изображение", "", IMAGE_FILTER,
        )
        if not path:
            return
        # При сохранении файл будет скопирован в data/images.
        self._picked_file = path
        self.ui.filepath_lineEdit.setText(Path(path).name)

    def _collect(self) -> dict:
        return {
            "code": self.ui.locomotiveCode_lineEdit.text().strip(),
            "manufacturer_id": self.ui.maufacturer_comboBox.currentData(),
            "name": self.ui.locomotiveModel_lineEdit.text().strip(),
        }

    def _validate(self, fields: dict) -> bool:
        if not fields["code"]:
            QMessageBox.warning(self, "Внимание", "Укажите артикул")
            return False
        try:
            int(fields["code"])
        except ValueError:
            QMessageBox.warning(self, "Внимание", "Артикул должен быть целым числом")
            return False
        if fields["manufacturer_id"] is None:
            QMessageBox.warning(self, "Внимание", "Выберите производителя")
            return False
        if not fields["name"]:
            QMessageBox.warning(self, "Внимание", "Укажите название модели")
            return False
        return True

    def _resolve_image_path(self, manufacturer_id: int, code: int) -> str | None:
        """Путь к фото для записи в БД. Без выбора файла возвращает прежний."""
        if self._picked_file is None:
            return self.item.image_path if self.item else None
        manufacturer = self.services.manufacturers.get_or_raise(manufacturer_id)
        return save_model_image(self._picked_file, manufacturer.name, code)

    def _on_save(self) -> None:
        fields = self._collect()
        if not self._validate(fields):
            return
        code = int(fields["code"])

        # Сначала файл, потом БД. Если фото не сохранилось, БД не трогаем.
        try:
            new_image_path = self._resolve_image_path(fields["manufacturer_id"], code)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить фото:\n{exc}")
            return

        payload = {
            "code": code,
            "manufacturer_id": fields["manufacturer_id"],
            "name": fields["name"],
            "image_path": new_image_path,
        }
        old_image_path = self.item.image_path if self.item else None

        def action():
            if self.item is None:
                self.services.locomotive_models.create(**payload)
            else:
                self.services.locomotive_models.update(self.item.id, **payload)

        if not _try_save(self, action):
            return
        # Старое фото больше не используется.
        if old_image_path and old_image_path != new_image_path:
            delete_image(old_image_path)
        self.accept()


class LocomotiveDialog(QDialog):
    """Создание и редактирование локомотива."""

    def __init__(self, services: Services, current_user, item=None, parent=None):
        super().__init__(parent)
        self.services = services
        self.item = item

        self.ui = Ui_addLocomotive_dialog()
        self.ui.setupUi(self)
        self.ui.addLocomotive_buttonBox.accepted.connect(self._on_save)
        self.ui.addLocomotive_buttonBox.rejected.connect(self.reject)

        _fill_combo(
            self.ui.locomotiveModel_comboBox,
            self.services.locomotive_models.list_all(),
            _model_label,
        )

        if item is None:
            self.setWindowTitle("Новый локомотив")
        else:
            self.setWindowTitle("Редактирование локомотива")
            self._load_data(item)

    def _load_data(self, item) -> None:
        self.ui.system_spinBox.setValue(int(item.system))
        self.ui.number_lineEdit.setText(str(item.number))
        index = self.ui.locomotiveModel_comboBox.findData(item.locomotive_model_id)
        if index >= 0:
            self.ui.locomotiveModel_comboBox.setCurrentIndex(index)

    def _collect(self) -> dict:
        return {
            "system": self.ui.system_spinBox.value(),
            "number": self.ui.number_lineEdit.text().strip(),
            "locomotive_model_id": self.ui.locomotiveModel_comboBox.currentData(),
        }

    def _validate(self, fields: dict) -> bool:
        if not fields["number"]:
            QMessageBox.warning(self, "Внимание", "Укажите номер локомотива")
            return False
        try:
            int(fields["number"])
        except ValueError:
            QMessageBox.warning(self, "Внимание", "Номер должен быть целым числом")
            return False
        if fields["locomotive_model_id"] is None:
            QMessageBox.warning(self, "Внимание", "Выберите модель")
            return False
        return True

    def _on_save(self) -> None:
        fields = self._collect()
        if not self._validate(fields):
            return

        payload = {
            "system": fields["system"],
            "number": int(fields["number"]),
            "locomotive_model_id": fields["locomotive_model_id"],
        }

        def action():
            if self.item is None:
                self.services.locomotives.create(**payload)
            else:
                self.services.locomotives.update(self.item.id, **payload)

        if _try_save(self, action):
            self.accept()


class DetailDialog(QDialog):
    """Создание и редактирование детали.

    Производитель вводится текстом. Если такого имени нет, репозиторий
    создаст нового производителя при сохранении детали.
    """

    def __init__(self, services: Services, current_user, item=None, parent=None):
        super().__init__(parent)
        self.services = services
        self.item = item

        self.ui = Ui_addDetail_dialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.accepted.connect(self._on_save)
        self.ui.buttonBox.rejected.connect(self.reject)

        _fill_combo(
            self.ui.detailManufacturer_comboBox,
            self.services.manufacturers.list_all(),
            lambda man: man.name or NO_DATA,
            data=lambda man: man.name,
        )

        if item is None:
            self.setWindowTitle("Новая деталь")
        else:
            self.setWindowTitle("Редактирование детали")
            self._load_data(item)

    def _load_data(self, item) -> None:
        self.ui.detailCode_lineEdit.setText(str(item.code))
        self.ui.detailName_lineEdit.setText(item.name)
        self.ui.detailCount_spinBox.setValue(item.quantity_in_stock)
        if item.manufacturer:
            self.ui.detailManufacturer_comboBox.setCurrentText(item.manufacturer.name)

    def _collect(self) -> dict:
        return {
            "code": self.ui.detailCode_lineEdit.text().strip(),
            "manufacturer_name": self.ui.detailManufacturer_comboBox.currentText().strip(),
            "name": self.ui.detailName_lineEdit.text().strip(),
            "quantity_in_stock": self.ui.detailCount_spinBox.text(),
        }

    def _validate(self, fields: dict) -> bool:
        if not fields["code"]:
            QMessageBox.warning(self, "Внимание", "Укажите артикул")
            return False
        try:
            int(fields["code"])
        except ValueError:
            QMessageBox.warning(self, "Внимание", "Артикул должен быть целым числом")
            return False
        if not fields["manufacturer_name"]:
            QMessageBox.warning(self, "Внимание", "Укажите производителя")
            return False
        if not fields["name"]:
            QMessageBox.warning(self, "Внимание", "Укажите наименование")
            return False
        try:
            quantity = int(fields["quantity_in_stock"] or "0")
        except ValueError:
            QMessageBox.warning(self, "Внимание", "Остаток должен быть целым числом")
            return False
        if quantity < 0:
            QMessageBox.warning(self, "Внимание", "Остаток не может быть отрицательным")
            return False
        return True

    def _on_save(self) -> None:
        fields = self._collect()
        if not self._validate(fields):
            return

        manufacturer = self.services.manufacturers.get_or_create_by_name(
            fields["manufacturer_name"]
        )
        payload = {
            "code": int(fields["code"]),
            "manufacturer_id": manufacturer.id,
            "name": fields["name"],
            "quantity_in_stock": int(fields["quantity_in_stock"] or "0"),
        }

        def action():
            if self.item is None:
                self.services.details.create(**payload)
            else:
                self.services.details.update(self.item.id, **payload)

        if _try_save(self, action):
            self.accept()


class MaintenanceDialog(QDialog):
    """Создание и редактирование листа обслуживания."""

    def __init__(self, services: Services, current_user, item=None, parent=None):
        super().__init__(parent)
        self.services = services
        self.current_user = current_user
        self.item = item

        self.ui = Ui_addMaintenance_dialog()
        self.ui.setupUi(self)
        self.ui.addMaintenance_buttonBox.accepted.connect(self._on_save)
        self.ui.addMaintenance_buttonBox.rejected.connect(self.reject)

        self.details = self.services.details.list_all()
        self.detail_rows = DetailRowsEditor(
            self.ui.detailsTable_tableWidget,
            self.ui.detailAdd_pushButton,
            self.ui.detailRemove_pushButton,
            self,
            self.details,
        )

        _fill_combo(
            self.ui.addMaintenanceLoco_comboBox,
            self.services.locomotives.list_all(),
            _locomotive_label,
        )
        _fill_combo(
            self.ui.addMaintenanceType_comboBox,
            self.services.maintenance_types.list_all(),
            lambda mtype: mtype.name,
        )

        if item is None:
            self.setWindowTitle("Новый лист обслуживания")
            self.ui.addMaintenanceDate_dateEdit.setDate(QDate.currentDate())
            # Минимум — полгода назад.
            min_date = QDate.currentDate().addMonths(-6)
            self.ui.addMaintenanceDate_dateEdit.setMinimumDateTime(
                QDateTime(min_date, QTime(9, 40, 1))
            )
            self.ui.addMaintenanceDate_dateEdit.setMinimumDate(min_date)
        else:
            self.setWindowTitle("Редактирование листа обслуживания")
            self._load_data(item)

    def _load_data(self, item) -> None:
        index = self.ui.addMaintenanceLoco_comboBox.findData(item.locomotive_id)
        if index >= 0:
            self.ui.addMaintenanceLoco_comboBox.setCurrentIndex(index)
        index = self.ui.addMaintenanceType_comboBox.findData(item.maintenance_type_id)
        if index >= 0:
            self.ui.addMaintenanceType_comboBox.setCurrentIndex(index)
        if item.description:
            self.ui.addMaintenanceComment_textEdit.setPlainText(item.description)
        if item.date is not None:
            self.ui.addMaintenanceDate_dateEdit.setDate(item.date.date())
        self.detail_rows.set_rows(self.services.maintenances.get_rows(item.id))

    def _collect(self) -> dict:
        return {
            "locomotive_id": self.ui.addMaintenanceLoco_comboBox.currentData(),
            "maintenance_type_id": self.ui.addMaintenanceType_comboBox.currentData(),
            "description": self.ui.addMaintenanceComment_textEdit.toPlainText().strip(),
            "date": datetime.combine(
                self.ui.addMaintenanceDate_dateEdit.date().toPython(),
                time.min,
                tzinfo=UTC,
            ),
        }

    def _validate(self, _fields: dict) -> bool:
        if self.ui.addMaintenanceLoco_comboBox.currentData() is None:
            QMessageBox.warning(self, "Внимание", "Выберите локомотив")
            return False
        if self.ui.addMaintenanceType_comboBox.currentData() is None:
            QMessageBox.warning(self, "Внимание", "Выберите тип обслуживания")
            return False
        return True

    def _payload(self, fields: dict) -> dict:
        # user_id проставляется только при создании. При правке не трогаем.
        if self.item is None:
            return {**fields, "user_id": self.current_user.id}
        return fields

    def _save(self, fields: dict, allow_negative: bool = False) -> dict | None:
        """Сохраняет лист. Возвращает недостачи или None при ошибке."""
        try:
            return self.services.maintenances.save_with_details(
                maintenance_id=self.item.id if self.item else None,
                fields=self._payload(fields),
                rows=self.detail_rows.get_rows(),
                allow_negative_stock=allow_negative,
            )
        except MaintenanceNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Запись не найдена")
            return None

    def _on_save(self) -> None:
        fields = self._collect()
        if not self._validate(fields):
            return

        deficits = self._save(fields)
        if deficits is None:
            return
        if not deficits:
            self.accept()
            return

        # Есть нехватка на складе. Спрашиваем разрешение на минус.
        details_by_id = {d.id: d for d in self.details}
        lines = []
        for detail_id, deficit in deficits.items():
            detail = details_by_id.get(detail_id)
            label = _detail_label(detail) if detail else f"Деталь {detail_id}"
            lines.append(f"{label}: не хватает {deficit} шт.")

        reply = QMessageBox.warning(
            self,
            "Недостаточно деталей",
            f"На складе недостаточно деталей:\n{chr(10).join(lines)}"
            "\nПродолжить и разрешить отрицательный остаток?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        if self._save(fields, allow_negative=True) is not None:
            self.accept()


class _UserDialogBase(QDialog):
    """Общая основа для создания и редактирования пользователя.

    Разделяет одну и ту же форму. Наследники переопределяют только
    валидацию и действие сохранения.
    """

    def __init__(self, services: Services, parent=None):
        super().__init__(parent)
        self.services = services

        self.ui = Ui_userEdit_dialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.accepted.connect(self._on_save)
        self.ui.buttonBox.rejected.connect(self.reject)

    def _fields(self) -> dict:
        return {
            "login": self.ui.login_lineEdit.text().strip().lower(),
            "first_name": self.ui.firstName_lineEdit.text().strip(),
            "last_name": self.ui.lastName_lineEdit.text().strip(),
            "password": self.ui.newPass_lineEdit.text(),
            "password_confirm": self.ui.newPassConfirm_lineEdit.text(),
            "is_admin": self.ui.isAdmin_checkBox.isChecked(),
            "is_active": not self.ui.disabled_checkBox.isChecked(),
        }

    def _validate(self, fields: dict) -> bool:
        if not fields["login"]:
            QMessageBox.warning(self, "Внимание", "Логин не может быть пустым")
            return False
        if fields["password"] != fields["password_confirm"]:
            QMessageBox.warning(self, "Внимание", "Пароли не совпадают")
            return False
        return True

    def _save_action(self, fields: dict) -> None:
        raise NotImplementedError

    def _on_save(self) -> None:
        fields = self._fields()
        if not self._validate(fields):
            return
        try:
            self._save_action(fields)
        except LoginAlreadyTakenError:
            QMessageBox.warning(self, "Внимание", "Этот логин уже занят")
            return
        except LastActiveAdminError:
            QMessageBox.warning(
                self, "Внимание",
                _last_admin_message(fields["is_admin"], fields["is_active"]),
            )
            return
        except UserNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Пользователь не найден")
            return
        self.accept()


class UserEditDialog(_UserDialogBase):
    """Редактирование существующего пользователя.

    В обычном режиме админ и активность скрыты, в admin_mode доступны.
    """

    def __init__(self, services: Services, target_user, admin_mode: bool = False, parent=None):
        super().__init__(services, parent)
        self.user = target_user
        self.admin_mode = admin_mode

        if not admin_mode:
            self.ui.isAdmin_checkBox.setVisible(False)
            self.ui.disabled_checkBox.setVisible(False)

        self._load_data()

    def _load_data(self) -> None:
        self.ui.login_lineEdit.setText(self.user.login)
        self.ui.firstName_lineEdit.setText(self.user.first_name or "")
        self.ui.lastName_lineEdit.setText(self.user.last_name or "")
        self.ui.isAdmin_checkBox.setChecked(bool(self.user.is_admin))
        self.ui.disabled_checkBox.setChecked(not self.user.is_active)

    def _validate(self, fields: dict) -> bool:
        if not fields["login"]:
            QMessageBox.warning(self, "Внимание", "Логин не может быть пустым")
            return False
        # При редактировании пароль необязателен.
        if fields["password"] and fields["password"] != fields["password_confirm"]:
            QMessageBox.warning(self, "Внимание", "Пароли не совпадают")
            return False
        return True

    def _save_action(self, fields: dict) -> None:
        self.services.users.update(
            self.user.id,
            login=fields["login"],
            first_name=fields["first_name"],
            last_name=fields["last_name"],
            password=fields["password"] or None,
            is_admin=fields["is_admin"] if self.admin_mode else None,
            is_active=fields["is_active"] if self.admin_mode else None,
        )


class UserCreateDialog(_UserDialogBase):
    """Создание нового пользователя. Пароль обязателен."""

    def __init__(self, services: Services, current_user, parent=None):
        super().__init__(services, parent)
        self.setWindowTitle("Новый пользователь")
        self.ui.newPass_label.setText("Пароль")
        self.ui.newPassConfirm_label.setText("Подтвердите пароль")

    def _validate(self, fields: dict) -> bool:
        if not super()._validate(fields):
            return False
        if not fields["password"]:
            QMessageBox.warning(self, "Внимание", "Пароль не может быть пустым")
            return False
        return True

    def _save_action(self, fields: dict) -> None:
        self.services.users.create(
            login=fields["login"],
            password=fields["password"],
            first_name=fields["first_name"],
            last_name=fields["last_name"],
            is_admin=fields["is_admin"],
            is_active=fields["is_active"],
        )


class UserManagementDialog(QDialog):
    """Окно со списком пользователей и операциями над ними."""

    HEADERS = ("ID", "Логин", "Имя", "Фамилия", "Админ", "Отключен")

    def __init__(self, services: Services, current_user, parent=None):
        super().__init__(parent)
        self.services = services
        self.current_user = current_user

        self.ui = Ui_usersManagement_dialog()
        self.ui.setupUi(self)

        table = self.ui.users_tableWidget
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.ui.userAdd_button.clicked.connect(self._on_add)
        self.ui.userEdit_button.clicked.connect(self._on_edit)
        self.ui.userDelete_button.clicked.connect(self._on_delete)

        self._users: list = []
        self._reload()

    def _reload(self) -> None:
        table = self.ui.users_tableWidget
        self._users = self.services.users.list_all()
        table.setColumnCount(len(self.HEADERS))
        table.setHorizontalHeaderLabels(list(self.HEADERS))
        table.setRowCount(len(self._users))
        for row, user in enumerate(self._users):
            values = [
                str(user.id), user.login,
                user.first_name or "", user.last_name or "",
                BOOL_YES if user.is_admin else BOOL_NO,
                BOOL_YES if not user.is_active else BOOL_NO,
            ]
            for col, value in enumerate(values):
                table.setItem(row, col, QTableWidgetItem(value))

    def _selected(self):
        row = self.ui.users_tableWidget.currentRow()
        if row < 0 or row >= len(self._users):
            return None
        return self._users[row]

    def _on_add(self) -> None:
        dialog = UserCreateDialog(self.services, self.current_user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._reload()

    def _on_edit(self) -> None:
        user = self._selected()
        if user is None:
            QMessageBox.information(self, "Внимание", "Выберите пользователя")
            return
        dialog = UserEditDialog(self.services, user, admin_mode=True, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._reload()

    def _on_delete(self) -> None:
        user = self._selected()
        if user is None:
            QMessageBox.information(self, "Внимание", "Выберите пользователя")
            return
        if user.id == self.current_user.id:
            QMessageBox.warning(self, "Внимание", "Нельзя удалить самого себя")
            return

        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить пользователя «{user.login}»?\nДействие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self.services.users.delete(user.id)
        except LastActiveAdminError:
            QMessageBox.warning(
                self, "Внимание",
                "Нельзя удалить последнего активного администратора",
            )
            return
        except EntityInUseError as exc:
            QMessageBox.warning(self, "Внимание", str(exc))
            return
        except UserNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Пользователь уже удалён")
            return

        self._reload()


class SupplyDialog(QDialog):
    """Создание и редактирование прихода деталей на склад.

    Один supply_number это одна партия, несколько строк Supply.
    Номер новой партии назначается сервисом автоматически.
    """

    def __init__(self, services: Services, current_user,
                 supply_number: int | None = None, parent=None):
        super().__init__(parent)
        self.services = services
        self.current_user = current_user
        # None — новая партия. Число — редактирование существующей.
        self.supply_number = supply_number

        self.ui = Ui_addSupply_dialog()
        self.ui.setupUi(self)
        self.ui.addSupply_buttonBox.accepted.connect(self._on_save)
        self.ui.addSupply_buttonBox.rejected.connect(self.reject)

        self.details = self.services.details.list_all()
        self.detail_rows = DetailRowsEditor(
            self.ui.detailsTable_tableWidget,
            self.ui.detailAdd_pushButton,
            self.ui.detailRemove_pushButton,
            self,
            self.details,
        )

        if supply_number is None:
            self.setWindowTitle("Новый приход")
        else:
            self.setWindowTitle(f"Редактирование прихода №{supply_number}")
            self.detail_rows.set_rows(
                self.services.supplies.get_rows_by_number(supply_number)
            )

    def _on_save(self) -> None:
        rows = self.detail_rows.get_rows()
        if not rows:
            QMessageBox.warning(self, "Внимание", "Добавьте хотя бы одну деталь")
            return

        def action():
            if self.supply_number is None:
                self.services.supplies.create_batch(
                    rows=rows, user_id=self.current_user.id,
                )
            else:
                self.services.supplies.update_batch(
                    supply_number=self.supply_number, rows=rows,
                )

        if _try_save(self, action):
            self.accept()
