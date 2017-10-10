from PyQt5.QtWidgets import QWidget, QHBoxLayout, QSizePolicy
from fd_data_viewer import FastDmDataViewer
from fd_df_viewer import FastDmDfViewer
from fd_rt_spec import FastDmRtSpecifier


class FastDmDataTab(QWidget):

    def __init__(self, model, modelTab, console,
                 status, loadDataFunc, parent=None):
        super(FastDmDataTab, self).__init__(parent)

        self._model = model
        self._modelTab = modelTab
        self._console = console
        self._status = status
        self._loadDataFunc = loadDataFunc
        self._dataFilesList = None
        self._dataTable = None
        self._rtSpecifier = None
        self._initTab()

    def _initTab(self):

        self._configureLayout(QHBoxLayout())

    def _configureLayout(self, layout):
        """Initializes widgets and sets the main layout of the tab."""

        # Initialize widgets
        self._dataTable = FastDmDataViewer(self._model)
        self._rtSpecifier = FastDmRtSpecifier(self._model, self._dataTable)
        self._dataTable.connectTo(self._rtSpecifier)
        self._dataFilesList = FastDmDfViewer(self._model, self._modelTab, self._console, self._status,
                                             self._dataTable, self._rtSpecifier, self._loadDataFunc)

        # Set stretch factors
        self._setStretchFactor(self._dataTable, 3)
        self._setStretchFactor(self._rtSpecifier, 1)
        self._setStretchFactor(self._dataFilesList, 1)

        # Create layout
        layout.addWidget(self._dataFilesList)
        layout.addWidget(self._dataTable)
        layout.addWidget(self._rtSpecifier)
        self.setLayout(layout)

    def _setStretchFactor(self, widget, factor):
        """A helper method to set set stretch factor to widget."""

        policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        policy.setHorizontalStretch(factor)
        widget.setSizePolicy(policy)

    def updateFilesList(self, newFiles):
        """Calls update files list on dataFileList on load data call."""

        self._dataFilesList.updateFilesList(newFiles)

    def updateWidgets(self):
        """Called when session loaded. Updates widgets after model."""

        # Updates list AND table AND entries
        self._dataFilesList.sessionUpdate()
        self._rtSpecifier.updateEntries()






