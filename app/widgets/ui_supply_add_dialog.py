# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'supply_add_dialog.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialogButtonBox, QHBoxLayout,
    QHeaderView, QLabel, QPushButton, QSizePolicy,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

class Ui_addSupply_dialog(object):
    def setupUi(self, addSupply_dialog):
        if not addSupply_dialog.objectName():
            addSupply_dialog.setObjectName(u"addSupply_dialog")
        addSupply_dialog.resize(400, 276)
        self.verticalLayout = QVBoxLayout(addSupply_dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.detailsTable_label = QLabel(addSupply_dialog)
        self.detailsTable_label.setObjectName(u"detailsTable_label")

        self.verticalLayout.addWidget(self.detailsTable_label)

        self.detailsTable_tableWidget = QTableWidget(addSupply_dialog)
        self.detailsTable_tableWidget.setObjectName(u"detailsTable_tableWidget")

        self.verticalLayout.addWidget(self.detailsTable_tableWidget)

        self.detailsManageButtons_hLayout = QHBoxLayout()
        self.detailsManageButtons_hLayout.setObjectName(u"detailsManageButtons_hLayout")
        self.detailAdd_pushButton = QPushButton(addSupply_dialog)
        self.detailAdd_pushButton.setObjectName(u"detailAdd_pushButton")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.detailAdd_pushButton.sizePolicy().hasHeightForWidth())
        self.detailAdd_pushButton.setSizePolicy(sizePolicy)

        self.detailsManageButtons_hLayout.addWidget(self.detailAdd_pushButton)

        self.detailRemove_pushButton = QPushButton(addSupply_dialog)
        self.detailRemove_pushButton.setObjectName(u"detailRemove_pushButton")
        sizePolicy.setHeightForWidth(self.detailRemove_pushButton.sizePolicy().hasHeightForWidth())
        self.detailRemove_pushButton.setSizePolicy(sizePolicy)

        self.detailsManageButtons_hLayout.addWidget(self.detailRemove_pushButton)


        self.verticalLayout.addLayout(self.detailsManageButtons_hLayout)

        self.addSupply_buttonBox = QDialogButtonBox(addSupply_dialog)
        self.addSupply_buttonBox.setObjectName(u"addSupply_buttonBox")
        self.addSupply_buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout.addWidget(self.addSupply_buttonBox)


        self.retranslateUi(addSupply_dialog)

        QMetaObject.connectSlotsByName(addSupply_dialog)
    # setupUi

    def retranslateUi(self, addSupply_dialog):
        addSupply_dialog.setWindowTitle(QCoreApplication.translate("addSupply_dialog", u"Form", None))
        self.detailsTable_label.setText(QCoreApplication.translate("addSupply_dialog", u"\u0414\u0435\u0442\u0430\u043b\u0438", None))
        self.detailAdd_pushButton.setText(QCoreApplication.translate("addSupply_dialog", u"+", None))
        self.detailRemove_pushButton.setText(QCoreApplication.translate("addSupply_dialog", u"-", None))
    # retranslateUi

