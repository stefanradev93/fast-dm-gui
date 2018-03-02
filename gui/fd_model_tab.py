from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QThread, QTimer
from fd_param_spec import FastDmParameterSpec, FastDmParameterSpecSim
from fd_tab_controller import FastDmTabController
from fd_binary_handlers import *
from multiprocessing import cpu_count
import tracksave
from functools import partial
import re


class FastDmModelTab(QWidget):

    def __init__(self, model, console, status, parent=None):
        """The main container for the the model tab."""

        super(FastDmModelTab, self).__init__(parent)

        self._model = model
        self._console = console
        self._status = status
        self._analysisFrame = None
        self._simulationFrame = None

        self._initTab()
        self.updateWidgets()

    def _initTab(self):

        self._configureLayout(QHBoxLayout())

    def _configureLayout(self, layout):
        """Initializes widgets and sets the main layout of the tab."""

        # Create parameters and run frame for analysis frame
        self._parFrameAnalysis = FastDmParameterSpec(self._model, rows=9, columns=4)
        self._runFrameAnalysis = FastDmRunFrame(self._model, self._console, self._status)
        # Create analysis frame
        self._analysisFrame = FastDmMainFrame(self._parFrameAnalysis, self._runFrameAnalysis)

        # Create parameters and run frame for simulation frame
        self._parFrameSim = FastDmParameterSpecSim(self._model, rows=9, columns=2)
        self._runFrameSim = FastDmRunFrameSim(self._model, self._console, self._status)

        # Create simulation frame
        self._simulationFrame = FastDmMainFrame(self._parFrameSim, self._runFrameSim)

        # Create tab controller
        tabSettings = [(self._analysisFrame, 'Analysis', 0, './icons/analysis.png'),
                       (self._simulationFrame, 'Simulation', 1, 'icons/simulation.png')]
        self._tabController = FastDmTabController(tabSettings)
        self._tabController.setTabPosition(QTabWidget.South)

        # Configure layout
        layout.addWidget(self._tabController)
        self.setLayout(layout)

    def updateWidgets(self):
        """Called to update the widgets values with the actual values from model."""

        self._analysisFrame.updateWidgets()
        self._simulationFrame.updateWidgets()


class FastDmMainFrame(QWidget):
    """Represents the analysis frame as a whole."""

    def __init__(self, leftFrame, rightFrame, parent=None):
        super(FastDmMainFrame, self).__init__(parent)

        # Add main frames
        self._leftFrame = leftFrame
        self._rightFrame = rightFrame
        self._configureFrame(QGridLayout())

    def _configureFrame(self, layout):
        """Configures the layout of the frame."""

        layout.addWidget(self._leftFrame, 0, 0, 1, 1)
        layout.addWidget(self._rightFrame, 0, 1, 1, 1)
        layout.setColumnStretch(0, 3)
        layout.setColumnStretch(1, 2)
        self.setLayout(layout)
        self.adjustSize()

    def updateWidgets(self):
        """Called to update the widgets values with the actual values from model."""

        self._leftFrame.updateWidgets()
        self._rightFrame.updateWidgets()


class FastDmOutputDirFrame(QWidget):
    STRING_PATTERN = r"^[0-9A-Za-z_-]+$"

    def __init__(self, session, parent=None):
        super(FastDmOutputDirFrame, self).__init__(parent)

        self._session = session
        self._edit = None
        self._button = None
        self._initFrame(QHBoxLayout())

    def _initFrame(self, layout):
        """Creates and sets the layout."""

        # Create Group Box
        box = QGroupBox("Output Settings")
        boxLayout = QHBoxLayout()

        # Create edit for path
        self._edit = QLineEdit()
        self._edit.setPlaceholderText('Output location...')
        self._edit.textChanged.connect(self._onEdit)

        # Create edit for dir name (session name)
        self._name = QLineEdit()
        self._name.setPlaceholderText('Directory name...')
        self._name.textChanged.connect(self._onName)
        self._name.setMaximumSize(self._name.sizeHint())

        # Create button for dir
        self._button = QToolButton()
        self._button.setIcon(QIcon('./icons/load.png'))
        self._button.setToolTip('Select output directory...')
        self._button.setStatusTip('Select output directory...')
        self._button.clicked.connect(self._onOpen)

        # Configure layout
        boxLayout.addWidget(self._button)
        boxLayout.addWidget(self._edit)
        boxLayout.addWidget(self._name)

        box.setLayout(boxLayout)
        layout.addWidget(box)
        layout.setSpacing(0)

        self.setLayout(layout)

    def _onOpen(self):
        """Opens up a file dialog for choosing an output folder."""

        # Create file dialog
        open = QFileDialog()
        dirPath = open.getExistingDirectory(self, 'Select an Empty Output Directory...',
                                            '', QFileDialog.ShowDirsOnly)

        # If any path specified
        if dirPath:
            self._edit.setText(dirPath)
            self._session['outputdir'] = dirPath
            # Modify save flag
            tracksave.saved = False

    def _onEdit(self, text):
        """Triggered when user types into dir edit."""

        self._session['outputdir'] = text

    def _onName(self, text):
        """Triggered when user types into session edit."""

        if re.match(FastDmOutputDirFrame.STRING_PATTERN, text):
            self._session['sessionname'] = text.rstrip().lstrip()
            self._name.setText(self._session['sessionname'])
        else:
            # Revert to previous and warn
            self._name.setText(self._session['sessionname'])
            msg = QMessageBox()
            msg.warning(self, "Session Name Warning", "Make sure session name contains "
                                                      "only English characters, numbers, or the symbols '-_'")

    def updateDirName(self, newSession):
        """
        Called externally to update dir name from model.
        Note, that since this frame has only a reference to 
        the sim parameters and not the whole model, we also need to update
        the reference to point to the new session dict.
        """

        self._session = newSession

        if self._session['outputdir']:
            self._edit.setText(self._session['outputdir'])
        if self._session['sessionname']:
            self._name.setText(self._session['sessionname'])


class FastDmComputationFrame(QWidget):

    def __init__(self, model, console, parent=None):

        super(FastDmComputationFrame, self).__init__(parent)

        self._model = model
        self._console = console
        self._methodDrop = None
        self._jobsDrop = None
        self._precisionSpin = None
        self._checkBoxes = None
        self._maxJobs = getCpuCount(self._console)
        self._initFrame(QHBoxLayout())

    def _initFrame(self, layout):
        """Creates main components of frame."""

        # Create layouts and groups
        groupBox = QGroupBox('Computation')
        checkGroup = QGroupBox('Additional Settings')
        boxLayout = QGridLayout()
        checkLayout = QVBoxLayout()

        # Create method combo
        self._methodDrop = QComboBox()
        self._methodDrop.addItems(['Maximum Likelihood',
                                   'Kolmogorov-Smirnov',
                                   'Chi-Square'])
        self._methodDrop.currentIndexChanged.connect(self._onMethodChange)
        self._methodDrop.setStatusTip('Parameter estimation algorithm')
        self._methodDrop.setItemData(0,
                                     'Estimation with Maximum Likelihood:\n'
                                     'Recommended Number of Trials: Low (n<40)\n'
                                     'Speed of Estimation: Low (if inter-trial-variability parameters are included)\n'
                                     'Robustness: Low (strict outlier analysis necessary)',
                                     Qt.ToolTipRole)
        self._methodDrop.setItemData(1,
                                     'Estimation with Kolmogorov-Smirnov:\n'
                                     'Recommended Number of Trials: Medium (n>100)\n'
                                     'Speed of Estimation: Medium (Dependent on Trial Numbers)\n'
                                     'Robustness: High',
                                     Qt.ToolTipRole)
        self._methodDrop.setItemData(2,
                                     'Estimation with Chi-Square:\n'
                                     'Recommended Number of Trials: High (n>500)\n'
                                     'Speed of Estimation: High (Independent on Trial Numbers)\n'
                                     'Robustness: High',
                                     Qt.ToolTipRole)
        # Create jobs combo
        self._jobsDrop = QComboBox()
        self._jobsDrop.addItems([str(i) for i in range(1, self._maxJobs + 1)])
        self._jobsDrop.currentIndexChanged.connect(self._onJobsChange)
        self._jobsDrop.setStatusTip('Number of CPU cores to use for computation')

        # Create precision spin
        self._precisionSpin = QDoubleSpinBox()
        self._precisionSpin.setRange(1.0, 5.0)
        self._precisionSpin.valueChanged.connect(self._onPrecisionChange)
        self._precisionSpin.setToolTip('Number of decimals of the predicted CDFs '
                                       'that are calculated accurately  ')
        self._precisionSpin.setStatusTip('Precision of calculation')

        # Create checkboxes
        self._checkBoxes = self._createCheckBoxes(['Save Control File',
                                                   'Calculate CDFs',
                                                   'Calculate Density'],
                                                  ['ctl', 'cdf', 'dens'])
        # Configure additional checkboxes box
        for box in self._checkBoxes:
            checkLayout.addWidget(box)
        checkGroup.setLayout(checkLayout)

        # Configure layout of group
        boxLayout.addWidget(QLabel('Method'), 0, 0)
        boxLayout.addWidget(self._methodDrop, 0, 1)
        boxLayout.addWidget(QLabel('CPU Cores'), 1, 0)
        boxLayout.addWidget(self._jobsDrop, 1, 1)
        boxLayout.addWidget(QLabel('Precision'), 2, 0)
        boxLayout.addWidget(self._precisionSpin, 2, 1)
        groupBox.setLayout(boxLayout)

        # Configure main layout
        layout.addWidget(groupBox)
        layout.addWidget(checkGroup)
        self.setLayout(layout)

    def _createCheckBoxes(self, texts, keys):
        """A Helper to create a list of checkboxes with appropriate callbacks."""

        checkBoxes = []
        for idx, text in enumerate(texts):
            checkBox = QCheckBox()
            checkBox.setText(text)
            checkBox.toggled[bool].connect(partial(self._onToggle, keys[idx]))
            checkBoxes.append(checkBox)
        return checkBoxes

    def _onMethodChange(self, idx):
        """Sets the method into the model."""
        if idx == 0:
            self._model.computation['method'] = 'ml'
        elif idx == 1:
            self._model.computation['method'] = 'ks'
        else:
            self._model.computation['method'] = 'cs'
        # Modify save flag
        tracksave.saved = False

    def _onJobsChange(self, idx):
        """Sets tje jobs number."""

        self._model.computation['jobs'] = int(idx) + 1
        # Modify save flag
        tracksave.saved = False

    def _onPrecisionChange(self, val):
        """Sets precision to specified value."""

        self._model.computation['precision'] = val
        # Modify save flag
        tracksave.saved = False

    def _onToggle(self, key, checked):
        """Changes save option."""

        self._model.save[key] = checked
        # Modify save flag
        tracksave.saved = False

    def updateWidgets(self):
        """Called externally to update widgets from model."""

        # Update checkboxes, order matters
        self._checkBoxes[0].setChecked(self._model.save['ctl'])
        self._checkBoxes[1].setChecked(self._model.save['cdf'])
        self._checkBoxes[2].setChecked(self._model.save['dens'])

        # Update method
        if self._model.computation['method'] == 'ml':
            self._methodDrop.setCurrentIndex(0)
        elif self._model.computation['method'] == 'ks':
            self._methodDrop.setCurrentIndex(1)
        else:
            self._methodDrop.setCurrentIndex(2)

        # Update jobs, -1, since indices begin with 0
        self._jobsDrop.setCurrentIndex(self._model.computation['jobs']-1)

        # Update precision
        self._precisionSpin.setValue(self._model.computation['precision'])


class FastDmExecuteFrame(QWidget):

        def __init__(self, model, console, status, parent=None):
            super(FastDmExecuteFrame, self).__init__(parent)

            self._model = model
            self._console = console
            self._status = status
            self._flag = {'run': False}
            self._run = None
            self._stop = None
            self._progress = None
            self._runHandler = None
            self._runThread = None
            self._cdfHandler = None
            self._cdfThread = None

            self._initFrame(QHBoxLayout())
            self._initRunHandler()
            self._initCdfHanlder()

        def _initFrame(self, layout):
            """Create buttons and configure frame."""

            # Create buttons
            self._run = self._createButton('Run', './icons/run', self._onRun,
                                           Qt.NoFocus, True)
            self._stop = self._createButton('Stop', './icons/stop', self._onStop,
                                           Qt.NoFocus, False)
            # Create progress bar
            self._progress = QProgressBar()
            self._progress.setOrientation(Qt.Horizontal)
            self._progress.hide()

            layout.addWidget(self._run)
            layout.addWidget(self._stop)
            layout.addStretch(0)
            layout.addWidget(self._progress)
            layout.setStretchFactor(self._progress, 3)
            self.setLayout(layout)

        def _createButton(self, label, iconPath, func, focusPolicy, enabled):
            """Utility to save typing"""

            button = QPushButton(label)
            button.setIcon(QIcon(iconPath))
            button.clicked.connect(func)
            button.setFocusPolicy(focusPolicy)
            button.setEnabled(enabled)
            return button

        def _initRunHandler(self):
            """Called when frame initialized, creates a run handler instance."""

            # Create a persistent model handler instance
            self._runHandler = FastDmRunHandler(self._model, self._flag)
            # Create a persistent thread instance
            self._runThread = QThread()
            # Move handler to thread (essentially moving run method)
            self._runHandler.moveToThread(self._runThread)
            # Connect signals
            # It is essential to connect the finished signal of the handler to the quit
            # method of the thread, otherwise it never returns!
            self._runHandler.finished.connect(self._runThread.quit)
            # Connect run handler signal to thread methods
            self._runHandler.progressUpdate.connect(self._updateProgress)
            self._runHandler.estimationStarting.connect(self._onRunStarting)
            self._runHandler.consoleLog.connect(self._onLog)
            # Connect thread signals to run handler methods
            self._runThread.started.connect(self._runHandler.run)
            self._runThread.finished.connect(self._onRunFinished)

        def _initCdfHanlder(self):
            """Called when frame initialized, initializes a cdf handler."""

            # Create a persistent model handler instance
            self._cdfHandler = FastDmCdfHanlder(self._model)
            # Create a persistent thread instance
            self._cdfThread = QThread()
            # Move handler to thread (essentially moving run method)
            self._cdfHandler.moveToThread(self._cdfThread)
            # Connect signals of cdf handler to thread methods
            self._cdfHandler.finished.connect(self._cdfThread.quit)
            self._cdfHandler.calculationStarting.connect(self._onCdfStarting)
            self._cdfHandler.consoleLog.connect(self._onErrorLog)
            # Connect thread signals to cdf methods
            self._cdfThread.started.connect(self._cdfHandler.run)
            self._cdfThread.finished.connect(self._onCdfFinished)

        def _onRunStarting(self):
            """Prepare buttons and progressbar for running."""

            self._console.write('\n----- STARTING ESTIMATION -----')
            self._status.changeStatus("Running fast-dm...")
            self._run.setEnabled(False)
            self._stop.setEnabled(True)
            self._progress.reset()
            self._progress.show()
            self._progress.setMaximum(len(self._model.session['datafiles']))

        def _onRunFinished(self):
            """Reset buttons and progress, and reset flag."""

            if self._runHandler.aborted:
                self._console.writeWarning('\n----- ESTIMATION ABORTED BY USER -----')

            elif self._runHandler.error:
                self._console.writeError('\n----- ESTIMATION ABORTED DUE TO ERROR -----')

            else:
                # Save control file, if specified
                self._saveCtl()
                # Calculate cdf, if specified by user
                if not self._model.save['cdf']:
                    self._console.write('\n----- ESTIMATION FINISHED -----')
                else:
                    self._calculateCdf()

            # Reset buttons and all
            self._flag['run'] = False
            self._run.setEnabled(True)
            self._stop.setEnabled(False)
            self._status.changeStatus("Done")
            self._runHandler.reset()

            # Hide progressbar after timeout
            # Set max of progressbar (since processes not writing correctly)
            QTimer.singleShot(5000, self._hideProgress)

        def _onCdfStarting(self):
            """Give verbose to user. Process very fast, so run right away."""

            # So fast that this isn't event necessary
            pass

        def _onCdfFinished(self):
            """Give verbose to user."""

            self._console.write('Cdf values stored in ' + self._model.session['outputdir'] + '/' +
                                self._model.session['sessionname'] + '/' + CDFDIR)
            self._console.write('\n----- ESTIMATION FINISHED -----')

        def _calculateCdf(self):
            """Called only if user did not abort run."""

            # If user has specified save cdf, predict and calc cdfs
            if self._model.save['cdf']:
                self._cdfThread.start()

        def _saveCtl(self):
            """Saves a control file, if specified."""

            if self._model.save['ctl']:
                filePath = self._runHandler.saveFileTemplate()
                self._console.write('Control file saved as ' + filePath)

        def _updateProgress(self, val):
            """Updates progress"""

            self._progress.setValue(val)

        def _hideProgress(self):
            """Hides progressbar after the specified timeout."""

            if not self._flag['run']:
                self._progress.reset()
                self._progress.hide()

        def _onRun(self):
            """Calls a run handler."""

            # If sanity checks passed, run fast-dm in a separate thread
            if checkModelSanity(self._model, self):
                self._runThread.start()

        def _onLog(self, txt):
            """Logs out to console fast-dm out."""

            self._console.write(txt)

        def _onErrorLog(self, txt):
            """Writes errors from threads to console."""

            self._console.writeError(txt)

        def _onStop(self):
            """Sets run flag to stop, thus notifying fast-dm thread to abort."""

            self._flag['run'] = False


class FastDmImageFrame(QWidget):

    def __init__(self, parent=None):
        """The main container for the model image."""
        super(FastDmImageFrame, self).__init__(parent)

        self._initImage(QHBoxLayout())

    def _initImage(self, layout):

        image = QLabel()
        image.setPixmap(QPixmap('./icons/temp_fd_pic.gif'))
        layout.addStretch(1)
        layout.addWidget(image)
        layout.addStretch(1)
        self.setLayout(layout)


class FastDmRunFrame(QScrollArea):
    """The main container for the analysis functionality."""
    def __init__(self, model, console, status, parent=None):

        super(FastDmRunFrame, self).__init__(parent)

        self._model = model
        self._outputFrame = FastDmOutputDirFrame(model.session)
        self._compFrame = FastDmComputationFrame(model, console)
        self._execFrame = FastDmExecuteFrame(model, console, status)
        self._initFrame(QVBoxLayout(self))

    def _initFrame(self, contentsLayout):
        """Creates all components and sets layout."""

        # Make sure run button is always visible
        self.ensureWidgetVisible(self._execFrame)
        # Add widgets to the inner layout
        contentsLayout.addWidget(self._outputFrame)
        contentsLayout.addWidget(self._compFrame)
        contentsLayout.addWidget(self._execFrame)
        # We don't use the image frame anymore
        #contentsLayout.addWidget(FastDmImageFrame())
        contentsLayout.addSpacing(1)
        content = QWidget()
        content.setLayout(contentsLayout)

        # Place inner widget inside the scrollable area
        self.setWidget(content)
        self.setWidgetResizable(True)

    def updateWidgets(self):
        """Called externally to update widget values."""

        self._outputFrame.updateDirName(self._model.session)
        self._compFrame.updateWidgets()


class FastDmRunFrameSim(QScrollArea):
    """The main container for the simulation functionality."""

    def __init__(self, model, console, status, parent=None):
        super(FastDmRunFrameSim, self).__init__(parent)

        self._model = model
        self._outputFrame = FastDmOutputDirFrame(model.simOptions)
        self._optionsFrame = FastDmOptionsFrameSim(model)
        self._execFrame = FastDmExecuteFrameSim(model, console, status)

        self._initFrame(QVBoxLayout(self))

    def _initFrame(self, contentsLayout):
        """Configures the layout of the simulation frame."""

        # make sure run button is always visible
        self.ensureWidgetVisible(self._execFrame)
        # Add widgets to the inner layout
        contentsLayout.addWidget(self._outputFrame)
        contentsLayout.addWidget(self._optionsFrame)
        contentsLayout.addWidget(self._execFrame)
        # we don't use the image frame anymore
        #contentsLayout.addWidget(FastDmImageFrame())
        contentsLayout.addSpacing(1)
        content = QWidget()
        content.setLayout(contentsLayout)

        # Place inner widget inside the scrollable area
        self.setWidget(content)
        self.setWidgetResizable(True)

    def updateWidgets(self):
        """Called externally, updates simulation options."""

        self._outputFrame.updateDirName(self._model.simOptions)
        self._optionsFrame.updateWidgets()


class FastDmOptionsFrameSim(QWidget):
    """Groups together all simulation options"""

    def __init__(self, model, parent=None):
        super(FastDmOptionsFrameSim, self).__init__(parent)

        self._model = model
        self._initFrame(QVBoxLayout())

    def _initFrame(self, layout):
        """Initializes the main components of the frame."""

        # Create Group Box
        groupBox = QGroupBox("Simulation Settings")
        boxLayout = QGridLayout()

        # Create spin boxes
        self._precisionBox = self._createSpinBox((1.0, 5.0, 1), 'self._onPrecision',
                                                 key='precision', floating=True)
        self._trialNumBox = self._createSpinBox((1, 100000000, 10),
                                                'self._onTrialNum', key='ntrials')
        self._numDataSetsBox = self._createSpinBox((1, 10000000, 1),
                                                   'self._onNumDataSets', key='nsamples')
        # Create deterministic check box
        self._deterministicBox = QCheckBox()
        self._deterministicBox.setText('Create a Deterministic Sample')
        self._deterministicBox.toggled.connect(self._onDeterministic)

        # Define some label texts
        labelTexts = ('Precision', 'Number of Trials', 'Number of Data Sets')
        spinBoxes = (self._precisionBox, self._trialNumBox, self._numDataSetsBox)

        # Add all to box layout
        for idx, box in enumerate(spinBoxes):
            boxLayout.addWidget(QLabel(labelTexts[idx]), idx, 0)
            boxLayout.addWidget(box, idx, 1)
        boxLayout.addWidget(self._deterministicBox, idx+1, 1)

        # Configure layouts
        groupBox.setLayout(boxLayout)
        layout.addWidget(groupBox)
        self.setLayout(layout)

    def _createSpinBox(self, spinRange, func, key=None, floating=False):
        """Utility function to simplify creation of spinboxes."""

        if floating:
            spin = QDoubleSpinBox()
        else:
            spin = QSpinBox()
        spin.setRange(spinRange[0], spinRange[1])
        spin.setSingleStep(spinRange[2])
        spin.setValue(self._model.simOptions[key])
        spin.valueChanged.connect(eval(func))
        return spin

    def _onPrecision(self, val):
        """Activated when precision spinbox moved."""

        self._model.simOptions['precision'] = round(val, 2)
        tracksave.saved = False

    def _onTrialNum(self, val):
        """Activated when trial num spinbox moved."""

        self._model.simOptions['ntrials'] = val
        tracksave.saved = False

    def _onNumDataSets(self, val):
        """Activated when num datasets spinbox moved."""

        self._model.simOptions['nsamples'] = val
        tracksave.saved = False

    def _onDeterministic(self, selected):
        """Activated when user chooses a deterministic sample."""

        self._numDataSetsBox.setEnabled(not selected)
        self._model.simOptions['determ'] = selected

    def updateWidgets(self):
        """Called externally, updates widgets according to model."""

        self._precisionBox.setValue(self._model.simOptions['precision'])
        self._trialNumBox.setValue(self._model.simOptions['ntrials'])
        self._numDataSetsBox.setValue(self._model.simOptions['nsamples'])
        self._deterministicBox.setChecked(self._model.simOptions['determ'])


class FastDmExecuteFrameSim(QWidget):
    """Main container and initializer of simulation."""

    def __init__(self, model, console, status, parent=None):
        super(FastDmExecuteFrameSim, self).__init__(parent)

        self._model = model
        self._console = console
        self._status = status
        self._run = None
        self._stop = None
        self._progress = None
        self._flag = {'run': False}
        self._simHandler = None
        self._simThread = None

        self._initFrame(QHBoxLayout())
        self._initRunHandler()

    def _initFrame(self, layout):
        """Create buttons and configure frame."""

        # Create buttons
        self._run = self._createButton('Run', './icons/run', self._onRun,
                                       Qt.NoFocus, True)
        self._stop = self._createButton('Stop', './icons/stop', self._onStop,
                                       Qt.NoFocus, False)
        # Create progress bar
        self._progress = QProgressBar()
        self._progress.setOrientation(Qt.Horizontal)
        self._progress.hide()

        layout.addWidget(self._run)
        layout.addWidget(self._stop)
        layout.addStretch(0)
        layout.addWidget(self._progress)
        layout.setStretchFactor(self._progress, 3)
        self.setLayout(layout)

    def _createButton(self, label, iconPath, func, focusPolicy, enabled):
        """Utility to save typing"""

        button = QPushButton(label)
        button.setIcon(QIcon(iconPath))
        button.clicked.connect(func)
        button.setFocusPolicy(focusPolicy)
        button.setEnabled(enabled)
        return button

    def _initRunHandler(self):
        """Called when frame initialized, creates a run simulation handler instance."""

        # Create a persistent model handler instance
        self._simHandler = FastDmSimHandler(self._model, self._flag)
        # Create a persistent thread instance
        self._simThread = QThread()
        # Move handler to thread (essentially moving run method)
        self._simHandler.moveToThread(self._simThread)
        # Connect signals
        # It is essential to connect the finished signal of the handler to the quit
        # method of the thread, otherwise it never returns!
        self._simHandler.finished.connect(self._simThread.quit)
        self._simHandler.consoleLog.connect(self._onLog)
        # Connect run handler signal to thread methods
        self._simHandler.simulationStarting.connect(self._onSimStarting)
        # Connect thread signals to run handler methods
        self._simThread.started.connect(self._simHandler.run)
        self._simThread.finished.connect(self._onSimFinished)

    def _onRun(self):
        """Runs a simulation."""

        # If sanity checks passed, run fast-dm in a separate thread
        if checkSimulationSanity(self._model, self):
            self._simThread.start()

    def _onStop(self):
        """Set run flag to stop and notify simulation to abort."""

        self._flag['run'] = False

    def _onSimStarting(self):
        """Called when simulation starting signal emitted from sim thread."""

        # Give some verbose
        self._console.write('\n----- STARTING SIMULATION -----')
        self._console.write('Simulating ' + str(self._model.simOptions['nsamples']) +
                            ' data files' + ' in ' + self._model.simOptions['outputdir'] + '/' +
                            self._model.simOptions['sessionname'] + ' ...')
        # Change status
        self._status.changeStatus('Running simulation...')

        # Start progress bar
        self._progress.show()
        self._progress.setMinimum(0)
        self._progress.setMaximum(0)

        # Disable run button, enable stop button
        self._run.setEnabled(False)
        self._stop.setEnabled(True)

    def _onSimFinished(self):
        """Called when simulation has finished or user has aborted."""

        # If aborted, notify and restore flag
        if self._simHandler.aborted:
            self._console.write('\n----- SIMULATION ABORTED BY USER -----')
            self._simHandler.aborted = False
        else:
            self._console.write('\n----- SIMULATION FINISHED -----')

        # Restore flag and buttons
        self._flag['run'] = False
        self._run.setEnabled(True)
        self._stop.setEnabled(False)
        self._status.changeStatus("Done")
        self._progress.hide()

    def _onLog(self, txt):
        """Give verbose to console."""

        self._console.write(txt)


def getCpuCount(console):
    """
    A helper method to return the number 
    of CPU cores on current machine.
    """

    try:
        count = cpu_count()
        console.write('...Determined number of available (logical) CPUs on this machine: ' + str(count))
        return count
    except NotImplementedError:
        console.write('...Could not determine number of available CPUs on this machine.')
        return 1
