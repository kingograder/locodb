# -*- coding: utf-8 -*-
"""Экран приложения: авторизация, вкладки, диалоги."""

import logging
from contextlib import contextmanager
from typing import Any

from PySide6.QtCore import QDate, Signal, Slot
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QHeaderView,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.db.functions import (
    add_detail,
    add_locomotive,
    add_locomotive_model,
    add_maintenance,
    add_maintenance_type,
    add_manufacturer,
    add_user,
    assert_not_last_admin,
    authenticate,
    delete_detail,
    delete_locomotive,
    delete_locomotive_model,
    delete_maintenance_type,
    delete_manufacturer,
    delete_user,
    get_all_details,
    get_all_locomotive_models,
    get_all_locomotives,
    get_all_maintenance_types,
    get_all_maintenances,
    get_all_manufacturers,
    get_all_users,
    mark_maintenance_deleted,
    update_detail,
    update_locomotive,
    update_locomotive_model,
    update_maintenance,
    update_maintenance_type,
    update_manufacturer,
    update_user_full,
    DetailNotFoundError,
    EntityInUseError,
    LastActiveAdminError,
    LocomotiveModelNotFoundError,
    LocomotiveNotFoundError,
    LoginAlreadyTakenError,
    MaintenanceNotFoundError,
    MaintenanceTypeNotFoundError,
    ManufacturerNotFoundError,
    UserNotFoundError,
)
from app.db.models import (
    Detail,
    Locomotive,
    LocomotiveModel,
    Maintenance,
    MaintenanceType,
    Manufacturer,
    User,
)
from app.widgets.ui_auth_window import Ui_auth_window
from app.widgets.ui_main_window import Ui_main_window
from app.widgets.ui_base_tab_widget import Ui_baseTab_widget
from app.widgets.ui_user_edit_dialog import Ui_userEdit_dialog
from app.widgets.ui_user_management_dialog import Ui_usersManagement_dialog
from app.widgets.ui_maintenance_add_dialog import Ui_addMaintenance_dialog
from app.widgets.ui_locomotive_add_dialog import Ui_addLocomotive_dialog
from app.widgets.ui_locomotive_model_add_dialog import Ui_addLocomotiveModel_dialog
from app.widgets.ui_detail_add_dialog import Ui_addDetail_dialog
from app.widgets.ui_maintenance_type_add_dialog import Ui_addMaintenanceType_dialog
from app.widgets.ui_manufacturer_add_dialog import Ui_addManufacturer_dialog

logger = logging.getLogger(__name__)

IMAGE_FILTER = "Изображения (*.png *.jpg *.jpeg *.bmp)"
BOOL_YES = "Да"
BOOL_NO = "Нет"
NO_DATA = "—"


# =============================================================
# Вспомогательные функции
# =============================================================

def ensure_not_last_active_admin(
    session_factory: sessionmaker,
    user_id: int,
    *,
    will_be_admin: bool,
    will_be_active: bool,
    parent: QWidget | None = None,
) -> bool:
    """Проверяет, не останется ли система без активных администраторов."""
    if will_be_admin and will_be_active:
        return True

    try:
        assert_not_last_admin(session_factory, user_id)
    except LastActiveAdminError:
        if not will_be_admin and not will_be_active:
            msg = "Нельзя разжаловать и отключить последнего активного администратора"
        elif not will_be_admin:
            msg = "Нельзя разжаловать последнего активного администратора"
        else:
            msg = "Нельзя отключить последнего активного администратора"

        QMessageBox.warning(parent, "Внимание", msg)
        return False

    return True


def get_or_create_manufacturer(session_factory: sessionmaker, name: str) -> int:
    """Возвращает ID производителя по имени, при отсутствии — создаёт."""
    clean = name.strip().lower()
    with session_factory() as session:
        existing = session.scalar(
            select(Manufacturer).where(Manufacturer.name == clean)
        )
        if existing is not None:
            return existing.id

        manufacturer = Manufacturer(name=clean)
        session.add(manufacturer)
        try:
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            logger.exception(f"Ошибка БД при создании производителя {clean}")
            raise
        return manufacturer.id


# =============================================================
# Экран авторизации
# =============================================================

class AuthScreen(QWidget):
    """Экран авторизации."""

    auth_successful = Signal(User)

    def __init__(self, session_factory: sessionmaker, parent: QWidget | None = None):
        super().__init__(parent)
        self.session_factory = session_factory
        self._busy = False

        self.ui = Ui_auth_window()
        self.ui.setupUi(self)

        self.ui.enter_button.clicked.connect(self._enter_auth)
        for key in ("Return", "Enter"):
            QShortcut(QKeySequence(key), self).activated.connect(self._enter_auth)

    @contextmanager
    def _busy_context(self):
        """Блокирует кнопку входа на время выполнения операции."""
        self._busy = True
        self.ui.enter_button.setEnabled(False)
        try:
            yield
        finally:
            self._busy = False
            self.ui.enter_button.setEnabled(True)

    def _enter_auth(self) -> None:
        """Проверяет логин и пароль, отправляет сигнал при успехе."""
        if self._busy:
            return

        login = self.ui.login_lineEdit.text().strip().lower()
        password = self.ui.pass_lineEdit.text()

        if not login or not password:
            QMessageBox.warning(self, "Внимание", "Заполните все поля")
            return

        with self._busy_context():
            try:
                user = authenticate(self.session_factory, login, password)
            except SQLAlchemyError as e:
                logger.exception("Ошибка БД при авторизации")
                QMessageBox.critical(self, "Ошибка БД", f"Не удалось подключиться к базе:\n{e}")
                return

        if user is None:
            QMessageBox.critical(self, "Ошибка авторизации", "Неверный логин или пароль")
            return

        self.auth_successful.emit(user)

    def reset_form(self) -> None:
        """Очищает поля ввода."""
        self.ui.login_lineEdit.clear()
        self.ui.pass_lineEdit.clear()
        self.ui.login_lineEdit.setFocus()


# =============================================================
# Диалог: тип обслуживания
# =============================================================

class MaintenanceTypeDialog(QDialog):
    """Диалог создания и редактирования типа обслуживания."""

    def __init__(
        self,
        session_factory: sessionmaker,
        current_user: User,
        entity: MaintenanceType | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.session_factory = session_factory
        self.current_user = current_user
        self.entity = entity

        self.ui = Ui_addMaintenanceType_dialog()
        self.ui.setupUi(self)

        self.ui.buttonBox.accepted.connect(self._on_save)
        self.ui.buttonBox.rejected.connect(self.reject)

        if entity is None:
            self.setWindowTitle("Новый тип обслуживания")
        else:
            self.setWindowTitle("Редактирование типа обслуживания")
            self.ui.maintenanceType_lineEdit.setText(entity.name)

    def _on_save(self) -> None:
        """Сохраняет тип обслуживания."""
        name = self.ui.maintenanceType_lineEdit.text().strip()
        if not name:
            QMessageBox.warning(self, "Внимание", "Укажите название типа")
            return

        try:
            if self.entity is None:
                add_maintenance_type(self.session_factory, name=name)
            else:
                update_maintenance_type(self.session_factory, self.entity.id, name=name)
        except MaintenanceTypeNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Запись не найдена")
            return
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при сохранении типа обслуживания")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось сохранить:\n{e}")
            return

        self.accept()


# =============================================================
# Диалог: производитель
# =============================================================

class ManufacturerDialog(QDialog):
    """Диалог создания и редактирования производителя."""

    def __init__(
        self,
        session_factory: sessionmaker,
        current_user: User,
        entity: Manufacturer | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.session_factory = session_factory
        self.current_user = current_user
        self.entity = entity

        self.ui = Ui_addManufacturer_dialog()
        self.ui.setupUi(self)

        self.ui.buttonBox.accepted.connect(self._on_save)
        self.ui.buttonBox.rejected.connect(self.reject)

        if entity is None:
            self.setWindowTitle("Новый производитель")
        else:
            self.setWindowTitle("Редактирование производителя")
            self.ui.manufacturerName_lineEdit.setText(entity.name)

    def _on_save(self) -> None:
        """Сохраняет производителя."""
        name = self.ui.manufacturerName_lineEdit.text().strip()
        if not name:
            QMessageBox.warning(self, "Внимание", "Укажите название производителя")
            return

        try:
            if self.entity is None:
                add_manufacturer(self.session_factory, name=name)
            else:
                update_manufacturer(self.session_factory, self.entity.id, name=name)
        except ManufacturerNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Запись не найдена")
            return
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при сохранении производителя")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось сохранить:\n{e}")
            return

        self.accept()


# =============================================================
# Диалог: модель локомотива
# =============================================================

class LocomotiveModelDialog(QDialog):
    """Диалог создания и редактирования модели локомотива."""

    def __init__(
        self,
        session_factory: sessionmaker,
        current_user: User,
        entity: LocomotiveModel | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.session_factory = session_factory
        self.current_user = current_user
        self.entity = entity

        self.ui = Ui_addLocomotiveModel_dialog()
        self.ui.setupUi(self)

        self.ui.addLocomotiveModel_buttonBox.accepted.connect(self._on_save)
        self.ui.addLocomotiveModel_buttonBox.rejected.connect(self.reject)
        self.ui.filepicker_toolButton.clicked.connect(self._on_pick_file)
        self.ui.maufacturer_toolButton.clicked.connect(self._on_add_manufacturer)

        self._load_manufacturers()

        if entity is None:
            self.setWindowTitle("Новая модель локомотива")
        else:
            self.setWindowTitle("Редактирование модели локомотива")
            self._load_data(entity)

    def _load_manufacturers(self, select_id: int | None = None) -> None:
        """Загружает производителей в выпадающий список."""
        try:
            manufacturers = get_all_manufacturers(self.session_factory)
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при загрузке производителей")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось загрузить производителей:\n{e}")
            manufacturers = []

        combo = self.ui.maufacturer_comboBox
        combo.clear()
        for m in manufacturers:
            combo.addItem(m.name, m.id)

        if select_id is not None:
            index = combo.findData(select_id)
            if index >= 0:
                combo.setCurrentIndex(index)

    def _load_data(self, entity: LocomotiveModel) -> None:
        """Заполняет поля данными модели."""
        self.ui.locomotiveCode_lineEdit.setText(str(entity.code))
        self.ui.locomotiveModel_lineEdit.setText(entity.name)

        if entity.manufacturer_id is not None:
            index = self.ui.maufacturer_comboBox.findData(entity.manufacturer_id)
            if index >= 0:
                self.ui.maufacturer_comboBox.setCurrentIndex(index)

        if entity.image_path:
            self.ui.filepath_lineEdit.setText(entity.image_path)

    def _on_add_manufacturer(self) -> None:
        """Создаёт производителя прямо из диалога."""
        name, ok = QInputDialog.getText(self, "Новый производитель", "Название:")
        if not ok:
            return

        name = name.strip()
        if not name:
            QMessageBox.warning(self, "Внимание", "Название не может быть пустым")
            return

        try:
            add_manufacturer(self.session_factory, name=name)
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при создании производителя")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось создать производителя:\n{e}")
            return

        # Перезагружаем список и выделяем созданного
        try:
            manufacturers = get_all_manufacturers(self.session_factory)
        except SQLAlchemyError:
            manufacturers = []

        new_id = next((m.id for m in manufacturers if m.name == name.lower()), None)
        self._load_manufacturers(select_id=new_id)

    def _on_pick_file(self) -> None:
        """Открывает диалог выбора файла изображения."""
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать изображение", "", IMAGE_FILTER)
        if path:
            self.ui.filepath_lineEdit.setText(path)

    def _collect_fields(self) -> dict[str, Any]:
        """Собирает значения полей формы."""
        return {
            "code": self.ui.locomotiveCode_lineEdit.text().strip(),
            "manufacturer_id": self.ui.maufacturer_comboBox.currentData(),
            "name": self.ui.locomotiveModel_lineEdit.text().strip(),
            "image_path": self.ui.filepath_lineEdit.text().strip() or None,
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

    def _on_save(self) -> None:
        """Сохраняет модель локомотива в БД."""
        if not self._validate():
            return

        fields = self._collect_fields()

        try:
            if self.entity is None:
                add_locomotive_model(
                    self.session_factory,
                    code=int(fields["code"]),
                    manufacturer_id=fields["manufacturer_id"],
                    name=fields["name"],
                    image_path=fields["image_path"],
                )
            else:
                update_locomotive_model(
                    self.session_factory,
                    model_id=self.entity.id,
                    code=int(fields["code"]),
                    manufacturer_id=fields["manufacturer_id"],
                    name=fields["name"],
                    image_path=fields["image_path"],
                )
        except LocomotiveModelNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Запись не найдена")
            return
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при сохранении модели локомотива")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось сохранить:\n{e}")
            return

        self.accept()


# =============================================================
# Диалог: локомотив
# =============================================================

class LocomotiveDialog(QDialog):
    """Диалог создания и редактирования локомотива."""

    def __init__(
        self,
        session_factory: sessionmaker,
        current_user: User,
        entity: Locomotive | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.session_factory = session_factory
        self.current_user = current_user
        self.entity = entity

        self.ui = Ui_addLocomotive_dialog()
        self.ui.setupUi(self)

        self.ui.addLocomotive_buttonBox.accepted.connect(self._on_save)
        self.ui.addLocomotive_buttonBox.rejected.connect(self.reject)

        self._load_models()

        if entity is None:
            self.setWindowTitle("Новый локомотив")
        else:
            self.setWindowTitle("Редактирование локомотива")
            self._load_data(entity)

    def _load_models(self) -> None:
        """Загружает список моделей локомотивов."""
        try:
            models = get_all_locomotive_models(self.session_factory)
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при загрузке моделей локомотивов")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось загрузить модели:\n{e}")
            models = []

        self.ui.locomotiveModel_comboBox.clear()
        for model in models:
            manufacturer = model.manufacturer.name if model.manufacturer else NO_DATA
            self.ui.locomotiveModel_comboBox.addItem(
                f"{manufacturer} {model.name}", model.id
            )

    def _load_data(self, entity: Locomotive) -> None:
        """Заполняет поля данными локомотива."""
        self.ui.system_spinBox.setValue(int(entity.system))
        self.ui.number_lineEdit.setText(str(entity.number))

        index = self.ui.locomotiveModel_comboBox.findData(entity.locomotive_model_id)
        if index >= 0:
            self.ui.locomotiveModel_comboBox.setCurrentIndex(index)

    def _collect_fields(self) -> dict[str, Any]:
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
        """Сохраняет локомотив в БД."""
        if not self._validate():
            return

        fields = self._collect_fields()

        try:
            if self.entity is None:
                add_locomotive(
                    self.session_factory,
                    system=fields["system"],
                    number=int(fields["number"]),
                    locomotive_model_id=fields["locomotive_model_id"],
                )
            else:
                update_locomotive(
                    self.session_factory,
                    locomotive_id=self.entity.id,
                    system=fields["system"],
                    number=int(fields["number"]),
                    locomotive_model_id=fields["locomotive_model_id"],
                )
        except LocomotiveNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Запись не найдена")
            return
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при сохранении локомотива")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось сохранить:\n{e}")
            return

        self.accept()


# =============================================================
# Диалог: деталь
# =============================================================

class DetailDialog(QDialog):
    """Диалог создания и редактирования детали."""

    def __init__(
        self,
        session_factory: sessionmaker,
        current_user: User,
        entity: Detail | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.session_factory = session_factory
        self.current_user = current_user
        self.entity = entity

        self.ui = Ui_addDetail_dialog()
        self.ui.setupUi(self)

        self.ui.buttonBox.accepted.connect(self._on_save)
        self.ui.buttonBox.rejected.connect(self.reject)

        if entity is None:
            self.setWindowTitle("Новая деталь")
        else:
            self.setWindowTitle("Редактирование детали")
            self._load_data(entity)

    def _load_data(self, entity: Detail) -> None:
        """Заполняет поля данными детали."""
        self.ui.detailCode_lineEdit.setText(str(entity.code))
        self.ui.detailCode_lineEdit_2.setText(entity.name)
        self.ui.detailCount_lineEdit.setText(str(entity.quantity_in_stock))

        if entity.manufacturer is not None:
            self.ui.detailManufacturer_lineEdit.setText(entity.manufacturer.name)

    def _collect_fields(self) -> dict[str, Any]:
        """Собирает значения полей формы."""
        return {
            "code": self.ui.detailCode_lineEdit.text().strip(),
            "manufacturer_name": self.ui.detailManufacturer_lineEdit.text().strip(),
            "name": self.ui.detailCode_lineEdit_2.text().strip(),
            "quantity_in_stock": self.ui.detailCount_lineEdit.text().strip(),
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

        if not fields["manufacturer_name"]:
            QMessageBox.warning(self, "Внимание", "Укажите производителя")
            return False

        if not fields["name"]:
            QMessageBox.warning(self, "Внимание", "Укажите наименование")
            return False

        return True

    def _on_save(self) -> None:
        """Сохраняет деталь в БД."""
        if not self._validate():
            return

        fields = self._collect_fields()

        # Получаем/создаём производителя
        try:
            manufacturer_id = get_or_create_manufacturer(
                self.session_factory, fields["manufacturer_name"]
            )
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при работе с производителем")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось сохранить производителя:\n{e}")
            return

        # Количество (пустое → 0)
        try:
            quantity = int(fields["quantity_in_stock"] or "0")
        except ValueError:
            quantity = 0

        try:
            if self.entity is None:
                add_detail(
                    self.session_factory,
                    code=int(fields["code"]),
                    manufacturer_id=manufacturer_id,
                    name=fields["name"],
                    quantity_in_stock=quantity,
                )
            else:
                update_detail(
                    self.session_factory,
                    detail_id=self.entity.id,
                    code=int(fields["code"]),
                    manufacturer_id=manufacturer_id,
                    name=fields["name"],
                    quantity_in_stock=quantity,
                )
        except DetailNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Запись не найдена")
            return
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при сохранении детали")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось сохранить:\n{e}")
            return

        self.accept()


# =============================================================
# Диалог: лист обслуживания
# =============================================================

class MaintenanceDialog(QDialog):
    """Диалог создания и редактирования листа обслуживания."""

    def __init__(
        self,
        session_factory: sessionmaker,
        current_user: User,
        entity: Maintenance | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.session_factory = session_factory
        self.current_user = current_user
        self.entity = entity

        self.ui = Ui_addMaintenance_dialog()
        self.ui.setupUi(self)

        self.ui.addMaintenance_buttonBox.accepted.connect(self._on_save)
        self.ui.addMaintenance_buttonBox.rejected.connect(self.reject)

        self._load_locomotives()
        self._load_types()

        if entity is None:
            self.setWindowTitle("Новый лист обслуживания")
        else:
            self.setWindowTitle("Редактирование листа обслуживания")
            self._load_data(entity)

    def _load_locomotives(self) -> None:
        """Загружает список локомотивов."""
        try:
            locomotives = get_all_locomotives(self.session_factory)
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при загрузке локомотивов")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось загрузить локомотивы:\n{e}")
            locomotives = []

        combo = self.ui.addMaintenanceLoco_comboBox
        combo.clear()
        for loco in locomotives:
            combo.addItem(f"{loco.system} {loco.number}", loco.id)

    def _load_types(self) -> None:
        """Загружает список типов обслуживания."""
        try:
            types = get_all_maintenance_types(self.session_factory)
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при загрузке типов обслуживания")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось загрузить типы:\n{e}")
            types = []

        combo = self.ui.addMaintenanceType_comboBox
        combo.clear()
        for item in types:
            combo.addItem(item.name, item.id)

    def _load_data(self, entity: Maintenance) -> None:
        """Заполняет поля данными листа обслуживания."""
        loco_index = self.ui.addMaintenanceLoco_comboBox.findData(entity.locomotive_id)
        if loco_index >= 0:
            self.ui.addMaintenanceLoco_comboBox.setCurrentIndex(loco_index)

        type_index = self.ui.addMaintenanceType_comboBox.findData(entity.maintenance_type_id)
        if type_index >= 0:
            self.ui.addMaintenanceType_comboBox.setCurrentIndex(type_index)

        if entity.description:
            self.ui.addMaintenanceComment_textEdit.setPlainText(entity.description)

    def _collect_fields(self) -> dict[str, Any]:
        """Собирает значения полей формы."""
        return {
            "locomotive_id": self.ui.addMaintenanceLoco_comboBox.currentData(),
            "maintenance_type_id": self.ui.addMaintenanceType_comboBox.currentData(),
            "description": self.ui.addMaintenanceComment_textEdit.toPlainText().strip() or None,
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
        """Сохраняет лист обслуживания в БД."""
        if not self._validate():
            return

        fields = self._collect_fields()

        try:
            if self.entity is None:
                add_maintenance(
                    self.session_factory,
                    locomotive_id=fields["locomotive_id"],
                    maintenance_type_id=fields["maintenance_type_id"],
                    description=fields["description"],
                    user_id=self.current_user.id,
                )
            else:
                update_maintenance(
                    self.session_factory,
                    maintenance_id=self.entity.id,
                    locomotive_id=fields["locomotive_id"],
                    maintenance_type_id=fields["maintenance_type_id"],
                    description=fields["description"],
                )
        except MaintenanceNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Запись не найдена")
            return
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при сохранении листа обслуживания")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось сохранить:\n{e}")
            return

        self.accept()


# =============================================================
# Вкладка: типы обслуживания
# =============================================================

class MaintenanceTypesTab(QWidget):
    """Вкладка «Типы обслуживания»."""

    HEADERS = ["ID", "Название"]

    def __init__(
        self,
        session_factory: sessionmaker,
        current_user: User,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.session_factory = session_factory
        self.current_user = current_user

        self.ui = Ui_baseTab_widget()
        self.ui.setupUi(self)

        self.ui.base_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.ui.addBase_button.setText("Добавить")
        self.ui.editBase_button.setText("Изменить")
        self.ui.deleteBase_button.setText("Удалить")

        self.ui.addBase_button.clicked.connect(self._on_add_clicked)
        self.ui.editBase_button.clicked.connect(self._on_edit_clicked)
        self.ui.deleteBase_button.clicked.connect(self._on_delete_clicked)

        self._items: list[MaintenanceType] = []
        self.reload()

    def reload(self) -> None:
        """Перечитывает данные из БД и перерисовывает таблицу."""
        try:
            self._items = get_all_maintenance_types(self.session_factory)
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при загрузке типов обслуживания")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось загрузить данные:\n{e}")
            self._items = []

        table = self.ui.base_table
        table.setColumnCount(len(self.HEADERS))
        table.setHorizontalHeaderLabels(self.HEADERS)
        table.setRowCount(len(self._items))

        for row, item in enumerate(self._items):
            table.setItem(row, 0, QTableWidgetItem(str(item.id)))
            table.setItem(row, 1, QTableWidgetItem(item.name))

    def _selected_item(self) -> MaintenanceType | None:
        """Возвращает выбранную запись."""
        row = self.ui.base_table.currentRow()
        if row < 0 or row >= len(self._items):
            return None
        return self._items[row]

    def _on_add_clicked(self) -> None:
        """Открывает диалог создания."""
        dialog = MaintenanceTypeDialog(
            self.session_factory, self.current_user, parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _on_edit_clicked(self) -> None:
        """Открывает диалог редактирования."""
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "Внимание", "Выберите запись")
            return

        dialog = MaintenanceTypeDialog(
            self.session_factory, self.current_user, item, parent=self
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
            f"Удалить тип обслуживания «{item.name}»?\nДействие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            delete_maintenance_type(self.session_factory, item.id)
        except EntityInUseError as e:
            QMessageBox.warning(self, "Внимание", str(e))
            return
        except MaintenanceTypeNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Запись уже удалена")
            return
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при удалении типа обслуживания")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось удалить:\n{e}")
            return

        self.reload()


# =============================================================
# Вкладка: производители
# =============================================================

class ManufacturersTab(QWidget):
    """Вкладка «Производители»."""

    HEADERS = ["ID", "Название"]

    def __init__(
        self,
        session_factory: sessionmaker,
        current_user: User,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.session_factory = session_factory
        self.current_user = current_user

        self.ui = Ui_baseTab_widget()
        self.ui.setupUi(self)

        self.ui.base_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.ui.addBase_button.setText("Добавить")
        self.ui.editBase_button.setText("Изменить")
        self.ui.deleteBase_button.setText("Удалить")

        self.ui.addBase_button.clicked.connect(self._on_add_clicked)
        self.ui.editBase_button.clicked.connect(self._on_edit_clicked)
        self.ui.deleteBase_button.clicked.connect(self._on_delete_clicked)

        self._items: list[Manufacturer] = []
        self.reload()

    def reload(self) -> None:
        """Перечитывает данные из БД и перерисовывает таблицу."""
        try:
            self._items = get_all_manufacturers(self.session_factory)
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при загрузке производителей")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось загрузить данные:\n{e}")
            self._items = []

        table = self.ui.base_table
        table.setColumnCount(len(self.HEADERS))
        table.setHorizontalHeaderLabels(self.HEADERS)
        table.setRowCount(len(self._items))

        for row, item in enumerate(self._items):
            table.setItem(row, 0, QTableWidgetItem(str(item.id)))
            table.setItem(row, 1, QTableWidgetItem(item.name))

    def _selected_item(self) -> Manufacturer | None:
        """Возвращает выбранную запись."""
        row = self.ui.base_table.currentRow()
        if row < 0 or row >= len(self._items):
            return None
        return self._items[row]

    def _on_add_clicked(self) -> None:
        """Открывает диалог создания."""
        dialog = ManufacturerDialog(self.session_factory, self.current_user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _on_edit_clicked(self) -> None:
        """Открывает диалог редактирования."""
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "Внимание", "Выберите запись")
            return

        dialog = ManufacturerDialog(
            self.session_factory, self.current_user, item, parent=self
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
            f"Удалить производителя «{item.name}»?\nДействие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            delete_manufacturer(self.session_factory, item.id)
        except EntityInUseError as e:
            QMessageBox.warning(self, "Внимание", str(e))
            return
        except ManufacturerNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Запись уже удалена")
            return
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при удалении производителя")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось удалить:\n{e}")
            return

        self.reload()


# =============================================================
# Вкладка: модели локомотивов
# =============================================================

class LocomotiveModelsTab(QWidget):
    """Вкладка «Модели локомотивов»."""

    HEADERS = ["ID", "Фото", "Артикул", "Производитель", "Модель"]

    def __init__(
        self,
        session_factory: sessionmaker,
        current_user: User,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.session_factory = session_factory
        self.current_user = current_user

        self.ui = Ui_baseTab_widget()
        self.ui.setupUi(self)

        self.ui.base_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.ui.addBase_button.setText("Добавить")
        self.ui.editBase_button.setText("Изменить")
        self.ui.deleteBase_button.setText("Удалить")

        self.ui.addBase_button.clicked.connect(self._on_add_clicked)
        self.ui.editBase_button.clicked.connect(self._on_edit_clicked)
        self.ui.deleteBase_button.clicked.connect(self._on_delete_clicked)

        self._items: list[LocomotiveModel] = []
        self.reload()

    def reload(self) -> None:
        """Перечитывает данные из БД и перерисовывает таблицу."""
        try:
            self._items = get_all_locomotive_models(self.session_factory)
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при загрузке моделей локомотивов")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось загрузить данные:\n{e}")
            self._items = []

        table = self.ui.base_table
        table.setColumnCount(len(self.HEADERS))
        table.setHorizontalHeaderLabels(self.HEADERS)
        table.setRowCount(len(self._items))

        for row, item in enumerate(self._items):
            manufacturer = item.manufacturer.name if item.manufacturer else NO_DATA
            values = [
                str(item.id),
                item.image_path or NO_DATA,
                str(item.code),
                manufacturer,
                item.name,
            ]
            for col, value in enumerate(values):
                table.setItem(row, col, QTableWidgetItem(value))

    def _selected_item(self) -> LocomotiveModel | None:
        """Возвращает выбранную запись."""
        row = self.ui.base_table.currentRow()
        if row < 0 or row >= len(self._items):
            return None
        return self._items[row]

    def _on_add_clicked(self) -> None:
        """Открывает диалог создания."""
        dialog = LocomotiveModelDialog(self.session_factory, self.current_user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _on_edit_clicked(self) -> None:
        """Открывает диалог редактирования."""
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "Внимание", "Выберите запись")
            return

        dialog = LocomotiveModelDialog(
            self.session_factory, self.current_user, item, parent=self
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
            f"Удалить модель локомотива «{item.code} {item.name}»?\n"
            f"Действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            delete_locomotive_model(self.session_factory, item.id)
        except EntityInUseError as e:
            QMessageBox.warning(self, "Внимание", str(e))
            return
        except LocomotiveModelNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Запись уже удалена")
            return
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при удалении модели локомотива")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось удалить:\n{e}")
            return

        self.reload()


# =============================================================
# Вкладка: локомотивы
# =============================================================

class LocomotivesTab(QWidget):
    """Вкладка «Локомотивы»."""

    HEADERS = ["ID", "Система", "Номер", "Производитель", "Модель", "Артикул"]

    def __init__(
        self,
        session_factory: sessionmaker,
        current_user: User,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.session_factory = session_factory
        self.current_user = current_user

        self.ui = Ui_baseTab_widget()
        self.ui.setupUi(self)

        self.ui.base_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.ui.addBase_button.setText("Добавить")
        self.ui.editBase_button.setText("Изменить")
        self.ui.deleteBase_button.setText("Удалить")

        self.ui.addBase_button.clicked.connect(self._on_add_clicked)
        self.ui.editBase_button.clicked.connect(self._on_edit_clicked)
        self.ui.deleteBase_button.clicked.connect(self._on_delete_clicked)

        self._items: list[Locomotive] = []
        self.reload()

    def reload(self) -> None:
        """Перечитывает данные из БД и перерисовывает таблицу."""
        try:
            self._items = get_all_locomotives(self.session_factory)
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при загрузке локомотивов")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось загрузить данные:\n{e}")
            self._items = []

        table = self.ui.base_table
        table.setColumnCount(len(self.HEADERS))
        table.setHorizontalHeaderLabels(self.HEADERS)
        table.setRowCount(len(self._items))

        for row, item in enumerate(self._items):
            model = item.model
            manufacturer = model.manufacturer.name if model and model.manufacturer else NO_DATA
            values = [
                str(item.id),
                str(item.system),
                str(item.number),
                manufacturer,
                model.name if model else NO_DATA,
                str(model.code) if model else NO_DATA,
            ]
            for col, value in enumerate(values):
                table.setItem(row, col, QTableWidgetItem(value))

    def _selected_item(self) -> Locomotive | None:
        """Возвращает выбранную запись."""
        row = self.ui.base_table.currentRow()
        if row < 0 or row >= len(self._items):
            return None
        return self._items[row]

    def _on_add_clicked(self) -> None:
        """Открывает диалог создания."""
        dialog = LocomotiveDialog(self.session_factory, self.current_user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _on_edit_clicked(self) -> None:
        """Открывает диалог редактирования."""
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "Внимание", "Выберите запись")
            return

        dialog = LocomotiveDialog(self.session_factory, self.current_user, item, parent=self)
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
            f"Удалить локомотив «{item.system} {item.number}»?\n"
            f"Действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            delete_locomotive(self.session_factory, item.id)
        except EntityInUseError as e:
            QMessageBox.warning(self, "Внимание", str(e))
            return
        except LocomotiveNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Запись уже удалена")
            return
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при удалении локомотива")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось удалить:\n{e}")
            return

        self.reload()


# =============================================================
# Вкладка: детали
# =============================================================

class DetailsTab(QWidget):
    """Вкладка «Детали»."""

    HEADERS = ["ID", "Артикул", "Производитель", "Наименование", "Остаток"]

    def __init__(
        self,
        session_factory: sessionmaker,
        current_user: User,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.session_factory = session_factory
        self.current_user = current_user

        self.ui = Ui_baseTab_widget()
        self.ui.setupUi(self)

        self.ui.base_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.ui.addBase_button.setText("Добавить")
        self.ui.editBase_button.setText("Изменить")
        self.ui.deleteBase_button.setText("Удалить")

        self.ui.addBase_button.clicked.connect(self._on_add_clicked)
        self.ui.editBase_button.clicked.connect(self._on_edit_clicked)
        self.ui.deleteBase_button.clicked.connect(self._on_delete_clicked)

        self._items: list[Detail] = []
        self.reload()

    def reload(self) -> None:
        """Перечитывает данные из БД и перерисовывает таблицу."""
        try:
            self._items = get_all_details(self.session_factory)
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при загрузке деталей")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось загрузить данные:\n{e}")
            self._items = []

        table = self.ui.base_table
        table.setColumnCount(len(self.HEADERS))
        table.setHorizontalHeaderLabels(self.HEADERS)
        table.setRowCount(len(self._items))

        for row, item in enumerate(self._items):
            manufacturer = item.manufacturer.name if item.manufacturer else NO_DATA
            values = [
                str(item.id),
                str(item.code),
                manufacturer,
                item.name,
                str(item.quantity_in_stock),
            ]
            for col, value in enumerate(values):
                table.setItem(row, col, QTableWidgetItem(value))

    def _selected_item(self) -> Detail | None:
        """Возвращает выбранную запись."""
        row = self.ui.base_table.currentRow()
        if row < 0 or row >= len(self._items):
            return None
        return self._items[row]

    def _on_add_clicked(self) -> None:
        """Открывает диалог создания."""
        dialog = DetailDialog(self.session_factory, self.current_user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _on_edit_clicked(self) -> None:
        """Открывает диалог редактирования."""
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "Внимание", "Выберите запись")
            return

        dialog = DetailDialog(self.session_factory, self.current_user, item, parent=self)
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
            f"Удалить деталь «{item.name}»?\nДействие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            delete_detail(self.session_factory, item.id)
        except EntityInUseError as e:
            QMessageBox.warning(self, "Внимание", str(e))
            return
        except DetailNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Запись уже удалена")
            return
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при удалении детали")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось удалить:\n{e}")
            return

        self.reload()


# =============================================================
# Вкладка: листы обслуживания
# =============================================================

class MaintenancesTab(QWidget):
    """Вкладка «Листы обслуживания»."""

    HEADERS = ["ID", "Локомотив", "Тип", "Комментарий", "Автор"]

    def __init__(
        self,
        session_factory: sessionmaker,
        current_user: User,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.session_factory = session_factory
        self.current_user = current_user

        self.ui = Ui_baseTab_widget()
        self.ui.setupUi(self)

        self.ui.base_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.ui.addBase_button.setText("Создать")
        self.ui.editBase_button.setText("Изменить")
        self.ui.deleteBase_button.setText("Пометить на удаление")

        self.ui.addBase_button.clicked.connect(self._on_add_clicked)
        self.ui.editBase_button.clicked.connect(self._on_edit_clicked)
        self.ui.deleteBase_button.clicked.connect(self._on_delete_clicked)

        self._items: list[Maintenance] = []
        self.reload()

    def reload(self) -> None:
        """Перечитывает данные из БД и перерисовывает таблицу."""
        try:
            self._items = get_all_maintenances(self.session_factory)
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при загрузке листов обслуживания")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось загрузить данные:\n{e}")
            self._items = []

        table = self.ui.base_table
        table.setColumnCount(len(self.HEADERS))
        table.setHorizontalHeaderLabels(self.HEADERS)
        table.setRowCount(len(self._items))

        for row, item in enumerate(self._items):
            locomotive_text = f"{item.locomotive.system} {item.locomotive.number}" if item.locomotive else NO_DATA
            type_text = item.maintenance_type.name if item.maintenance_type else NO_DATA
            author_text = item.user.login if item.user else NO_DATA

            values = [
                str(item.id),
                locomotive_text,
                type_text,
                item.description or "",
                author_text,
            ]
            for col, value in enumerate(values):
                table.setItem(row, col, QTableWidgetItem(value))

    def _selected_item(self) -> Maintenance | None:
        """Возвращает выбранную запись."""
        row = self.ui.base_table.currentRow()
        if row < 0 or row >= len(self._items):
            return None
        return self._items[row]

    def _on_add_clicked(self) -> None:
        """Открывает диалог создания."""
        dialog = MaintenanceDialog(self.session_factory, self.current_user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _on_edit_clicked(self) -> None:
        """Открывает диалог редактирования."""
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "Внимание", "Выберите запись")
            return

        dialog = MaintenanceDialog(self.session_factory, self.current_user, item, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _on_delete_clicked(self) -> None:
        """Помечает выбранную запись как удалённую."""
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "Внимание", "Выберите запись")
            return

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Пометить на удаление лист обслуживания «{item.id}»?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            mark_maintenance_deleted(self.session_factory, item.id)
        except MaintenanceNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Запись уже удалена")
            return
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при удалении листа обслуживания")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось удалить:\n{e}")
            return

        self.reload()


# =============================================================
# Пользователи
# =============================================================

class UserEditDialog(QDialog):
    """Диалог редактирования пользователя."""

    def __init__(
        self,
        session_factory: sessionmaker,
        user: User,
        admin_mode: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.session_factory = session_factory
        self.user = user
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
        """Сохраняет изменения пользователя одной атомарной операцией."""
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

        if self.admin_mode and self.user.is_admin and self.user.is_active:
            if not ensure_not_last_active_admin(
                self.session_factory,
                self.user.id,
                will_be_admin=is_admin,
                will_be_active=is_active,
                parent=self,
            ):
                return

        try:
            update_user_full(
                self.session_factory,
                self.user.id,
                login=login,
                first_name=first_name,
                last_name=last_name,
                password=new_pass if new_pass else None,
                is_admin=is_admin if self.admin_mode else None,
                is_active=is_active if self.admin_mode else None,
            )
        except LoginAlreadyTakenError:
            QMessageBox.warning(self, "Внимание", "Этот логин уже занят")
            return
        except LastActiveAdminError:
            QMessageBox.warning(self, "Внимание", "Нельзя оставить систему без активных администраторов")
            return
        except UserNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Пользователь не найден")
            return
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при сохранении пользователя")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось сохранить:\n{e}")
            return

        self.user.login = login
        self.user.first_name = first_name
        self.user.last_name = last_name

        if self.admin_mode:
            self.user.is_admin = is_admin
            self.user.is_active = is_active

        self.accept()


class UserCreateDialog(QDialog):
    """Диалог создания нового пользователя."""

    def __init__(self, session_factory: sessionmaker, parent: QWidget | None = None):
        super().__init__(parent)
        self.session_factory = session_factory

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
            add_user(
                self.session_factory,
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
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при создании пользователя")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось создать пользователя:\n{e}")
            return

        self.accept()


class UserManagementDialog(QDialog):
    """Окно со списком пользователей."""

    def __init__(
        self,
        session_factory: sessionmaker,
        current_user: User,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.session_factory = session_factory
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

        self._users: list[User] = []
        self._load_users_table()

    def _load_users_table(self) -> None:
        """Перечитывает список пользователей и перерисовывает таблицу."""
        table = self.ui.users_tableWidget

        try:
            self._users = get_all_users(self.session_factory)
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при загрузке пользователей")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось загрузить пользователей:\n{e}")
            self._users = []

        headers = ["ID", "Логин", "Имя", "Фамилия", "Админ", "Отключен"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(self._users))

        columns = (
            lambda u: str(u.id),
            lambda u: u.login,
            lambda u: u.first_name or "",
            lambda u: u.last_name or "",
            lambda u: BOOL_YES if u.is_admin else BOOL_NO,
            lambda u: BOOL_YES if not u.is_active else BOOL_NO,
        )

        for row, user in enumerate(self._users):
            for col, get_value in enumerate(columns):
                table.setItem(row, col, QTableWidgetItem(get_value(user)))

    def _selected_user(self) -> User | None:
        """Возвращает выбранного пользователя."""
        row = self.ui.users_tableWidget.currentRow()
        if row < 0 or row >= len(self._users):
            return None
        return self._users[row]

    def _on_add_clicked(self) -> None:
        """Открывает диалог создания пользователя."""
        dialog = UserCreateDialog(self.session_factory, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_users_table()

    def _on_edit_clicked(self) -> None:
        """Открывает диалог редактирования пользователя."""
        user = self._selected_user()
        if user is None:
            QMessageBox.information(self, "Внимание", "Выберите пользователя")
            return

        dialog = UserEditDialog(self.session_factory, user, admin_mode=True, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_users_table()

    def _on_delete_clicked(self) -> None:
        """Удаляет выбранного пользователя."""
        user = self._selected_user()
        if user is None:
            QMessageBox.information(self, "Внимание", "Выберите пользователя")
            return

        if user.id == self.current_user.id:
            QMessageBox.warning(self, "Внимание", "Нельзя удалить самого себя")
            return

        if user.is_admin and user.is_active:
            if not ensure_not_last_active_admin(
                self.session_factory,
                user.id,
                will_be_admin=False,
                will_be_active=False,
                parent=self,
            ):
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
            delete_user(self.session_factory, user.id)
        except EntityInUseError as e:
            QMessageBox.warning(self, "Внимание", str(e))
            return
        except UserNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Пользователь уже удалён")
            return
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при удалении пользователя")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось удалить пользователя:\n{e}")
            return

        self._load_users_table()


# =============================================================
# Главное окно
# =============================================================

class MainScreen(QMainWindow):
    """Главное окно после входа."""

    logout_requested = Signal()

    def __init__(
        self,
        session_factory: sessionmaker,
        user: User,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.session_factory = session_factory
        self.user = user

        self.ui = Ui_main_window()
        self.ui.setupUi(self)

        self._setup_menu()
        self._apply_role_visibility()
        self._embed_tabs()

    def _setup_menu(self) -> None:
        """Настраивает действия меню."""
        self.ui.user_menuItem.setText(f"{self.user.first_name} {self.user.last_name}")
        self.ui.user_menuItem.triggered.connect(self._open_user_edit_dialog)
        self.ui.changeUser_menuItem.triggered.connect(self.logout_requested.emit)
        self.ui.userManagement_menuItem.triggered.connect(self._open_user_management_dialog)

    def _apply_role_visibility(self) -> None:
        """Скрывает административные пункты для не-администраторов."""
        if self.user.is_admin:
            return

        self.ui.userManagement_menuItem.setVisible(False)
        self.ui.programmSettings_menuItem.setVisible(False)

    def _embed_tabs(self) -> None:
        """Встраивает вкладки в главное окно."""
        self.maintenances_tab = MaintenancesTab(self.session_factory, self.user)
        self._add_tab(self.ui.maintenances_tab, self.maintenances_tab)

        self.locomotives_tab = LocomotivesTab(self.session_factory, self.user)
        self._add_tab(self.ui.locomotives_tab, self.locomotives_tab)

        self.details_tab = DetailsTab(self.session_factory, self.user)
        self._add_tab(self.ui.details_tab, self.details_tab)

        self.locomotive_models_tab = LocomotiveModelsTab(self.session_factory, self.user)
        self._add_tab(self.ui.locomotiveModels_tab, self.locomotive_models_tab)

        self.maintenance_types_tab = MaintenanceTypesTab(self.session_factory, self.user)
        self._add_tab(self.ui.maintenanceTypes_tab, self.maintenance_types_tab)

        self.manufacturers_tab = ManufacturersTab(self.session_factory, self.user)
        self._add_tab(self.ui.manufactures_tab, self.manufacturers_tab)

    @staticmethod
    def _add_tab(container: QWidget, widget: QWidget) -> None:
        """Помещает виджет в layout контейнера без отступов."""
        layout = container.layout()
        if layout is None:
            layout = QVBoxLayout(container)

        while layout.count():
            item = layout.takeAt(0)
            if item is not None:
                child = item.widget()
                if child is not None:
                    child.setParent(None)
                    child.deleteLater()

        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)

    def _open_user_management_dialog(self) -> None:
        """Открывает окно управления пользователями."""
        UserManagementDialog(self.session_factory, self.user, parent=self).exec()
        self.ui.user_menuItem.setText(f"{self.user.first_name} {self.user.last_name}")
        self._apply_role_visibility()

    def _open_user_edit_dialog(self) -> None:
        """Открывает диалог редактирования своего профиля."""
        dialog = UserEditDialog(self.session_factory, self.user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.ui.user_menuItem.setText(f"{self.user.first_name} {self.user.last_name}")


# =============================================================
# Стек экранов
# =============================================================

class ScreensStack(QStackedWidget):
    """Стек экранов: авторизация и главное окно."""

    def __init__(self, session_factory: sessionmaker, parent: QWidget | None = None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.main_screen: MainScreen | None = None

        self.auth_screen = AuthScreen(session_factory=self.session_factory)
        self.addWidget(self.auth_screen)
        self.auth_screen.auth_successful.connect(self._handle_login_success)
        self.setCurrentWidget(self.auth_screen)

    @Slot(User)
    def _handle_login_success(self, user: User) -> None:
        """Создаёт главный экран после успешного входа."""
        self._clear_main_screens()
        self.main_screen = MainScreen(self.session_factory, user)
        self.main_screen.logout_requested.connect(self._handle_logout)
        self.addWidget(self.main_screen)
        self.setCurrentWidget(self.main_screen)

    def _handle_logout(self) -> None:
        """Возвращает пользователя на экран авторизации."""
        self._clear_main_screens()
        self.auth_screen.reset_form()
        self.setCurrentWidget(self.auth_screen)

    def _clear_main_screens(self) -> None:
        """Удаляет все экраны, кроме экрана авторизации."""
        for index in range(self.count() - 1, 0, -1):
            widget = self.widget(index)
            if widget:
                self.removeWidget(widget)
                widget.deleteLater()

        self.main_screen = None
