# -*- coding: utf-8 -*-
"""Экраны приложения: авторизация, главное окно, стек экранов."""

import logging
from contextlib import contextmanager

from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.services import Services
from app.gui.dialogs import UserEditDialog, UserManagementDialog
from app.gui.tabs import (
    DetailsTab,
    LocomotivesTab,
    LocomotiveModelsTab,
    MaintenancesTab,
    MaintenanceTypesTab,
    ManufacturersTab,
    SuppliesTab,
)
from app.widgets.ui_auth_window import Ui_auth_window
from app.widgets.ui_main_window import Ui_main_window

from app.db.exceptions import (
    InvalidPasswordError,
    UserNotActiveError,
    UserNotFoundError,
)

logger = logging.getLogger(__name__)


class AuthScreen(QWidget):
    """Экран авторизации."""

    auth_successful = Signal(object)

    def __init__(self, services: Services, parent=None):
        super().__init__(parent)
        self.services = services
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

        login = self.ui.login_lineEdit.text().strip()
        password = self.ui.pass_lineEdit.text()

        if not login or not password:
            QMessageBox.warning(self, "Внимание", "Заполните все поля")
            return

        with self._busy_context():
            try:
                user = self.services.users.authenticate(login, password)
            except UserNotFoundError:
                QMessageBox.critical(
                    self, "Ошибка авторизации",
                    f"Пользователь «{login}» не найден",
                )
                return
            except UserNotActiveError:
                QMessageBox.critical(
                    self, "Ошибка авторизации",
                    "Учётная запись отключена администратором",
                )
                return
            except InvalidPasswordError:
                QMessageBox.critical(
                    self, "Ошибка авторизации", "Неверный пароль",
                )
                return

        self.auth_successful.emit(user)

    def reset_form(self) -> None:
        """Очищает поля ввода."""
        self.ui.login_lineEdit.clear()
        self.ui.pass_lineEdit.clear()
        self.ui.login_lineEdit.setFocus()


class MainScreen(QMainWindow):
    """Главное окно после входа."""

    logout_requested = Signal()

    def __init__(self, services: Services, user, parent=None):
        super().__init__(parent)
        self.services = services
        self.user = user

        self.ui = Ui_main_window()
        self.ui.setupUi(self)

        self._setup_menu()
        self._apply_role_visibility()
        self._embed_user_tabs()
        self._embed_admin_tabs()
        self.ui.tabWidget.currentChanged.connect(self._refresh_details_tab)

    def _refresh_details_tab(self, index: int) -> None:
        """Обновляет остатки при открытии вкладки деталей."""
        if self.ui.tabWidget.widget(index) is not self.ui.details_tab:
            return

        details_tab = self.ui.details_tab.findChild(DetailsTab)
        if details_tab is not None:
            details_tab.reload()

    def _setup_menu(self) -> None:
        """Настраивает действия меню."""
        self._refresh_user_menu_title()
        self.ui.user_menuItem.triggered.connect(self._open_user_edit_dialog)
        self.ui.changeUser_menuItem.triggered.connect(self.logout_requested.emit)
        self.ui.userManagement_menuItem.triggered.connect(self._open_user_management_dialog)

    def _refresh_user_menu_title(self) -> None:
        """Обновляет заголовок пункта меню с именем текущего пользователя."""
        first = (self.user.first_name or "").capitalize()
        last = (self.user.last_name or "").capitalize()
        title = f"{first} {last}".strip() or self.user.login
        self.ui.user_menuItem.setText(title)

    def _apply_role_visibility(self) -> None:
        """Согласованно показывает меню и вкладки согласно роли."""
        is_admin = self.user.is_admin
        self.ui.userManagement_menuItem.setVisible(is_admin)
        self.ui.programmSettings_menuItem.setVisible(is_admin)

        for page in self._admin_tab_pages():
            index = self.ui.tabWidget.indexOf(page)
            if index >= 0:
                self.ui.tabWidget.setTabVisible(index, is_admin)

    def _embed_user_tabs(self) -> None:
        """Встраивает вкладки в главное окно."""
        tabs = [
            (self.ui.maintenances_tab, MaintenancesTab),
            (self.ui.locomotives_tab, LocomotivesTab),
            (self.ui.details_tab, DetailsTab),
        ]

        for container, tab_class in tabs:
            widget = tab_class(self.services, self.user)
            self._add_tab(container, widget)

    def _embed_admin_tabs(self) -> None:
        """Встраивает админские вкладки в главное меню."""
        tabs = [
            (self.ui.locomotiveModels_tab, LocomotiveModelsTab),
            (self.ui.maintenanceTypes_tab, MaintenanceTypesTab),
            (self.ui.manufactures_tab, ManufacturersTab),
            (self.ui.supplies_tab, SuppliesTab),
        ]
        for container, tab_class in tabs:
            widget = tab_class(self.services, self.user)
            self._add_tab(container, widget)

    def _admin_tab_pages(self) -> tuple[QWidget, ...]:
        """Возвращает страницы, доступные только администраторам."""
        return (
            self.ui.locomotiveModels_tab,
            self.ui.maintenanceTypes_tab,
            self.ui.manufactures_tab,
            self.ui.supplies_tab,
        )

    def _refresh_current_user(self) -> None:
        """Обновляет текущего пользователя и ссылки вкладок после редактирования."""
        user = self.services.users.get(self.user.id)
        if user is None or not user.is_active:
            self.logout_requested.emit()
            return

        self.user = user
        for widget in self.findChildren(QWidget):
            if hasattr(widget, "current_user"):
                widget.current_user = user

        self._refresh_user_menu_title()
        self._apply_role_visibility()

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
        UserManagementDialog(self.services, self.user, parent=self).exec()
        self._refresh_current_user()

    def _open_user_edit_dialog(self) -> None:
        """Открывает диалог редактирования своего профиля."""
        dialog = UserEditDialog(self.services, self.user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._refresh_current_user()


class ScreensStack(QStackedWidget):
    """Стек экранов: авторизация и главное окно."""

    def __init__(self, services: Services, parent=None):
        super().__init__(parent)
        self.services = services
        self.main_screen: MainScreen | None = None

        self.auth_screen = AuthScreen(services=self.services)
        self.addWidget(self.auth_screen)
        self.auth_screen.auth_successful.connect(self._handle_login_success)
        self.setCurrentWidget(self.auth_screen)

    @Slot(object)
    def _handle_login_success(self, user) -> None:
        """Создаёт главный экран после успешного входа."""
        self._clear_main_screens()
        self.main_screen = MainScreen(self.services, user)
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
