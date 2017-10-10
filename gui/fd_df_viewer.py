from PyQt5.QtWidgets import QListWidget, QListWidgetItem, \
                            QAbstractItemView, QMenu, QAction
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from fd_io_handlers import FastDmFileLoader, LoadDataError
import tracksave


class FastDmDummyItem(QListWidgetItem):

    def __init__(self, parent=None):
        super(FastDmDummyItem, self).__init__(parent)


class FastDmDfViewer(QListWidget):

    currentIdx = None

    def __init__(self, model, modelTab, console, status,
                 table, rtSpec, loadDataFunc, parent=None):

        super(FastDmDfViewer, self).__init__(parent)

        self._model = model
        self._modelTab = modelTab
        self._console = console
        self._status = status
        self._table = table
        self._rtSpec = rtSpec
        self._loadDataFunc = loadDataFunc
        self._dummy = True
        self._initList()

    def _initList(self):
        """Initializes and configures the table."""

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._onContext)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        dummy = QListWidgetItem("No Data Files...")
        dummy.setToolTip('Click to load files...')
        dummy.setStatusTip("Click to load files...")
        self.addItem(dummy)
        self.clicked.connect(self._onClick)

    def updateFilesList(self, newFiles):
        """Adds files as list elements to file list."""

        # Remove dummy if there
        if self._dummy:
            self.takeItem(0)
            self._status.changeStatus("Data File(s) Loaded")
            self._dummy = not self._dummy

        # Add file names without path
        for file in newFiles:
            item = QListWidgetItem(file.split('/')[-1])
            item.setIcon(QIcon('./icons/data.png'))
            self.addItem(item)

        # If nothing selected previously, set selected to last
        if not self.selectedItems():
            last = len(self._model.session['datafiles']) - 1
            self.setCurrentRow(last)
            self._table.updateTable(last)

    def _deleteFiles(self):
        """Removes files from list and model."""

        # Get selected item
        files = self.selectedItems()

        # Clear Table
        self._table.clearTable()

        # Remove files from list and model
        for i, file in enumerate(files):
            idx = self.indexFromItem(file)
            self.takeItem(idx.row())
            self._model.session['datafiles'].pop(idx.row())

        # Add dummy if no more data-files left and prepare load
        if not self._model.dataFilesLoaded():
            dummy = QListWidgetItem("No Data Files...")
            dummy.setToolTip('Click to load files...')
            dummy.setStatusTip("Click to load files...")
            self.addItem(dummy)
            self._status.changeStatus("No Data File(s) Loaded")
            self._dummy = not self._dummy
            self._model.prepareForNewLoad()
            self._rtSpec.updateEntries()
            self._modelTab.updateWidgets()

    def _onClick(self, item):
        """Activated on key press on an item."""

        if not self._dummy:
            self._updateTable(item)
        else:
            self._loadDataFunc()

    def _updateTable(self, item):
        """Updates the table according to selected item index."""

        if FastDmDfViewer.currentIdx != item.row():
            FastDmDfViewer.currentIdx = item.row()
            self._table.updateTable(item.row())

    def sessionUpdate(self):
        """Called externally when a new session was loaded."""

        # Remove all previous items
        while self.count() > 0:
            self.takeItem(0)

        # Add dummy and new, if any
        if self._model.session['datafiles']:
            self.updateFilesList(self._model.session['datafiles'])
        else:
            dummy = QListWidgetItem("No Data Files...")
            dummy.setToolTip('Click to load files...')
            dummy.setStatusTip("Click to load files...")
            self.addItem(dummy)
            self._dummy = True

    def _onContext(self, point):

        if not self._dummy:
            menu = QMenu()
            deleteAction = QAction("Remove File(s)")
            deleteAction.triggered.connect(self._deleteFiles)
            menu.addAction(deleteAction)
            menu.exec_(self.mapToGlobal(point))

    # ===== Event handlers ===== #

    def keyPressEvent(self, event):
        """Checks for delete key and removes currently selected if pressed."""

        key = event.key()

        if key == Qt.Key_Delete:
            if not self._dummy:
                self._deleteFiles()
                # Modify save flag
                tracksave.saved = False

        QListWidget.keyPressEvent(self, event)

    def mimeTypes(self):

        return ['text/uri-list',
                'application/x-qabstractitemmodeldatalist']

    def dragMoveEvent(self, event):

        if event.source() is not self:
            event.accept()
        else:
            event.ignore()

    def dragEnterEvent(self, event):
        """Re-implement drag enter event."""

        if event.mimeData().hasUrls():
            event.accept()

        QAbstractItemView.dragEnterEvent(self, event)

    def dropEvent(self, event):
        """Load files as regular files."""

        try:
            # Get files
            files = [url.toLocalFile() for url in event.mimeData().urls()]
            fileLoader = FastDmFileLoader(self._model, self)
            fileLoader.load(files)
            # Update list
            self.updateFilesList(fileLoader.newFiles)
            # Modify save flag
            tracksave.saved = False
            # Log out
            for file in fileLoader.newFiles:
                self._console.write('Loaded data file ' + file)
            for file in fileLoader.repeated:
                self._console.writeWarning('File ' + file + ' already loaded!')
        except LoadDataError as e:
            self._console.writeError(str(e))





