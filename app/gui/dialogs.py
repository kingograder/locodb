# -*- coding: utf-8 -*-
"""Диалоги создания и редактирования.

Каждый диалог принимает Services и работает только через репозитории.
Диалоги не открывают сессии и не ловят SQLAlchemyError — эти заботы
полностью лежат на слое репозиториев.
"""

from dataclasses import dataclass

from PySide6.QtCore import QDate, QDateTime, QTime

from app.db.models import Detail
from app.utils.image_storage import delete_image, save_model_image
from datetime import UTC, datetime, time
from pathlib import Path
import logging

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
)
from app.db.exceptions import (
    DetailNotFoundError,
    EntityInUseError,
    LastActiveAdminError,
    LocomotiveModelNotFoundError,
    LocomotiveNotFoundError,
    MaintenanceNotFoundError,
    MaintenanceTypeNotFoundError,
    ManufacturerNotFoundError,
    UserNotFoundError,
    SupplyNotFoundError,
)
from app.services import Services
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


def _last_admin_message(will_be_admin: bool, will_be_active: bool) -> str:
    """Подбирает текст сообщения под то, что именно меняется у последнего админа."""
    if not will_be_admin and not will_be_active:
        return "Нельзя разжаловать и отключить последнего активного администратора"
    if not will_be_admin:
        return "Нельзя разжаловать последнего активного администратора"
    return "Нельзя отключить последнего активного администратора"


class DetailRowsEditor:
    """Одинаково настраивает и читает таблицы количества деталей."""

    def __init__(
        self,
        table: QTableWidget,
        add_button: QPushButton,
        remove_button: QPushButton,
        parent: QDialog,
        details: list[Detail],
    ) -> None:
        self.table = table
        self.parent = parent
        self.details = details

        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Деталь", "Количество"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        add_button.clicked.connect(lambda _checked=False: self.add_row())
        remove_button.clicked.connect(lambda _checked=False: self.remove_row())
        self._add_button = add_button
        self._remove_button = remove_button

    def add_row(self, detail_id: int | None = None, quantity: int = 1) -> None:
        """Добавляет деталь и восстанавливает количество, если оно задано."""
        if not self.details:
            QMessageBox.information(
                self.parent, "Нет деталей", "Сначала добавьте деталь в справочник."
            )
            return
        if detail_id is not None and all(
            detail.id != detail_id for detail in self.details
        ):
            return

        row = self.table.rowCount()
        self.table.insertRow(row)

        combo = QComboBox(self.parent)
        for detail in self.details:
            manufacturer = detail.manufacturer.name if detail.manufacturer else NO_DATA
            combo.addItem(f"{manufacturer} · {detail.code} · {detail.name}", detail.id)
        if detail_id is not None:
            combo.setCurrentIndex(combo.findData(detail_id))

        spin = QSpinBox(self.parent)
        spin.setRange(1, 9999)
        spin.setValue(max(1, quantity))
        self.table.setCellWidget(row, 0, combo)
        self.table.setCellWidget(row, 1, spin)

    def remove_row(self) -> None:
        """Удаляет выбранную позицию."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(
                self.parent, "Внимание", "Выберите строку для удаления"
            )
            return
        self.table.removeRow(row)

    def set_rows(self, rows: dict[int, int]) -> None:
        """Заменяет содержимое таблицы сохранённым составом."""
        self.table.setRowCount(0)
        for detail_id, quantity in rows.items():
            self.add_row(detail_id, quantity)

    def get_rows(self) -> dict[int, int]:
        """Собирает значения таблицы в словарь ID детали и количества."""
        rows: dict[int, int] = {}
        for row in range(self.table.rowCount()):
            combo = self.table.cellWidget(row, 0)
            spin = self.table.cellWidget(row, 1)

            if not isinstance(combo, QComboBox) or not isinstance(spin, QSpinBox):
                continue

            detail_id = combo.currentData()
            if detail_id is not None:
                rows[detail_id] = rows.get(detail_id, 0) + spin.value()
        return rows


class MaintenanceTypeDialog(QDialog):
    """Диалог создания и редактирования типа обслуживания."""

    def __init__(self, services: Services, current_user, item=None, parent=None):
        super().__init__(parent)
        self.services = services
        self.current_user = current_user
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
        """Сохраняет тип обслуживания."""
        name = self.ui.maintenanceType_lineEdit.text().strip()
        if not name:
            QMessageBox.warning(self, "Внимание", "Укажите название типа")
            return

        try:
            if self.item is None:
                self.services.maintenance_types.create(name=name)
            else:
                self.services.maintenance_types.update(self.item.id, name=name)
        except MaintenanceTypeNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Запись не найдена")
            return

        self.accept()


class ManufacturerDialog(QDialog):
    """Диалог создания и редактирования производителя."""

    def __init__(self, services: Services, current_user, item=None, parent=None):
        super().__init__(parent)
        self.services = services
        self.current_user = current_user
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
        """Сохраняет производителя."""
        name = self.ui.manufacturerName_lineEdit.text().strip()
        if not name:
            QMessageBox.warning(self, "Внимание", "Укажите название производителя")
            return

        try:
            if self.item is None:
                self.services.manufacturers.create(name=name)
            else:
                self.services.manufacturers.update(self.item.id, name=name)
        except ManufacturerNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Запись не найдена")
            return

        self.accept()


class LocomotiveModelDialog(QDialog):
    """Диалог создания и редактирования модели локомотива."""

    def __init__(self, services: Services, current_user, item=None, parent=None):
        super().__init__(parent)
        self.services = services
        self.current_user = current_user
        self.item = item

        # Локальный путь к файлу, выбранному пользователем в этой сессии.
        # None означает «фото не менялось»: сохраняем то, что уже было в БД.
        self._picked_file: str | None = None

        self.ui = Ui_addLocomotiveModel_dialog()
        self.ui.setupUi(self)

        self.ui.addLocomotiveModel_buttonBox.accepted.connect(self._on_save)
        self.ui.addLocomotiveModel_buttonBox.rejected.connect(self.reject)
        self.ui.filepicker_toolButton.clicked.connect(self._on_pick_file)

        self._load_manufacturers()

        if item is None:
            self.setWindowTitle("Новая модель локомотива")
        else:
            self.setWindowTitle("Редактирование модели локомотива")
            self._load_data(item)

    def _load_manufacturers(self, select_id: int | None = None) -> None:
        """Загружает производителей в выпадающий список."""
        combo = self.ui.maufacturer_comboBox
        combo.clear()
        for m in self.services.manufacturers.list_all():
            combo.addItem(m.name, m.id)
        if select_id is not None:
            index = combo.findData(select_id)
            if index >= 0:
                combo.setCurrentIndex(index)

    def _load_data(self, item) -> None:
        """Заполняет поля данными модели."""
        self.ui.locomotiveCode_lineEdit.setText(str(item.code))
        self.ui.locomotiveModel_lineEdit.setText(item.name)

        if item.manufacturer_id is not None:
            index = self.ui.maufacturer_comboBox.findData(item.manufacturer_id)
            if index >= 0:
                self.ui.maufacturer_comboBox.setCurrentIndex(index)

        if item.image_path:
            # Показываем только имя файла — полный путь пользователю неинтересен.
            self.ui.filepath_lineEdit.setText(Path(item.image_path).name)

    def _on_pick_file(self) -> None:
        """Открывает диалог выбора файла изображения."""
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать изображение", "", IMAGE_FILTER)
        if not path:
            return

        # Запоминаем источник: при сохранении скопируем файл в data/images.
        self._picked_file = path
        self.ui.filepath_lineEdit.setText(Path(path).name)

    def _collect_fields(self) -> dict:
        """Собирает значения полей формы."""
        return {
            "code": self.ui.locomotiveCode_lineEdit.text().strip(),
            "manufacturer_id": self.ui.maufacturer_comboBox.currentData(),
            "name": self.ui.locomotiveModel_lineEdit.text().strip(),
        }

    def _validate(self) -> bool:
        """Проверяет корректность заполнения формы."""
        fields = self._collect_fields()

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
        """Определяет путь к фото, который нужно сохранить в БД.

        Если пользователь не выбирал новый файл — оставляем то,
        что было раньше (или None для новой записи).
        Если выбирал — копируем файл в data/images и возвращаем путь к копии.
        """
        if self._picked_file is None:
            return self.item.image_path if self.item else None

        manufacturer = self.services.manufacturers.get_or_raise(manufacturer_id)
        return save_model_image(
            source_path=self._picked_file,
            manufacturer_name=manufacturer.name,
            code=code,
        )

    def _on_save(self) -> None:
        """Сохраняет модель локомотива."""
        if not self._validate():
            return

        fields = self._collect_fields()
        code = int(fields["code"])

        # Сначала работаем с файлом: если он не сохранится, БД не трогаем.
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

        try:
            if self.item is None:
                self.services.locomotive_models.create(**payload)
            else:
                self.services.locomotive_models.update(self.item.id, **payload)
        except LocomotiveModelNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Запись не найдена")
            return

        # Старое фото больше не используется — удаляем его с диска.
        if old_image_path and old_image_path != new_image_path:
            delete_image(old_image_path)

        self.accept()


class LocomotiveDialog(QDialog):
    """Диалог создания и редактирования локомотива."""

    def __init__(self, services: Services, current_user, item=None, parent=None):
        super().__init__(parent)
        self.services = services
        self.current_user = current_user
        self.item = item

        self.ui = Ui_addLocomotive_dialog()
        self.ui.setupUi(self)

        self.ui.addLocomotive_buttonBox.accepted.connect(self._on_save)
        self.ui.addLocomotive_buttonBox.rejected.connect(self.reject)

        self._load_models()

        if item is None:
            self.setWindowTitle("Новый локомотив")
        else:
            self.setWindowTitle("Редактирование локомотива")
            self._load_data(item)

    def _load_models(self) -> None:
        """Загружает список моделей локомотивов."""
        combo = self.ui.locomotiveModel_comboBox
        combo.clear()
        for model in self.services.locomotive_models.list_all():
            manufacturer = model.manufacturer.name if model.manufacturer else NO_DATA
            combo.addItem(f"{manufacturer} {model.name}", model.id)

    def _load_data(self, item) -> None:
        """Заполняет поля данными локомотива."""
        self.ui.system_spinBox.setValue(int(item.system))
        self.ui.number_lineEdit.setText(str(item.number))
        index = self.ui.locomotiveModel_comboBox.findData(item.locomotive_model_id)
        if index >= 0:
            self.ui.locomotiveModel_comboBox.setCurrentIndex(index)

    def _collect_fields(self) -> dict:
        """Собирает значения полей формы."""
        return {
            "system": self.ui.system_spinBox.value(),
            "number": self.ui.number_lineEdit.text().strip(),
            "locomotive_model_id": self.ui.locomotiveModel_comboBox.currentData(),
        }

    def _validate(self) -> bool:
        """Проверяет корректность заполнения формы."""
        fields = self._collect_fields()
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
        """Сохраняет локомотив."""
        if not self._validate():
            return

        fields = self._collect_fields()
        payload = {
            "system": fields["system"],
            "number": int(fields["number"]),
            "locomotive_model_id": fields["locomotive_model_id"],
        }

        try:
            if self.item is None:
                self.services.locomotives.create(**payload)
            else:
                self.services.locomotives.update(self.item.id, **payload)
        except LocomotiveNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Запись не найдена")
            return

        self.accept()


class DetailDialog(QDialog):
    """Диалог создания и редактирования детали."""

    def __init__(self, services: Services, current_user, item=None, parent=None):
        super().__init__(parent)
        self.services = services
        self.current_user = current_user
        self.item = item

        self.ui = Ui_addDetail_dialog()
        self.ui.setupUi(self)

        self.ui.buttonBox.accepted.connect(self._on_save)
        self.ui.buttonBox.rejected.connect(self.reject)

        self._load_manufacturers()

        if item is None:
            self.setWindowTitle("Новая деталь")
        else:
            self.setWindowTitle("Редактирование детали")
            self._load_data(item)

    def _load_data(self, item) -> None:
        """Заполняет поля данными детали."""
        self.ui.detailCode_lineEdit.setText(str(item.code))
        self.ui.detailName_lineEdit.setText(item.name)
        self.ui.detailCount_spinBox.setValue(item.quantity_in_stock)
        self.ui.detailManufacturer_comboBox.addItem(item)

    def _collect_fields(self) -> dict:
        """Собирает значения полей формы."""
        return {
            "code": self.ui.detailCode_lineEdit.text().strip(),
            "manufacturer_name": self.ui.detailManufacturer_comboBox.currentText(),
            "name": self.ui.detailName_lineEdit.text().strip(),
            "quantity_in_stock": self.ui.detailCount_spinBox.text(),
        }

    def _load_manufacturers(self) -> None:
        """Загружает список моделей локомотивов."""
        combo = self.ui.detailManufacturer_comboBox
        combo.clear()
        for man in self.services.manufacturers.list_all():
            combo.addItem(man.name if man.name else NO_DATA)

    def _validate(self) -> bool:
        """Проверяет корректность заполнения формы."""
        fields = self._collect_fields()
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
            quantity = int(fields["quantity_in_stock"])
        except ValueError:
            QMessageBox.warning(self, "Внимание", "Остаток должен быть целым числом")
            return False
        if quantity < 0:
            QMessageBox.warning(self, "Внимание", "Остаток не может быть отрицательным")
            return False
        return True

    def _on_save(self) -> None:
        """Сохраняет деталь."""
        if not self._validate():
            return

        fields = self._collect_fields()

        # Правило "производитель создаётся на лету" живёт в репозитории.
        manufacturer = self.services.manufacturers.get_or_create_by_name(
            fields["manufacturer_name"]
        )

        quantity = int(fields["quantity_in_stock"] or "0")

        payload = {
            "code": int(fields["code"]),
            "manufacturer_id": manufacturer.id,
            "name": fields["name"],
            "quantity_in_stock": quantity,
        }

        try:
            if self.item is None:
                self.services.details.create(**payload)
            else:
                self.services.details.update(self.item.id, **payload)
        except DetailNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Запись не найдена")
            return

        self.accept()


class MaintenanceDialog(QDialog):
    """Диалог создания и редактирования листа обслуживания."""

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

        self._load_locomotives()
        self._load_types()

        if item is None:
            self.setWindowTitle("Новый лист обслуживания")
            # Дата по умолчанию - сегодня
            self.ui.addMaintenanceDate_dateEdit.setDate(QDate.currentDate())
            # Минимальаня дата - полгода назад
            min_date = QDate.currentDate().addMonths(-6)
            self.ui.addMaintenanceDate_dateEdit.setMinimumDateTime(QDateTime(min_date, QTime(9, 40, 1)))
            self.ui.addMaintenanceDate_dateEdit.setMinimumDate(min_date)
        else:
            self.setWindowTitle("Редактирование листа обслуживания")
            self._load_data(item)

    def _load_locomotives(self) -> None:
        """Загружает список локомотивов."""
        combo = self.ui.addMaintenanceLoco_comboBox
        combo.clear()
        for loco in self.services.locomotives.list_all():
            combo.addItem(f"{loco.system} {loco.number}", loco.id)

    def _load_types(self) -> None:
        """Загружает список типов обслуживания."""
        combo = self.ui.addMaintenanceType_comboBox
        combo.clear()
        for mtype in self.services.maintenance_types.list_all():
            combo.addItem(mtype.name, mtype.id)

    def _load_data(self, item) -> None:
        """Заполняет поля данными листа обслуживания."""
        loco_index = self.ui.addMaintenanceLoco_comboBox.findData(item.locomotive_id)
        if loco_index >= 0:
            self.ui.addMaintenanceLoco_comboBox.setCurrentIndex(loco_index)

        type_index = self.ui.addMaintenanceType_comboBox.findData(item.maintenance_type_id)
        if type_index >= 0:
            self.ui.addMaintenanceType_comboBox.setCurrentIndex(type_index)

        if item.description:
            self.ui.addMaintenanceComment_textEdit.setPlainText(item.description)

        if item.date is not None:
            self.ui.addMaintenanceDate_dateEdit.setDate(item.date.date())

        self.detail_rows.set_rows(self.services.maintenances.get_rows(item.id))

    def _collect_fields(self) -> dict:
        """Собирает значения полей формы."""
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

    def _validate(self) -> bool:
        """Проверяет корректность заполнения формы."""
        if self.ui.addMaintenanceLoco_comboBox.currentData() is None:
            QMessageBox.warning(self, "Внимание", "Выберите локомотив")
            return False
        if self.ui.addMaintenanceType_comboBox.currentData() is None:
            QMessageBox.warning(self, "Внимание", "Выберите тип обслуживания")
            return False
        return True

    def _on_save(self) -> None:
        """Сохраняет лист обслуживания."""
        if not self._validate():
            return

        fields = self._collect_fields()

        try:
            deficits = self.services.maintenances.save_with_details(
                maintenance_id=self.item.id if self.item is not None else None,
                fields={
                    **fields,
                    **(
                        {"user_id": self.current_user.id}
                        if self.item is None
                        else {}
                    ),
                },
                rows=self.detail_rows.get_rows(),
            )
        except MaintenanceNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Запись не найдена")
            return

        if deficits:
            details_by_id = {detail.id: detail for detail in self.details}
            shortage_lines = []
            for detail_id, deficit in deficits.items():
                detail = details_by_id.get(detail_id)
                manufacturer = (
                    detail.manufacturer.name if detail and detail.manufacturer else NO_DATA
                )
                label = (
                    f"{manufacturer} · {detail.code} · {detail.name}"
                    if detail is not None
                    else f"Деталь {detail_id}"
                )
                shortage_lines.append(f"{label}: не хватает {deficit} шт.")

            reply = QMessageBox.warning(
                self,
                "Недостаточно деталей",
                f"На складе недостаточно деталей:\n{chr(10).join(shortage_lines)}"
                "\nПродолжить и разрешить отрицательный остаток?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            try:
                self.services.maintenances.save_with_details(
                    maintenance_id=self.item.id if self.item is not None else None,
                    fields={
                        **fields,
                        **(
                            {"user_id": self.current_user.id}
                            if self.item is None
                            else {}
                        ),
                    },
                    rows=self.detail_rows.get_rows(),
                    allow_negative_stock=True,
                )
            except MaintenanceNotFoundError:
                QMessageBox.critical(self, "Ошибка", "Запись не найдена")
                return

        self.accept()


class UserEditDialog(QDialog):
    """Диалог редактирования пользователя."""

    def __init__(self, services: Services, target_user, admin_mode: bool = False, parent=None):
        super().__init__(parent)
        self.services = services
        self.user = target_user
        self.admin_mode = admin_mode

        self.ui = Ui_userEdit_dialog()
        self.ui.setupUi(self)

        if not admin_mode:
            self.ui.isAdmin_checkBox.setVisible(False)
            self.ui.disabled_checkBox.setVisible(False)

        self._load_user_data()

        self.ui.buttonBox.accepted.connect(self._on_save)
        self.ui.buttonBox.rejected.connect(self.reject)

    def _load_user_data(self) -> None:
        """Заполняет поля данными пользователя."""
        self.ui.login_lineEdit.setText(self.user.login)
        self.ui.firstName_lineEdit.setText(self.user.first_name or "")
        self.ui.lastName_lineEdit.setText(self.user.last_name or "")
        self.ui.isAdmin_checkBox.setChecked(bool(self.user.is_admin))
        self.ui.disabled_checkBox.setChecked(not self.user.is_active)

    def _on_save(self) -> None:
        """Сохраняет изменения пользователя."""
        login = self.ui.login_lineEdit.text().strip().lower()
        first_name = self.ui.firstName_lineEdit.text().strip()
        last_name = self.ui.lastName_lineEdit.text().strip()
        new_pass = self.ui.newPass_lineEdit.text()
        new_pass_confirm = self.ui.newPassConfirm_lineEdit.text()

        if not login:
            QMessageBox.warning(self, "Внимание", "Логин не может быть пустым")
            return

        if new_pass or new_pass_confirm:
            if new_pass != new_pass_confirm:
                QMessageBox.warning(self, "Внимание", "Пароли не совпадают")
                return

        is_admin = self.ui.isAdmin_checkBox.isChecked()
        is_active = not self.ui.disabled_checkBox.isChecked()

        try:
            self.services.users.update(
                self.user.id,
                login=login,
                first_name=first_name,
                last_name=last_name,
                password=new_pass or None,
                is_admin=is_admin if self.admin_mode else None,
                is_active=is_active if self.admin_mode else None,
            )
        except LoginAlreadyTakenError:
            QMessageBox.warning(self, "Внимание", "Этот логин уже занят")
            return
        except LastActiveAdminError:
            QMessageBox.warning(
                self, "Внимание", _last_admin_message(is_admin, is_active)
            )
            return
        except UserNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Пользователь не найден")
            return

        self.accept()


class UserCreateDialog(QDialog):
    """Диалог создания нового пользователя."""

    def __init__(self, services: Services, current_user, parent=None):
        super().__init__(parent)
        self.services = services
        self.current_user = current_user

        self.ui = Ui_userEdit_dialog()
        self.ui.setupUi(self)
        self.setWindowTitle("Новый пользователь")

        self.ui.newPass_label.setText("Пароль")
        self.ui.newPassConfirm_label.setText("Подтвердите пароль")

        self.ui.buttonBox.accepted.connect(self._on_save)
        self.ui.buttonBox.rejected.connect(self.reject)

    def _on_save(self) -> None:
        """Создаёт нового пользователя."""
        login = self.ui.login_lineEdit.text().strip().lower()
        first_name = self.ui.firstName_lineEdit.text().strip()
        last_name = self.ui.lastName_lineEdit.text().strip()
        password = self.ui.newPass_lineEdit.text()
        password_confirm = self.ui.newPassConfirm_lineEdit.text()
        is_admin = self.ui.isAdmin_checkBox.isChecked()
        is_active = not self.ui.disabled_checkBox.isChecked()

        if not login:
            QMessageBox.warning(self, "Внимание", "Логин не может быть пустым")
            return
        if not password:
            QMessageBox.warning(self, "Внимание", "Пароль не может быть пустым")
            return
        if password != password_confirm:
            QMessageBox.warning(self, "Внимание", "Пароли не совпадают")
            return

        try:
            self.services.users.create(
                login=login,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_admin=is_admin,
                is_active=is_active,
            )
        except LoginAlreadyTakenError:
            QMessageBox.warning(self, "Внимание", "Этот логин уже занят")
            return

        self.accept()


class UserManagementDialog(QDialog):
    """Окно со списком пользователей."""

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

        self.ui.userAdd_button.clicked.connect(self._on_add_clicked)
        self.ui.userEdit_button.clicked.connect(self._on_edit_clicked)
        self.ui.userDelete_button.clicked.connect(self._on_delete_clicked)

        self._users: list = []
        self._load_users_table()

    def _load_users_table(self) -> None:
        """Перечитывает список пользователей и перерисовывает таблицу."""
        table = self.ui.users_tableWidget
        self._users = self.services.users.list_all()

        headers = ["ID", "Логин", "Имя", "Фамилия", "Админ", "Отключен"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(self._users))

        for row, user in enumerate(self._users):
            values = [
                str(user.id),
                user.login,
                user.first_name or "",
                user.last_name or "",
                BOOL_YES if user.is_admin else BOOL_NO,
                BOOL_YES if not user.is_active else BOOL_NO,
            ]
            for col, value in enumerate(values):
                table.setItem(row, col, QTableWidgetItem(value))

    def _selected_user(self):
        """Возвращает выбранного пользователя или None."""
        row = self.ui.users_tableWidget.currentRow()
        if row < 0 or row >= len(self._users):
            return None
        return self._users[row]

    def _on_add_clicked(self) -> None:
        """Открывает диалог создания пользователя."""
        dialog = UserCreateDialog(self.services, self.current_user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_users_table()

    def _on_edit_clicked(self) -> None:
        """Открывает диалог редактирования пользователя."""
        user = self._selected_user()
        if user is None:
            QMessageBox.information(self, "Внимание", "Выберите пользователя")
            return

        dialog = UserEditDialog(self.services, user, admin_mode=True, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_users_table()

    def _on_delete_clicked(self) -> None:
        """Удаляет выбранного пользователя после подтверждения."""
        user = self._selected_user()
        if user is None:
            QMessageBox.information(self, "Внимание", "Выберите пользователя")
            return

        if user.id == self.current_user.id:
            QMessageBox.warning(self, "Внимание", "Нельзя удалить самого себя")
            return

        reply = QMessageBox.question(
            self,
            "Подтверждение",
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

        self._load_users_table()


class SupplyDialog(QDialog):
    """Диалог создания и редактирования прихода деталей на склад.

    Один supply_number соответствует одной партии: несколько строк Supply,
    по одной на каждую деталь. Номер новой партии назначается автоматически.
    В режиме редактирования открывается существующая партия.
    """

    def __init__(self, services: Services, current_user,
                 supply_number: int | None = None, parent=None):
        super().__init__(parent)
        self.services = services
        self.current_user = current_user
        # None → создание новой партии, число → редактирование существующей.
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
            self._prepare_edit_mode(supply_number)

    def _prepare_edit_mode(self, supply_number: int) -> None:
        """Загружает существующую партию в таблицу.

        Сохраняет номер партии в объекте диалога для обновления этой партии.
        """
        rows = self.services.supplies.get_rows_by_number(supply_number)
        self.detail_rows.set_rows(rows)

    # Валидация

    def _validate(self) -> bool:
        """Проверяет корректность заполнения формы."""
        if not self.detail_rows.get_rows():
            QMessageBox.warning(self, "Внимание", "Добавьте хотя бы одну деталь")
            return False

        return True

    # Сохранение

    def _on_save(self) -> None:
        """Сохраняет приход в БД."""
        if not self._validate():
            return

        rows = self.detail_rows.get_rows()

        try:
            if self.supply_number is None:
                self.services.supplies.create_batch(
                    rows=rows,
                    user_id=self.current_user.id,
                )
            else:
                self.services.supplies.update_batch(
                    supply_number=self.supply_number,
                    rows=rows,
                )
        except SupplyNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Запись не найдена")
            return
        self.accept()
