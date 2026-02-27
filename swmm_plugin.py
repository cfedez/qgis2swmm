# -*- coding: utf-8 -*-
"""
QGIS2SWMM - Main Plugin
Integration with QGIS interface
"""

from qgis.core import QgsApplication
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QSize
from .swmm_dialog import SWMMMainDialog
import os


class SWMMPlugin:
    """
    Main class for QGIS2SWMM plugin.
    Integrates with QGIS.
    """

    def __init__(self, iface):
        """
        Constructor.

        Args:
            iface: QGIS application interface
        """
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.actions = []
        self.menu = "QGIS2SWMM"
        self.toolbar = None
        self.dialog = None

        self.plugin_dir = os.path.dirname(__file__)

    def initGui(self):
        """Initializes the plugin GUI."""
        try:
            icon_path = os.path.join(self.plugin_dir, 'resources', 'icon.png')
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
            else:
                icon = QIcon(":/images/themes/default/mIconPointLayer.svg")

            action = QAction(
                icon,
                "QGIS2SWMM",
                self.iface.mainWindow()
            )
            action.triggered.connect(self.run)
            action.setStatusTip("Digitize drainage networks and export to EPA SWMM")

            self.iface.addPluginToMenu(self.menu, action)
            self.iface.addToolBarIcon(action)
            self.actions.append(action)

        except Exception as e:
            QMessageBox.critical(
                self.iface.mainWindow(),
                "QGIS2SWMM Error",
                f"Failed to initialize plugin GUI:\n{str(e)}"
            )

    def unload(self):
        """Unloads the plugin."""
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        """Runs the plugin and opens main dialog."""
        try:
            if self.dialog is None:
                self.dialog = SWMMMainDialog(self.iface)

            self.dialog.show()
            result = self.dialog.exec_()
            return result
        except Exception as e:
            QMessageBox.critical(
                self.iface.mainWindow(),
                "QGIS2SWMM Error",
                f"Failed to run plugin:\n{str(e)}"
            )
