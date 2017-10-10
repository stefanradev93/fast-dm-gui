from collections import OrderedDict
import copy
import os


class FastDmModel:

    def __init__(self):
        """The main model of a fast-dm session."""

        # ===== Group parameter attributes ===== #
        self.parameters = OrderedDict([
                            ('a', {'val': 1.0, 'fix': False, 'depends': []}),
                            ('zr', {'val': 0.5, 'fix': False, 'depends': []}),
                            ('v', {'val': 1.0, 'fix': False, 'depends': []}),
                            ('t0', {'val': 0.3, 'fix': False, 'depends': []}),
                            ('d', {'val': 0.0, 'fix': True, 'depends': []}),
                            ('szr', {'val': 0.0, 'fix': True, 'depends': []}),
                            ('sv', {'val': 0.0, 'fix': True, 'depends': []}),
                            ('st0', {'val': 0.0, 'fix': True, 'depends': []}),
                            ('p', {'val': 0.0, 'fix': True, 'depends': []})
                           ])

        # ===== Group computation attributes ===== #
        self.computation = {'method': 'ks',
                            'precision': 3.0,
                            'jobs': 1}

        # ===== Group session attributes ===== #
        self.session = {'datafiles': [],
                        'columns': [],
                        'RESPONSE': {'idx': None, 'name': None},
                        'TIME': {'idx': None, 'name': None},
                        'sessionname': None,
                        'outputdir': None,
                        'fastdmpath':
                            os.path.dirname(os.path.realpath(__file__)) +
                            '{0}fast-dm-bin{0}fast-dm.exe'.format(os.sep),
                        'plotcdfpath':
                            os.path.dirname(os.path.realpath(__file__)) +
                            '{0}fast-dm-bin{0}plot-cdf.exe'.format(os.sep),
                        'plotdensepath':
                            os.path.dirname(os.path.realpath(__file__)) +
                            '{0}fast-dm-bin{0}plot-density.exe'.format(os.sep),
                        'constructpath':
                            os.path.dirname(os.path.realpath(__file__)) +
                            '{0}fast-dm-bin{0}construct-samples.exe'.format(os.sep)
                        }

        # ===== Group plot attributes ===== #
        self.plot = {'cdffiles': []}

        # ===== Group save attributes ===== #
        self.save = {'ctl': True,
                     'cdf': True,
                     'dens': True}

        # ===== Group simulation attributes ===== #
        self.simParameters = OrderedDict([
                                ('a', 1.0),
                                ('zr', 0.5),
                                ('v', 1.0),
                                ('t0', 0.3),
                                ('d', 0.0),
                                ('szr', 0.0),
                                ('sv', 0.0),
                                ('st0', 0.0),
                                ('p', 0.0)])

        self.simOptions = {'outputdir': None,
                           'sessionname': None,
                           'precision': 4.0,
                           'ntrials': 500,
                           'nsamples': 1,
                           'determ': False}

    def dataFilesLoaded(self):
        """Helper method to indicate whether data files loaded."""

        return self.session['datafiles'] != []

    def prepareForNewLoad(self):
        """
        Called externally when no more data-files left.
        Resets header, depends response and time.
        """

        self.session['datafiles'] = []
        self.session['columns'] = []
        self.session['RESPONSE'] = {'idx': None, 'name': None}
        self.session['TIME'] = {'idx': None, 'name': None}
        for key in self.parameters.keys():
            self.parameters[key]['depends'] = []

    def overwrite(self, newModel):
        """Overwrites all data members with members from newModel."""

        self.parameters = copy.deepcopy(newModel.parameters)
        self.computation = copy.deepcopy(newModel.computation)
        self.session = copy.deepcopy(newModel.session)
        self.plot = copy.deepcopy(newModel.plot)
        self.save = copy.deepcopy(newModel.save)
        self.simParameters = copy.deepcopy(newModel.simParameters)
        self.simOptions = copy.deepcopy(newModel.simOptions)


