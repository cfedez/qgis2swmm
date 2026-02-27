# -*- coding: utf-8 -*-
"""
QGIS2SWMM - QGIS Plugin for Drainage Infrastructure Management
Author: Geogarnet
License: GPL v3
Version: 1.0.0
"""

def classFactory(iface):
    """
    Load SWMMPlugin class on demand.

    Args:
        iface: QGIS interface object

    Returns:
        SWMMPlugin: Plugin class instance
    """
    from .swmm_plugin import SWMMPlugin
    return SWMMPlugin(iface)


def serverClassFactory(serverIface):
    """
    Not used for this plugin (GUI only).
    """
    pass
