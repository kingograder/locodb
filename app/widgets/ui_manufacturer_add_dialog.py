# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'manufacturer_add_dialog.ui'
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

class Ui_addManufacturer_dialog(object):
    def setupUi(self, addManufacturer_dialog):
        if not addManufacturer_dialog.objectName():
            addManufacturer_dialog.setObjectName(u"addManufacturer_dialog")
        addManufacturer_dialog.resize(244, 76)
        self.verticalLayout = QVBoxLayout(addManufacturer_dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.manufacturerName_lineEdit = QLineEdit(addManufacturer_dialog)
        self.manufacturerName_lineEdit.setObjectName(u"manufacturerName_lineEdit")

        self.verticalLayout.addWidget(self.manufacturerName_lineEdit)

        self.buttonBox = QDialogButtonBox(addManufacturer_dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(addManufacturer_dialog)

        QMetaObject.connectSlotsByName(addManufacturer_dialog)
    # setupUi

    def retranslateUi(self, addManufacturer_dialog):
        addManufacturer_dialog.setWindowTitle(QCoreApplication.translate("addManufacturer_dialog", u"Form", None))
    # retranslateUi

