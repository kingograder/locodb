import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from PySide6.QtCore import QDate, Signal, Slot
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QHeaderView,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.strategy_options import raiseload

from app.db.functions import (
    add_detail,
    add_locomotive,
    add_locomotive_model,
    add_maintenance,
    add_user,
    assert_not_last_admin,
    authenticate,
    delete_detail,
    delete_locomotive,
    delete_user,
    get_all_details,
    get_all_locomotive_models,
    get_all_locomotives,
    get_all_maintenance_types,
    get_all_maintenances,
    get_all_users,
    mark_maintenance_deleted,
    update_detail,
    update_locomotive,
    update_locomotive_model,
    update_maintenance,
    update_user_full,
    DetailNotFoundError,
    LastActiveAdminError,
    LocomotiveModelNotFoundError,
    LocomotiveNotFoundError,
    LoginAlreadyTakenError,
    MaintenanceNotFoundError,
    UserNotFoundError,
)
from app.db.models import Detail, Locomotive, LocomotiveModel, Maintenance, User
from app.widgets.ui_auth_window import Ui_auth_window
from app.widgets.ui_main_window import Ui_main_window
from app.widgets.ui_base_tab_widget import Ui_baseTab_widget
from app.widgets.ui_user_edit_dialog import Ui_userEdit_dialog
from app.widgets.ui_user_management_dialog import Ui_usersManagement_dialog
from app.widgets.ui_maintenance_add_dialog import Ui_addMaintenance_dialog
from app.widgets.ui_locomotive_add_dialog import Ui_addLocomotive_dialog
from app.widgets.ui_locomotive_model_add_dialog import Ui_addLocomotiveModel_dialog
from app.widgets.ui_detail_add_dialog import Ui_addDetail_dialog

logger = logging.getLogger(__name__)

IMAGE_FILTER = "Изображения (*.png *.jpg *.jpeg *.bmp)"
BOOL_YES = "Да"
BOOL_NO = "Нет"
NO_DATA = "—"

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


class BaseEntityDialog(QDialog):
    not_found_error: type[Exception] = Exception

    def __init__(
        self,
        session_factory: sessionmaker,
        current_user: User,
        entity: Any | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.session_factory = session_factory
        self.current_user = current_user
        self.entity = entity

        # Вызываем методы, которые наследник обязан определить сам
        self._setup_ui()
        self._connect_buttons()

        if entity is None:
            self.setWindowTitle(self._create_title())
        else:
            self.setWindowTitle(self._edit_title())
            self._load_data(entity)

    def _sync_entity(self, entity: Any, fields: dict[str, Any]) -> None:
        for key, value in fields.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        if hasattr(entity, "updated_by_id"):
            entity.updated_by_id = self.current_user.id

    def _on_save(self) -> None:
        if not self._validate():
            return

        fields = self._collect_fields()
        entity = self.entity

        try:
            if entity is None:
                self._add_to_db(fields)
            else:
                self._update_in_db(entity, fields)
                self._sync_entity(entity, fields)
        except self.not_found_error:
            QMessageBox.critical(self, "Ошибка", "Запись не найдена")
            return
        except SQLAlchemyError as e:
            logger.exception(f"Ошибка БД при сохранении {type(self).__name__}")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось сохранить:\n{e}")
            return

        self.accept()


class MaintenanceDialog(BaseEntityDialog):
    """Диалог создания и редактирования листа обслуживания."""

    not_found_error = MaintenanceNotFoundError

    def _setup_ui(self) -> None:
        self.ui = Ui_addMaintenance_dialog()
        self.ui.setupUi(self)
        self._load_locomotives()
        self._load_types()

    def _connect_buttons(self) -> None:
        self.ui.addMaintenance_buttonBox.accepted.connect(self._on_save)
        self.ui.addMaintenance_buttonBox.rejected.connect(self.reject)

    def _create_title(self) -> str:
        return "Новый лист обслуживания"

    def _edit_title(self) -> str:
        return "Редактирование листа обслуживания"

    def _load_locomotives(self) -> None:
        try:
            locomotives = get_all_locomotives(self.session_factory)
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при загрузке локомотивов")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось загрузить локомотивы:\n{e}")
            locomotives = []

        self.ui.addMaintenanceLoco_comboBox.clear()
        for loco in locomotives:
            self.ui.addMaintenanceLoco_comboBox.addItem(f"{loco.system} {loco.number}", loco.id)

    def _load_types(self) -> None:
        try:
            types = get_all_maintenance_types(self.session_factory)
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при загрузке типов обслуживания")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось загрузить типы:\n{e}")
            types = []

        self.ui.addMaintenanceType_comboBox.clear()
        for item in types:
            self.ui.addMaintenanceType_comboBox.addItem(item.name, item.id)

    def _load_data(self, entity: Maintenance) -> None:
        loco_index = self.ui.addMaintenanceLoco_comboBox.findData(entity.locomotive_id)
        if loco_index >= 0:
            self.ui.addMaintenanceLoco_comboBox.setCurrentIndex(loco_index)

        type_index = self.ui.addMaintenanceType_comboBox.findData(entity.maintenance_type_id)
        if type_index >= 0:
            self.ui.addMaintenanceType_comboBox.setCurrentIndex(type_index)

        maintenance_date = entity.maintenance_date
        self.ui.addMaintenanceDate_dateEdit.setDate(
            QDate(maintenance_date.year, maintenance_date.month, maintenance_date.day)
        )

        if entity.description:
            self.ui.addMaintenanceComment_textEdit.setPlainText(entity.description)

    def _collect_fields(self) -> dict[str, Any]:
        qdate = self.ui.addMaintenanceDate_dateEdit.date()
        return {
            "locomotive_id": self.ui.addMaintenanceLoco_comboBox.currentData(),
            "maintenance_type_id": self.ui.addMaintenanceType_comboBox.currentData(),
            "maintenance_date": datetime(qdate.year(), qdate.month(), qdate.day()).astimezone(),
            "description": self.ui.addMaintenanceComment_textEdit.toPlainText().strip() or None,
        }

    def _validate(self) -> bool:
        if self.ui.addMaintenanceLoco_comboBox.currentData() is None:
            QMessageBox.warning(self, "Внимание", "Выберите локомотив")
            return False

        if self.ui.addMaintenanceType_comboBox.currentData() is None:
            QMessageBox.warning(self, "Внимание", "Выберите тип обслуживания")
            return False

        return True

    def _add_to_db(self, fields: dict[str, Any]) -> None:
        add_maintenance(
            self.session_factory,
            locomotive_id=fields["locomotive_id"],
            maintenance_type_id=fields["maintenance_type_id"],
            maintenance_date=fields["maintenance_date"],
            description=fields["description"],
            created_by_id=self.current_user.id,
        )

    def _update_in_db(self, entity: Maintenance, fields: dict[str, Any]) -> None:
        update_maintenance(
            self.session_factory,
            maintenance_id=entity.id,
            locomotive_id=fields["locomotive_id"],
            maintenance_type_id=fields["maintenance_type_id"],
            maintenance_date=fields["maintenance_date"],
            description=fields["description"],
            updated_by_id=self.current_user.id,
        )


class LocomotiveModelDialog(BaseEntityDialog):
    """Диалог создания и редактирования модели локомотива."""

    not_found_error = LocomotiveModelNotFoundError

    def _setup_ui(self) -> None:
        self.ui = Ui_addLocomotiveModel_dialog()
        self.ui.setupUi(self)
        self.ui.filepicker.clicked.connect(self._on_pick_file)

    def _connect_buttons(self) -> None:
        self.ui.addLocomotiveModel_buttonBox.accepted.connect(self._on_save)
        self.ui.addLocomotiveModel_buttonBox.rejected.connect(self.reject)

    def _create_title(self) -> str:
        return "Новая модель локомотива"

    def _edit_title(self) -> str:
        return "Редактирование модели локомотива"

    def _on_pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать изображение", "", IMAGE_FILTER)
        if path:
            self.ui.filepath.setText(path)

    def _load_data(self, entity: LocomotiveModel) -> None:
        self.ui.locomotiveModel_lineEdit.setText(entity.model_name)
        self.ui.manufacturer_lineEdit.setText(entity.manufacturer)
        self.ui.locomotiveCode_lineEdit.setText(entity.code)

        if entity.image_path:
            self.ui.filepath.setText(entity.image_path)

    def _collect_fields(self) -> dict[str, Any]:
        return {
            "code": self.ui.locomotiveCode_lineEdit.text().strip(),
            "manufacturer": self.ui.manufacturer_lineEdit.text().strip(),
            "model_name": self.ui.locomotiveModel_lineEdit.text().strip(),
            "image_path": self.ui.filepath.text().strip() or None,
        }

    def _validate(self) -> bool:
        fields = self._collect_fields()

        if not fields["code"]:
            QMessageBox.warning(self, "Внимание", "Укажите артикул")
            return False

        if not fields["manufacturer"]:
            QMessageBox.warning(self, "Внимание", "Укажите производителя")
            return False

        if not fields["model_name"]:
            QMessageBox.warning(self, "Внимание", "Укажите название модели")
            return False

        return True

    def _add_to_db(self, fields: dict[str, Any]) -> None:
        add_locomotive_model(
            self.session_factory,
            code=fields["code"],
            manufacturer=fields["manufacturer"],
            model_name=fields["model_name"],
            image_path=fields["image_path"],
            created_by_id=self.current_user.id,
        )

    def _update_in_db(self, entity: LocomotiveModel, fields: dict[str, Any]) -> None:
        update_locomotive_model(
            self.session_factory,
            model_id=entity.id,
            code=fields["code"],
            manufacturer=fields["manufacturer"],
            model_name=fields["model_name"],
            image_path=fields["image_path"],
            updated_by_id=self.current_user.id,
        )


class LocomotiveDialog(BaseEntityDialog):
    """Диалог создания и редактирования локомотива."""

    not_found_error = LocomotiveNotFoundError

    def _setup_ui(self) -> None:
        self.ui = Ui_addLocomotive_dialog()
        self.ui.setupUi(self)
        self._load_models()

    def _connect_buttons(self) -> None:
        self.ui.addLocomotive_buttonBox.accepted.connect(self._on_save)
        self.ui.addLocomotive_buttonBox.rejected.connect(self.reject)

    def _create_title(self) -> str:
        return "Новый локомотив"

    def _edit_title(self) -> str:
        return "Редактирование локомотива"

    def _load_models(self) -> None:
        try:
            models = get_all_locomotive_models(self.session_factory)
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при загрузке моделей локомотивов")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось загрузить модели:\n{e}")
            models = []

        self.ui.locomotiveModel_comboBox.clear()
        for model in models:
            self.ui.locomotiveModel_comboBox.addItem(f"{model.manufacturer} {model.model_name}", model.id)

    def _load_data(self, entity: Locomotive) -> None:
        try:
            self.ui.system_spinBox.setValue(int(entity.system))
        except (ValueError, TypeError):
            logger.warning(f"LocomotiveDialog: не удалось преобразовать system={entity.system!r} в int")
            self.ui.system_spinBox.setValue(0)

        self.ui.number_lineEdit.setText(entity.number)
        self.ui.type_lineEdit.setText(entity.model_type)

        model_index = self.ui.locomotiveModel_comboBox.findData(entity.model_id)
        if model_index >= 0:
            self.ui.locomotiveModel_comboBox.setCurrentIndex(model_index)

    def _collect_fields(self) -> dict[str, Any]:
        return {
            "system": str(self.ui.system_spinBox.value()),
            "number": self.ui.number_lineEdit.text().strip(),
            "model_type": self.ui.type_lineEdit.text().strip(),
            "model_id": self.ui.locomotiveModel_comboBox.currentData(),
        }

    def _validate(self) -> bool:
        fields = self._collect_fields()

        if not fields["number"]:
            QMessageBox.warning(self, "Внимание", "Укажите номер локомотива")
            return False

        if not fields["model_type"]:
            QMessageBox.warning(self, "Внимание", "Укажите тип локомотива")
            return False

        if fields["model_id"] is None:
            QMessageBox.warning(self, "Внимание", "Выберите модель")
            return False

        return True

    def _add_to_db(self, fields: dict[str, Any]) -> None:
        add_locomotive(
            self.session_factory,
            system=fields["system"],
            number=fields["number"],
            model_type=fields["model_type"],
            model_id=fields["model_id"],
            created_by_id=self.current_user.id,
        )

    def _update_in_db(self, entity: Locomotive, fields: dict[str, Any]) -> None:
        update_locomotive(
            self.session_factory,
            locomotive_id=entity.id,
            system=fields["system"],
            number=fields["number"],
            model_type=fields["model_type"],
            model_id=fields["model_id"],
            updated_by_id=self.current_user.id,
        )


class DetailDialog(BaseEntityDialog):
    """Диалог создания и редактирования детали."""

    not_found_error = DetailNotFoundError

    def _setup_ui(self) -> None:
        self.ui = Ui_addDetail_dialog()
        self.ui.setupUi(self)

    def _connect_buttons(self) -> None:
        self.ui.buttonBox.accepted.connect(self._on_save)
        self.ui.buttonBox.rejected.connect(self.reject)

    def _create_title(self) -> str:
        return "Новая деталь"

    def _edit_title(self) -> str:
        return "Редактирование детали"

    def _load_data(self, entity: Detail) -> None:
        self.ui.detailCode_lineEdit.setText(entity.code)
        self.ui.detailManufacturer_lineEdit.setText(entity.manufacturer)
        self.ui.detailCount_lineEdit.setText(str(entity.quantity_in_stock))

    def _collect_fields(self) -> dict[str, Any]:
        code = self.ui.detailCode_lineEdit.text().strip()
        return {
            "code": code,
            "manufacturer": self.ui.detailManufacturer_lineEdit.text().strip(),
            "name": code,
            "quantity_in_stock": self._parse_quantity(),
        }

    def _parse_quantity(self) -> int:
        try:
            return int(self.ui.detailCount_lineEdit.text() or "0")
        except ValueError:
            return 0

    def _validate(self) -> bool:
        if not self.ui.detailCode_lineEdit.text().strip():
            QMessageBox.warning(self, "Внимание", "Укажите артикул")
            return False

        if not self.ui.detailManufacturer_lineEdit.text().strip():
            QMessageBox.warning(self, "Внимание", "Укажите производителя")
            return False

        return True

    def _add_to_db(self, fields: dict[str, Any]) -> None:
        add_detail(
            self.session_factory,
            code=fields["code"],
            manufacturer=fields["manufacturer"],
            name=fields["name"],
            quantity_in_stock=fields["quantity_in_stock"],
            created_by_id=self.current_user.id,
        )

    def _update_in_db(self, entity: Detail, fields: dict[str, Any]) -> None:
        update_detail(
            self.session_factory,
            detail_id=entity.id,
            code=fields["code"],
            manufacturer=fields["manufacturer"],
            name=fields["name"],
            quantity_in_stock=fields["quantity_in_stock"],
            updated_by_id=self.current_user.id,
        )


class BaseListTab(QWidget):
    headers: list[str] = []
    add_button_text = "Добавить"
    edit_button_text = "Изменить"
    delete_button_text = "Удалить"

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

        self.ui.base_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ui.addBase_button.setText(self.add_button_text)
        self.ui.editBase_button.setText(self.edit_button_text)
        self.ui.deleteBase_button.setText(self.delete_button_text)

        self.ui.addBase_button.clicked.connect(self._on_add_clicked)
        self.ui.editBase_button.clicked.connect(self._on_edit_clicked)
        self.ui.deleteBase_button.clicked.connect(self._on_delete_clicked)

        self._items: list[Any] = []
        self.reload()

    def _fetch_items(self) -> list:
        raise NotImplementedError

    def _row_values(self, item) -> list:
        raise NotImplementedError

    def _open_dialog(self) -> QDialog:
        raise NotImplementedError

    def reload(self) -> None:
        table = self.ui.base_table
        try:
            self._items = self._fetch_items()
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при загрузке данных")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось загрузить данные:\n{e}")
            self._items = []

        table.setColumnCount(len(self.headers))
        table.setHorizontalHeaderLabels(self.headers)
        table.setRowCount(len(self._items))

        for row, item in enumerate(self._items):
            for col, value in enumerate(self._row_values(item)):
                table.setItem(row, col, QTableWidgetItem(value))

    def _selected_item(self) -> Any | None:
        row = self.ui.base_table.currentRow()
        if row < 0 or row >= len(self._items):
            return None
        return self._items[row]

    def _on_add_clicked(self) -> None:
        dialog = self._open_dialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _on_edit_clicked(self) -> None:
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "Внимание", "Выберите запись")
            return
        dialog = self._open_dialog(item)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _on_delete_clicked(self) -> None:
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "Внимание", "Выберите запись")
            return

        reply = QMessageBox.question(
            self, "Подтверждение", self._delete_confirm_text(item),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self._delete_item(item)
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при удалении")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось удалить:\n{e}")
            return

        self.reload()

class MaintenancesTab(BaseListTab):
    """Вкладка «Листы обслуживания»."""

    headers = ["ID", "Локомотив", "Дата", "Тип", "Комментарий", "Автор"]
    add_button_text = "Создать"
    delete_button_text = "Пометить на удаление"

    def _fetch_items(self) -> list[Maintenance]:
        return get_all_maintenances(self.session_factory)

    def _row_values(self, item: Maintenance) -> list[str]:
        return [
            str(item.id),
            f"{item.locomotive.system} {item.locomotive.number}",
            item.maintenance_date.strftime("%d.%m.%Y"),
            item.maintenance_type.name if item.maintenance_type else NO_DATA,
            item.description or "",
            item.created_by.login if item.created_by else NO_DATA,
        ]

    def _open_dialog(self, item: Maintenance | None = None) -> QDialog:
        return MaintenanceDialog(self.session_factory, self.current_user, item, parent=self)

    def _delete_item(self, item: Maintenance) -> None:
        mark_maintenance_deleted(self.session_factory, item.id, updated_by_id=self.current_user.id)

    def _item_name(self, item: Maintenance) -> str:
        return f"{item.locomotive.system} {item.locomotive.number}"

    def _delete_confirm_text(self, item: Maintenance) -> str:
        return f"Пометить на удаление лист «{self._item_name(item)}»?"


class LocomotivesTab(BaseListTab):
    """Вкладка «Локомотивы»."""

    headers = [
        "ID",
        "Система",
        "Номер",
        "Тип",
        "Модель",
        "Производитель",
        "Артикул",
        "Создан", # поле создан не нужно
        "Изменил", # поле изменил не нужно
        # Правильный порядок
        # ID
        # Фото (путь из базы данных)
        # Номер (number)
        # Система
        # Производитель
        # Артику (code)
        # Модель
        # Эта таблица формируется из двух таблиц базы данных Locomotive и LocomotiveModel
        # TODO
    ]

    def _fetch_items(self) -> list[Locomotive]:
        return get_all_locomotives(self.session_factory)

    def _row_values(self, item: Locomotive) -> list[str]:
        model = item.model
        return [
            str(item.id),
            item.system,
            item.number,
            item.model_type,
            model.model_name if model else "—",
            model.manufacturer if model else "—",
            model.code if model else "—",
            item.created_at.strftime("%d.%m.%Y %H:%M"),
            item.updated_by.login if item.updated_by else NO_DATA,
        ]

    def _open_dialog(self, item: Locomotive | None = None) -> QDialog:
        return LocomotiveDialog(self.session_factory, self.current_user, item, parent=self)

    def _delete_item(self, item: Locomotive) -> None:
        delete_locomotive(self.session_factory, item.id)

    def _item_name(self, item: Locomotive) -> str:
        return f"{item.system} {item.number}"

    def _delete_confirm_text(self, item: Locomotive) -> str:
        return f"Удалить локомотив «{self._item_name(item)}»?\nДействие нельзя отменить."


class DetailsTab(BaseListTab):
    """Вкладка «Детали»."""

    headers = ["ID", "Артикул", "Производитель", "Название", "Остаток"]

    def _fetch_items(self) -> list[Detail]:
        return get_all_details(self.session_factory)

    def _row_values(self, item: Detail) -> list[str]:
        return [
            str(item.id),
            item.code,
            item.manufacturer,
            item.name,
            str(item.quantity_in_stock),
        ]

    def _open_dialog(self, item: Detail | None = None) -> QDialog:
        return DetailDialog(self.session_factory, self.current_user, item, parent=self)

    def _delete_item(self, item: Detail) -> None:
        delete_detail(self.session_factory, item.id)

    def _item_name(self, item: Detail) -> str:
        return item.name

    def _delete_confirm_text(self, item: Detail) -> str:
        return f"Удалить деталь «{self._item_name(item)}»?\nДействие нельзя отменить."


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
        row = self.ui.users_tableWidget.currentRow()
        if row < 0 or row >= len(self._users):
            return None
        return self._users[row]

    def _on_add_clicked(self) -> None:
        dialog = UserCreateDialog(self.session_factory, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_users_table()

    def _on_edit_clicked(self) -> None:
        user = self._selected_user()
        if user is None:
            QMessageBox.information(self, "Внимание", "Выберите пользователя")
            return

        dialog = UserEditDialog(self.session_factory, user, admin_mode=True, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_users_table()

    def _on_delete_clicked(self) -> None:
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
        except UserNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Пользователь уже удалён")
        except SQLAlchemyError as e:
            logger.exception("Ошибка БД при удалении пользователя")
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось удалить пользователя:\n{e}")

        self._load_users_table()


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
        self.ui.user_menuItem.setText(f"{self.user.first_name} {self.user.last_name}")
        self.ui.user_menuItem.triggered.connect(self._open_user_edit_dialog)
        self.ui.changeUser_menuItem.triggered.connect(self.logout_requested.emit)
        self.ui.userManagement_menuItem.triggered.connect(self._open_user_management_dialog)

    def _apply_role_visibility(self) -> None:
        if self.user.is_admin:
            return

        self.ui.userManagement_menuItem.setVisible(False)
        self.ui.programmSettings_menuItem.setVisible(False)

    def _embed_tabs(self) -> None:
        self.maintenances_tab = MaintenancesTab(self.session_factory, self.user)
        self._add_tab(self.ui.maintenances_tab, self.maintenances_tab)

        self.locomotives_tab = LocomotivesTab(self.session_factory, self.user)
        self._add_tab(self.ui.locomotives_tab, self.locomotives_tab)

        self.details_tab = DetailsTab(self.session_factory, self.user)
        self._add_tab(self.ui.details_tab, self.details_tab)

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
        UserManagementDialog(self.session_factory, self.user, parent=self).exec()
        self.ui.user_menuItem.setText(f"{self.user.first_name} {self.user.last_name}")
        self._apply_role_visibility()

    def _open_user_edit_dialog(self) -> None:
        dialog = UserEditDialog(self.session_factory, self.user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.ui.user_menuItem.setText(f"{self.user.first_name} {self.user.last_name}")


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
        self._clear_main_screens()
        self.main_screen = MainScreen(self.session_factory, user)
        self.main_screen.logout_requested.connect(self._handle_logout)
        self.addWidget(self.main_screen)
        self.setCurrentWidget(self.main_screen)

    def _handle_logout(self) -> None:
        self._clear_main_screens()
        self.auth_screen.reset_form()
        self.setCurrentWidget(self.auth_screen)

    def _clear_main_screens(self) -> None:
        for index in range(self.count() - 1, 0, -1):
            widget = self.widget(index)
            if widget:
                self.removeWidget(widget)
                widget.deleteLater()

        self.main_screen = None
