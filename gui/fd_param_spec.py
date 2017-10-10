from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from fd_dialogs import FastDmVarParamDialog
from fd_par_helper_texts import helperTexts
from fd_rt_spec import FastDmClickableEntry
import tracksave


class FastDmSpinBox(QDoubleSpinBox):

    def __init__(self, model, key, spinRange, type='est', parent=None):
        """A custom utility spinbox class."""

        super(FastDmSpinBox, self).__init__(parent)

        self._model = model
        self.key = key
        self.setMinimum(spinRange[0])
        self.setMaximum(spinRange[1])
        self.setSingleStep(spinRange[2])
        self._type = type
        self.valueChanged[float].connect(self._onSpin)

    def _onSpin(self, val):
        """Update value of parameter in model."""

        if self._type == 'est':
            # Try to overwrite parameters dict
            self._model.parameters[self.key]['val'] = round(val, 2)
        else:
            # If this happens, we are modifying simulation dict
            self._model.simParameters[self.key] = round(val, 2)

        # Modify save flag
        tracksave.saved = False


class FastDmCheckBox(QWidget):

    def __init__(self, key, model, widgets, parent=None):
        """A custom utility spinbox class."""

        super(FastDmCheckBox, self).__init__(parent)

        self.key = key
        self._model = model
        self._checkBox = None
        self._widgets = widgets
        self._configureLayout()

    def _configureLayout(self):
        """Creates a checkbox with a horizontal layout and centers it."""

        self._checkBox = QCheckBox()
        self._checkBox.toggled[bool].connect(self._onToggle)
        self._checkBox.setStyleSheet("spacing: 0px;")
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._checkBox)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def _onToggle(self, checked):
        """
        Sets the fixed property of parameter to either True or False 
        and changes state of other widgets on same row.
        """

        # Configure spinbox (idx 0) and specifier (idx 1)
        self._widgets[0].setEnabled(checked)
        self._widgets[1].setEnabled(not checked)
        # Modify model
        self._model.parameters[self.key]['fix'] = checked
        # Modify save flag
        tracksave.saved = False

    def setChecked(self, checked):
        """Used to call set checked on the checkbox."""

        self._checkBox.setChecked(checked)


class FastDmVariableParameter(QWidget):

    lineWidth = 300

    def __init__(self, model, key, parent=None):
        super(FastDmVariableParameter, self).__init__(parent)

        self._model = model
        self.key = key
        self._edit = None
        self._setButton = None
        self._customizeLayout()

    def _customizeLayout(self):
        """Initialize components and layout."""

        # Create a size policy to widget take sup whole cell
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Create line edit and button
        self._edit = FastDmClickableEntry('None', True, Qt.NoFocus, self._onClick)
        self._edit.setFixedWidth(FastDmVariableParameter.lineWidth)
        self._edit.setSizePolicy(sizePolicy)

        self._setButton = QToolButton()
        self._setButton.setIcon(QIcon("./icons/varparam.png"))
        self._setButton.setSizePolicy(sizePolicy)
        self._setButton.clicked.connect(self._onClick)
        self._setButton.setToolTip('Configure parameter dependency')
        self._setButton.setStatusTip('Configure parameter dependency')

        # Create layout
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._edit)
        layout.addWidget(self._setButton)
        self.setLayout(layout)

    def _onClick(self):
        """Pops up a dialog to ask for conditional parameters."""

        if len(self._model.session['columns']) <= 2:
            return
        if self._model.dataFilesLoaded():

            # Open dialog
            dialog = FastDmVarParamDialog(self._model, self.key, self)
            dialog.exec_()

            # If dialog was accepted, update parameters and list
            if dialog.accepted:
                self._model.parameters[self.key]['depends'] = dialog.depends
                self.updateEntry(dialog.depends if dialog.depends else None)
                # Modify save flag
                tracksave.saved = False

    def updateEntry(self, depends):
        """Updates the table depends entry."""

        if depends:
            self._edit.setText(','.join(depends))
        else:
            self._edit.setText('None')


class FastDmParameterSpec(QTableWidget):

    def __init__(self, model, rows, columns, parent=None):
        """A class to specify variable parameters."""
        super(FastDmParameterSpec, self).__init__(parent)

        self._model = model
        self._rows = rows
        self._columns = columns
        self._configureLayout()
        self._initSpec()

    def _initSpec(self):
        """Initializes settings of parameter specifier."""

        # Disable focusable pane
        self.setFocusPolicy(Qt.NoFocus)
        # Disable editing
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # Disable selection
        self.setSelectionMode(QAbstractItemView.NoSelection)
        # Disable resizing columns
        for i in range(self._columns):
            self.horizontalHeader().setSectionResizeMode(i, QHeaderView.Fixed)

    def _getParTexts(self):
        """Returns a list of parameter descriptions in order."""

        return ['Threshold Separation (\U0001D44E)',
                'Relative Starting Point (\U0001D467\U0001D45F)',
                'Drift (\U0001D463)',
                'Response Time Constant (\U0001D461\u2080)',
                'Difference in Speed of Response Execution (\U0001D451)',
                'Intertrial-variability of \U0001D467\U0001D45F (s\U0001D467\U0001D45F)',
                'Intertrial-variability of \U0001D463 (s\u1D65)',
                'Intertrial-variability of \U0001D461\u2080 (s\U0001D461\u2080)',
                'Percentage of Contaminants (\U0001D45D)']

    def _getParRanges(self):
        """Returns a list of parameter ranges in order."""

        return [(0., 100000, 0.1),
                (0., 1.0, 0.1),
                (-100000., 100000., 0.1),
                (0., 100000., 0.1),
                (-100000., 100000., 0.1),
                (0., 100000., 0.1),
                (0., 100000., 0.1),
                (0., 100000., 0.1),
                (0., 1., 0.1)]

    def _configureLayout(self):

        """Creates the main grid of the layout."""

        parTexts = self._getParTexts()
        # Start, stop, step
        ranges = self._getParRanges()

        self.setColumnCount(self._columns)
        self.setRowCount(self._rows)

        # Create header labels
        headerTexts = ['Parameter Name', 'Parameter Value', 'Fixed', 'Varies by Condition(s)']
        self.setHorizontalHeaderLabels(headerTexts)
        self.verticalHeader().hide()

        # Populate table
        for idx, text in enumerate(parTexts):

            # ----- Create Items ----- #
            item = QTableWidgetItem(text)
            item.setToolTip(helperTexts[idx])
            paramSpec = FastDmVariableParameter(self._model,
                            list(self._model.parameters.keys())[idx])
            spinBox = FastDmSpinBox(self._model,
                                    list(self._model.parameters.keys())[idx],
                                    ranges[idx], type='est')
            checkBox = FastDmCheckBox(list(self._model.parameters.keys())[idx],
                                           self._model,
                                          (spinBox, paramSpec))

            # ----- Add Items ----- #
            self.setItem(idx, 0, item)
            self.setCellWidget(idx, 1, spinBox)
            self.setCellWidget(idx, 2, checkBox)
            self.setCellWidget(idx, 3, paramSpec)

        self.resizeColumnsToContents()

    def updateWidgets(self):
        """Called externally to update widgets according to model values."""

        for i in range(self._rows):

            # ===== Update checkboxes ===== #
            check = self.cellWidget(i, 2)

            check.setChecked(self._model.parameters[check.key]['fix'])
            # ===== Update spinboxes ===== #
            spin = self.cellWidget(i, 1)
            spin.setValue(self._model.parameters[spin.key]['val'])
            spin.setEnabled(self._model.parameters[spin.key]['fix'])

            # ===== Update depends ===== #
            depend = self.cellWidget(i, 3)
            depend.updateEntry(self._model.parameters[depend.key]['depends'])
            depend.setEnabled(not self._model.parameters[depend.key]['fix'])


class FastDmParameterSpecSim(FastDmParameterSpec):

    def __init__(self, model, rows, columns, parent=None):
        """A class to specify variable parameters."""
        super(FastDmParameterSpecSim, self).__init__(model, rows, columns, parent)

    def _configureLayout(self):
        """Creates the main grid of the layout."""

        # Get texts and ranges
        parTexts = self._getParTexts()
        ranges = self._getParRanges()

        # Set column and row count
        self.setColumnCount(self._columns)
        self.setRowCount(self._rows)

        # Create header labels
        headerTexts = ['Parameter Name', 'Parameter Value']
        self.setHorizontalHeaderLabels(headerTexts)
        self.verticalHeader().hide()

        # Get parameter names (keys)
        parameterNames = list(self._model.simParameters.keys())

        # Populate table
        for idx, text in enumerate(parTexts):

            # ----- Create Items ----- #
            item = QTableWidgetItem(text)
            item.setToolTip(helperTexts[idx])

            spinBox = FastDmSpinBox(self._model,
                                    parameterNames[idx],
                                    ranges[idx], type='sim')

            # ----- Add Items ----- #
            self.setItem(idx, 0, item)
            self.setCellWidget(idx, 1, spinBox)

        self.resizeColumnsToContents()

    def updateWidgets(self):
        """Called externally to update widgets according to model values."""

        for i in range(self._rows):
            # ===== Update spin boxes ===== #
            spin = self.cellWidget(i, 1)
            spin.setValue(self._model.simParameters[spin.key])







