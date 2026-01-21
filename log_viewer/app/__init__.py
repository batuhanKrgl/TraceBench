"""
App module for Log Viewer application.
Contains Qt UI components and main window.
"""

from .main_window import MainWindow
from .dialogs import (
    AxisSettingsDialog,
    HeaderDiffDialog,
    JoinOptionsDialog,
    TimeSettingsDialog,
)
from .widgets import (
    ChannelSelector,
    FilterPanel,
    PlotContainer,
    TestTreeWidget,
)

__all__ = [
    "MainWindow",
    "AxisSettingsDialog",
    "HeaderDiffDialog",
    "JoinOptionsDialog",
    "TimeSettingsDialog",
    "ChannelSelector",
    "FilterPanel",
    "PlotContainer",
    "TestTreeWidget",
]
