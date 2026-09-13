# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'auth.ui'
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

class Ui_Form_Auth(object):
    def setupUi(self, Form_Auth):
        if not Form_Auth.objectName():
            Form_Auth.setObjectName(u"Form_Auth")
        Form_Auth.resize(678, 577)
        self.verticalLayout_2 = QVBoxLayout(Form_Auth)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_Main = QVBoxLayout()
        self.verticalLayout_Main.setObjectName(u"verticalLayout_Main")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_Main.addItem(self.verticalSpacer)

        self.horizontalLayout_4_Auth = QHBoxLayout()
        self.horizontalLayout_4_Auth.setObjectName(u"horizontalLayout_4_Auth")
        self.horizontalSpacer_7 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4_Auth.addItem(self.horizontalSpacer_7)

        self.label_Auth = QLabel(Form_Auth)
        self.label_Auth.setObjectName(u"label_Auth")

        self.horizontalLayout_4_Auth.addWidget(self.label_Auth)

        self.horizontalSpacer_8 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4_Auth.addItem(self.horizontalSpacer_8)


        self.verticalLayout_Main.addLayout(self.horizontalLayout_4_Auth)

        self.horizontalLayout_2_Login = QHBoxLayout()
        self.horizontalLayout_2_Login.setObjectName(u"horizontalLayout_2_Login")
        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2_Login.addItem(self.horizontalSpacer_3)

        self.label_3_Login = QLabel(Form_Auth)
        self.label_3_Login.setObjectName(u"label_3_Login")

        self.horizontalLayout_2_Login.addWidget(self.label_3_Login)

        self.lineEdit_2_Login = QLineEdit(Form_Auth)
        self.lineEdit_2_Login.setObjectName(u"lineEdit_2_Login")
        self.lineEdit_2_Login.setMaxLength(255)

        self.horizontalLayout_2_Login.addWidget(self.lineEdit_2_Login)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2_Login.addItem(self.horizontalSpacer_4)


        self.verticalLayout_Main.addLayout(self.horizontalLayout_2_Login)

        self.horizontalLayout_3_Password = QHBoxLayout()
        self.horizontalLayout_3_Password.setObjectName(u"horizontalLayout_3_Password")
        self.horizontalSpacer_5 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3_Password.addItem(self.horizontalSpacer_5)

        self.label_4_Password = QLabel(Form_Auth)
        self.label_4_Password.setObjectName(u"label_4_Password")

        self.horizontalLayout_3_Password.addWidget(self.label_4_Password)

        self.lineEdit_3_Password = QLineEdit(Form_Auth)
        self.lineEdit_3_Password.setObjectName(u"lineEdit_3_Password")
        self.lineEdit_3_Password.setMaxLength(32)
        self.lineEdit_3_Password.setEchoMode(QLineEdit.EchoMode.Password)

        self.horizontalLayout_3_Password.addWidget(self.lineEdit_3_Password)

        self.horizontalSpacer_6 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3_Password.addItem(self.horizontalSpacer_6)


        self.verticalLayout_Main.addLayout(self.horizontalLayout_3_Password)

        self.horizontalLayout_Enter = QHBoxLayout()
        self.horizontalLayout_Enter.setObjectName(u"horizontalLayout_Enter")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_Enter.addItem(self.horizontalSpacer)

        self.pushButton_Enter = QPushButton(Form_Auth)
        self.pushButton_Enter.setObjectName(u"pushButton_Enter")

        self.horizontalLayout_Enter.addWidget(self.pushButton_Enter)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_Enter.addItem(self.horizontalSpacer_2)


        self.verticalLayout_Main.addLayout(self.horizontalLayout_Enter)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_Main.addItem(self.verticalSpacer_2)


        self.verticalLayout_2.addLayout(self.verticalLayout_Main)


        self.retranslateUi(Form_Auth)

        QMetaObject.connectSlotsByName(Form_Auth)
    # setupUi

    def retranslateUi(self, Form_Auth):
        Form_Auth.setWindowTitle(QCoreApplication.translate("Form_Auth", u"Form", None))
        self.label_Auth.setText(QCoreApplication.translate("Form_Auth", u"\u0410\u0432\u0442\u043e\u0440\u0438\u0437\u0430\u0446\u0438\u044f", None))
        self.label_3_Login.setText(QCoreApplication.translate("Form_Auth", u"\u041b\u043e\u0433\u0438\u043d", None))
        self.label_4_Password.setText(QCoreApplication.translate("Form_Auth", u"\u041f\u0430\u0440\u043e\u043b\u044c", None))
        self.pushButton_Enter.setText(QCoreApplication.translate("Form_Auth", u"\u0412\u043e\u0439\u0442\u0438", None))
    # retranslateUi
