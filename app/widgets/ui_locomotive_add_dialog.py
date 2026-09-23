# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'locomotive_add_dialog.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QComboBox, QDialogButtonBox,
    QHBoxLayout, QLabel, QLineEdit, QSizePolicy,
    QSpinBox, QTextEdit, QToolButton, QVBoxLayout,
    QWidget)

class Ui_addLocomotive_dialog(object):
    def setupUi(self, addLocomotive_dialog):
        if not addLocomotive_dialog.objectName():
            addLocomotive_dialog.setObjectName(u"addLocomotive_dialog")
        addLocomotive_dialog.resize(422, 413)
        self.verticalLayout = QVBoxLayout(addLocomotive_dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.comment_label = QLabel(addLocomotive_dialog)
        self.comment_label.setObjectName(u"comment_label")

        self.verticalLayout.addWidget(self.comment_label)

        self.comment_textEdit = QTextEdit(addLocomotive_dialog)
        self.comment_textEdit.setObjectName(u"comment_textEdit")

        self.verticalLayout.addWidget(self.comment_textEdit)

        self.number_label = QLabel(addLocomotive_dialog)
        self.number_label.setObjectName(u"number_label")

        self.verticalLayout.addWidget(self.number_label)

        self.number_lineEdit = QLineEdit(addLocomotive_dialog)
        self.number_lineEdit.setObjectName(u"number_lineEdit")

        self.verticalLayout.addWidget(self.number_lineEdit)

        self.locomotiveModel_label = QLabel(addLocomotive_dialog)
        self.locomotiveModel_label.setObjectName(u"locomotiveModel_label")

        self.verticalLayout.addWidget(self.locomotiveModel_label)

        self.locomotiveModel_hLayout = QHBoxLayout()
        self.locomotiveModel_hLayout.setSpacing(0)
        self.locomotiveModel_hLayout.setObjectName(u"locomotiveModel_hLayout")
        self.locomotiveModel_comboBox = QComboBox(addLocomotive_dialog)
        self.locomotiveModel_comboBox.setObjectName(u"locomotiveModel_comboBox")

        self.locomotiveModel_hLayout.addWidget(self.locomotiveModel_comboBox)

        self.locomotiveModel_toolButton = QToolButton(addLocomotive_dialog)
        self.locomotiveModel_toolButton.setObjectName(u"locomotiveModel_toolButton")

        self.locomotiveModel_hLayout.addWidget(self.locomotiveModel_toolButton)


        self.verticalLayout.addLayout(self.locomotiveModel_hLayout)

        self.system_label = QLabel(addLocomotive_dialog)
        self.system_label.setObjectName(u"system_label")

        self.verticalLayout.addWidget(self.system_label)

        self.system_spinBox = QSpinBox(addLocomotive_dialog)
        self.system_spinBox.setObjectName(u"system_spinBox")

        self.verticalLayout.addWidget(self.system_spinBox)

        self.typt_label = QLabel(addLocomotive_dialog)
        self.typt_label.setObjectName(u"typt_label")

        self.verticalLayout.addWidget(self.typt_label)

        self.type_lineEdit = QLineEdit(addLocomotive_dialog)
        self.type_lineEdit.setObjectName(u"type_lineEdit")

        self.verticalLayout.addWidget(self.type_lineEdit)

        self.addLocomotive_buttonBox = QDialogButtonBox(addLocomotive_dialog)
        self.addLocomotive_buttonBox.setObjectName(u"addLocomotive_buttonBox")
        self.addLocomotive_buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout.addWidget(self.addLocomotive_buttonBox)


        self.retranslateUi(addLocomotive_dialog)

        QMetaObject.connectSlotsByName(addLocomotive_dialog)
    # setupUi

    def retranslateUi(self, addLocomotive_dialog):
        addLocomotive_dialog.setWindowTitle(QCoreApplication.translate("addLocomotive_dialog", u"Form", None))
        self.comment_label.setText(QCoreApplication.translate("addLocomotive_dialog", u"\u041a\u043e\u043c\u043c\u0435\u043d\u0442\u0430\u0440\u0438\u0439", None))
        self.number_label.setText(QCoreApplication.translate("addLocomotive_dialog", u"\u041d\u043e\u043c\u0435\u0440", None))
        self.locomotiveModel_label.setText(QCoreApplication.translate("addLocomotive_dialog", u"\u041c\u043e\u0434\u0435\u043b\u044c \u043b\u043e\u043a\u043e\u043c\u043e\u0442\u0438\u0432\u0430", None))
        self.locomotiveModel_toolButton.setText(QCoreApplication.translate("addLocomotive_dialog", u"...", None))
        self.system_label.setText(QCoreApplication.translate("addLocomotive_dialog", u"\u0421\u0438\u0441\u0442\u0435\u043c\u0430", None))
        self.typt_label.setText(QCoreApplication.translate("addLocomotive_dialog", u"\u0422\u0438\u043f", None))
    # retranslateUi

