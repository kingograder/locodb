from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QComboBox, QPushButton, QMessageBox, QFormLayout)
from PySide6.QtCore import Qt
from sqlalchemy.orm import Session
from models import Locomotive, LocomotiveModel, User


class AddLocomotiveDialog(QDialog):
    """Диалог добавления нового локомотива."""
    
    def __init__(self, db_session: Session, current_user: User, parent=None):
        super().__init__(parent)
        self.db = db_session
        self.current_user = current_user
        self.setWindowTitle("Добавить локомотив")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        self._init_ui()
        self._load_models()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Форма
        form_layout = QFormLayout()
        
        # Выбор модели
        self.model_combo = QComboBox()
        self.model_combo.setEditable(False)
        self.model_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        
        btn_add_model = QPushButton("+")
        btn_add_model.setFixedWidth(30)
        btn_add_model.setToolTip("Добавить новую модель")
        btn_add_model.clicked.connect(self._add_new_model)
        
        model_layout = QHBoxLayout()
        model_layout.addWidget(self.model_combo)
        model_layout.addWidget(btn_add_model)
        
        form_layout.addRow("Модель", model_layout)
        
        # Инвентарный номер
        self.number_input = QLineEdit()
        self.number_input.setPlaceholderText("Например: ТЭМ2-123")
        form_layout.addRow("Инв. номер *", self.number_input)
        
        # Система
        self.system_input = QLineEdit()
        self.system_input.setPlaceholderText("Например: Север, Юг")
        form_layout.addRow("Система *", self.system_input)
        
        # Тип локомотива (можно выбрать вручную, если отличается от модели или для уточнения)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Тепловоз", "Электровоз", "Маневровый"])
        form_layout.addRow("Тип", self.type_combo)
        
        layout.addLayout(form_layout)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("Сохранить")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._save_locomotive)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)
        
    def _load_models(self):
        """Загрузка списка моделей из БД."""
        models = self.db.query(LocomotiveModel).filter_by(is_deleted=False).all()
        self.model_combo.clear()
        self.model_combo.addItem("-- Выберите модель --", None)
        for m in models:
            display_text = f"{m.model_name} ({m.manufacturer})"
            self.model_combo.addItem(display_text, m.id)
            
    def _add_new_model(self):
        """Открытие диалога добавления модели."""
        dialog = AddModelDialog(self.db, self)
        if dialog.exec() == QDialog.Accepted:
            # Обновляем список моделей после добавления
            self._load_models()
            # Выбираем только что добавленную модель
            new_model_id = dialog.new_model_id
            for i in range(self.model_combo.count()):
                if self.model_combo.itemData(i) == new_model_id:
                    self.model_combo.setCurrentIndex(i)
                    break
                    
    def _save_locomotive(self):
        """Сохранение локомотива в БД."""
        model_id = self.model_combo.currentData()
        number = self.number_input.text().strip()
        system = self.system_input.text().strip()
        loco_type = self.type_combo.currentText()
        
        if not model_id:
            QMessageBox.warning(self, "Ошибка", "Выберите модель локомотива.")
            return
        if not number:
            QMessageBox.warning(self, "Ошибка", "Введите инвентарный номер.")
            return
        if not system:
            QMessageBox.warning(self, "Ошибка", "Введите систему.")
            return
            
        try:
            new_loco = Locomotive(
                model_id=model_id,
                number=number,
                system=system,
                model_type=loco_type
            )
            self.db.add(new_loco)
            self.db.commit()
            self.accept()
        except Exception as e:
            self.db.rollback()
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить локомотив: {e}")


class AddModelDialog(QDialog):
    """Диалог добавления новой модели локомотива."""
    
    def __init__(self, db_session: Session, parent=None):
        super().__init__(parent)
        self.db = db_session
        self.new_model_id = None
        self.setWindowTitle("Добавить модель локомотива")
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Например: ТЭМ2")
        form_layout.addRow("Название модели *", self.name_input)
        
        self.manufacturer_input = QLineEdit()
        self.manufacturer_input.setPlaceholderText("Например: Брянский завод")
        form_layout.addRow("Производитель", self.manufacturer_input)
        
        layout.addLayout(form_layout)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("Сохранить")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._save_model)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)
        
    def _save_model(self):
        name = self.name_input.text().strip()
        manufacturer = self.manufacturer_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название модели.")
            return
            
        try:
            new_model = LocomotiveModel(
                model_name=name,
                manufacturer=manufacturer
            )
            self.db.add(new_model)
            self.db.commit()
            self.new_model_id = new_model.id
            self.accept()
        except Exception as e:
            self.db.rollback()
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить модель: {e}")
