from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, \
    QAbstractItemView, QMenu, QAction, QActionGroup, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import pandas as pd
import numpy as np
from pandas.errors import ParserError


class FastDmContextAction(QAction):
    """Used to represent a checkable action for changing response/time columns."""
    def __init__(self, text, model, table, key, opposite):
        super(FastDmContextAction, self).__init__(text)

        self._model = model
        self._table = table
        self.key = key
        self.opposite = opposite
        self.columnName = None  # must be specified with prepareActions call!
        self.setCheckable(True)
        self.toggled[bool].connect(self._onChange)

    def _onChange(self, checked):
        """Triggered when action selected. Assumes that columnName attribute is defined."""

        if checked:
            self._onChecked()
        else:
            self._onUnchecked()

    def _onChecked(self):
        """Called from onChange. Perform action when column selected."""

        # Check if time, test range
        if self.key == 'TIME':
            # Check and give warning if time values are too large, or time column non-numeric
            data = np.genfromtxt(self._model.session['datafiles'][0], skip_header=True)
            # Try calculating maximum of column, TypeError is thrown, if column is non numeric
            try:
                idx = self._model.session['columns'].index(self.columnName)
                if data[:, idx].max() > 121:
                    msg = QMessageBox()
                    text = 'Some reaction times of column \'{}\' appear to be very large. Note, that ' \
                           'fast-dm works with reaction times in SECONDS, not milliseconds.'.format(self.columnName)
                    msg.information(self._table, 'Suspicious reaction time range...', text)

            # Column non-numeric, give error and reset
            except TypeError:
                msg = QMessageBox()
                text = 'Could not set {} as TIME. Reaction time column must be numeric!'.format(self.columnName)
                msg.critical(self._table, 'Error setting time...', text)
                return

        # If anything selected previously
        self._applyChange()

    def _applyChange(self):
        """Called if column is numeric, updates model entries and table."""

        if self._model.session[self.key]['idx'] is not None:
            # Change previous color
            self._table.changeColor(self._model.session[self.key]['idx'], FastDmDataViewer.normalColumnColor)
            # Reset if column was previously response or time
            if self._model.session[self.opposite]['name'] == self.columnName:
                self._model.session[self.opposite]['name'] = None
                self._model.session[self.opposite]['idx'] = None

        self._model.session[self.key]['idx'] = self._model.session['columns'].index(self.columnName)
        self._model.session[self.key]['name'] = self.columnName
        self._table.changeColor(self._model.session[self.key]['idx'], FastDmDataViewer.timeColor)

    def _onUnchecked(self):
        """Change back column color to normal and reset model entries."""
        self._table.changeColor(self._model.session[self.key]['idx'], FastDmDataViewer.normalColumnColor)
        self._model.session[self.key]['idx'] = None
        self._model.session[self.key]['name'] = None

    def prepare(self, columnName):
        """Called to decide status of action."""

        self.columnName = columnName
        self.blockSignals(True)
        if self._model.session[self.key]['name'] == self.columnName:
            self.setChecked(True)
        else:
            self.setChecked(False)

        if self._isCondition():
            self.setEnabled(False)
        else:
            self.setEnabled(True)
        self.blockSignals(False)

    def _isCondition(self):
        """Returns True if column is set as condition, False otherwise"""

        for _, values in self._model.parameters.items():
            if self.columnName in values['depends']:
                return True
        return False


class FastDmColumnContextMenu(QMenu):
    """Represents a custom context menu used to set columns as time or response."""

    def __init__(self, table, model, parent=None):
        super(FastDmColumnContextMenu, self).__init__(parent)

        self._table = table
        self._model = model
        self._initActions()

    def _initActions(self):
        """Adds the two actions to change columns."""

        # Create actions
        self.setTime = FastDmContextAction('Set as Reaction Time', self._model, self._table,
                                           'TIME', 'RESPONSE')
        self.setResponse = FastDmContextAction('Set as Response', self._model, self._table,
                                               'RESPONSE', 'TIME')

        # Create action group
        self.actionGroup = QActionGroup(self)
        self.actionGroup.addAction(self.setTime)
        self.actionGroup.addAction(self.setResponse)

        # Add them to menu
        self.addAction(self.setTime)
        self.addAction(self.setResponse)

    def prepareActions(self, columnName):
        """Check conditions for actions and show them."""

        self.setTime.prepare(columnName)
        self.setResponse.prepare(columnName)


class FastDmDataViewer(QTableWidget):

    normalColumnColor = QColor(35, 38, 41)
    timeColor = QColor(40, 115, 153)
    responseColor = QColor(40, 115, 153)

    def __init__(self, model, parent=None):
        super(FastDmDataViewer, self).__init__(parent)

        self._model = model
        self._rtSpecifier = None  # must be added with connect to
        self._initTable()

    def _initTable(self):
        """Initializes and configures the table."""

        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.header = self.horizontalHeader()
        #self.header.setStretchLastSection(True)
        self.header.setToolTip("Right-click to set as RESPONSE or TIME")
        self.header.setStatusTip("Right-click to set as RESPONSE or TIME")

        # ===== Context header menu ===== #
        self.header.setContextMenuPolicy(Qt.CustomContextMenu)
        self.header.customContextMenuRequested.connect(self._context)
        self.menu = FastDmColumnContextMenu(self, self._model, self.header)

    def _context(self, pos):
        """Activated on context menu click."""

        self.selectColumn(self.header.logicalIndexAt(pos))
        self.menu.prepareActions(self._model.session['columns'][self.header.logicalIndexAt(pos)])
        self.menu.exec_(self.header.mapToGlobal(pos))
        self._rtSpecifier.updateEntries()
        self.clearSelection()

    def updateTable(self, fileIndex):
        """Updates the table view with the data file specified by fileIndex"""

        # Assume delimiter is either whitespace or tab, read data
        # Try to catch any runtime errors like changing the file etc.
        try:
            data = pd.read_csv(self._model.session['datafiles'][fileIndex],
                                                    delim_whitespace=True,
                                                    engine='python',
                                                    header=0,
                                                    usecols=range(len(self._model.session['columns'])))
            nRows = data.shape[0]
            nCols = data.shape[1]

            # Clear table
            self.clearTable()

            # Populate table
            self._populate(data, nRows, nCols)

            # Highlight RESPONSE and TIME
            self._highlightSelected()
        except (IOError, OSError, FileNotFoundError) as e:
            # Handle exception
            msg = QMessageBox()
            text = 'Could not open {}! File probably changed/moved. Try reloading the file.'.\
                format(self._model.session['datafiles'][fileIndex])
            msg.critical(self, 'Error displaying data file...', text)
            
        except ParserError as e:
            # Handle pandas parser exception
            msg = QMessageBox()
            text = 'Could not load {} correctly! File probably has bad format'. \
                format(self._model.session['datafiles'][fileIndex])
            msg.critical(self, 'Error loading data file...', text)

    def clearTable(self):
        """Clears all entries."""

        while self.rowCount() > 0:
            self.removeRow(0)
        self.horizontalHeader().hide()

    def changeColor(self, columnIdx, color):
        """Called externally to change color."""

        for i in range(self.rowCount()):
            self.item(i, columnIdx).setBackground(color)

    def connectTo(self, rtSpecifier):
        """Adds a reference to the rt specifier."""

        self._rtSpecifier = rtSpecifier

    def _populate(self, data, r, c):
        """Populates table according to num columns and rows."""

        self.setRowCount(r)
        self.setColumnCount(c)
        self.setHorizontalHeaderLabels(self._model.session['columns'])

        for i in range(r):
            for j in range(c):
                item = QTableWidgetItem()
                item.setText(str(data.iloc[i, j]))
                self.setItem(i, j, item)

        self.horizontalHeader().show()
        self.resizeColumnsToContents()

    def _highlightSelected(self):
        """Called each time to highlight selected time and response columns."""

        # Highlight RESPONSE
        if self._model.session['RESPONSE']['idx'] is not None:
            self.changeColor(self._model.session['RESPONSE']['idx'], FastDmDataViewer.responseColor)

        # Highlight TIME
        if self._model.session['TIME']['idx'] is not None:
            self.changeColor(self._model.session['TIME']['idx'], FastDmDataViewer.timeColor)

