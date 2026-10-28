# -*- coding: utf-8 -*-
"""
Диалоги создания и редактирования.
"""

import logging
from datetime import UTC, datetime, time
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QDate, QDateTime, QTime
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QFileDialog, QHeaderView,
    QMessageBox, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem,
)

from app.db.exceptions import (
    AlreadyAddedError, DetailNotFoundError, EntityInUseError,
    LastActiveAdminError, LocomotiveModelNotFoundError, LocomotiveNotFoundError,
    LoginAlreadyTakenError, MaintenanceNotFoundError,
    MaintenanceTypeNotFoundError, ManufacturerNotFoundError,
    SupplyNotFoundError, UserNotFoundError,
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
PLACEHOLDER = "— выберите —"

_NOT_FOUND = (
    DetailNotFoundError, LocomotiveModelNotFoundError, LocomotiveNotFoundError,
    MaintenanceNotFoundError, MaintenanceTypeNotFoundError, ManufacturerNotFoundError,
    UserNotFoundError, SupplyNotFoundError,
)


def _fill_combo(
    combo: QComboBox,
    items: list,
    label_func: Callable[[Any], str],
    data_func: Callable[[Any], Any] = lambda item: item.id,
    placeholder: str | None = PLACEHOLDER,
    sort_key: Callable[[Any], Any] | None = None,
) -> None:
    """Заполняет combo, настраивая плейсхолдер для обычного или редактируемого вида.

    sort_key — необязательный ключ сортировки элементов (применяется до вставки
    плейсхолдера, чтобы заглушка всегда оставалась на индексе 0).
    """
    combo.clear()

    if sort_key is not None:
        items = sorted(items, key=sort_key)

    if combo.isEditable():
        for item in items:
            combo.addItem(label_func(item), data_func(item))
        combo.setCurrentIndex(-1)
        combo.setEditText("")
        if placeholder is not None:
            combo.lineEdit().setPlaceholderText(placeholder)
    else:
        if placeholder is not None:
            combo.addItem(placeholder, None)
        for item in items:
            combo.addItem(label_func(item), data_func(item))
        combo.setCurrentIndex(0)


def _select_combo_data(combo: QComboBox, value: Any) -> None:
    index = combo.findData(value)
    if index >= 0:
        combo.setCurrentIndex(index)


def _try_save(
    dialog: QDialog,
    action: Callable[[], None],
    not_found_msg: str = "Запись не найдена",
) -> bool:
    try:
        action()
        return True
    except AlreadyAddedError as exc:
        QMessageBox.warning(dialog, "Внимание", str(exc))
    except _NOT_FOUND:
        QMessageBox.critical(dialog, "Ошибка", not_found_msg)
    return False


def _validate_required(value: str, field_name: str) -> str | None:
    if not value.strip():
        return f"Укажите {field_name.lower()}"
    return None


def _validate_int(value: str, field_name: str, min_value: int | None = None) -> str | None:
    if not value.strip():
        return f"Укажите {field_name.lower()}"
    try:
        parsed_value = int(value)
    except ValueError:
        return f"{field_name.capitalize()} должен быть целым числом"

    if min_value is not None and parsed_value < min_value:
        return f"{field_name.capitalize()} не может быть меньше {min_value}"
    return None


def _validate_model_fields(fields: dict) -> str | None:
    if error := _validate_int(fields["code"], "Артикул", min_value=0): return error
    if fields["manufacturer_id"] is None: return "Выберите производителя"
    if error := _validate_required(fields["name"], "название модели"): return error
    return None


def _validate_locomotive_fields(fields: dict) -> str | None:
    if error := _validate_int(fields["number"], "Номер локомотива", min_value=0): return error
    if fields["locomotive_model_id"] is None: return "Выберите модель"
    return None


def _validate_detail_fields(fields: dict) -> str | None:
    if error := _validate_detail_code(fields["code"]): return error
    if fields["manufacturer_id"] is None: return "Выберите производителя"
    if error := _validate_required(fields["name"], "наименование"): return error
    if error := _validate_int(fields["quantity_in_stock"], "Остаток", min_value=0): return error
    return None


def _validate_maintenance_fields(fields: dict) -> str | None:
    if fields["locomotive_id"] is None: return "Выберите локомотив"
    if fields["maintenance_type_id"] is None: return "Выберите тип обслуживания"
    return None

def _validate_detail_code(value: str) -> str | None:
    value = value.strip()
    if not value:
        return "Укажите артикул"
    if len(value) > 16:
        return "Артикул не может быть длиннее 16 символов"
    if any(ch not in "0123456789-" for ch in value):
        return "Артикул может содержать только цифры и дефис"
    return None

def _last_admin_message(will_be_admin: bool, will_be_active: bool) -> str:
    if not will_be_admin and not will_be_active:
        return "Нельзя разжаловать и отключить последнего активного администратора"
    if not will_be_admin:
        return "Нельзя разжаловать последнего активного администратора"
    return "Нельзя отключить последнего активного администратора"


def _locomotive_label(loco) -> str:
    return f"S:{loco.system} N:{loco.number}"


def _model_label(model) -> str:
    man = model.manufacturer.name if model.manufacturer else NO_DATA
    return f"{man} {model.code}"


def _detail_label(detail) -> str:
    man = detail.manufacturer.name if detail.manufacturer else NO_DATA
    return f"M: {man}  Art: {detail.code}  Name: {detail.name}"


class DetailRowsEditor:
    """Управляет таблицей состава деталей в листах обслуживания и приходах."""

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
        if not self.details:
            QMessageBox.information(
                self.parent, "Нет деталей", "Сначала добавьте деталь в справочник."
            )
            return
        if detail_id is not None and not any(d.id == detail_id for d in self.details):
            return

        row = self.table.rowCount()
        self.table.insertRow(row)

        combo = QComboBox(self.parent)
        _fill_combo(combo, self.details, _detail_label, placeholder=PLACEHOLDER)

        if detail_id is not None:
            _select_combo_data(combo, detail_id)

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
        self.table.setRowCount(0)
        for detail_id, quantity in rows.items():
            self.add_row(detail_id, quantity)

    def get_rows(self) -> dict[int, int]:
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

    def has_unselected_rows(self) -> bool:
        return any(
            isinstance(combo := self.table.cellWidget(row, 0), QComboBox) and combo.currentData() is None
            for row in range(self.table.rowCount())
        )


class MaintenanceTypeDialog(QDialog):
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
        if error := _validate_required(name, "название типа"):
            QMessageBox.warning(self, "Внимание", error)
            return

        def action():
            if self.item is None:
                self.services.maintenance_types.create(name=name)
            else:
                self.services.maintenance_types.update(self.item.id, name=name)

        if _try_save(self, action):
            self.accept()


class ManufacturerDialog(QDialog):
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
        if error := _validate_required(name, "название производителя"):
            QMessageBox.warning(self, "Внимание", error)
            return

        def action():
            if self.item is None:
                self.services.manufacturers.create(name=name)
            else:
                self.services.manufacturers.update(self.item.id, name=name)

        if _try_save(self, action):
            self.accept()


class LocomotiveModelDialog(QDialog):
    def __init__(self, services: Services, current_user, item=None, parent=None):
        super().__init__(parent)
        self.services = services
        self.item = item
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
        _select_combo_data(self.ui.maufacturer_comboBox, item.manufacturer_id)
        if item.image_path:
            self.ui.filepath_lineEdit.setText(Path(item.image_path).name)

    def _on_pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать изображение", "", IMAGE_FILTER)
        if not path:
            return
        self._picked_file = path
        self.ui.filepath_lineEdit.setText(Path(path).name)

    def _collect(self) -> dict:
        return {
            "code": self.ui.locomotiveCode_lineEdit.text().strip(),
            "manufacturer_id": self.ui.maufacturer_comboBox.currentData(),
            "name": self.ui.locomotiveModel_lineEdit.text().strip(),
        }

    def _resolve_image_path(self, manufacturer_id: int, code: int) -> str | None:
        if self._picked_file is None:
            return self.item.image_path if self.item else None
        manufacturer = self.services.manufacturers.get_or_raise(manufacturer_id)
        return save_model_image(self._picked_file, manufacturer.name, code)

    def _on_save(self) -> None:
        fields = self._collect()
        if error := _validate_model_fields(fields):
            QMessageBox.warning(self, "Внимание", error)
            return

        code = int(fields["code"])
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
        if old_image_path and old_image_path != new_image_path:
            delete_image(old_image_path)
        self.accept()


class LocomotiveDialog(QDialog):
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
            sort_key=lambda m: (m.manufacturer.name.casefold(), m.code),
        )

        if item is None:
            self.setWindowTitle("Новый локомотив")
        else:
            self.setWindowTitle("Редактирование локомотива")
            self._load_data(item)

    def _load_data(self, item) -> None:
        self.ui.system_spinBox.setValue(int(item.system))
        self.ui.number_lineEdit.setText(str(item.number))
        _select_combo_data(self.ui.locomotiveModel_comboBox, item.locomotive_model_id)
        if getattr(item, "comment", None):
            self.ui.comment_textEdit.setPlainText(item.comment)
        if getattr(item, "kind", None):
            self.ui.type_lineEdit.setText(item.kind)

    def _collect(self) -> dict:
        return {
            "system": self.ui.system_spinBox.value(),
            "number": self.ui.number_lineEdit.text().strip(),
            "locomotive_model_id": self.ui.locomotiveModel_comboBox.currentData(),
            "comment": self.ui.comment_textEdit.toPlainText().strip(),
            "kind": self.ui.type_lineEdit.text().strip(),
        }

    def _on_save(self) -> None:
        fields = self._collect()
        if error := _validate_locomotive_fields(fields):
            QMessageBox.warning(self, "Внимание", error)
            return

        payload = {
            "system": fields["system"],
            "number": int(fields["number"]),
            "locomotive_model_id": fields["locomotive_model_id"],
            "comment": fields["comment"] or None,
            "kind": fields["kind"] or None,
        }

        def action():
            if self.item is None:
                self.services.locomotives.create(**payload)
            else:
                self.services.locomotives.update(self.item.id, **payload)

        if _try_save(self, action):
            self.accept()


class DetailDialog(QDialog):
    """Создание и редактирование детали."""

    def __init__(self, services: Services, current_user, item=None, parent=None):
        super().__init__(parent)
        self.services = services
        self.item = item

        self.ui = Ui_addDetail_dialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.accepted.connect(self._on_save)
        self.ui.buttonBox.rejected.connect(self.reject)

        # Производитель только выбирается из списка
        self.ui.detailManufacturer_comboBox.setEditable(False)
        _fill_combo(
            self.ui.detailManufacturer_comboBox,
            self.services.manufacturers.list_all(),
            lambda man: man.name or NO_DATA,
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
            _select_combo_data(self.ui.detailManufacturer_comboBox, item.manufacturer_id)

    def _collect(self) -> dict:
        return {
            "code": self.ui.detailCode_lineEdit.text().strip(),
            "manufacturer_id": self.ui.detailManufacturer_comboBox.currentData(),
            "name": self.ui.detailName_lineEdit.text().strip(),
            "quantity_in_stock": self.ui.detailCount_spinBox.text(),
        }

    def _on_save(self) -> None:
        fields = self._collect()
        if error := _validate_detail_fields(fields):
            QMessageBox.warning(self, "Внимание", error)
            return

        payload = {
            "code": fields["code"].strip(),
            "manufacturer_id": fields["manufacturer_id"],
            "name": fields["name"],
            "quantity_in_stock": int(fields["quantity_in_stock"]),
        }

        def action():
            if self.item is None:
                self.services.details.create(**payload)
            else:
                self.services.details.update(self.item.id, **payload)

        if _try_save(self, action):
            self.accept()


class MaintenanceDialog(QDialog):
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
            min_date = QDate.currentDate().addMonths(-6)
            self.ui.addMaintenanceDate_dateEdit.setMinimumDateTime(QDateTime(min_date, QTime(9, 40, 1)))
            self.ui.addMaintenanceDate_dateEdit.setMinimumDate(min_date)
        else:
            self.setWindowTitle("Редактирование листа обслуживания")
            self._load_data(item)

    def _load_data(self, item) -> None:
        _select_combo_data(self.ui.addMaintenanceLoco_comboBox, item.locomotive_id)
        _select_combo_data(self.ui.addMaintenanceType_comboBox, item.maintenance_type_id)
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
                self.ui.addMaintenanceDate_dateEdit.date().toPython(), time.min, tzinfo=UTC
            ),
        }

    def _save(self, fields: dict, allow_negative: bool = False) -> dict | None:
        payload = {**fields, "user_id": self.current_user.id} if self.item is None else fields
        try:
            return self.services.maintenances.save_with_details(
                maintenance_id=self.item.id if self.item else None,
                fields=payload,
                rows=self.detail_rows.get_rows(),
                allow_negative_stock=allow_negative,
            )
        except MaintenanceNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Запись не найдена")
            return None

    def _confirm_negative_stock(self, deficits: dict[int, int]) -> bool:
        details_by_id = {d.id: d for d in self.details}
        lines = []
        for detail_id, deficit in deficits.items():
            detail = details_by_id.get(detail_id)
            label = _detail_label(detail) if detail else f"Деталь {detail_id}"
            lines.append(f"{label}: не хватает {deficit} шт.")

        msg = (
            f"На складе недостаточно деталей:\n{chr(10).join(lines)}"
            "\nПродолжить и разрешить отрицательный остаток?"
        )
        reply = QMessageBox.warning(
            self, "Недостаточно деталей", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def _save_and_handle_deficits(self, fields: dict) -> bool:
        deficits = self._save(fields)
        if deficits is None:
            return False
        if not deficits:
            return True
        if not self._confirm_negative_stock(deficits):
            return False
        return self._save(fields, allow_negative=True) is not None

    def _on_save(self) -> None:
        fields = self._collect()
        if error := _validate_maintenance_fields(fields):
            QMessageBox.warning(self, "Внимание", error)
            return
        if self.detail_rows.has_unselected_rows():
            QMessageBox.warning(self, "Внимание", "В одной из строк не выбрана деталь")
            return

        if self._save_and_handle_deficits(fields):
            self.accept()


class _UserDialogBase(QDialog):
    require_password: bool = False

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

    def _validate(self, fields: dict) -> str | None:
        if error := _validate_required(fields["login"], "Логин"): return error
        if self.require_password and not fields["password"]:
            return "Пароль не может быть пустым"
        if fields["password"] and fields["password"] != fields["password_confirm"]:
            return "Пароли не совпадают"
        return None

    def _save_action(self, fields: dict) -> None:
        raise NotImplementedError

    def _on_save(self) -> None:
        fields = self._fields()
        if error := self._validate(fields):
            QMessageBox.warning(self, "Внимание", error)
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
    def __init__(self, services: Services, target_user, admin_mode: bool = False, parent=None):
        super().__init__(services, parent)
        self.user = target_user
        self.admin_mode = admin_mode

        if not admin_mode:
            self.ui.isAdmin_checkBox.setVisible(False)
            self.ui.disabled_checkBox.setVisible(False)

        self.ui.login_lineEdit.setText(self.user.login)
        self.ui.firstName_lineEdit.setText(self.user.first_name or "")
        self.ui.lastName_lineEdit.setText(self.user.last_name or "")
        self.ui.isAdmin_checkBox.setChecked(bool(self.user.is_admin))
        self.ui.disabled_checkBox.setChecked(not self.user.is_active)

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
    require_password = True

    def __init__(self, services: Services, current_user, parent=None):
        super().__init__(services, parent)
        self.setWindowTitle("Новый пользователь")
        self.ui.newPass_label.setText("Пароль")
        self.ui.newPassConfirm_label.setText("Подтвердите пароль")

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
        return self._users[row] if 0 <= row < len(self._users) else None

    def _on_add(self) -> None:
        dialog = UserCreateDialog(self.services, self.current_user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._reload()

    def _on_edit(self) -> None:
        if not (user := self._selected()):
            QMessageBox.information(self, "Внимание", "Выберите пользователя")
            return
        dialog = UserEditDialog(self.services, user, admin_mode=True, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._reload()

    def _on_delete(self) -> None:
        if not (user := self._selected()):
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
            QMessageBox.warning(self, "Внимание", "Нельзя удалить последнего активного администратора")
            return
        except EntityInUseError as exc:
            QMessageBox.warning(self, "Внимание", str(exc))
            return
        except UserNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Пользователь уже удалён")
            return

        self._reload()


class SupplyDialog(QDialog):
    def __init__(
        self, services: Services, current_user,
        supply_number: int | None = None, parent=None
    ):
        super().__init__(parent)
        self.services = services
        self.current_user = current_user
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
        if self.detail_rows.has_unselected_rows():
            QMessageBox.warning(self, "Внимание", "В одной из строк не выбрана деталь")
            return

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
