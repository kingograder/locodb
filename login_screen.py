from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont


class LoginScreen(QWidget):
    """
    Виджет экрана авторизации.
    Отправляет сигнал login_successful при успешной валидации.
    """
    login_successful = Signal(str, str)  # Сигнал передает username и full_name

    def __init__(self):
        super().__init__()
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(40, 40, 40, 40)

        # Заголовок
        title = QLabel("Авторизация")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Поле логина
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Логин (admin)")
        layout.addWidget(self.username_input)

        # Поле пароля
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Пароль (admin)")
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        # Сообщение об ошибке
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red; font-size: 12px;")
        self.error_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.error_label)

        # Кнопка входа
        self.login_button = QPushButton("Войти")
        self.login_button.setMinimumHeight(40)
        layout.addWidget(self.login_button)

        self.setLayout(layout)

    def _connect_signals(self):
        self.login_button.clicked.connect(self._attempt_login)
        # Вход по нажатию Enter
        self.password_input.returnPressed.connect(self._attempt_login)

    def _attempt_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        # Сброс ошибок
        self.error_label.setText("")
        self.username_input.setStyleSheet("")
        self.password_input.setStyleSheet("")

        # Простая валидация (заглушка)
        if not username or not password:
            self.error_label.setText("Заполните все поля")
            return

        # Хардкод проверка для демо
        if username == "admin" and password == "admin":
            self.login_successful.emit(username, "Admin Admin")
        else:
            self.error_label.setText("Неверный логин или пароль")
            # Подсветка полей красным
            error_style = "border: 1px solid red;"
            self.username_input.setStyleSheet(error_style)
            self.password_input.setStyleSheet(error_style)

    def clear_fields(self):
        """Очистка полей при выходе из аккаунта"""
        self.username_input.clear()
        self.password_input.clear()
        self.error_label.setText("")
        self.username_input.setStyleSheet("")
        self.password_input.setStyleSheet("")
        self.username_input.setFocus()
