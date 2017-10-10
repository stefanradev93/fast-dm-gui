class LoadDataError(Exception):
    def __init__(self, message, errors=None):
        """To be thrown on data file load."""
        super(LoadDataError, self).__init__(message)

        self.errors = errors