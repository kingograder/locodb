from PySide6.QtWidgets import (
    QWidget, QMainWindow, QStackedWidget, QMessageBox, QLabel, QVBoxLayout
)
from PySide6.QtCore import Signal

from app.layouts.auth import Ui_Form_Auth

class AuthScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.auth_ui = Ui_Form_Auth()
        self.auth_ui.setupUi(self)
        

class MainScreenUser(QWidget):
    pass

class MainScreenAdmin(QWidget):
    pass

class ScreensStack(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Создаем экраны в стеке
        self.auth_screen  = AuthScreen()
        self.user_screen  = MainScreenUser()
        self.admin_screen = MainScreenAdmin()
        # Добавить экраны в стек
        self.addWidget(self.auth_screen)
        self.addWidget(self.user_screen)
        self.addWidget(self.admin_screen)
        # Вызываем экран логина
        self.setCurrentWidget(self.auth_screen)
