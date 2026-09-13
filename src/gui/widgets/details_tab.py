"""
Виджет таблицы деталей.
Отображает данные о деталях с возможностью добавления новых записей.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableView, QPushButton, QHBoxLayout,
    QAbstractItemView, QMessageBox
)
from PySide6.QtCore import QAbstractTableModel, Qt

from src.services.detail_service import DetailService


class DetailTableModel(QAbstractTableModel):
    """Модель данных для таблицы деталей."""

    def __init__(self, data: list[dict]):
        super().__init__()
        self._data = data
        self._headers = [
            "Код",
            "Название",
            "Производитель",
            "Количество на складе"
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
                return item["code"]
            elif col == 1:
                return item["name"]
            elif col == 2:
                return item["manufacturer"]
            elif col == 3:
                return str(item["quantity_in_stock"])

        if role == Qt.TextAlignmentRole:
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


class DetailsTab(QWidget):
    """Виджет вкладки с таблицей деталей."""

    def __init__(self, session_factory):
        super().__init__()
        self.session_factory = session_factory
        self.service = DetailService(session_factory)
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Панель с кнопками
        button_layout = QHBoxLayout()
        
        self.add_button = QPushButton("Добавить деталь")
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
            data = self.service.get_all_details()
            
            if not hasattr(self, 'table_model'):
                self.table_model = DetailTableModel(data)
                self.table_view.setModel(self.table_model)
                
                # Настройка ширины колонок
                header = self.table_view.horizontalHeader()
                header.setSectionResizeMode(0, header.ResizeToContents)  # Код
                header.setSectionResizeMode(1, header.Stretch)  # Название
                header.setSectionResizeMode(2, header.Stretch)  # Производитель
                header.setSectionResizeMode(3, header.ResizeToContents)  # Количество
            else:
                self.table_model.update_data(data)
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить данные: {e}")

    def _on_add_clicked(self):
        """Обработчик нажатия кнопки добавления."""
        QMessageBox.information(self, "Информация", "Диалог добавления детали будет реализован в следующем шаге.")
