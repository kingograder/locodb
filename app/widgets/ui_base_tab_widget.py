# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'base_tab_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QHeaderView, QPushButton,
    QSizePolicy, QSpacerItem, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget)

class Ui_baseTab_widget(object):
    def setupUi(self, baseTab_widget):
        if not baseTab_widget.objectName():
            baseTab_widget.setObjectName(u"baseTab_widget")
        baseTab_widget.resize(400, 300)
        self.verticalLayout = QVBoxLayout(baseTab_widget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.baseTopButtons_hLayout = QHBoxLayout()
        self.baseTopButtons_hLayout.setObjectName(u"baseTopButtons_hLayout")
        self.base_leftSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.baseTopButtons_hLayout.addItem(self.base_leftSpacer)

        self.addBase_button = QPushButton(baseTab_widget)
        self.addBase_button.setObjectName(u"addBase_button")

        self.baseTopButtons_hLayout.addWidget(self.addBase_button)

        self.editBase_button = QPushButton(baseTab_widget)
        self.editBase_button.setObjectName(u"editBase_button")

        self.baseTopButtons_hLayout.addWidget(self.editBase_button)

        self.deleteBase_button = QPushButton(baseTab_widget)
        self.deleteBase_button.setObjectName(u"deleteBase_button")

        self.baseTopButtons_hLayout.addWidget(self.deleteBase_button)


        self.verticalLayout.addLayout(self.baseTopButtons_hLayout)

        self.base_table = QTableWidget(baseTab_widget)
        self.base_table.setObjectName(u"base_table")

        self.verticalLayout.addWidget(self.base_table)


        self.retranslateUi(baseTab_widget)

        QMetaObject.connectSlotsByName(baseTab_widget)
    # setupUi

    def retranslateUi(self, baseTab_widget):
        baseTab_widget.setWindowTitle(QCoreApplication.translate("baseTab_widget", u"Form", None))
        self.addBase_button.setText(QCoreApplication.translate("baseTab_widget", u"\u041a\u043d\u043e\u043f\u043a\u0430 1", None))
        self.editBase_button.setText(QCoreApplication.translate("baseTab_widget", u"\u041a\u043d\u043e\u043f\u043a\u0430 1", None))
        self.deleteBase_button.setText(QCoreApplication.translate("baseTab_widget", u"\u041a\u043d\u043e\u043f\u043a\u0430 3", None))
    # retranslateUi

