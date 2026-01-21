"""
Multi-axis plot widget with crosshair and hover readout.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QColor, QFont, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core import CompareMode, FilterManager, PlotSettings, TestComparer


# Color palette for multiple series
COLORS = [
    "#1f77b4",  # Blue
    "#ff7f0e",  # Orange
    "#2ca02c",  # Green
    "#d62728",  # Red
    "#9467bd",  # Purple
    "#8c564b",  # Brown
    "#e377c2",  # Pink
    "#7f7f7f",  # Gray
    "#bcbd22",  # Yellow-green
    "#17becf",  # Cyan
]

# Axis colors
AXIS_COLORS = [
    "#1f77b4",  # Y1 - Blue
    "#ff7f0e",  # Y2 - Orange
    "#2ca02c",  # Y3 - Green
]


class CrosshairReadout(QFrame):
    """Widget displaying crosshair readout values."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(40, 40, 40, 200);
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
            }
            QLabel {
                color: white;
                font-family: monospace;
                font-size: 11px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        self.time_label = QLabel("Time: --")
        self.time_label.setFont(QFont("monospace", 10))
        layout.addWidget(self.time_label)

        self.values_label = QLabel("")
        self.values_label.setFont(QFont("monospace", 10))
        layout.addWidget(self.values_label)

        self.setVisible(False)

    def set_values(self, time_val: float, channel_values: dict[str, float]):
        """Set the readout values."""
        self.time_label.setText(f"Time: {time_val:.4f} s")

        if channel_values:
            lines = []
            for ch, val in list(channel_values.items())[:6]:  # Limit to 6 channels
                if len(ch) > 15:
                    ch = ch[:12] + "..."
                lines.append(f"{ch}: {val:.4f}")
            self.values_label.setText("\n".join(lines))
        else:
            self.values_label.setText("")

        self.adjustSize()

    def clear(self):
        """Clear the readout."""
        self.time_label.setText("Time: --")
        self.values_label.setText("")


class MultiAxisPlotWidget(QWidget):
    """
    Plot widget supporting up to 3 Y-axes with crosshair and hover readout.

    For the primary plot (is_primary=True), supports 3 Y-axes.
    For secondary plots, supports 1 Y-axis with editable X and Y settings.
    """

    crosshair_moved = Signal(float)  # x_value
    axis_settings_requested = Signal(int)  # plot_index

    def __init__(
        self,
        is_primary: bool = False,
        filter_manager: Optional[FilterManager] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.is_primary = is_primary
        self.filter_manager = filter_manager
        self.plot_index = 0

        # Data storage
        self._series: list[pg.PlotDataItem] = []
        self._series_data: dict[str, tuple[np.ndarray, np.ndarray]] = {}

        # Crosshair state
        self._crosshair_locked = False
        self._locked_x = 0.0

        self._setup_ui()
        self._setup_crosshair()

    def _setup_ui(self):
        """Set up the plot UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(5, 2, 5, 2)

        self.title_label = QLabel("Plot")
        self.title_label.setStyleSheet("font-weight: bold;")
        toolbar.addWidget(self.title_label)

        toolbar.addStretch()

        # Lock crosshair button
        self.lock_btn = QPushButton("Lock Crosshair")
        self.lock_btn.setCheckable(True)
        self.lock_btn.clicked.connect(self._toggle_crosshair_lock)
        toolbar.addWidget(self.lock_btn)

        # Axis settings button
        settings_btn = QPushButton("Axis Settings")
        settings_btn.clicked.connect(lambda: self.axis_settings_requested.emit(self.plot_index))
        toolbar.addWidget(settings_btn)

        layout.addLayout(toolbar)

        # Create pyqtgraph plot widget
        pg.setConfigOptions(antialias=True, useOpenGL=False)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#1e1e1e")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # Get the PlotItem
        self.plot_item = self.plot_widget.getPlotItem()

        # Set up X-axis
        self.plot_item.setLabel("bottom", "Time", "s")

        # Set up Y-axes
        self._setup_y_axes()

        # Enable downsampling for performance - DISABLED for debugging
        # self.plot_item.setDownsampling(mode="peak")
        # self.plot_item.setClipToView(True)

        layout.addWidget(self.plot_widget)

        # Crosshair readout (overlay)
        self.readout = CrosshairReadout(self.plot_widget)
        self.readout.move(10, 10)

    def _setup_y_axes(self):
        """Set up Y-axes (up to 3 for primary plot)."""
        # Y1 is the default left axis
        self.plot_item.setLabel("left", "Y1", color=AXIS_COLORS[0])
        self.plot_item.getAxis("left").setPen(pg.mkPen(AXIS_COLORS[0], width=1))

        self.y_axes = [self.plot_item.getViewBox()]
        self.y_axis_items = [self.plot_item.getAxis("left")]

        if self.is_primary:
            # Create Y2 and Y3 axes
            for i in range(2):
                axis_name = f"Y{i + 2}"
                color = AXIS_COLORS[i + 1]

                # Create axis item
                axis = pg.AxisItem("right")
                axis.setLabel(axis_name, color=color)
                axis.setPen(pg.mkPen(color, width=1))

                # Create view box
                vb = pg.ViewBox()

                # Add to layout
                self.plot_item.layout.addItem(axis, 2, 3 + i)
                self.plot_item.scene().addItem(vb)

                # Link X-axis
                axis.linkToView(vb)
                vb.setXLink(self.plot_item.vb)

                self.y_axes.append(vb)
                self.y_axis_items.append(axis)

            # Handle view range updates
            self.plot_item.vb.sigResized.connect(self._update_views)

    def _update_views(self):
        """Update secondary view boxes when main view is resized."""
        if self.is_primary:
            for vb in self.y_axes[1:]:
                vb.setGeometry(self.plot_item.vb.sceneBoundingRect())

    def _setup_crosshair(self):
        """Set up crosshair lines."""
        pen = pg.mkPen(color="#888", width=1, style=Qt.PenStyle.DashLine)

        self.vline = pg.InfiniteLine(angle=90, movable=False, pen=pen)
        self.hline = pg.InfiniteLine(angle=0, movable=False, pen=pen)

        self.plot_item.addItem(self.vline, ignoreBounds=True)
        self.plot_item.addItem(self.hline, ignoreBounds=True)

        # Connect mouse move
        self.plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)

        # Connect click for lock
        self.plot_widget.scene().sigMouseClicked.connect(self._on_mouse_clicked)

    def _on_mouse_moved(self, pos):
        """Handle mouse movement for crosshair."""
        if self._crosshair_locked:
            return

        if self.plot_item.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_item.vb.mapSceneToView(pos)
            x = mouse_point.x()
            y = mouse_point.y()

            self.vline.setPos(x)
            self.hline.setPos(y)

            # Update readout with scene position for proper widget positioning
            self._update_readout(x, pos)

            # Emit for sync
            self.crosshair_moved.emit(x)

            self.readout.setVisible(True)
        else:
            self.readout.setVisible(False)

    def _on_mouse_clicked(self, event):
        """Handle mouse click for crosshair lock."""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.plot_item.sceneBoundingRect().contains(event.scenePos()):
                # Toggle lock on double-click
                if event.double():
                    self._toggle_crosshair_lock()

    def _toggle_crosshair_lock(self):
        """Toggle crosshair lock state."""
        self._crosshair_locked = not self._crosshair_locked
        self.lock_btn.setChecked(self._crosshair_locked)

        if self._crosshair_locked:
            self._locked_x = self.vline.getXPos()
            self.vline.setPen(pg.mkPen(color="#ff0", width=2))
            self.hline.setPen(pg.mkPen(color="#ff0", width=2))
        else:
            self.vline.setPen(pg.mkPen(color="#888", width=1, style=Qt.PenStyle.DashLine))
            self.hline.setPen(pg.mkPen(color="#888", width=1, style=Qt.PenStyle.DashLine))

    def _update_readout(self, x_val: float, scene_pos=None):
        """Update the readout widget with values at x position."""
        values = {}

        for name, (x_data, y_data) in self._series_data.items():
            if len(x_data) == 0:
                continue

            # Find nearest point
            idx = np.searchsorted(x_data, x_val)
            if idx >= len(x_data):
                idx = len(x_data) - 1
            elif idx > 0:
                # Check which neighbor is closer
                if abs(x_data[idx - 1] - x_val) < abs(x_data[idx] - x_val):
                    idx = idx - 1

            values[name] = float(y_data[idx])

        self.readout.set_values(x_val, values)

        # Position readout near cursor but within bounds
        if scene_pos is not None:
            # Map scene position to widget coordinates
            widget_pos = self.plot_widget.mapFromScene(scene_pos)
            
            # Offset the readout to the right and below the cursor
            x_pos = widget_pos.x() + 15
            y_pos = widget_pos.y() + 10
            
            # Ensure readout stays within plot widget bounds
            max_x = self.plot_widget.width() - self.readout.width() - 5
            max_y = self.plot_widget.height() - self.readout.height() - 5
            
            # Adjust if readout would go outside bounds
            if x_pos > max_x:
                x_pos = widget_pos.x() - self.readout.width() - 15  # Place on left side
            if y_pos > max_y:
                y_pos = max_y
            
            # Ensure minimum position
            x_pos = max(5, x_pos)
            y_pos = max(5, y_pos)
            
            self.readout.move(int(x_pos), int(y_pos))

    def set_crosshair_x(self, x_val: float, emit_signal: bool = True):
        """Set crosshair X position (for sync from other plots)."""
        self.vline.setPos(x_val)
        self._update_readout(x_val)

        if emit_signal:
            self.crosshair_moved.emit(x_val)

    def update_plot(
        self,
        test_ids: list[str],
        channels: list[str],
        settings: PlotSettings,
        compare_mode: CompareMode = CompareMode.OVERLAY,
        compare_gap: float = 0.0
    ):
        """Update the plot with new data."""
        # Clear existing series
        for item in self._series:
            self.plot_item.removeItem(item)
            # Also remove from secondary view boxes if applicable
            if self.is_primary:
                for vb in self.y_axes[1:]:
                    try:
                        vb.removeItem(item)
                    except Exception:
                        pass

        self._series.clear()
        self._series_data.clear()

        if not test_ids or not channels:
            return

        # Get tests from filter manager
        tests = []
        for test_id in test_ids:
            test = self.filter_manager.get_test(test_id) if self.filter_manager else None
            if test:
                tests.append(test)

        if not tests:
            return

        # Prepare data with comparison mode
        comparer = TestComparer(mode=compare_mode, gap=compare_gap)
        prepared_data = comparer.prepare_tests_for_comparison(tests, channels)

        # Plot each test's data
        color_idx = 0
        for test_id, df in prepared_data.items():
            if df.empty or "_plot_time_" not in df.columns:
                continue

            time_data = df["_plot_time_"].values

            for channel in channels:
                if channel not in df.columns:
                    continue

                y_data = df[channel].values

                # Handle NaN values - filter them out for plotting
                mask = ~(np.isnan(time_data) | np.isnan(y_data))
                x_clean = time_data[mask]
                y_clean = y_data[mask]

                if len(x_clean) == 0:
                    continue

                # Determine color
                color = COLORS[color_idx % len(COLORS)]
                color_idx += 1

                # Determine which Y-axis to use
                axis_num = settings.channel_axis_map.get(channel, 1) if self.is_primary else 1

                # Create plot curve
                pen = pg.mkPen(color=color, width=1.5)
                curve = pg.PlotDataItem(
                    x_clean, y_clean,
                    pen=pen,
                    name=channel,
                    # Temporarily disable optimizations to fix rendering issue
                    autoDownsample=False,
                    clipToView=False
                )

                # Add to appropriate axis
                if self.is_primary and axis_num > 1 and axis_num <= len(self.y_axes):
                    self.y_axes[axis_num - 1].addItem(curve)
                else:
                    self.plot_item.addItem(curve)

                self._series.append(curve)

                # Store data for crosshair readout
                series_name = f"{channel}"
                if len(tests) > 1:
                    test = self.filter_manager.get_test(test_id)
                    if test:
                        series_name = f"{test.name}: {channel}"
                self._series_data[series_name] = (x_clean, y_clean)

        # Update axis labels and ranges
        self._update_axis_settings(settings)

        # Auto-range
        if settings.x_autoscale:
            self.plot_item.enableAutoRange(axis="x")
        else:
            if settings.x_min is not None and settings.x_max is not None:
                self.plot_item.setXRange(settings.x_min, settings.x_max)

        for i, autoscale in enumerate(settings.y_autoscales[:len(self.y_axes)]):
            if autoscale:
                self.y_axes[i].enableAutoRange(axis="y")
            else:
                y_min = settings.y_mins[i] if i < len(settings.y_mins) else None
                y_max = settings.y_maxs[i] if i < len(settings.y_maxs) else None
                if y_min is not None and y_max is not None:
                    self.y_axes[i].setYRange(y_min, y_max)

        # Update views for secondary axes
        if self.is_primary:
            self._update_views()

    def _update_axis_settings(self, settings: PlotSettings):
        """Update axis labels and settings."""
        # X-axis
        x_label = settings.x_label
        if settings.x_unit:
            x_label += f" ({settings.x_unit})"
        self.plot_item.setLabel("bottom", x_label)

        # Y-axes
        for i, axis_item in enumerate(self.y_axis_items):
            if i < len(settings.y_labels):
                y_label = settings.y_labels[i]
                if i < len(settings.y_units) and settings.y_units[i]:
                    y_label += f" ({settings.y_units[i]})"
                axis_item.setLabel(y_label, color=AXIS_COLORS[i])

    def clear_plot(self):
        """Clear all series from the plot."""
        for item in self._series:
            self.plot_item.removeItem(item)
        self._series.clear()
        self._series_data.clear()
        self.readout.clear()

    def get_visible_range(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """Get the current visible X and Y ranges."""
        view_range = self.plot_item.viewRange()
        return (tuple(view_range[0]), tuple(view_range[1]))

    def set_title(self, title: str):
        """Set the plot title."""
        self.title_label.setText(title)

    def resizeEvent(self, event):
        """Handle resize event."""
        super().resizeEvent(event)
        if self.is_primary:
            self._update_views()

    def showEvent(self, event):
        """Handle show event to initialize view geometry."""
        super().showEvent(event)
        if self.is_primary:
            # Delay the update slightly to ensure geometry is ready
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, self._update_views)

