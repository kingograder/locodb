"""
Виджет таблицы локомотивов.
Отображает данные о локомотивах с возможностью добавления новых записей.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableView, QPushButton, QHBoxLayout,
    QAbstractItemView, QMessageBox, QDialog
)
from PySide6.QtCore import QAbstractTableModel, Qt, Signal
from PySide6.QtGui import QColor

from src.services.locomotive_service import LocomotiveService
from dialogs import AddLocomotiveDialog


class LocomotiveTableModel(QAbstractTableModel):
    """Модель данных для таблицы локомотивов."""

    def __init__(self, data: list[dict]):
        super().__init__()
        self._data = data
        self._headers = [
            "Модель",
            "Производитель",
            "Инв. номер",
            "Система",
            "Тип модели",
            "Дата последнего ТО"
        ]

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole or role == Qt.EditRole:
            row = index.row()
            col = index.column()
            item = self._data[row]

            if col == 0:
                return item["model_name"]
            elif col == 1:
                return item["manufacturer"]
            elif col == 2:
                return item["number"]
            elif col == 3:
                return item["system"]
            elif col == 4:
                return item["model_type"]
            elif col == 5:
                date = item["last_maintenance_date"]
                if date:
                    return date.strftime("%d.%m.%Y")
                return "-"

        if role == Qt.TextAlignmentRole:
            # Выравнивание по центру для всех колонок
            return Qt.AlignCenter

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._headers[section]
            elif orientation == Qt.Vertical:
                return str(section + 1)
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignCenter | Qt.AlignVCenter
        return None

    def update_data(self, new_data: list[dict]):
        """Обновить данные в модели."""
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()


class LocomotivesTab(QWidget):
    """Виджет вкладки с таблицей локомотивов."""

    # Сигнал для запроса обновления данных
    refresh_requested = Signal()

    def __init__(self, session_factory):
        super().__init__()
        self.session_factory = session_factory
        self.service = LocomotiveService(session_factory)
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Панель с кнопками
        button_layout = QHBoxLayout()
        
        self.add_button = QPushButton("Добавить локомотив")
        self.add_button.clicked.connect(self._on_add_clicked)
        button_layout.addWidget(self.add_button)

        button_layout.addStretch()

        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.clicked.connect(self._load_data)
        button_layout.addWidget(self.refresh_button)

        layout.addLayout(button_layout)

        # Таблица
        self.table_view = QTableView()
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(True)
        
        # Настройка внешнего вида
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.setShowGrid(True)
        
        layout.addWidget(self.table_view)

    def _load_data(self):
        """Загрузить данные из БД."""
        try:
            data = self.service.get_all_locomotives_with_last_maintenance()
            
            if not hasattr(self, 'table_model'):
                self.table_model = LocomotiveTableModel(data)
                self.table_view.setModel(self.table_model)
                
                # Настройка ширины колонок
                header = self.table_view.horizontalHeader()
                header.setSectionResizeMode(0, header.Stretch)  # Модель
                header.setSectionResizeMode(1, header.Stretch)  # Производитель
                header.setSectionResizeMode(2, header.ResizeToContents)  # Инв. номер
                header.setSectionResizeMode(3, header.ResizeToContents)  # Система
                header.setSectionResizeMode(4, header.ResizeToContents)  # Тип
                header.setSectionResizeMode(5, header.ResizeToContents)  # Дата ТО
            else:
                self.table_model.update_data(data)
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить данные: {e}")

    def _on_add_clicked(self):
        """Обработчик нажатия кнопки добавления."""
        # Получаем сессию из фабрики
        db = self.session_factory()
        try:
            # Для демонстрации используем первого пользователя (admin)
            # В реальном приложении нужно передавать текущего пользователя из MainWindow
            from models import User
            current_user = db.query(User).first()
            
            if not current_user:
                QMessageBox.warning(self, "Ошибка", "Пользователь не найден в БД.")
                return
                
            dialog = AddLocomotiveDialog(db, current_user, self)
            if dialog.exec() == QDialog.Accepted:
                # После успешного добавления обновляем таблицу
                self._load_data()
                QMessageBox.information(self, "Успех", "Локомотив успешно добавлен!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить локомотив: {e}")
        finally:
            db.close()
