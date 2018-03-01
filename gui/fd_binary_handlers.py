from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QObject, pyqtSignal
from fd_cdf_stats import ECDF
from itertools import zip_longest
import numpy as np
import os
import subprocess
import tempfile


"""Global variables indicating end directory names."""
PARAMETERSDIR = 'individual_estimates'
CDFDIR = 'cdf'
DENSITYDIR = 'density'
ALL_ESTIMATES_NAME = 'estimates_all.csv'


class FastDmRunHandler(QObject):

    finished = pyqtSignal()
    estimationStarting = pyqtSignal()
    consoleLog = pyqtSignal(str)
    progressUpdate = pyqtSignal(int)

    def __init__(self, model, flag):
        """
        Creates a new instance of run handler which will run fast-dm
        in a parallel manner according to the num CPUs specified. Assumes
        that the model has valid parameter specifications.
        """
        super(FastDmRunHandler, self).__init__()

        self._model = model
        self._flag = flag
        self.controlFileTemplate = None
        self.aborted = False
        self.error = False

    def run(self):
        """Runs fast-dm estimation."""

        try:
            # Emit starting and modify flag
            self.estimationStarting.emit()
            self._flag['run'] = True
            self._runBinary()
        finally:
            # Emit finished and make sure flag is correctly implemented
            self.finished.emit()

    def _runBinary(self):
        """Starts parallel instances of fast-dm."""

        # Get file contents as string with two {} placeholders
        self.controlFileTemplate = self._getFileTemplate()

        # Overwrite session dir so no clash occurs
        self._model.session['sessionname'] = self._sessionDir(self._model.session['sessionname'])

        # Shorten some variable names
        files = self._model.session['datafiles']
        jobs = self._model.computation['jobs']
        path = self._model.session['outputdir'] + '/' + \
               self._model.session['sessionname'] + '/' + \
               PARAMETERSDIR + '/'
        allEstimatesFileName = self._model.session['outputdir'] + '/' + \
                               self._model.session['sessionname'] + '/' + \
                               ALL_ESTIMATES_NAME
        fastdm = self._model.session['fastdmpath']

        # Create path, if it does not exist
        if not os.path.isdir(path):
            os.makedirs(path)

        # Open file to write all logs
        allEstimatesFile = open(allEstimatesFileName, 'a')

        # Loop through all data files in chunks
        for i in range(0, len(files), jobs):

            # Initialize a simple queue for processors
            processes = []

            # Loop for the number of jobs specified
            # Calculate remaining files and specify inner iterations
            nProcesses = jobs if (len(files) - i) >= jobs else len(files) - i
            for j in range(0, nProcesses):

                # Get control file name
                controlFileName = path + '.controlfile_{}.ctl'.format(i+j)
                # Create file contents form template
                controlFileContents = self.controlFileTemplate.format(files[i+j],
                        path + 'parameters_' + files[i+j].split('/')[-1])

                # Create control file and write out contents
                with open(controlFileName, 'w') as controlFile:
                    controlFile.write(controlFileContents)

                # Open a temporary file
                f = tempfile.NamedTemporaryFile()
                # Spawn fast-dm subprocess with controlFileName just created
                p = subprocess.Popen([fastdm, controlFileName], stdout=f, stderr=f)
                # Append to improvised queue
                processes.append((p, f))

            # Now wait for all sub processes to finish before going to next chunk
            for p, f in processes:

                # Block execution until this processes finishes
                while p.poll() is None:
                    if not self._flag['run']:
                        self.aborted = True
                        p.kill()
                # If not aborted print out
                if not self.aborted:
                    # Return read pointer to temp file to start
                    f.seek(0)
                    # Read log
                    log = f.read().decode('utf-8')
                    # Close temporary file - removes it
                    f.close()
                    # Write log to console
                    self.consoleLog.emit(log)
                    # Check for invalid or error, exit
                    if 'invalid' in log or 'error' in log or "Not enough" in log:
                        self.error = True
                        return

            # Delete temporary control files
            for k in range(0, nProcesses):
                os.remove(path + '/' + '.controlfile_{}.ctl'.format(i + k))

            # Break main loop, if aborted, do before writing to common data file
            # since it does not exist, if user aborts before the first data set is processed
            if self.aborted:
                return

            # Write to file containing all data sets
            for sf in range(0, nProcesses):
                # Write header, if we are at first iteration
                # since there is a big problem with this approach
                # (different files have different order of estimated parameters)
                # we need to make sure that all comply to the first header:
                try:
                    name = files[i + sf].split('/')[-1]
                    if i == 0 and sf == 0:
                        h2v, header = self._parseSingleFile(path, 'parameters_', name)
                        allEstimatesFile.write(";".join(['dataset'] + header) + '\n')
                    else:
                        h2v, _ = self._parseSingleFile(path, 'parameters_', name)
                    # Write values lines in order of the first header
                    allEstimatesFile.write(";".join([name] + [h2v[h] for h in header]) + '\n')
                except FileNotFoundError as e:
                    # Catch problem, if any with fast-dm failing
                    self.error = True
                    return

                # Update progress bar
                self.progressUpdate.emit(i + sf + 1)

    def _getFileTemplate(self):
        """Returns a template for generating control files."""

        template = ""

        # ===== Add method AND precision ===== #
        template += 'method' + ' ' + self._model.computation['method'] + '\n'
        template += 'precision' + ' ' + str(self._model.computation['precision']) + '\n'

        # ===== Add model parameters ===== #
        for key, entry in self._model.parameters.items():
            if entry['fix']:
                template += 'set' + ' ' + key + ' ' + str(entry['val']) + '\n'

        # ===== Add depends ===== #
        for key, entry in self._model.parameters.items():
            if entry['depends']:
                template += 'depends' + ' ' + key + ' ' + ' '.join(entry['depends']) + '\n'

        # ===== Add format ===== #
        formatLine = 'format'
        # Loop through column names and indices
        for idx, column in enumerate(self._model.session['columns']):

            if idx == self._model.session['RESPONSE']['idx']:
                # Found index of response
                formatLine += ' ' + 'RESPONSE'
            elif idx == self._model.session['TIME']['idx']:
                # Found index of time
                formatLine += ' ' + 'TIME'
            else:
                # Found other column
                if column == 'RESPONSE' or column == 'TIME':
                    # If the var is RESPONSE or TIME, then another var was specified
                    # as response or time, so we rename the current.
                    column = column + '_old'
                formatLine += ' ' + column
        # Add to template
        template += formatLine + '\n'

        # ===== Add Load ===== #
        template += 'load "{}"\n'

        # ===== Add Save ===== #
        template += 'save "{}"\n'

        return template

    def _sessionDir(self, sessionName):
        """Checks if directory exists, if exists, changes name so it matches."""

        if not os.path.isdir(self._model.session['outputdir'] + '/' + sessionName):
            return sessionName
        else:
            return self._sessionDir(sessionName + '_1')

    def _parseSingleFile(self, path, base, name):
        """Reads in the contents of a single fd file and returns header and values."""

        # Open file
        with open(path + base + name, 'r') as dataFile:
            # Read lines into a list
            lines = dataFile.read().splitlines()
            # Get header in order
            header = [line.split('=')[0].rstrip().lstrip() for line in lines]
            # Get header and values in oder
            header_and_values = {line.split('=')[0].rstrip().lstrip():
                                 line.split('=')[-1].lstrip().rstrip() for line in lines}
            # Return in this order
            return header_and_values, header

    def saveFileTemplate(self):
        """Called externally, saves the file template to the session directory."""

        # Get save path
        path = self._model.session['outputdir'] + '/' + \
               self._model.session['sessionname'] + '/'

        # Get extension of data files (assume all files come form same folder)
        ext = self._model.session['datafiles'][0].split(".")[-1]
        dataPath = os.path.dirname(self._model.session['datafiles'][0])
        loadEntry = dataPath + '/' + '*.' + ext
        saveEntry = path + 'individual_estimates' + '/*.dat'

        # Fill up template and save
        toSave = self.controlFileTemplate.format(loadEntry, saveEntry)
        with open(path + 'session.ctl', 'w') as ctl:
            ctl.write(toSave)
        return path + 'session.ctl'

    def reset(self):
        """Resets flags."""

        self.controlFileTemplate = None
        self.aborted = False
        self.error = False


class FastDmCdfHanlder(QObject):

    finished = pyqtSignal()
    consoleLog = pyqtSignal(str)
    calculationStarting = pyqtSignal()

    def __init__(self, model, parent=None):
        """Creates a new instance of cdf handler which will calculate cdf files."""

        super(FastDmCdfHanlder, self).__init__(parent)
        self._model = model

    def run(self):
        """Does all the computation in the background.
        1. Runs plot cdf into the directory.
        2. Calculates empirical cdfs.
        3. Concatenates the two into a single file.
        """

        # TODO - Handle depends
        self.calculationStarting.emit()
        try:
            cdfDir = self._createCdfDir()
            self._calculatePredictedCdf(cdfDir)
            self._calculateEmpiricalCdf(cdfDir)
        finally:
            self.finished.emit()

    def _runAsSubprocess(self, fileName, funcArgs):
        """Runs the given plotting function as a subprocess."""

        # Create output argument
        outputArg = '-o "{}"'.format(fileName)

        # Create argument for subprocess
        procArg = self._model.session['plotcdfpath'] + ' ' + \
                    subprocess.list2cmdline(funcArgs) + ' ' + outputArg

        # Open a temporary file
        f = tempfile.NamedTemporaryFile()

        # Spawn plot-cdf subprocess with funcArgs
        p = subprocess.Popen(procArg, stdout=f, stderr=f)

        # Wait for it to finish (very fast, but better not start 100 processes...)
        p.wait()

    def _createCdfDir(self):
        """Creates cdf dir name and returns it as aa string."""

        # Get name of cdf dir
        cdfDir = self._model.session['outputdir'] + '/' + \
                 self._model.session['sessionname'] + '/' + \
                 CDFDIR

        # Create new cdf directory
        os.mkdir(cdfDir)

        # Return if successful
        return cdfDir

    def _calculatePredictedCdf(self, cdfDir):
        """Runs plot cdf with the predicted parameters."""

        # Get parameter files from directory
        parameterFiles = self._getParameterFileNames()

        # Loop through datafiles and run calculate cdf on them
        for fileName in parameterFiles:

            # Get plotting function arguments
            funcArgs = self._getCdfArgs(fileName)

            # Get new file name (use dot to indicate hidden file)
            newFileName = self._getCdfFileName(cdfDir, fileName)

            # Run as a subprocess
            self._runAsSubprocess(newFileName, funcArgs)

    def _getCdfFileName(self, cdfDir, fileName):
        """Determines the name of the df output file."""

        # Get only file name
        onlyFileName = fileName.split('/')[-1]
        # Get extension
        ext = '.' + fileName.split('.')[-1]
        # Return determined file name
        return cdfDir + '/' + '.' + onlyFileName.replace(ext, '_cdf.csv')

    def _getCdfArgs(self, fname):
        """Returns the cdf arguments as a string."""

        # Initialize an empty list to hold the functions arguments
        funcArgs = []
        # Open file and read parameters
        with open(fname, 'r') as infile:
            for line in infile:
                # Determine parameter
                parameter = self._getParameter(line)
                # Append to list, if any found (just in case)
                if parameter:
                    funcArgs.append(parameter)
        return funcArgs

    def _getParameter(self, line):
        """Determines the parameter from a given line."""

        # Remove all whitespaces
        line = ''.join(line.split())
        # Split after = sign
        line = line.split('=')
        # Determine which parameter is contained in the line
        if line[0] == 'precision':
            return '-p {0:.2f}'.format(float(line[-1]))
        if line[0] == 'a':
            return '-a {0:.2f}'.format(float(line[-1]))
        elif line[0] == 'zr':
            return '-z {0:.2f}'.format(float(line[-1]))
        elif line[0] == 'v':
            return '-v {0:.2f}'.format(float(line[-1]))
        elif line[0] == 't0':
            return '-t {0:.2f}'.format(float(line[-1]))
        elif line[0] == 'd':
            return '-d {0:.2f}'.format(float(line[-1]))
        elif line[0] == 'szr':
            return '-Z {0:.2f}'.format(float(line[-1]))
        elif line[0] == 'sv':
            return '-V {0:.2f}'.format(float(line[-1]))
        elif line[0] == 'st0':
            return '-T {0:.2f}'.format(float(line[-1]))
        # No parameter found
        return False

    def _getParameterFileNames(self):
        """
        Reads the names of all separate parameter files and 
        returns them as list containing absolute paths."""

        directory = self._model.session['outputdir'] + '/' + \
                    self._model.session['sessionname'] + '/' + \
                    PARAMETERSDIR
        filenames = []
        # Loop through each file in the target directory
        for filename in os.listdir(directory):
            if filename.startswith('parameters'):
                filenames.append(directory + '/' + filename)
        return filenames

    def _calculateEmpiricalCdf(self, cdfDir):
        """Runs after plot-cdf has finished. Calculates cdfs from files."""

        # Loop through all datafiles
        for file in self._model.session['datafiles']:

            # If fast-dm fails to estimate, the output is not written to stderr
            # so we need to handle the errors the ugly way in the two loops for
            # calculating empirical and predicted cdfs
            try:
                # Load file
                data = np.genfromtxt(file, skip_header=True)

                # Get relevant data columns
                response = data[:, self._model.session['RESPONSE']['idx']]
                rt = data[:, self._model.session['TIME']['idx']]

                # Reverse time data (mirror negative)
                rt = np.where(response == 0, -rt, rt)

                # Calculate empirical cdf (returns an object)
                empCdf = ECDF(rt)

                # Replace negative inf in x
                empCdf.x[np.isneginf(empCdf.x)] = \
                    np.min(empCdf.x[np.logical_not(np.isneginf(empCdf.x))])

                # Read in temporary predicted cdf
                predCdf = np.genfromtxt(self._getPredictedCdfFileName(file, cdfDir))

                # Concatenate empirical and predicted
                self._concatenateFiles(self._getConcatenatedFileName(file, cdfDir), empCdf, predCdf)

                # Delete temporary cdf file
                self._deletePredictedCdfFileName(self._getPredictedCdfFileName(file, cdfDir))

            except OSError as e:
                self.consoleLog.emit('Could not calculate cdf values for ' + file)

    def _getPredictedCdfFileName(self, fname, cdfDir):
        """Accepts a data file file name and dir name, and returns a temp cdf file name."""

        return cdfDir + '/' + '.' + 'parameters_' + os.path.splitext(fname.split('/')[-1])[0] + '_cdf.csv'

    def _getConcatenatedFileName(self, fname, cdfDir):
        """Accepts a data file file name and dir name, and returns a real cdf file name."""

        return cdfDir + '/' + 'parameters_' + os.path.splitext(fname.split('/')[-1])[0] + '_cdf.csv'

    def _concatenateFiles(self, fname, empCdf, predCdf):
        """Concatenates predicted and empirical cdfs."""

        # Open a file to store cdfs
        with open(fname, 'w') as testfile:
            # Write out header
            testfile.write('# x_emp\ty_emp\tx_pred\ty_pred; cdf-plot\n')
            for empX, empY, predX, predY in zip_longest(empCdf.x, empCdf.y,
                                                        predCdf[:, 0], predCdf[:, 1], fillvalue='NaN'):
                # Write out values
                testfile.write('{}\t{}\t{}\t{}\n'.format(empX, empY, predX, predY))

    def _deletePredictedCdfFileName(self, fname):
        """Deletes the temporary predicted cdf fname created by fast-dm."""

        os.remove(fname)


class FastDmSimHandler(QObject):
    """Main class to handle construct-samples in a separate thread."""

    finished = pyqtSignal()
    consoleLog = pyqtSignal(str)
    simulationStarting = pyqtSignal()

    def __init__(self, model, flag, parent=None):
        super(FastDmSimHandler, self).__init__(parent)

        self._model = model
        self._flag = flag
        self.aborted = False

    def run(self):
        """Launches the simulation in a separate thread."""

        try:
            # Send signal that simulation is starting and set flag
            self.simulationStarting.emit()
            self._flag['run'] = True
            # Get directory
            simDir = self._getSimDir()
            # Get process cmd arguments
            simArgs = self._getSimArgs(simDir)
            # Run as a subprocess
            self._runAsSubprocess(simDir, simArgs)
        finally:
            # Emit finished signal
            self.finished.emit()

    def _runAsSubprocess(self, simDir, simArgs):
        """Tries to run construct samples as a subprocess."""

        # Create argument list for subprocess
        simArgs = self._model.session['constructpath'] + ' ' + \
                                    subprocess.list2cmdline(simArgs)
        # Add output file
        simArgs += ' -o "{}sim_%d.lst"'.format(simDir.replace('/', os.sep))

        # Open a temporary file for IO redirection
        f = tempfile.NamedTemporaryFile()

        # Spawn construct samples process
        p = subprocess.Popen(simArgs, stdout=f, stderr=f)

        # Wait to finish
        while p.poll() is None:
            # If aborted, kill
            if not self._flag['run']:
                self.aborted = True
                p.kill()

        # Read from temp file and give verbose on console, if any error occurred
        f.seek(0)
        for line in f:
            line = line.decode('utf-8').replace('\n', '')
            if 'error' in line:
                self.consoleLog.emit(line)

    def _getSimDir(self):
        """Returns the full path to the simulation directory. Assumes settings sanity."""

        # Get name of sim dir
        simDir = self._model.simOptions['outputdir'] + '/' + \
                 self._sessionDir(self._model.simOptions['sessionname']) + '/'

        # Create new simulation directory
        os.mkdir(simDir)

        # Return path to sim dir
        return simDir

    def _sessionDir(self, sessionName):
        """Recursively check if session dir exists and append 1 if so."""

        if not os.path.isdir(self._model.simOptions['outputdir'] + '/' + sessionName):
            return sessionName
        else:
            return self._sessionDir(sessionName + '_1')

    def _getSimArgs(self, simDir):
        """Determines the simulation command line arguments."""

        # Initialize argument list
        args = list()

        # Get other parameters
        args.append('-a {}'.format(self._model.simParameters['a']))
        args.append('-z {}'.format(self._model.simParameters['zr']))
        args.append('-v {}'.format(self._model.simParameters['v']))
        args.append('-t {}'.format(self._model.simParameters['t0']))
        args.append('-d {}'.format(self._model.simParameters['d']))
        args.append('-Z {}'.format(self._model.simParameters['szr']))
        args.append('-V {}'.format(self._model.simParameters['sv']))
        args.append('-T {}'.format(self._model.simParameters['st0']))

        # Get precision, n trials, data sets and random or not
        args.append('-n {}'.format(self._model.simOptions['ntrials']))
        args.append('-N {}'.format(self._model.simOptions['nsamples']))
        args.append('-p {}'.format(self._model.simOptions['precision']))
        if not self._model.simOptions['determ']:
            args.append('-r')

        # Return arguments list
        return args


def checkModelSanity(model, parent=None):
    """
    Checks various conditions for the model output,
    return True if anything ok, False otherwise.
    """

    # ===== Initialize message box ===== #
    msg = QMessageBox()
    errorTitle = 'Could not run fast-dm...'

    # ===== Check if any data left ===== #
    if not model.session['datafiles']:
        text = 'No data files loaded!'
        msg.critical(parent, errorTitle, text)
        return False

    # ===== Check if RESPONSE AND TIME specified ===== #
    if not model.session['TIME']['name']:
        text = 'No "Reaction Times Column" specified!'
        msg.critical(parent, errorTitle, text)
        return False

    if not model.session['RESPONSE']['name']:
        text = 'No "Responses Column" specified!'
        msg.critical(parent, errorTitle, text)
        return False

    # ===== Check if output directory specified ===== #
    if not model.session['outputdir']:
        text = 'No output location specified!'
        msg.critical(parent, errorTitle, text)
        return False

    # ===== Check if session name specified ===== #
    if not model.session['sessionname']:
        text = 'No directory name specified!'
        msg.critical(parent, errorTitle, text)
        return False

    # ===== Check if output directory exists ===== #
    if not os.path.exists(model.session['outputdir']):
        text = 'Output location is nonexistent!'
        msg.critical(parent, errorTitle, text)
        return False

    # ===== Check if path to fast dm correctly specified ===== #
    if not os.path.isfile(model.session['fastdmpath']):
        text = 'Could not find fast-dm executable. Check your path settings!'
        msg.critical(parent, errorTitle, text)
        return False

    # ===== If we are here, all tests have been passed ===== #
    return True


def checkSimulationSanity(model, parent=None):
    """
    Checks various conditions for simulation (actually path issues).
    """

    # ===== Initialize message box ===== #
    msg = QMessageBox()
    errorTitle = 'Could not run simulation...'

    # ===== Check if output directory specified ===== #
    if not model.simOptions['outputdir']:
        text = 'No output location specified!'
        msg.critical(parent, errorTitle, text)
        return False

    # ===== Check if session name specified ===== #
    if not model.simOptions['sessionname']:
        text = 'No directory name specified!'
        msg.critical(parent, errorTitle, text)
        return False

    # ===== Check if output directory exists ===== #
    if not os.path.exists(model.simOptions['outputdir']):
        text = 'Output location is nonexistent!'
        msg.critical(parent, errorTitle, text)
        return False

    # ===== Check if path to fast dm correctly specified ===== #
    if not os.path.isfile(model.session['constructpath']):
        text = 'Could not find construct-samples executable. Check your path settings!'
        msg.critical(parent, errorTitle, text)
        return False

    # ===== If we are here, all tests have been passed ===== #
    return True
