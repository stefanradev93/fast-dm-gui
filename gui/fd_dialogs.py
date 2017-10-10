from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class FastDmParamCheck(QCheckBox):

    def __init__(self, column, depends, parent=None):
        super(FastDmParamCheck, self).__init__(parent)

        self._column = column
        self.dependsList = depends
        self.toggled[bool].connect(self._onToggle)

    def _onToggle(self, checked):
        """Appends or removes current column from depends list."""

        if checked:
            self.dependsList.append(self._column)
        else:
            self.dependsList.remove(self._column)


class FastDmColumnCheck(QCheckBox):

    def __init__(self, idx, checked, group, parent=None):
        super(FastDmColumnCheck, self).__init__(parent)

        self._idx = idx
        self._checked = checked
        self._group = group
        self.toggled[bool].connect(self._onToggle)

    def _onToggle(self, checked):
        """Adds or removes checked column."""

        if checked:
            self._checked['idx'] = self._idx
        else:
            self._checked['idx'] = None


class FastDmVarParamDialog(QDialog):
    """
    Represents a pop-up for adding a response.
    """

    def __init__(self, model, key, parent=None):
        super(FastDmVarParamDialog, self).__init__(parent)

        self._key = key
        self._model = model
        self.depends = []
        self.accepted = False

        self._initDialog()

    def _initDialog(self):
        """Configures dialog."""

        # Set title
        self.setWindowTitle('Set Dependent Conditions...')

        # Create layout
        dialogLayout = QVBoxLayout()

        # Create a group box and buttons box
        groupBox = self._createGroupBox()
        buttonsBox = self._createButtonsBox()

        # Set layout
        dialogLayout.addWidget(groupBox)
        dialogLayout.addWidget(buttonsBox)
        self.setLayout(dialogLayout)
        self.adjustSize()

    def _createGroupBox(self):
        """Creates the parameter checkboxes and sets them accordingly."""

        boxLayout = QVBoxLayout()
        groupBox = QGroupBox('Conditions')

        # Only if there are more than two columns we cna have depends
        if len(self._model.session['columns']) > 2:
            # Loop through columns
            for idx, column in enumerate(self._model.session['columns']):

                # Create check box
                checkBox = FastDmParamCheck(column, self.depends)

                # If parameter already depending on column, set to true
                if column in self._model.parameters[self._key]['depends']:
                    checkBox.setChecked(True)
                # If column set as RESPONSE or TIME, disable
                if idx == self._model.session['RESPONSE']['idx'] or \
                   idx == self._model.session['TIME']['idx']:
                    checkBox.setEnabled(False)
                # Add label to checkbox
                checkBox.setText(column)
                boxLayout.addWidget(checkBox)

        groupBox.setLayout(boxLayout)
        return groupBox

    def _createButtonsBox(self):
        """Creates the no and cancel buttons."""

        # Create OK and Cancel buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Reset,
            Qt.Horizontal)
        buttons.accepted.connect(self._onOk)
        buttons.rejected.connect(self._onCancel)
        buttons.button(QDialogButtonBox.Reset).clicked.connect(self._onReset)
        return buttons

    def _onOk(self):
        """
        Called when ok button of dialog clicked.
        Check if input ok, then destroy.
        """

        self.accepted = True
        self.close()

    def _onCancel(self):
        """Called when user presses cancel. Accepted stay as False."""

        self.close()

    def _onReset(self):
        """Called when user presses reset. Sets entry to None and depends to empty list."""

        self.depends = []
        self.accepted = True
        self.close()


class FastDmChangeColumn(QDialog):
    """
    Represents a pop-up for changing a column.
    """

    def __init__(self, model, key, title, parent=None):
        super(FastDmChangeColumn, self).__init__(parent)

        self._key = key
        self._model = model
        self.checked = {'idx': None}
        self.accepted = False

        self._initDialog(title)

    def _initDialog(self, title):
        """Configures dialog."""

        # Set title
        self.setWindowTitle(title)

        # Create layout
        dialogLayout = QVBoxLayout()

        # Create a group box and buttons box
        groupBox = self._createGroupBox()
        buttonsBox = self._createButtonsBox()

        # Set layout
        dialogLayout.addWidget(groupBox)
        dialogLayout.addWidget(buttonsBox)
        self.setLayout(dialogLayout)
        self.adjustSize()

    def _createGroupBox(self):
        """Creates the parameter checkboxes and sets them accordingly."""

        boxLayout = QVBoxLayout()
        groupBox = QGroupBox('Columns')

        # Make buttons exclusive, note tht group is member,
        # since we need to avoid it being garbage collected
        self.buttonGroup = QButtonGroup()
        self.buttonGroup.setExclusive(True)

        # Loop through column names
        for idx, column in enumerate(self._model.session['columns']):

                # Create check box
                checkBox = FastDmColumnCheck(idx, self.checked, self.buttonGroup)
                checkBox.setText(column)

                # If column for current already set, set checked:
                if self._model.session[self._key]['name'] == column:
                    checkBox.setChecked(True)
                    self.checked['checked'] = self._model.session[self._key]['idx']

                # If column for other set, make this checkbox disabled
                if self._key == 'RESPONSE':
                    if idx == self._model.session['TIME']['idx']:
                        checkBox.setEnabled(False)
                else:
                    if idx == self._model.session['RESPONSE']['idx']:
                        checkBox.setEnabled(False)

                # If is set as condition, disable
                if self._isCondition(column):
                    checkBox.setEnabled(False)
                    checkBox.setText(column + ' (condition)')

                # Add checkbox to layout
                self.buttonGroup.addButton(checkBox, idx)
                boxLayout.addWidget(checkBox)

        groupBox.setLayout(boxLayout)
        return groupBox

    def _isCondition(self, column):
        """
        Accepts a column name from all available, returns True if column 
        is set as condition, False otherwise
        """

        for _, values in self._model.parameters.items():
            if column in values['depends']:
                return True
        return False

    def _createButtonsBox(self):
        """Creates the no and cancel buttons."""

        # Create OK and Cancel buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Reset,
            Qt.Horizontal)
        buttons.accepted.connect(self._onOk)
        buttons.rejected.connect(self._onCancel)
        buttons.button(QDialogButtonBox.Reset).clicked.connect(self._onReset)

        return buttons

    def _onOk(self):
        """
        Called when ok button of dialog clicked.
        Check if input ok, then destroy.
        """

        self.accepted = True
        self.close()

    def _onCancel(self):

        self.close()

    def _onReset(self):
        """
        Called when reset button of dialog clicked.
        Sets selected index to None and returns to caller.
        """

        self.checked['idx'] = None
        self.accepted = True
        self.close()


class FastDmLoading(QDialog):

    def __init__(self, parent=None):
        super(FastDmLoading, self).__init__(parent, Qt.FramelessWindowHint)

        self._initDialog()

    def _initDialog(self):
        """Initializes layout and behavior of dialog."""

        # ===== Configure focus policy ===== #
        self.setFocusPolicy(Qt.NoFocus)
        self.setFocus(False)

        # ===== Create movie parameters ===== #
        movieLabel = QLabel()
        self._movie = QMovie('./icons/loading.gif')
        movieLabel.setMovie(self._movie)

        # ===== Create layout ===== #
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(movieLabel)
        self.setLayout(layout)

    def showWheel(self):
        """Used to start loading animation."""

        self._movie.start()
        self.show()

    def hideWheel(self):

        self._movie.stop()
        self.hide()
