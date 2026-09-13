import sys
from PySide6.QtWidgets import QApplication
from login_screen import LoginScreen
from main_window import MainWindow


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 1. Создаем экран логина
    login_screen = LoginScreen()
    
    # 2. Создаем главное окно (пока скрыто)
    main_window = MainWindow()

    def handle_login(username, full_name):
        """Обработчик успешного входа"""
        print(f"Успешный вход: {username}")
        
        # Парсим имя и фамилию
        names = full_name.split(" ")
        first_name = names[0] if len(names) > 0 else ""
        last_name = names[1] if len(names) > 1 else " ".join(names[1:])
        
        # Передаем данные в главное окно
        main_window.set_user_info(first_name, last_name)
        
        # Показываем главное окно
        main_window.show()
        # Скрываем логин
        login_screen.hide()

    def handle_logout():
        """Обработчик выхода из системы"""
        print("Выход из системы")
        main_window.hide()
        login_screen.clear_fields()
        login_screen.show()

    # Подключаем сигнал логина
    login_screen.login_successful.connect(handle_login)
    
    # Подключаем сигнал выхода
    main_window.logout_requested.connect(handle_logout)

    # Показываем экран входа
    login_screen.show()

    sys.exit(app.exec())
