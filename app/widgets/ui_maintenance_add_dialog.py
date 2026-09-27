# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'maintenance_add_dialog.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QComboBox, QDateEdit,
    QDialogButtonBox, QGridLayout, QHBoxLayout, QHeaderView,
    QLabel, QPushButton, QSizePolicy, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget)

class Ui_addMaintenance_dialog(object):
    def setupUi(self, addMaintenance_dialog):
        if not addMaintenance_dialog.objectName():
            addMaintenance_dialog.setObjectName(u"addMaintenance_dialog")
        addMaintenance_dialog.resize(637, 494)
        self.verticalLayout = QVBoxLayout(addMaintenance_dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.addMaintenanceComment_label = QLabel(addMaintenance_dialog)
        self.addMaintenanceComment_label.setObjectName(u"addMaintenanceComment_label")

        self.verticalLayout.addWidget(self.addMaintenanceComment_label)

        self.addMaintenanceComment_textEdit = QTextEdit(addMaintenance_dialog)
        self.addMaintenanceComment_textEdit.setObjectName(u"addMaintenanceComment_textEdit")

        self.verticalLayout.addWidget(self.addMaintenanceComment_textEdit)

        self.detailsTable_label = QLabel(addMaintenance_dialog)
        self.detailsTable_label.setObjectName(u"detailsTable_label")

        self.verticalLayout.addWidget(self.detailsTable_label)

        self.detailsTable_tableWidget = QTableWidget(addMaintenance_dialog)
        self.detailsTable_tableWidget.setObjectName(u"detailsTable_tableWidget")

        self.verticalLayout.addWidget(self.detailsTable_tableWidget)

        self.detailsManageButtons_hLayout = QHBoxLayout()
        self.detailsManageButtons_hLayout.setObjectName(u"detailsManageButtons_hLayout")
        self.detailAdd_pushButton = QPushButton(addMaintenance_dialog)
        self.detailAdd_pushButton.setObjectName(u"detailAdd_pushButton")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.detailAdd_pushButton.sizePolicy().hasHeightForWidth())
        self.detailAdd_pushButton.setSizePolicy(sizePolicy)

        self.detailsManageButtons_hLayout.addWidget(self.detailAdd_pushButton)

        self.detailRemove_pushButton = QPushButton(addMaintenance_dialog)
        self.detailRemove_pushButton.setObjectName(u"detailRemove_pushButton")
        sizePolicy.setHeightForWidth(self.detailRemove_pushButton.sizePolicy().hasHeightForWidth())
        self.detailRemove_pushButton.setSizePolicy(sizePolicy)

        self.detailsManageButtons_hLayout.addWidget(self.detailRemove_pushButton)


        self.verticalLayout.addLayout(self.detailsManageButtons_hLayout)

        self.addMaintenanceMeta_gLayout = QGridLayout()
        self.addMaintenanceMeta_gLayout.setObjectName(u"addMaintenanceMeta_gLayout")
        self.addMaintenanceLoco_label = QLabel(addMaintenance_dialog)
        self.addMaintenanceLoco_label.setObjectName(u"addMaintenanceLoco_label")

        self.addMaintenanceMeta_gLayout.addWidget(self.addMaintenanceLoco_label, 0, 0, 1, 1)

        self.addMaintenanceType_lable = QLabel(addMaintenance_dialog)
        self.addMaintenanceType_lable.setObjectName(u"addMaintenanceType_lable")

        self.addMaintenanceMeta_gLayout.addWidget(self.addMaintenanceType_lable, 0, 1, 1, 1)

        self.addMaintenanceDate_label = QLabel(addMaintenance_dialog)
        self.addMaintenanceDate_label.setObjectName(u"addMaintenanceDate_label")

        self.addMaintenanceMeta_gLayout.addWidget(self.addMaintenanceDate_label, 0, 2, 1, 1)

        self.addMaintenanceLoco_comboBox = QComboBox(addMaintenance_dialog)
        self.addMaintenanceLoco_comboBox.setObjectName(u"addMaintenanceLoco_comboBox")

        self.addMaintenanceMeta_gLayout.addWidget(self.addMaintenanceLoco_comboBox, 1, 0, 1, 1)

        self.addMaintenanceType_comboBox = QComboBox(addMaintenance_dialog)
        self.addMaintenanceType_comboBox.setObjectName(u"addMaintenanceType_comboBox")

        self.addMaintenanceMeta_gLayout.addWidget(self.addMaintenanceType_comboBox, 1, 1, 1, 1)

        self.addMaintenanceDate_dateEdit = QDateEdit(addMaintenance_dialog)
        self.addMaintenanceDate_dateEdit.setObjectName(u"addMaintenanceDate_dateEdit")
        self.addMaintenanceDate_dateEdit.setMinimumDateTime(QDateTime(QDate(2024, 1, 1), QTime(3, 40, 1)))
        self.addMaintenanceDate_dateEdit.setMinimumDate(QDate(2024, 1, 1))
        self.addMaintenanceDate_dateEdit.setCalendarPopup(True)

        self.addMaintenanceMeta_gLayout.addWidget(self.addMaintenanceDate_dateEdit, 1, 2, 1, 1)


        self.verticalLayout.addLayout(self.addMaintenanceMeta_gLayout)

        self.addMaintenance_buttonBox = QDialogButtonBox(addMaintenance_dialog)
        self.addMaintenance_buttonBox.setObjectName(u"addMaintenance_buttonBox")
        self.addMaintenance_buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout.addWidget(self.addMaintenance_buttonBox)


        self.retranslateUi(addMaintenance_dialog)

        QMetaObject.connectSlotsByName(addMaintenance_dialog)
    # setupUi

    def retranslateUi(self, addMaintenance_dialog):
        addMaintenance_dialog.setWindowTitle(QCoreApplication.translate("addMaintenance_dialog", u"Form", None))
        self.addMaintenanceComment_label.setText(QCoreApplication.translate("addMaintenance_dialog", u"\u041a\u043e\u043c\u043c\u0435\u043d\u0442\u0430\u0440\u0438\u0439", None))
        self.detailsTable_label.setText(QCoreApplication.translate("addMaintenance_dialog", u"\u0414\u0435\u0442\u0430\u043b\u0438", None))
        self.detailAdd_pushButton.setText(QCoreApplication.translate("addMaintenance_dialog", u"+", None))
        self.detailRemove_pushButton.setText(QCoreApplication.translate("addMaintenance_dialog", u"-", None))
        self.addMaintenanceLoco_label.setText(QCoreApplication.translate("addMaintenance_dialog", u"\u041b\u043e\u043a\u043e\u043c\u043e\u0442\u0438\u0432", None))
        self.addMaintenanceType_lable.setText(QCoreApplication.translate("addMaintenance_dialog", u"\u0422\u0438\u043f \u043e\u0431\u0441\u043b\u0443\u0436\u0438\u0432\u0430\u043d\u0438\u044f", None))
        self.addMaintenanceDate_label.setText(QCoreApplication.translate("addMaintenance_dialog", u"\u0414\u0430\u0442\u0430 \u043e\u0431\u0441\u043b\u0443\u0436\u0438\u0432\u0430\u043d\u0438\u044f", None))
    # retranslateUi

