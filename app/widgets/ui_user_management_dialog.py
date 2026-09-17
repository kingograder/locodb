# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'user_management_dialog.ui'
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
    QSizePolicy, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget)

class Ui_usersManagement_dialog(object):
    def setupUi(self, usersManagement_dialog):
        if not usersManagement_dialog.objectName():
            usersManagement_dialog.setObjectName(u"usersManagement_dialog")
        usersManagement_dialog.resize(652, 570)
        self.verticalLayout = QVBoxLayout(usersManagement_dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.users_tableWidget = QTableWidget(usersManagement_dialog)
        self.users_tableWidget.setObjectName(u"users_tableWidget")

        self.verticalLayout.addWidget(self.users_tableWidget)

        self.bottomButtons_hLayout = QHBoxLayout()
        self.bottomButtons_hLayout.setObjectName(u"bottomButtons_hLayout")
        self.userAdd_button = QPushButton(usersManagement_dialog)
        self.userAdd_button.setObjectName(u"userAdd_button")

        self.bottomButtons_hLayout.addWidget(self.userAdd_button)

        self.userEdit_button = QPushButton(usersManagement_dialog)
        self.userEdit_button.setObjectName(u"userEdit_button")

        self.bottomButtons_hLayout.addWidget(self.userEdit_button)

        self.userDelete_button = QPushButton(usersManagement_dialog)
        self.userDelete_button.setObjectName(u"userDelete_button")

        self.bottomButtons_hLayout.addWidget(self.userDelete_button)


        self.verticalLayout.addLayout(self.bottomButtons_hLayout)


        self.retranslateUi(usersManagement_dialog)

        QMetaObject.connectSlotsByName(usersManagement_dialog)
    # setupUi

    def retranslateUi(self, usersManagement_dialog):
        usersManagement_dialog.setWindowTitle(QCoreApplication.translate("usersManagement_dialog", u"Form", None))
        self.userAdd_button.setText(QCoreApplication.translate("usersManagement_dialog", u"\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c", None))
        self.userEdit_button.setText(QCoreApplication.translate("usersManagement_dialog", u"\u0418\u0437\u043c\u0435\u043d\u0438\u0442\u044c", None))
        self.userDelete_button.setText(QCoreApplication.translate("usersManagement_dialog", u"\u0423\u0434\u0430\u043b\u0438\u0442\u044c", None))
    # retranslateUi

