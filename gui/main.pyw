#!/usr/bin/env python

import sys
import os
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtCore import QLocale, QTimer, Qt
from PyQt5.QtGui import QPixmap
import qdarkstyle
from fd_main_window import FastDmMainWindow
import ctypes
import time


"""Essential for standardizing the resources path"""

PATH = os.path.dirname(os.path.abspath(__file__))
os.chdir(PATH)


if __name__ == '__main__':
    # =============================================================== #
    #               SET APP ID SO ICON IS VISIBLE                     #
    # =============================================================== #
    myappid = 'heidelberg.university.fast-dm.30.2.2'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    # =============================================================== #
    #                   CHANGE LOCALE SETTINGS                        #
    # =============================================================== #
    QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))

    # =============================================================== #
    #                   SET APP GLOBAL INFORMATION                    #
    # =============================================================== #
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    app.setOrganizationName("Heidelberg University")
    app.setApplicationName("fast-dm")

    # =============================================================== #
    #                       CREATE SPLASH SCREEN                      #
    # =============================================================== #

    splash = QSplashScreen()
    splash.setPixmap(QPixmap('./icons/fast_icon.png'))
    splash.setEnabled(False)
    splash.show()
    app.processEvents()
    time.sleep(3)

    # =============================================================== #
    #                       CREATE MAIN WINDOW                        #
    # =============================================================== #
    mainWindow = FastDmMainWindow()
    mainWindow.showMaximized()
    splash.finish(mainWindow)
    sys.exit(app.exec_())
