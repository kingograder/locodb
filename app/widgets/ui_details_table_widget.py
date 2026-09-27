# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'details_table_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QHeaderView, QLabel,
    QLayout, QPushButton, QSizePolicy, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget)

class Ui_detailsTable_widget(object):
    def setupUi(self, detailsTable_widget):
        if not detailsTable_widget.objectName():
            detailsTable_widget.setObjectName(u"detailsTable_widget")
        detailsTable_widget.resize(400, 313)
        self.verticalLayout = QVBoxLayout(detailsTable_widget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.detailsTable_label = QLabel(detailsTable_widget)
        self.detailsTable_label.setObjectName(u"detailsTable_label")

        self.verticalLayout.addWidget(self.detailsTable_label)

        self.detailsTable_hLayout = QHBoxLayout()
        self.detailsTable_hLayout.setObjectName(u"detailsTable_hLayout")
        self.detailsTable_tableWidget = QTableWidget(detailsTable_widget)
        self.detailsTable_tableWidget.setObjectName(u"detailsTable_tableWidget")

        self.detailsTable_hLayout.addWidget(self.detailsTable_tableWidget)

        self.detailsTableButtons_vLayout = QVBoxLayout()
        self.detailsTableButtons_vLayout.setObjectName(u"detailsTableButtons_vLayout")
        self.detailsTableButtons_vLayout.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        self.detailAdd_pushButton = QPushButton(detailsTable_widget)
        self.detailAdd_pushButton.setObjectName(u"detailAdd_pushButton")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.detailAdd_pushButton.sizePolicy().hasHeightForWidth())
        self.detailAdd_pushButton.setSizePolicy(sizePolicy)

        self.detailsTableButtons_vLayout.addWidget(self.detailAdd_pushButton)

        self.detailRemove_pushButton = QPushButton(detailsTable_widget)
        self.detailRemove_pushButton.setObjectName(u"detailRemove_pushButton")
        sizePolicy.setHeightForWidth(self.detailRemove_pushButton.sizePolicy().hasHeightForWidth())
        self.detailRemove_pushButton.setSizePolicy(sizePolicy)

        self.detailsTableButtons_vLayout.addWidget(self.detailRemove_pushButton)


        self.detailsTable_hLayout.addLayout(self.detailsTableButtons_vLayout)


        self.verticalLayout.addLayout(self.detailsTable_hLayout)


        self.retranslateUi(detailsTable_widget)

        QMetaObject.connectSlotsByName(detailsTable_widget)
    # setupUi

    def retranslateUi(self, detailsTable_widget):
        detailsTable_widget.setWindowTitle(QCoreApplication.translate("detailsTable_widget", u"Form", None))
        self.detailsTable_label.setText(QCoreApplication.translate("detailsTable_widget", u"\u0414\u0435\u0442\u0430\u043b\u0438", None))
        self.detailAdd_pushButton.setText(QCoreApplication.translate("detailsTable_widget", u"+", None))
        self.detailRemove_pushButton.setText(QCoreApplication.translate("detailsTable_widget", u"-", None))
    # retranslateUi

