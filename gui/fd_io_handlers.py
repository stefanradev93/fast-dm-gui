import csv
import pickle
from PyQt5.QtWidgets import QMessageBox
from fd_exceptions import LoadDataError


class FastDmFileLoader:

    def __init__(self, model, mainWindow):

        self._model = model
        self._mainWindow = mainWindow
        self.newFiles = []
        self.repeated = []

    def load(self, filesList):
        """Tries to load files, throws LoadDataError exception if something goes wrong."""

        # If anything left, load
        self._load(self._testInput(filesList))

    def _load(self, filesList):
        """A helper method to append files to model list."""

        self._model.session['datafiles'] += filesList
        self.newFiles = filesList

    def _testInput(self, filesList):
        """Performs various checks for data sanity."""

        # ====== Test for duplicates    ===== #
        filesList = self._testExisting(filesList)

        # ====== Test for correct delimiter ===== #
        for file in filesList:
            self._testDelimiter(file)

        # ======= Test for correct header ====== #
        for file in filesList:

            if self._model.dataFilesLoaded():
                # Files already loaded
                header = self._testHeader(file)
                # Check if columns same as previous
                if header != self._model.session['columns']:
                    msg = "Header of {} does not match header of previous file(s)." \
                          "Make sure all files in the current session have identical headers".format(file)
                    QMessageBox.critical(self._mainWindow, 'Load error...', msg, QMessageBox.Ok)

                    raise LoadDataError(msg)
            else:
                # No data loaded
                header = self._testHeader(file)
                if not self._model.session['columns']:
                    self._model.session['columns'] = header
                else:
                    if self._model.session['columns'] != header:
                        msg = "Header of {} does not match header of previous file(s)." \
                              "Make sure all files in the current session have identical headers".format(file)
                        QMessageBox.critical(self._mainWindow, 'Load error...', msg, QMessageBox.Ok)
                        raise LoadDataError(msg)
        # ===== Data files have passed all tests ===== #
        return filesList

    def _testHeader(self, file):
        """Tests if header starts with #."""
        try:
            with open(file, 'r') as f:
                # Read first line
                firstLine = f.readline()
                # Check if it starts with a hash tag
                if firstLine[0] == "#":
                    # Then first line should be a header
                    firstLine = firstLine.split()
                    # Try to clean it even more (if there is a space)
                    if firstLine[0] == '#':
                        firstLine.pop(0)
                    # Clean if no space between hash tag and word, e.g. #TIME, RESPONSE
                    if firstLine[0][0] == '#':
                        firstLine[0] = firstLine[0].replace('#', '')
                    return firstLine
                # In case the file lacks a header
                else:
                    msg = "No header was found in {}. Make sure the first row of each file\n" \
                          "starts with a hash tag '#' describing the column names of the file.".format(file)
                    QMessageBox.critical(self._mainWindow, 'Load error...', msg, QMessageBox.Ok)
                    raise LoadDataError(msg)

        except FileNotFoundError as e:
            raise LoadDataError(e.strerror)

    def _testDelimiter(self, file):
        """Tests for delimiter type."""

        sniffer = csv.Sniffer()
        try:
            with open(file, 'r') as f:
                sniffer.sniff(f.read(1024*16), delimiters='\t ,')
        except csv.Error:
            msg = "Could not determine delimiter of file {}.\n" \
                  "Make sure your data files are whitespace or tab-delimited.".format(file)
            QMessageBox.critical(self._mainWindow, 'Load error...', msg, QMessageBox.Ok)
            raise LoadDataError(msg)

    def _testExisting(self, filesList):
        """Checks for duplicate loadings and removes duplicates."""

        if self._model.session['datafiles']:
            stripped = filesList[:]
            for file in filesList:
                for alreadyLoaded in self._model.session['datafiles']:
                    if file.split('/')[-1] in alreadyLoaded:
                        stripped.remove(file)
                        self.repeated.append(file)
                        break
            return stripped
        else:
            return filesList


class FastDmSessionSaver:

    def __init__(self, model, mainWindow):
        """Called to save a model to a given filename."""

        self._model = model
        self._mainWindow = mainWindow

    def save(self, fname):
        """Tries to pickle the model and save it under the given name."""

        with open(fname, 'wb') as savefile:
            try:
                pickle.dump(self._model, savefile)
                return True
            except pickle.PicklingError as e:
                QMessageBox.critical(self._mainWindow, 'Could not save file...',
                                     str(e), QMessageBox.Ok)
                return False


class FastDmSessionLoader:

    @staticmethod
    def load(fname, mainWindow):
        """Unpickles the binary fname and returns the unpickled object."""

        # Open pickled file
        with open(fname, 'rb') as openfile:
            try:
                return pickle.load(openfile)
            except pickle.UnpicklingError as e:
                QMessageBox.critical(mainWindow, 'Could not load file...',
                                     str(e), QMessageBox.Ok)
                return None

