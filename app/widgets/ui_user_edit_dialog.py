# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'user_edit_dialog.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QDialogButtonBox,
    QLabel, QLineEdit, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_userEdit_dialog(object):
    def setupUi(self, userEdit_dialog):
        if not userEdit_dialog.objectName():
            userEdit_dialog.setObjectName(u"userEdit_dialog")
        userEdit_dialog.resize(417, 382)
        self.verticalLayout = QVBoxLayout(userEdit_dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.firstName_label = QLabel(userEdit_dialog)
        self.firstName_label.setObjectName(u"firstName_label")

        self.verticalLayout.addWidget(self.firstName_label)

        self.firstName_lineEdit = QLineEdit(userEdit_dialog)
        self.firstName_lineEdit.setObjectName(u"firstName_lineEdit")

        self.verticalLayout.addWidget(self.firstName_lineEdit)

        self.lastName_label = QLabel(userEdit_dialog)
        self.lastName_label.setObjectName(u"lastName_label")

        self.verticalLayout.addWidget(self.lastName_label)

        self.lastName_lineEdit = QLineEdit(userEdit_dialog)
        self.lastName_lineEdit.setObjectName(u"lastName_lineEdit")
        self.lastName_lineEdit.setEchoMode(QLineEdit.EchoMode.Normal)

        self.verticalLayout.addWidget(self.lastName_lineEdit)

        self.login_label = QLabel(userEdit_dialog)
        self.login_label.setObjectName(u"login_label")

        self.verticalLayout.addWidget(self.login_label)

        self.login_lineEdit = QLineEdit(userEdit_dialog)
        self.login_lineEdit.setObjectName(u"login_lineEdit")

        self.verticalLayout.addWidget(self.login_lineEdit)

        self.newPass_label = QLabel(userEdit_dialog)
        self.newPass_label.setObjectName(u"newPass_label")

        self.verticalLayout.addWidget(self.newPass_label)

        self.newPass_lineEdit = QLineEdit(userEdit_dialog)
        self.newPass_lineEdit.setObjectName(u"newPass_lineEdit")
        self.newPass_lineEdit.setEchoMode(QLineEdit.EchoMode.Password)

        self.verticalLayout.addWidget(self.newPass_lineEdit)

        self.newPassConfirm_label = QLabel(userEdit_dialog)
        self.newPassConfirm_label.setObjectName(u"newPassConfirm_label")

        self.verticalLayout.addWidget(self.newPassConfirm_label)

        self.newPassConfirm_lineEdit = QLineEdit(userEdit_dialog)
        self.newPassConfirm_lineEdit.setObjectName(u"newPassConfirm_lineEdit")
        self.newPassConfirm_lineEdit.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.newPassConfirm_lineEdit.setEchoMode(QLineEdit.EchoMode.Password)

        self.verticalLayout.addWidget(self.newPassConfirm_lineEdit)

        self.isAdmin_checkBox = QCheckBox(userEdit_dialog)
        self.isAdmin_checkBox.setObjectName(u"isAdmin_checkBox")

        self.verticalLayout.addWidget(self.isAdmin_checkBox)

        self.disabled_checkBox = QCheckBox(userEdit_dialog)
        self.disabled_checkBox.setObjectName(u"disabled_checkBox")

        self.verticalLayout.addWidget(self.disabled_checkBox)

        self.buttonBox = QDialogButtonBox(userEdit_dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(userEdit_dialog)

        QMetaObject.connectSlotsByName(userEdit_dialog)
    # setupUi

    def retranslateUi(self, userEdit_dialog):
        userEdit_dialog.setWindowTitle(QCoreApplication.translate("userEdit_dialog", u"Form", None))
        self.firstName_label.setText(QCoreApplication.translate("userEdit_dialog", u"\u0418\u043c\u044f", None))
        self.lastName_label.setText(QCoreApplication.translate("userEdit_dialog", u"\u0424\u0430\u043c\u0438\u043b\u0438\u044f", None))
        self.login_label.setText(QCoreApplication.translate("userEdit_dialog", u"\u041b\u043e\u0433\u0438\u043d", None))
        self.newPass_label.setText(QCoreApplication.translate("userEdit_dialog", u"\u041d\u043e\u0432\u044b\u0439 \u043f\u0430\u0440\u043e\u043b\u044c", None))
        self.newPassConfirm_label.setText(QCoreApplication.translate("userEdit_dialog", u"\u041f\u043e\u0434\u0442\u0432\u0435\u0440\u0434\u0438\u0442\u0435 \u043f\u0430\u0440\u043e\u043b\u044c", None))
        self.isAdmin_checkBox.setText(QCoreApplication.translate("userEdit_dialog", u"\u0410\u0434\u043c\u0438\u043d\u0438\u0441\u0442\u0440\u0430\u0442\u043e\u0440", None))
        self.disabled_checkBox.setText(QCoreApplication.translate("userEdit_dialog", u"\u041e\u0442\u043a\u043b\u044e\u0447\u0435\u043d", None))
    # retranslateUi

