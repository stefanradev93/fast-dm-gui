from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import tracksave
from fd_io_handlers import *
from fd_tab_controller import FastDmTabController
from fd_console import FastDmConsole
from fd_model import FastDmModel
from fd_data_tab import FastDmDataTab
from fd_model_tab import FastDmModelTab
from fd_plot_tab import FastDmAdditionalTab
from fd_exceptions import LoadDataError
import webbrowser


class FastDmMainWindow(QMainWindow):

    def __init__(self, parent=None):
        super(FastDmMainWindow, self).__init__(parent)

        self._model = FastDmModel()
        self._console = FastDmConsole(self._model)
        self._status = FastDmStatus()
        self._initMain()

    def _initMain(self):
        """Initializes main GUI components."""

        # ===== Configure one by one ===== #
        self._configureMain()
        self._configureMenu()
        self._configureToolbar()
        self._configureTabController()
        self._configureConsole()
        # Modify save flag
        tracksave.saved = True

    def _configureMain(self):
        """Applies main settings to main window."""

        self.setWindowIcon(QIcon('./icons/icon.ico'))
        self.setWindowTitle('fast-dm - Diffusion Model Analysis Tool v30.2')
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setDockOptions(QMainWindow.AnimatedDocks |
                            QMainWindow.AllowNestedDocks |
                            QMainWindow.AllowTabbedDocks)
        self.setStatusBar(self._status)

    def _configureMenu(self):
        """Loads the menu bar and adds actions."""

        fileMenu = self.menuBar().addMenu('&File')
        toolsMenu = self.menuBar().addMenu('&Tools')
        self.viewMenu = self.menuBar().addMenu('&View')
        helpMenu = self.menuBar().addMenu('&Help')

        # ===== Add actions to file menu ===== #
        loadData = self._createAction('&Load Data', 'self._loadData',
                                      tip="Load data file(s)...", icon='open')
        loadSession = self._createAction('&Load Session', 'self._loadSession',
                                         tip='Load session...', icon='load')
        saveSession = self._createAction('&Save Session', 'self._saveSession',
                                         tip='Save current Session...', icon='save')
        exitAction = self._createAction('&Exit', 'self.close', tip='Quit fast-dm')

        self._addActionsToTargetBar(fileMenu, (loadData, loadSession, saveSession, None, exitAction))

        # ===== Add actions to tools menu ===== #
        pass

        # ===== Add actions to help menu ===== #
        helpOnline = self._createAction('&Get Help Online...', 'self._help', icon='help',
                                        tip='Get help from the fast-dm homepage')
        aboutQt = self._createAction('&About Qt', 'self._aboutQt', icon='about',
                                     tip='Read more about Qt')
        about = self._createAction('&About fast-dm', 'self._about', icon='about',
                                   tip='Read more about fast-dm')
        self._addActionsToTargetBar(helpMenu, (helpOnline, aboutQt, about))

    def _configureToolbar(self):
        """Adds actions to the toolbar."""

        toolbar = self.addToolBar('Toolbar')
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        loadData = self._createAction('&Load Data', 'self._loadData',
                                    tip="Load data file(s)...", icon='open')
        loadSession = self._createAction('&Load Session', 'self._loadSession',
                                    tip='Load session...', icon='load')
        saveSession = self._createAction('&Save Session', 'self._saveSession',
                                    tip='Save current Session...', icon='save')

        self._addActionsToTargetBar(toolbar, (loadData, loadSession, saveSession))

    def _configureTabController(self):
        """Instantiates the tab controller."""

        # Create Tabs
        self.modelTab = FastDmModelTab(self._model, self._console, self._status)
        self.dataTab = FastDmDataTab(self._model, self.modelTab,
                                     self._console, self._status, self._loadData)
        self.plotTab = FastDmAdditionalTab(self._model, self._console)

        # Create tab controller
        tabSettings = [(self.dataTab, 'Data Overview', 0, './icons/tab.png'),
                       (self.modelTab, 'Model Specifications', 1, './icons/temp_fd_pic.gif'),
                       (self.plotTab, 'Fast-dm Plot', 2, './icons/plot.png')]
        self.tabController = FastDmTabController(tabSettings)
        self.setCentralWidget(self.tabController)

    def _configureConsole(self):
        """Instantiates the console window as a dock widget."""

        # Create the dock widget
        consoleDockWindow = QDockWidget("Output Console", self)
        consoleDockWindow.setObjectName("ExpTreeDockWidget")
        consoleDockWindow.setAllowedAreas(Qt.AllDockWidgetAreas)
        consoleDockWindow.setFeatures(QDockWidget.AllDockWidgetFeatures)

        # Add console to dock
        consoleDockWindow.setWidget(self._console)

        # Add action to view menu
        action = consoleDockWindow.toggleViewAction()
        self.viewMenu.addAction(action)

        # Add dock to main
        self.addDockWidget(Qt.BottomDockWidgetArea, consoleDockWindow)

    def _createAction(self, text, callback=None, shortcut=None,
                      icon=None, tip=None, checkable=False):

        action = QAction(text, self)
        if icon is not None:
            action.setIcon(QIcon("./icons/{}.png".format(icon)))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tip is not None:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        if callback is not None:
            action.triggered.connect(eval(callback))
        if checkable:
            action.setCheckable(True)
        return action

    def _addActionsToTargetBar(self, target, actions):
        """
        A helper function to add many actions to 
        a target menu or a toolbar.
        """
        for action in actions:
            if action is None:
                target.addSeparator()
            else:
                target.addAction(action)

    def _loadData(self):
        """Opens a dialog for loading datafiles."""

        # Create instance and set filter
        openDialog = QFileDialog()
        openDialog.setFilter(QDir.Files)
        fnames = openDialog.getOpenFileNames(self, "Load Data File(s)...", "",
                                                    "Data Files (*.txt *.csv *.dat)")
        # If something loaded, try to load
        if fnames[0]:
            # Perform check
            try:
                # Create an instance of FastDmLoader and update model, if data files pass
                fileLoader = FastDmFileLoader(self._model, self)
                # File Loader takes care of input check and the actual loading
                fileLoader.load(fnames[0])
                # Update list
                self._updateList(fileLoader.newFiles)
                # Modify save flag
                tracksave.saved = False
                # Log out
                for file in fileLoader.newFiles:
                    self._console.write('Loaded data file ' + file)
                for file in fileLoader.repeated:
                    self._console.writeWarning('File ' + file + ' already loaded!')
            except LoadDataError as e:

                # Handle (output to console)
                self._console.writeError(str(e))

    def _updateList(self, newFiles):
        """Updates list data files viewer with the new files."""

        self.dataTab.updateFilesList(newFiles)

    def _loadSession(self):
        """Opens a dialog for loading a session."""

        loadDialog = QFileDialog()
        loadName = loadDialog.getOpenFileName(self, 'Select a Session File to Open...',
                                              "", "fast-dm File (*.fast)")
        # Check if something loaded
        if loadName[0]:
            # Try to Load
            newModel = FastDmSessionLoader.load(loadName[0], self)
            # If load successful, replace model and update all
            if newModel:
                # Ask for save old data
                self._askOverwrite()
                self._model.overwrite(newModel)
                self.dataTab.updateWidgets()
                self.modelTab.updateWidgets()
                self.plotTab.updateWidgets()

                # Modify save flag
                tracksave.saved = True

                # Log out
                self._console.write('Loaded session ' + loadName[0])

    def _saveSession(self):
        """Opens a dialog for saving a session."""

        saveDialog = QFileDialog()
        saveName = saveDialog.getSaveFileName(self, "Save Current Session as...",
                                              "", "Fast-Dm File (*.fast)")

        # If user has chosen something
        if saveName[0]:
            # Create a file saver instance and save files
            fileSaver = FastDmSessionSaver(self._model, self)
            ret = fileSaver.save(saveName[0])
            if ret:
                # Set saved flag
                tracksave.saved = True
                # Log to console
                self._console.write('Session saved as ' + saveName[0])
            else:
                pass

    def _askOverwrite(self):
        """Asks if user want to save old data on load new."""

        # Check if saved
        if not tracksave.saved:
            # Open up a dialog
            confirmed = QMessageBox.question(self, 'Loading a Session...',
                                             'Do you want to save your current session?',
                                             QMessageBox.Yes | QMessageBox.No)
            # If user agreed, ask for save
            if confirmed == QMessageBox.Yes:
                self._saveSession()

    def _about(self):
        """Triggered when about menu item clicked."""

        text = 'fast-dm developed by Voss & Voss (2007, 2008). ' \
               'Graphical user interface developed by Stefan Radev (2017). ' \
               'Dark style by https://github.com/ColinDuquesnoy.\n\n' \
               'Fast-dm is a free software distributed under the GNU 3.0 licence. ' \
               'The developers take no responsibility for the use of this program ' \
               'or sloppy data analysis in general. :) ' \
               'For more information, check out our webpage at "Get help online" ' \
               'or read the paper by Voss, Voss & Lerche (2015).'

        mbox = QMessageBox()
        mbox.information(self, 'About fast-dm', text)

    def _aboutQt(self):
        """Triggered when about qt item clicked."""

        dialog = QMessageBox()
        dialog.aboutQt(self, 'About Qt')

    def _help(self):
        """Triggered when get help online menu item clicked."""

        webbrowser.open_new('http://www.psychologie.uni-heidelberg.de/ae/meth/fast-dm/')

    def closeEvent(self, event):
        """
        Activated when user tries to exit fast-dm either by 
        clicking the X or by clicking the exit menu button.
        """

        if not tracksave.saved:
            # Create a dialog
            dialog = QMessageBox()

            # Ask if user sure
            choice = dialog.question(self, 'Exiting fast-dm...',
                                        'Do you want to save your session?',
                                        QMessageBox.Cancel | QMessageBox.No | QMessageBox.Yes)
            # Check user choice
            if choice == QMessageBox.Yes:
                self._saveSession()
                event.accept()
            elif choice == QMessageBox.No:
                event.accept()
            elif choice == QMessageBox.Cancel:
                event.ignore()
        else:
            QMainWindow.closeEvent(self, event)


class FastDmStatus(QStatusBar):

    def __init__(self, parent=None):
        super(FastDmStatus, self).__init__(parent)

        self._label = QLabel("No Data File(s) Loaded")
        self.setStyleSheet("border: 1px solid #535b68")
        self.addPermanentWidget(self._label)

    def changeStatus(self, txt):
        """Changes status to text."""

        self._label.setText(txt)