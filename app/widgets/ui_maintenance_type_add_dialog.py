# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'maintenance_type_add_dialog.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialogButtonBox, QLineEdit,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_addMaintenanceType_dialog(object):
    def setupUi(self, addMaintenanceType_dialog):
        if not addMaintenanceType_dialog.objectName():
            addMaintenanceType_dialog.setObjectName(u"addMaintenanceType_dialog")
        addMaintenanceType_dialog.resize(244, 76)
        self.verticalLayout = QVBoxLayout(addMaintenanceType_dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.maintenanceType_lineEdit = QLineEdit(addMaintenanceType_dialog)
        self.maintenanceType_lineEdit.setObjectName(u"maintenanceType_lineEdit")

        self.verticalLayout.addWidget(self.maintenanceType_lineEdit)

        self.buttonBox = QDialogButtonBox(addMaintenanceType_dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(addMaintenanceType_dialog)

        QMetaObject.connectSlotsByName(addMaintenanceType_dialog)
    # setupUi

    def retranslateUi(self, addMaintenanceType_dialog):
        addMaintenanceType_dialog.setWindowTitle(QCoreApplication.translate("addMaintenanceType_dialog", u"Form", None))
    # retranslateUi

