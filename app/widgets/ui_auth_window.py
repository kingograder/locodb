# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'auth_window.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

class Ui_auth_window(object):
    def setupUi(self, auth_window):
        if not auth_window.objectName():
            auth_window.setObjectName(u"auth_window")
        auth_window.resize(678, 577)
        self.verticalLayout = QVBoxLayout(auth_window)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.auth_topSpacer = QSpacerItem(20, 209, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.auth_topSpacer)

        self.title_hLayout = QHBoxLayout()
        self.title_hLayout.setObjectName(u"title_hLayout")
        self.title_leftSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.title_hLayout.addItem(self.title_leftSpacer)

        self.title_label = QLabel(auth_window)
        self.title_label.setObjectName(u"title_label")

        self.title_hLayout.addWidget(self.title_label)

        self.title_rightSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.title_hLayout.addItem(self.title_rightSpacer)


        self.verticalLayout.addLayout(self.title_hLayout)

        self.login_hLayout = QHBoxLayout()
        self.login_hLayout.setObjectName(u"login_hLayout")
        self.login_leftSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.login_hLayout.addItem(self.login_leftSpacer)

        self.login_label = QLabel(auth_window)
        self.login_label.setObjectName(u"login_label")

        self.login_hLayout.addWidget(self.login_label)

        self.login_lineEdit = QLineEdit(auth_window)
        self.login_lineEdit.setObjectName(u"login_lineEdit")
        self.login_lineEdit.setMaxLength(255)

        self.login_hLayout.addWidget(self.login_lineEdit)

        self.login_rightSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.login_hLayout.addItem(self.login_rightSpacer)


        self.verticalLayout.addLayout(self.login_hLayout)

        self.pass_hLayout = QHBoxLayout()
        self.pass_hLayout.setObjectName(u"pass_hLayout")
        self.pass_leftSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.pass_hLayout.addItem(self.pass_leftSpacer)

        self.pass_lable = QLabel(auth_window)
        self.pass_lable.setObjectName(u"pass_lable")

        self.pass_hLayout.addWidget(self.pass_lable)

        self.pass_lineEdit = QLineEdit(auth_window)
        self.pass_lineEdit.setObjectName(u"pass_lineEdit")
        self.pass_lineEdit.setMaxLength(32)
        self.pass_lineEdit.setEchoMode(QLineEdit.EchoMode.Password)

        self.pass_hLayout.addWidget(self.pass_lineEdit)

        self.pass_rightSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.pass_hLayout.addItem(self.pass_rightSpacer)


        self.verticalLayout.addLayout(self.pass_hLayout)

        self.enter_hLayout = QHBoxLayout()
        self.enter_hLayout.setObjectName(u"enter_hLayout")
        self.enter_leftSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.enter_hLayout.addItem(self.enter_leftSpacer)

        self.enter_button = QPushButton(auth_window)
        self.enter_button.setObjectName(u"enter_button")

        self.enter_hLayout.addWidget(self.enter_button)

        self.enter_rightSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.enter_hLayout.addItem(self.enter_rightSpacer)


        self.verticalLayout.addLayout(self.enter_hLayout)

        self.auth_bottomSpacer = QSpacerItem(20, 208, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.auth_bottomSpacer)


        self.retranslateUi(auth_window)

        QMetaObject.connectSlotsByName(auth_window)
    # setupUi

    def retranslateUi(self, auth_window):
        auth_window.setWindowTitle(QCoreApplication.translate("auth_window", u"Form", None))
        self.title_label.setText(QCoreApplication.translate("auth_window", u"\u0410\u0432\u0442\u043e\u0440\u0438\u0437\u0430\u0446\u0438\u044f", None))
        self.login_label.setText(QCoreApplication.translate("auth_window", u"\u041b\u043e\u0433\u0438\u043d", None))
        self.pass_lable.setText(QCoreApplication.translate("auth_window", u"\u041f\u0430\u0440\u043e\u043b\u044c", None))
        self.enter_button.setText(QCoreApplication.translate("auth_window", u"\u0412\u043e\u0439\u0442\u0438", None))
    # retranslateUi

