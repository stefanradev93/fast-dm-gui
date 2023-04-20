from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QColor


class FastDmConsoleTools(QFrame):

    def __init__(self, console, parent=None):
        super(FastDmConsoleTools, self).__init__(parent)

        self._initTools(QVBoxLayout())
        self._console = console

    def _initTools(self, layout):
        """Set up tools window."""

        # Configure style
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setFrameShape(QFrame.Box)

        # Create save button
        button = QToolButton()
        button.setIcon(QIcon('./icons/save_console.png'))
        button.setToolTip('Export console contents')
        button.setStatusTip('Export console contents')
        button.clicked.connect(self._onExport)

        # Create clear button
        button2 = QToolButton()
        button2.setIcon(QIcon('./icons/clear_console.png'))
        button2.setToolTip('Clear console contents')
        button2.setStatusTip('Clear console contents')
        button2.clicked.connect(self._onClear)

        # Set up layout
        layout.addWidget(button)
        layout.addWidget(button2)
        layout.addStretch(1)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.setLayout(layout)

    def _onClear(self):
        """Activated on clear click. Asks user if sure, then clears console."""

        # Open up dialog
        confirmed = QMessageBox.question(self, 'Confirm clear...', 'Are you sure you want to clear the console?',
                                      QMessageBox.Yes | QMessageBox.No)
        # If user agrees, clear
        if confirmed == QMessageBox.Yes:
            self._console.clearContents()

    def _onExport(self):
        """Activated on export click. Opens up a dialog and saves if user agrees."""

        self._console.exportContents()


class FastDmConsoleWindow(QTextEdit):

    def __init__(self, parent=None):
        super(FastDmConsoleWindow, self).__init__(parent)

        self.setReadOnly(True)


class FastDmConsole(QWidget):

    greeting = '<font color="#dce582"> {} Welcome to fast-dm v30.2 GUI! ' \
               'To start analyzing, simply load files and have fun! {}</font><br>'.\
                format('*'*5, '*'*5)
    defaultColor = QColor(239, 240, 241)
    warningColor = QColor(244, 241, 41)
    errorColor = QColor(244, 4, 44)

    def __init__(self, model, parent=None):
        super(FastDmConsole, self).__init__(parent)

        self._consoleWindow = FastDmConsoleWindow()
        self._consoleTools = FastDmConsoleTools(self)
        self._initConsole()
        self._greet()
        self._pathInfo(model)

    def _initConsole(self):

        self._configureLayout(QHBoxLayout())

    def _configureLayout(self, layout):

        layout.addWidget(self._consoleTools)
        layout.addWidget(self._consoleWindow)
        self.setLayout(layout)

    def _greet(self):
        """Write greeting message to console."""

        self._consoleWindow.append(FastDmConsole.greeting)
        self._align(Qt.AlignCenter)

    def _pathInfo(self, model):
        """Outputs the path to fast."""

        self._consoleWindow.append('...Path to fast-dm executable set to: ' +
                                   model.session['fastdmpath'])
        self._align(Qt.AlignLeft)

    def _align(self, alignment):
        cursor = self._consoleWindow.textCursor()
        block = cursor.blockFormat()
        block.setAlignment(alignment)
        cursor.mergeBlockFormat(block)
        self._consoleWindow.setTextCursor(cursor)

    def clearContents(self):
        """Clears all text from console."""

        self._consoleWindow.setText("")
        self._greet()

    def exportContents(self):
        """Opens up a dialog and asks user whether to save or not."""

        # Create dialog
        saveDialog = QFileDialog()
        saveDialog.setAcceptMode(QFileDialog.AcceptSave)
        saveName = saveDialog.getSaveFileName(self, "Save Console Contents as...",
                                              "", ".txt")

        # If user has chosen something
        if saveName[0]:
            with open(saveName[0] + saveName[1], 'w') as outfile:
                txt = self._consoleWindow.toPlainText()
                dummy = '***** Welcome to fast-dm v30.2 GUI! To start analyzing, ' \
                        'simply load files and have fun! *****\n'
                txt = txt.replace(dummy, '')
                outfile.write(txt)

    def write(self, txt):
        """Called externally to write a message."""

        self._consoleWindow.setTextColor(FastDmConsole.defaultColor)
        self._consoleWindow.append(txt)
        self._align(Qt.AlignLeft)

    def writeError(self, err):
        """Called externally to write an error."""

        self._consoleWindow.setTextColor(FastDmConsole.errorColor)
        self._consoleWindow.append(err)
        self._align(Qt.AlignLeft)

    def writeWarning(self, err):
        """Called externally to write a warning to console."""

        self._consoleWindow.setTextColor(FastDmConsole.warningColor)
        self._consoleWindow.append(err)
        self._align(Qt.AlignLeft)

    def sizeHint(self):
        """Used to make run button visible by shrinking console to 1/5 of display height."""

        screenHeight = QApplication.desktop().screenGeometry().height()
        return QSize(int(self.width()), int(screenHeight/5))
