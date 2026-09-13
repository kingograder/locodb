"""
Модуль экрана авторизации.
Реализует виджет входа с валидацией полей и сигналом об успешной авторизации.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QPushButton, 
    QLabel, QMessageBox, QFormLayout
)
from PySide6.QtCore import Signal, Qt


class LoginScreen(QWidget):
    """
    Виджет экрана авторизации.
    
    Сигналы:
        login_successful(str): Испускается при успешном входе, передает имя пользователя.
    """
    login_successful = Signal(str)

    def __init__(self, auth_service=None, parent=None):
        super().__init__(parent)
        self.auth_service = auth_service
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """Инициализация пользовательского интерфейса."""
        self.setWindowTitle("Вход в систему")
        self.setFixedSize(300, 200)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # Заголовок
        title = QLabel("Авторизация")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # Форма ввода
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Логин")
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Пароль")
        self.password_input.setEchoMode(QLineEdit.Password)

        form_layout.addRow("Логин:", self.username_input)
        form_layout.addRow("Пароль:", self.password_input)
        layout.addLayout(form_layout)

        # Кнопка входа
        self.login_button = QPushButton("Войти")
        self.login_button.setDefault(True)
        layout.addWidget(self.login_button)

        # Сообщение об ошибке (скрыто по умолчанию)
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red; font-size: 12px;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

    def _connect_signals(self):
        """Подключение сигналов и слотов."""
        self.login_button.clicked.connect(self._handle_login)
        self.username_input.returnPressed.connect(self._handle_login)
        self.password_input.returnPressed.connect(self._handle_login)

    def _handle_login(self):
        """Обработка нажатия кнопки входа."""
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not self._validate_input(username, password):
            return

        # Проверка через сервис авторизации или заглушка
        if self.auth_service:
            success, user_data = self.auth_service.authenticate(username, password)
        else:
            # Заглушка для демонстрации (можно убрать при интеграции)
            success = (username == "admin" and password == "admin")
            user_data = {"first_name": "Админ", "last_name": "Системы"} if success else None

        if success:
            full_name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
            if not full_name:
                full_name = username
            self.login_successful.emit(full_name)
        else:
            self._show_error("Неверный логин или пароль")

    def _validate_input(self, username: str, password: str) -> bool:
        """
        Валидация введенных данных.
        
        Возвращает True если данные корректны, иначе False и показывает ошибку.
        """
        if not username:
            self._show_error("Введите логин")
            self.username_input.setFocus()
            return False
        
        if not password:
            self._show_error("Введите пароль")
            self.password_input.setFocus()
            return False
            
        self._hide_error()
        return True

    def _show_error(self, message: str):
        """Отображение сообщения об ошибке."""
        self.error_label.setText(message)
        self.error_label.show()

    def _hide_error(self):
        """Скрытие сообщения об ошибке."""
        self.error_label.hide()
        self.error_label.clear()

    def clear_fields(self):
        """Очистка полей ввода."""
        self.username_input.clear()
        self.password_input.clear()
        self.username_input.setFocus()
        self._hide_error()
