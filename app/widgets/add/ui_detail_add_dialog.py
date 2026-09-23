# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'detail_add_dialog.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialogButtonBox, QLabel,
    QLineEdit, QSizePolicy, QVBoxLayout, QWidget)

class Ui_addDetail_dialog(object):
    def setupUi(self, addDetail_dialog):
        if not addDetail_dialog.objectName():
            addDetail_dialog.setObjectName(u"addDetail_dialog")
        addDetail_dialog.resize(384, 260)
        self.verticalLayout = QVBoxLayout(addDetail_dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.detailCode_label = QLabel(addDetail_dialog)
        self.detailCode_label.setObjectName(u"detailCode_label")

        self.verticalLayout.addWidget(self.detailCode_label)

        self.detailCode_lineEdit = QLineEdit(addDetail_dialog)
        self.detailCode_lineEdit.setObjectName(u"detailCode_lineEdit")

        self.verticalLayout.addWidget(self.detailCode_lineEdit)

        self.detailManufacturer_label = QLabel(addDetail_dialog)
        self.detailManufacturer_label.setObjectName(u"detailManufacturer_label")

        self.verticalLayout.addWidget(self.detailManufacturer_label)

        self.detailManufacturer_lineEdit = QLineEdit(addDetail_dialog)
        self.detailManufacturer_lineEdit.setObjectName(u"detailManufacturer_lineEdit")

        self.verticalLayout.addWidget(self.detailManufacturer_lineEdit)

        self.detailName_label = QLabel(addDetail_dialog)
        self.detailName_label.setObjectName(u"detailName_label")

        self.verticalLayout.addWidget(self.detailName_label)

        self.detailCode_lineEdit_2 = QLineEdit(addDetail_dialog)
        self.detailCode_lineEdit_2.setObjectName(u"detailCode_lineEdit_2")

        self.verticalLayout.addWidget(self.detailCode_lineEdit_2)

        self.detailCount_label = QLabel(addDetail_dialog)
        self.detailCount_label.setObjectName(u"detailCount_label")

        self.verticalLayout.addWidget(self.detailCount_label)

        self.detailCount_lineEdit = QLineEdit(addDetail_dialog)
        self.detailCount_lineEdit.setObjectName(u"detailCount_lineEdit")
        self.detailCount_lineEdit.setMaxLength(2)

        self.verticalLayout.addWidget(self.detailCount_lineEdit)

        self.buttonBox = QDialogButtonBox(addDetail_dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(addDetail_dialog)

        QMetaObject.connectSlotsByName(addDetail_dialog)
    # setupUi

    def retranslateUi(self, addDetail_dialog):
        addDetail_dialog.setWindowTitle(QCoreApplication.translate("addDetail_dialog", u"Form", None))
        self.detailCode_label.setText(QCoreApplication.translate("addDetail_dialog", u"\u0410\u0440\u0442\u0438\u043a\u0443\u043b", None))
        self.detailManufacturer_label.setText(QCoreApplication.translate("addDetail_dialog", u"\u041f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044c", None))
        self.detailName_label.setText(QCoreApplication.translate("addDetail_dialog", u"\u041d\u0430\u0438\u043c\u0435\u043d\u043e\u0432\u0430\u043d\u0438\u0435", None))
        self.detailCount_label.setText(QCoreApplication.translate("addDetail_dialog", u"\u041a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e", None))
    # retranslateUi

