# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.11.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QMainWindow, QMenu, QMenuBar,
    QSizePolicy, QStatusBar, QTabWidget, QVBoxLayout,
    QWidget)

class Ui_main_window(object):
    def setupUi(self, main_window):
        if not main_window.objectName():
            main_window.setObjectName(u"main_window")
        main_window.resize(800, 600)
        self.aboutProgram_menuItem = QAction(main_window)
        self.aboutProgram_menuItem.setObjectName(u"aboutProgram_menuItem")
        self.user_menuItem = QAction(main_window)
        self.user_menuItem.setObjectName(u"user_menuItem")
        self.userManagement_menuItem = QAction(main_window)
        self.userManagement_menuItem.setObjectName(u"userManagement_menuItem")
        self.changeUser_menuItem = QAction(main_window)
        self.changeUser_menuItem.setObjectName(u"changeUser_menuItem")
        self.aboutQt_menuItem = QAction(main_window)
        self.aboutQt_menuItem.setObjectName(u"aboutQt_menuItem")
        self.programmSettings_menuItem = QAction(main_window)
        self.programmSettings_menuItem.setObjectName(u"programmSettings_menuItem")
        self.centralwidget = QWidget(main_window)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.tabWidget = QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName(u"tabWidget")
        self.maintenances_tab = QWidget()
        self.maintenances_tab.setObjectName(u"maintenances_tab")
        self.verticalLayout_2 = QVBoxLayout(self.maintenances_tab)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.tabWidget.addTab(self.maintenances_tab, "")
        self.locomotives_tab = QWidget()
        self.locomotives_tab.setObjectName(u"locomotives_tab")
        self.verticalLayout_3 = QVBoxLayout(self.locomotives_tab)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.tabWidget.addTab(self.locomotives_tab, "")
        self.details_tab = QWidget()
        self.details_tab.setObjectName(u"details_tab")
        self.verticalLayout_4 = QVBoxLayout(self.details_tab)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.tabWidget.addTab(self.details_tab, "")

        self.verticalLayout.addWidget(self.tabWidget)

        main_window.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(main_window)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 800, 23))
        self.menubar.setDefaultUp(False)
        self.menubar.setNativeMenuBar(True)
        self.user_menuTab = QMenu(self.menubar)
        self.user_menuTab.setObjectName(u"user_menuTab")
        self.other_menuTab = QMenu(self.menubar)
        self.other_menuTab.setObjectName(u"other_menuTab")
        main_window.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(main_window)
        self.statusbar.setObjectName(u"statusbar")
        main_window.setStatusBar(self.statusbar)

        self.menubar.addAction(self.user_menuTab.menuAction())
        self.menubar.addAction(self.other_menuTab.menuAction())
        self.user_menuTab.addAction(self.user_menuItem)
        self.user_menuTab.addAction(self.userManagement_menuItem)
        self.user_menuTab.addAction(self.changeUser_menuItem)
        self.other_menuTab.addAction(self.programmSettings_menuItem)
        self.other_menuTab.addAction(self.aboutProgram_menuItem)
        self.other_menuTab.addAction(self.aboutQt_menuItem)

        self.retranslateUi(main_window)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(main_window)
    # setupUi

    def retranslateUi(self, main_window):
        main_window.setWindowTitle(QCoreApplication.translate("main_window", u"MainWindow", None))
        self.aboutProgram_menuItem.setText(QCoreApplication.translate("main_window", u"\u041e \u041f\u0440\u043e\u0433\u0440\u0430\u043c\u0435", None))
        self.user_menuItem.setText(QCoreApplication.translate("main_window", u"John Blade", None))
        self.userManagement_menuItem.setText(QCoreApplication.translate("main_window", u"\u0423\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044f\u043c\u0438", None))
        self.changeUser_menuItem.setText(QCoreApplication.translate("main_window", u"\u0421\u043c\u0435\u043d\u0438\u0442\u044c \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044f", None))
        self.aboutQt_menuItem.setText(QCoreApplication.translate("main_window", u"\u041e Qt", None))
        self.programmSettings_menuItem.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.maintenances_tab), QCoreApplication.translate("main_window", u"\u041b\u0438\u0441\u0442\u044b \u043e\u0431\u0441\u043b\u0443\u0436\u0438\u0432\u0430\u043d\u0438\u044f", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.locomotives_tab), QCoreApplication.translate("main_window", u"\u041b\u043e\u043a\u043e\u043c\u043e\u0442\u0438\u0432\u044b", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.details_tab), QCoreApplication.translate("main_window", u"\u0414\u0435\u0442\u0430\u043b\u0438", None))
        self.user_menuTab.setTitle(QCoreApplication.translate("main_window", u"\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c", None))
        self.other_menuTab.setTitle(QCoreApplication.translate("main_window", u"\u041f\u0440\u043e\u0447\u0435\u0435", None))
    # retranslateUi

