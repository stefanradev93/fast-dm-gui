from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QThread, QObject, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from fd_dialogs import FastDmLoading
import matplotlib.pyplot as plt
import numpy as np
import tracksave


class FastDmPlotter(QObject):

    finished = pyqtSignal()

    def __init__(self, model, figure, canvas, parent=None):
        super(FastDmPlotter, self).__init__(parent)

        self._model = model
        self.newScreen = False
        self.figure = figure
        self.canvas = canvas
        self.fileIndexes = None

    def run(self):
        """The method that is run in a separate thread."""

        self.plot()
        self.finished.emit()

    def plot(self):
        """Run in a separate thread."""

        # Clear figure
        self.figure.clear()
        # Adjust spacing
        self.figure.subplots_adjust(hspace=.1, wspace=.1)
        # Determine number of subplots to draw
        rows, cols = self._getNumSubPlots()

        # Create subplots in a loop
        for subi, idx in enumerate(self.fileIndexes):
            # Add subplot
            ax = self.figure.add_subplot(rows, cols, subi + 1)

            # Load data and unpack it neatly without nans
            data = np.genfromtxt(self._model.plot['cdffiles'][idx], skip_header=True)
            empX = data[:, 0][~np.isnan(data[:, 0])]
            empY = data[:, 1][~np.isnan(data[:, 1])]
            predX = data[:, 2][~np.isnan(data[:, 2])]
            predY = data[:, 3][~np.isnan(data[:, 3])]

            # Set y axes ticks
            ax.yaxis.set_ticks([0.2, 0.4, 0.6, 0.8, 1.0])

            # Change color of axes
            # ax.set_facecolor('#686868')
            # ax.spines['bottom'].set_color('#F0F0F0')
            # ax.spines['top'].set_color('#F0F0F0')
            # ax.spines['right'].set_color('#F0F0F0')
            # ax.spines['left'].set_color('#F0F0F0')

            # # Move left y-axis and bottim x-axis to centre, passing through (0,0)
            ax.spines['left'].set_position('center')
            ax.spines['bottom'].set_position('zero')
            # Eliminate upper and right axes
            ax.spines['right'].set_color('none')
            ax.spines['top'].set_color('none')
            # Tweak ticks a little bit more
            ax.xaxis.set_tick_params(bottom='on', top='off', direction='out')
            ax.yaxis.set_tick_params(left='on', right='off', direction='out')

            # Add text (which participant)
            ax.text(np.max(empX) / 2 if np.max(empX) > np.max(predX) else np.max(predX) / 2,
                    0.5, self._model.plot['cdffiles'][idx].split('/')[-1], size=12)

            # # Plot data
            ax.plot(empX, empY, label='Empirical', linestyle='-')
            ax.plot(predX, predY, label='Predicted', linestyle='--')

            # # Set legend
            handles, labels = ax.get_legend_handles_labels()
            legend = plt.figlegend(handles, labels, fontsize=12, loc='upper left', fancybox=True, frameon=True)
            # legend.get_frame().set_color('white')

        # If something plotted,pack it tight
        if len(self.fileIndexes) > 0:
            self.figure.tight_layout()

        self.figure.canvas.set_window_title('Test')

        # Refresh canvas
        self.canvas.draw()

    def _getNumSubPlots(self):
        """Determines the number of subplots to be drawn."""

        # Determine number of files to be plotted
        n = len(self.fileIndexes)

        # Handle square case
        if np.sqrt(n).is_integer():
            return int(np.sqrt(n)), int(np.sqrt(n))
        # # Handle case 5
        if n == 5:
            return 3, 2
        # Handle more difficult cases
        cols = int(np.ceil(n / 5))
        rows = int(np.ceil(n / cols))
        return rows, cols


class FastDmPlotToolbar(NavigationToolbar):

    def __init__(self, canvas, parent=None):

        super(FastDmPlotToolbar, self).__init__(canvas, parent)

        self._canvas = canvas
        self._viewer = None
        self.setEnabled(False)


class FastDmPlotDataViewer(QListWidget):

    currentIdx = None

    def __init__(self, model, console, plotArea, loadDataFunc, parent=None):

        super(FastDmPlotDataViewer, self).__init__(parent)

        self._model = model
        self._console = console
        self._plotArea = plotArea
        self._loadDataFunc = loadDataFunc
        self._loading = FastDmLoading(self)
        self._dummy = True
        self._initList()

    def _initList(self):
        """Initializes and configures the table."""

        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._onContext)
        self.itemSelectionChanged.connect(self._onSelectionChange)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.addItem(QListWidgetItem("No Files to Plot..."))

    def _onSelectionChange(self):
        """Plots selected plot files."""

        if not self._dummy:
            self._plotArea.plotCdf([idx.row() for idx in self.selectedIndexes()])
        else:
            self._loadDataFunc()

    def _deleteFiles(self):
        """Removes files from list and model."""

        # Clear plot
        self._plotArea.clearPlot()

        # Get selected files
        files = self.selectedItems()

        # Remove files from list and model
        for i, file in enumerate(files):
            idx = self.indexFromItem(file)
            self.takeItem(idx.row())
            self._model.plot['cdffiles'].pop(idx.row())

        # Add dummy if no more data-files left, disable toolbar
        if not self._model.plot['cdffiles']:
            self.addItem(QListWidgetItem("No Files To Plot..."))
            self._dummy = not self._dummy
            self._plotArea.toolbar.setEnabled(False)

    def _onContext(self, point):

        if not self._dummy:
            menu = QMenu()
            deleteAction = QAction("Remove File(s)")
            deleteAction.triggered.connect(self._deleteFiles)
            menu.addAction(deleteAction)
            menu.exec_(self.mapToGlobal(point))

    def sessionUpdate(self):
        """Called externally when a new session was loaded."""

        # Remove all previous items
        while self.count() > 0:
            self.takeItem(0)
        # Add new from loaded
        self.updateFilesList(self._model.plot['cdffiles'])

    def filesLoaded(self, newFiles):
        """Accepts a list of files, checks if files not already loaded and updates list."""

        # Get only new files
        new = []
        for file in newFiles:
            if file not in self._model.plot['cdffiles']:
                if self._headerOk(file):
                    new.append(file)
                else:
                    self._console.writeError('Could not load ' + file + " Header 'cdf-plot' missing.")
            else:
                self._console.writeError('Could not load ' + file + " File already loaded.")
        # Update cdf files in model
        self._model.plot['cdffiles'] += new
        # Update view
        self.updateFilesList(new)

    def _headerOk(self, file):
        """Tests if the header of the plot file contains the plot-cdf flag."""

        with open(file, 'r') as infile:
            if 'cdf-plot' not in infile.readline():
                return False
            return True

    def updateFilesList(self, newFiles):
        """Adds files as list elements to file list."""

        # Do not send signals during update
        self.blockSignals(True)

        # Add file names without path
        for file in newFiles:
            item = QListWidgetItem(file.split('/')[-1])
            item.setIcon(QIcon('./icons/plotdata.png'))
            item.setToolTip('Hint: select multiple files to plot at once')
            self.addItem(item)

        # Enable toolbar
        self._plotArea.toolbar.setEnabled(True)

        # Remove dummy if there
        if self._dummy:
            self.takeItem(0)
            self._dummy = not self._dummy
            # Select first and plot
            self.setCurrentRow(0)
            self._plotArea.plotCdf([idx.row() for idx in self.selectedIndexes()])

        # Update signals
        self.blockSignals(False)

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

        return ['text/uri-list']

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
        """Activated on drop event."""
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.filesLoaded(files)


class FastDmViewerFrame(QFrame):
    """A container for the viewer frame and the tools."""

    def __init__(self, model, console, plotArea, parent=None):
        super(FastDmViewerFrame, self).__init__(parent)

        self._model = model
        self._dataViewer = FastDmPlotDataViewer(self._model, console, plotArea, self._onLoad)
        self._toolBar = FastDmDataViewerToolbar(self._model, self._onLoad)
        self._configureLayout(QVBoxLayout())

    def _configureLayout(self, layout):
        """Adds main components to the container."""

        layout.addWidget(self._dataViewer)
        layout.addWidget(self._toolBar)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def sessionUpdate(self):
        """Called externally to update file list."""

        self._dataViewer.sessionUpdate()

    def _onLoad(self):
        """Activated when user pressed the load button."""

        # Open a dialog
        loadDialog = QFileDialog()
        loadName = loadDialog.getOpenFileNames(self, 'Select Plot Files to Open...',
                                               "", "CSV Files (*.csv)")
        # Check if something loaded
        if loadName[0]:
            self._dataViewer.filesLoaded(loadName[0])


class FastDmDataViewerToolbar(QFrame):

    def __init__(self, model, loadFunc, parent=None):
        super(FastDmDataViewerToolbar, self).__init__(parent)

        self._model = model
        self._loadFunc = loadFunc
        self._configureLayout(QHBoxLayout())

    def _configureLayout(self, layout):
        """Configures the main layout of the widget"""

        # Create a button for load
        loadButton = QPushButton('Add Files')
        loadButton.setIcon(QIcon('./icons/open.png'))
        loadButton.setToolTip('Load File(s) to Plot...')
        loadButton.setStatusTip('Load File(s) to Plot...')
        loadButton.clicked.connect(self._loadFunc)
        loadButton.setFocusPolicy(Qt.NoFocus)

        layout.addWidget(loadButton)
        layout.addStretch(1)
        self.setFrameShape(QFrame.Box)
        self.setLayout(layout)


class FastDmPlotCanvas(QFrame):
    """The main container for the plot area."""

    def __init__(self, model, parent=None):
        super(FastDmPlotCanvas, self).__init__(parent)

        self.figure = None
        self.canvas = None
        self.toolbar = None
        self._loading = FastDmLoading(self)
        self._model = model
        self._initCanvas(QVBoxLayout())
        self._initPlotThread()

    def _initCanvas(self, layout):
        """Initializes main components of canvas."""

        # Create the figure object
        self.figure = plt.figure()

        # Create the canvas widget as container
        self.canvas = FigureCanvas(self.figure)

        # Create the navigation toolbar
        self.toolbar = FastDmPlotToolbar(self.canvas, self)

        # ===== Add toolbar and canvas to layout ===== #
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        self.setFrameShape(QFrame.Panel)
        # Set style for matplotlib
        plt.style.use('grayscale')

    def _initPlotThread(self):
        """Plotting is slow, so we will plot in a thread."""

        # Create a persistent model handler instance
        self._plotter = FastDmPlotter(self._model, self.figure, self.canvas)
        self._plotThread = QThread()
        self._plotter.moveToThread(self._plotThread)
        self._plotter.finished.connect(self._plotThread.quit)
        # Connect thread signals to run handler methods
        self._plotThread.started.connect(self._plotter.run)
        self._plotThread.finished.connect(self._hideWaiting)

    def plotCdf(self, fileIndexes):
        """The main function to plot a cdf plot."""

        self._showWaiting(len(fileIndexes))
        self._plotter.newScreen = False
        self._plotter.fileIndexes = fileIndexes
        self._plotThread.start()

    def _showWaiting(self, n):
        """Indicate plotting with a gif."""

        if n > 2:
            # Only show if we are plotting many
            self._loading.showWheel()

    def _hideWaiting(self):
        """Hide plotting gif."""
        self._loading.hideWheel()

    def clearPlot(self):
        """Clears plot (called externally)."""

        self.figure.clear()
        self.canvas.draw()


class FastDmAdditionalTab(QWidget):

    def __init__(self, model, console, parent=None):
        """The main container for the additional tab."""
        super(FastDmAdditionalTab, self).__init__(parent)

        self._model = model
        self._console = console
        self._plotArea = FastDmPlotCanvas(self._model)
        self._filesFrame = FastDmViewerFrame(self._model, self._console, self._plotArea)
        self._initTab()

    def _initTab(self):
        """Initializes main settings of tab."""

        self._configureLayout(QHBoxLayout())

    def _configureLayout(self, layout):
        """Fills and sets main layout of tab."""

        layout.addWidget(self._filesFrame)
        layout.addWidget(self._plotArea)
        layout.setStretchFactor(self._filesFrame, 1)
        layout.setStretchFactor(self._plotArea, 3)
        self.setLayout(layout)

    def updateWidgets(self):
        """Called on load session, update file viewer."""

        self._filesFrame.sessionUpdate()




