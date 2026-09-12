from PySide6.QtWidgets import QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel, QMenu, QAction
from PySide6.QtCore import Qt, Signal


class MainWindow(QMainWindow):
    """
    Главное окно приложения с вкладками и зоной профиля пользователя.
    """
    # Сигнал для запроса выхода из системы
    logout_requested = Signal()
    # Сигнал для запроса добавления пользователя
    add_user_requested = Signal()

    def __init__(self):
        super().__init__()
        self._init_ui()
        self.current_user = None

    def _init_ui(self):
        self.setWindowTitle("Grandmaket LokoDB")
        self.resize(1000, 700)

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Виджет с вкладками
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)  # Более плоский стиль вкладок
        
        # Заглушки для вкладок (будут заполнены позже)
        self.trains_tab = QLabel("Таблица поездов (в разработке)")
        self.trains_tab.setAlignment(Qt.AlignCenter)
        
        self.parts_tab = QLabel("Таблица деталей (в разработке)")
        self.parts_tab.setAlignment(Qt.AlignCenter)

        self.tabs.addTab(self.trains_tab, "Поезда")
        self.tabs.addTab(self.parts_tab, "Детали")

        layout.addWidget(self.tabs)
        
        # Создаем меню после инициализации UI
        self._create_menu_bar()

    def _create_menu_bar(self):
        """Создание меню 'Аккаунт'"""
        menubar = self.menuBar()
        
        # Меню "Аккаунт"
        account_menu = menubar.addMenu("Аккаунт")
        
        # Пункт с именем пользователя (неактивный, просто информация)
        self.user_info_action = QAction("Гость", self)
        self.user_info_action.setEnabled(False)
        account_menu.addAction(self.user_info_action)
        
        account_menu.addSeparator()
        
        # Пункт "Добавить пользователя"
        add_user_action = QAction("Добавить пользователя", self)
        add_user_action.triggered.connect(self._on_add_user_triggered)
        account_menu.addAction(add_user_action)
        
        account_menu.addSeparator()
        
        # Пункт "Выйти"
        logout_action = QAction("Выйти", self)
        logout_action.triggered.connect(self._on_logout_triggered)
        account_menu.addAction(logout_action)

    def _on_add_user_triggered(self):
        """Обработчик нажатия 'Добавить пользователя'"""
        self.add_user_requested.emit()

    def _on_logout_triggered(self):
        """Обработчик нажатия 'Выйти'"""
        self.logout_requested.emit()

    def set_user_info(self, first_name: str, last_name: str):
        """Установка информации о текущем пользователе в меню"""
        self.current_user = {"first_name": first_name, "last_name": last_name}
        full_name = f"{first_name} {last_name}"
        if hasattr(self, 'user_info_action'):
            self.user_info_action.setText(full_name)
