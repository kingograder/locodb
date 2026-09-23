# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'locomotive_model_add_dialog.ui'
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
    QToolButton, QVBoxLayout, QWidget)

class Ui_addLocomotiveModel_dialog(object):
    def setupUi(self, addLocomotiveModel_dialog):
        if not addLocomotiveModel_dialog.objectName():
            addLocomotiveModel_dialog.setObjectName(u"addLocomotiveModel_dialog")
        addLocomotiveModel_dialog.resize(354, 264)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(addLocomotiveModel_dialog.sizePolicy().hasHeightForWidth())
        addLocomotiveModel_dialog.setSizePolicy(sizePolicy)
        self.verticalLayout = QVBoxLayout(addLocomotiveModel_dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.locomotiveCode_label = QLabel(addLocomotiveModel_dialog)
        self.locomotiveCode_label.setObjectName(u"locomotiveCode_label")

        self.verticalLayout.addWidget(self.locomotiveCode_label)

        self.locomotiveCode_lineEdit = QLineEdit(addLocomotiveModel_dialog)
        self.locomotiveCode_lineEdit.setObjectName(u"locomotiveCode_lineEdit")

        self.verticalLayout.addWidget(self.locomotiveCode_lineEdit)

        self.manufacturer_label = QLabel(addLocomotiveModel_dialog)
        self.manufacturer_label.setObjectName(u"manufacturer_label")

        self.verticalLayout.addWidget(self.manufacturer_label)

        self.manufacturer_hLayout = QHBoxLayout()
        self.manufacturer_hLayout.setObjectName(u"manufacturer_hLayout")
        self.maufacturer_comboBox = QComboBox(addLocomotiveModel_dialog)
        self.maufacturer_comboBox.setObjectName(u"maufacturer_comboBox")

        self.manufacturer_hLayout.addWidget(self.maufacturer_comboBox)

        self.maufacturer_toolButton = QToolButton(addLocomotiveModel_dialog)
        self.maufacturer_toolButton.setObjectName(u"maufacturer_toolButton")

        self.manufacturer_hLayout.addWidget(self.maufacturer_toolButton)


        self.verticalLayout.addLayout(self.manufacturer_hLayout)

        self.locomotiveModel_label = QLabel(addLocomotiveModel_dialog)
        self.locomotiveModel_label.setObjectName(u"locomotiveModel_label")

        self.verticalLayout.addWidget(self.locomotiveModel_label)

        self.locomotiveModel_lineEdit = QLineEdit(addLocomotiveModel_dialog)
        self.locomotiveModel_lineEdit.setObjectName(u"locomotiveModel_lineEdit")

        self.verticalLayout.addWidget(self.locomotiveModel_lineEdit)

        self.loadImage_label = QLabel(addLocomotiveModel_dialog)
        self.loadImage_label.setObjectName(u"loadImage_label")

        self.verticalLayout.addWidget(self.loadImage_label)

        self.filechooser_hLayout = QHBoxLayout()
        self.filechooser_hLayout.setSpacing(0)
        self.filechooser_hLayout.setObjectName(u"filechooser_hLayout")
        self.filepath_lineEdit = QLineEdit(addLocomotiveModel_dialog)
        self.filepath_lineEdit.setObjectName(u"filepath_lineEdit")

        self.filechooser_hLayout.addWidget(self.filepath_lineEdit)

        self.filepicker_toolButton = QToolButton(addLocomotiveModel_dialog)
        self.filepicker_toolButton.setObjectName(u"filepicker_toolButton")

        self.filechooser_hLayout.addWidget(self.filepicker_toolButton)


        self.verticalLayout.addLayout(self.filechooser_hLayout)

        self.addLocomotiveModel_buttonBox = QDialogButtonBox(addLocomotiveModel_dialog)
        self.addLocomotiveModel_buttonBox.setObjectName(u"addLocomotiveModel_buttonBox")
        self.addLocomotiveModel_buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout.addWidget(self.addLocomotiveModel_buttonBox)


        self.retranslateUi(addLocomotiveModel_dialog)

        QMetaObject.connectSlotsByName(addLocomotiveModel_dialog)
    # setupUi

    def retranslateUi(self, addLocomotiveModel_dialog):
        addLocomotiveModel_dialog.setWindowTitle(QCoreApplication.translate("addLocomotiveModel_dialog", u"Form", None))
        self.locomotiveCode_label.setText(QCoreApplication.translate("addLocomotiveModel_dialog", u"\u0410\u0440\u0442\u0438\u043a\u0443\u043b", None))
        self.manufacturer_label.setText(QCoreApplication.translate("addLocomotiveModel_dialog", u"\u041f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044c", None))
        self.maufacturer_toolButton.setText(QCoreApplication.translate("addLocomotiveModel_dialog", u"...", None))
        self.locomotiveModel_label.setText(QCoreApplication.translate("addLocomotiveModel_dialog", u"\u041c\u043e\u0434\u0435\u043b\u044c", None))
        self.loadImage_label.setText(QCoreApplication.translate("addLocomotiveModel_dialog", u"\u0417\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0435", None))
        self.filepicker_toolButton.setText(QCoreApplication.translate("addLocomotiveModel_dialog", u"...", None))
    # retranslateUi

