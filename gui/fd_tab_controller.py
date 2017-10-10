from PyQt5.QtWidgets import QTabWidget, QSizePolicy
from PyQt5.QtGui import QIcon


class FastDmTabController(QTabWidget):
    """Main representation of a tab widget. Constructor expects
    an iterable with 4-tuple items containing (widget, idx, text, icon name)."""
    def __init__(self, tabSettings, parent=None):
        super(FastDmTabController, self).__init__(parent)

        self._configureTabs(tabSettings)

    def _configureTabs(self, settings):
        """Configures tab layout and size policy."""

        for tab in settings:
            self.addTab(tab[0], tab[1])
            self.setTabIcon(tab[2], QIcon(tab[3]))
        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))



