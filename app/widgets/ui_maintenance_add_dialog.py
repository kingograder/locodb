# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'maintenance_add_dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.11.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QComboBox, QDateEdit,
    QDialogButtonBox, QGridLayout, QLabel, QSizePolicy,
    QTextEdit, QVBoxLayout, QWidget)

class Ui_addMaintenance_dialog(object):
    def setupUi(self, addMaintenance_dialog):
        if not addMaintenance_dialog.objectName():
            addMaintenance_dialog.setObjectName(u"addMaintenance_dialog")
        addMaintenance_dialog.resize(608, 232)
        self.verticalLayout_2 = QVBoxLayout(addMaintenance_dialog)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.addMaintenanceComment_label = QLabel(addMaintenance_dialog)
        self.addMaintenanceComment_label.setObjectName(u"addMaintenanceComment_label")

        self.verticalLayout_2.addWidget(self.addMaintenanceComment_label)

        self.addMaintenanceComment_textEdit = QTextEdit(addMaintenance_dialog)
        self.addMaintenanceComment_textEdit.setObjectName(u"addMaintenanceComment_textEdit")

        self.verticalLayout_2.addWidget(self.addMaintenanceComment_textEdit)

        self.addMaintenanceMeta_gLayout = QGridLayout()
        self.addMaintenanceMeta_gLayout.setObjectName(u"addMaintenanceMeta_gLayout")
        self.addMaintenanceLoco_label = QLabel(addMaintenance_dialog)
        self.addMaintenanceLoco_label.setObjectName(u"addMaintenanceLoco_label")

        self.addMaintenanceMeta_gLayout.addWidget(self.addMaintenanceLoco_label, 0, 0, 1, 1)

        self.addMaintenanceType_lable = QLabel(addMaintenance_dialog)
        self.addMaintenanceType_lable.setObjectName(u"addMaintenanceType_lable")

        self.addMaintenanceMeta_gLayout.addWidget(self.addMaintenanceType_lable, 0, 1, 1, 1)

        self.addMaintenanceDate_lable = QLabel(addMaintenance_dialog)
        self.addMaintenanceDate_lable.setObjectName(u"addMaintenanceDate_lable")

        self.addMaintenanceMeta_gLayout.addWidget(self.addMaintenanceDate_lable, 0, 2, 1, 1)

        self.addMaintenanceLoco_comboBox = QComboBox(addMaintenance_dialog)
        self.addMaintenanceLoco_comboBox.setObjectName(u"addMaintenanceLoco_comboBox")

        self.addMaintenanceMeta_gLayout.addWidget(self.addMaintenanceLoco_comboBox, 1, 0, 1, 1)

        self.addMaintenanceType_comboBox = QComboBox(addMaintenance_dialog)
        self.addMaintenanceType_comboBox.setObjectName(u"addMaintenanceType_comboBox")

        self.addMaintenanceMeta_gLayout.addWidget(self.addMaintenanceType_comboBox, 1, 1, 1, 1)

        self.addMaintenanceDate_dateEdit = QDateEdit(addMaintenance_dialog)
        self.addMaintenanceDate_dateEdit.setObjectName(u"addMaintenanceDate_dateEdit")
        self.addMaintenanceDate_dateEdit.setMinimumDateTime(QDateTime(QDate(2024, 1, 1), QTime(15, 40, 1)))
        self.addMaintenanceDate_dateEdit.setMinimumDate(QDate(2024, 1, 1))
        self.addMaintenanceDate_dateEdit.setCalendarPopup(True)

        self.addMaintenanceMeta_gLayout.addWidget(self.addMaintenanceDate_dateEdit, 1, 2, 1, 1)


        self.verticalLayout_2.addLayout(self.addMaintenanceMeta_gLayout)

        self.addMaintenance_buttonBox = QDialogButtonBox(addMaintenance_dialog)
        self.addMaintenance_buttonBox.setObjectName(u"addMaintenance_buttonBox")
        self.addMaintenance_buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout_2.addWidget(self.addMaintenance_buttonBox)


        self.retranslateUi(addMaintenance_dialog)

        QMetaObject.connectSlotsByName(addMaintenance_dialog)
    # setupUi

    def retranslateUi(self, addMaintenance_dialog):
        addMaintenance_dialog.setWindowTitle(QCoreApplication.translate("addMaintenance_dialog", u"Form", None))
        self.addMaintenanceComment_label.setText(QCoreApplication.translate("addMaintenance_dialog", u"\u041a\u043e\u043c\u043c\u0435\u043d\u0442\u0430\u0440\u0438\u0439", None))
        self.addMaintenanceLoco_label.setText(QCoreApplication.translate("addMaintenance_dialog", u"\u041b\u043e\u043a\u043e\u043c\u043e\u0442\u0438\u0432", None))
        self.addMaintenanceType_lable.setText(QCoreApplication.translate("addMaintenance_dialog", u"\u0422\u0438\u043f \u043e\u0431\u0441\u043b\u0443\u0436\u0438\u0432\u0430\u043d\u0438\u044f", None))
        self.addMaintenanceDate_lable.setText(QCoreApplication.translate("addMaintenance_dialog", u"\u0414\u0430\u0442\u0430 \u043e\u0431\u0441\u043b\u0443\u0436\u0438\u0432\u0430\u043d\u0438\u044f", None))
    # retranslateUi

