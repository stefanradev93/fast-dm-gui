from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtCore import Qt
from fd_dialogs import FastDmChangeColumn
import numpy as np
import tracksave


class FastDmClickableEntry(QLineEdit):
    """Inherit from line edit so mousePressEvent can be re-implemented"""
    def __init__(self, text, isReadOnly, focusPolicy, callback, parent=None):
        super(FastDmClickableEntry, self).__init__(parent)

        self.setText(text)
        self.setReadOnly(isReadOnly)
        self.setFocusPolicy(focusPolicy)
        self.callback = callback

    def mousePressEvent(self, QMouseEvent):

        self.callback()

        QLineEdit.mousePressEvent(self, QMouseEvent)


class FastDmRtWidget(QWidget):

    normalColumnColor = QColor(35, 38, 41)
    timeColor = QColor(40, 115, 153)
    responseColor = QColor(40, 115, 153)

    def __init__(self, model, table, key, txt, parent=None):
        super(FastDmRtWidget, self).__init__(parent)

        self._model = model
        self._table = table
        self.key = key
        self._txt = txt
        self._edit = None
        self._setButton = None
        self._customizeLayout(QHBoxLayout())

    def _customizeLayout(self, layout):
        """Initialize components and layout."""

        # Create line edit
        self._edit = FastDmClickableEntry('', True, Qt.NoFocus, self._onClick)

        if self.key == 'RESPONSE':
            self._edit.setPlaceholderText('Click to set Response...')
        else:
            self._edit.setPlaceholderText('Click to set Reaction Time...')
        self._edit.setToolTip('Configure ' + self._txt + ' column')
        self._edit.setStatusTip('Configure ' + self._txt + ' column')

        # Create button
        self._setButton = QToolButton()
        self._setButton.setIcon(QIcon("./icons/varparam.png"))
        self._setButton.clicked.connect(self._onClick)
        self._setButton.setToolTip('Configure ' + self._txt + ' column')
        self._setButton.setStatusTip('Configure ' + self._txt + ' column')

        # Create layout
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._edit)
        # Do not set button
        #layout.addWidget(self._setButton)
        self.setLayout(layout)

    def _onClick(self):
        """Checks if there is data and pops up a dialog to select columns, if any data."""

        if self._model.session['datafiles']:
            self._openDialog()

    def _openDialog(self):
        """Pops up a dialog to ask for reaction time and response columns."""

        self._edit.blockSignals(True)

        # Start a modal dialog
        dialog = FastDmChangeColumn(self._model, self.key, 'Set ' + self._txt + ' Column...', self)
        dialog.exec_()

        # Check if dialog accepted (ok clicked)
        if dialog.accepted:
            # Modify save flag
            tracksave.saved = False

            # Check if index changed
            if self._model.session[self.key]['idx'] != dialog.checked:

                # Check if reset clicked
                if dialog.checked['idx'] is None:
                    self._clearPreviousHighlight()
                # Reset not clicked
                else:
                    # Try calculating maximum of column, TypeError is thrown, if column is non numeric
                    try:
                        data = np.genfromtxt(self._model.session['datafiles'][0], skip_header=True)
                        if data[dialog.checked['idx']].max() > 121:
                            msg = QMessageBox()
                            text = 'Some reaction times of column {} appear to be very large. Note, that ' \
                                   'fast-dm works with reaction times in seconds, not milliseconds.'.format(
                                self._model.session['columns'][dialog.checked['idx']])
                            msg.information(self.parent(), 'Suspicious reaction time range...', text)

                    # Column non-numeric, give error and reset
                    except TypeError:
                        msg = QMessageBox()
                        text = 'Could not set {} as TIME. Reaction time column must be numeric!'.\
                            format(self._model.session['columns'][dialog.checked['idx']])
                        msg.critical(self.parent(), 'Error setting time...', text)
                        return

                    self._addNewAndHighlight(dialog)

        self._edit.blockSignals(False)

    def _clearPreviousHighlight(self):
        """Clears previous, entry in model, lineedit, and table."""

        # Clear previous highlight, if any
        if self._model.session[self.key]['idx'] is not None:
            # Clear name and idx
            self._changeColumnColor(self.normalColumnColor)
            self._model.session[self.key]['name'] = None
            self._model.session[self.key]['idx'] = None
            self._edit.setText('')

    def _addNewAndHighlight(self, dialog):
        """Apply changes to model, lineedit, and table."""

        # Change color of old column back to unselected, if any
        if self._model.session[self.key]['idx'] is not None:
            self._changeColumnColor(self.normalColumnColor)

        # Add text to edit
        self._edit.setText(self._model.session['columns'][dialog.checked['idx']])

        # Add column name and idx to model
        self._model.session[self.key]['name'] = self._edit.text()
        self._model.session[self.key]['idx'] = dialog.checked['idx']

        # Change color ot new column to selected
        if self.key == 'RESPONSE':
            self._changeColumnColor(self.responseColor)
        else:
            self._changeColumnColor(self.timeColor)

    def _changeColumnColor(self, color):
        """Changes color of current index."""

        self._table.changeColor(self._model.session[self.key]['idx'], color)

    def updateEntry(self):
        """Updates the column entry."""

        if self._model.session[self.key]['name'] is not None:
            self._edit.setText(self._model.session[self.key]['name'])
        else:
            self._edit.setText('')


class FastDmRtSpecifier(QScrollArea):
    def __init__(self, model, table, parent=None):
        super(FastDmRtSpecifier, self).__init__(parent)

        self._model = model
        self._table = table
        self._time = None
        self._response = None
        self._initSpecifier(QGridLayout())

    def _initSpecifier(self, layout):
        """Initializes and configures the specifier."""

        # Create widgets
        self._time = FastDmRtWidget(self._model, self._table, 'TIME', 'reaction times')
        self._response = FastDmRtWidget(self._model, self._table, 'RESPONSE', 'response')
        timeLabel = QLabel('Reaction Time Column ')
        responseLabel = QLabel('Response Column ')

        # Add widgets to frame
        layout.addWidget(timeLabel, 0, 0)
        layout.addWidget(responseLabel, 1, 0)
        layout.addWidget(self._time, 0, 1)
        layout.addWidget(self._response, 1, 1)

        # Add dummy widget to push widgets to top
        dummy = QWidget()
        dummy.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(dummy, 2, 0, 1, 2)

        # Create content widget
        content = QWidget()
        content.setLayout(layout)
        self.setWidget(content)
        self.setWidgetResizable(True)

    def updateEntries(self):
        """Called externally to update time and response entires."""

        self._time.updateEntry()
        self._response.updateEntry()
