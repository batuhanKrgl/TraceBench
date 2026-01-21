"""
Widget components for the Log Viewer application.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core import (
    ChannelMetadata,
    CompareMode,
    FilterManager,
    PlotSettings,
    Test,
)
from ..plot import MultiAxisPlotWidget


class TestTreeWidget(QWidget):
    """Widget displaying tests and their data files in a tree structure."""

    test_selected = Signal(str)  # test_id
    file_selected = Signal(str)  # file_id
    delete_requested = Signal(str)  # item_id

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._tests: dict[str, Test] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Files"])
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.tree)

    def add_test(self, test: Test) -> None:
        """Add a test to the tree."""
        self._tests[test.id] = test

        test_item = QTreeWidgetItem([test.name, str(len(test.data_files))])
        test_item.setData(0, Qt.ItemDataRole.UserRole, test.id)
        test_item.setData(0, Qt.ItemDataRole.UserRole + 1, "test")

        # Set color indicator
        test_item.setForeground(0, QColor(test.color))

        # Add file children
        for df in test.data_files:
            file_item = QTreeWidgetItem([df.filename, ""])
            file_item.setData(0, Qt.ItemDataRole.UserRole, df.id)
            file_item.setData(0, Qt.ItemDataRole.UserRole + 1, "file")
            test_item.addChild(file_item)

        self.tree.addTopLevelItem(test_item)
        test_item.setExpanded(True)

    def remove_test(self, test_id: str) -> None:
        """Remove a test from the tree."""
        if test_id in self._tests:
            del self._tests[test_id]

        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == test_id:
                self.tree.takeTopLevelItem(i)
                break

    def refresh_test(self, test: Test) -> None:
        """Refresh a test's display in the tree."""
        self._tests[test.id] = test

        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == test.id:
                # Update test info
                item.setText(0, test.name)
                item.setText(1, str(len(test.data_files)))

                # Remove old file items
                while item.childCount() > 0:
                    item.removeChild(item.child(0))

                # Add updated file items
                for df in test.data_files:
                    file_item = QTreeWidgetItem([df.filename, ""])
                    file_item.setData(0, Qt.ItemDataRole.UserRole, df.id)
                    file_item.setData(0, Qt.ItemDataRole.UserRole + 1, "file")
                    item.addChild(file_item)

                break

    def clear(self) -> None:
        """Clear all items from the tree."""
        self._tests.clear()
        self.tree.clear()

    def get_selected_tests(self) -> list[str]:
        """Get IDs of selected tests."""
        selected = []
        for item in self.tree.selectedItems():
            item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if item_type == "test":
                selected.append(item.data(0, Qt.ItemDataRole.UserRole))
            elif item_type == "file":
                # If file is selected, include its parent test
                parent = item.parent()
                if parent:
                    test_id = parent.data(0, Qt.ItemDataRole.UserRole)
                    if test_id not in selected:
                        selected.append(test_id)
        return selected

    def get_selected_file(self) -> Optional[str]:
        """Get ID of the first selected file."""
        for item in self.tree.selectedItems():
            item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if item_type == "file":
                return item.data(0, Qt.ItemDataRole.UserRole)
        return None

    def _on_selection_changed(self):
        """Handle selection change."""
        selected = self.tree.selectedItems()
        if not selected:
            return

        item = selected[0]
        item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
        item_id = item.data(0, Qt.ItemDataRole.UserRole)

        if item_type == "test":
            self.test_selected.emit(item_id)
        elif item_type == "file":
            self.file_selected.emit(item_id)

    def _show_context_menu(self, pos):
        """Show context menu for tree items."""
        item = self.tree.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)

        item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
        item_id = item.data(0, Qt.ItemDataRole.UserRole)

        if item_type == "test":
            rename_action = QAction("Rename Test", self)
            rename_action.triggered.connect(lambda: self._rename_test(item))
            menu.addAction(rename_action)

            menu.addSeparator()

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.delete_requested.emit(item_id))
        menu.addAction(delete_action)

        menu.exec(self.tree.mapToGlobal(pos))

    def _rename_test(self, item: QTreeWidgetItem):
        """Start editing the test name."""
        self.tree.editItem(item, 0)


class ChannelSelector(QWidget):
    """Widget for selecting channels, organized by category and unit."""

    channels_selected = Signal(list)  # List of channel names
    axis_assignment_changed = Signal(str, int)  # channel, axis

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._channels: dict[str, dict[str, list[str]]] = {}
        self._metadata: dict[str, ChannelMetadata] = {}
        self._selected: set[str] = set()
        self._axis_assignments: dict[str, int] = {}  # channel -> axis (1, 2, 3)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Search box
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search channels...")
        self.search_edit.textChanged.connect(self._filter_channels)
        layout.addWidget(self.search_edit)

        # Tree for channel selection
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Channel", "Y-Axis"])
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.NoSelection)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setStretchLastSection(False)
        self.tree.itemChanged.connect(self._on_item_changed)

        layout.addWidget(self.tree)

        # Quick actions
        actions_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all)
        actions_layout.addWidget(select_all_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_selection)
        actions_layout.addWidget(clear_btn)

        layout.addLayout(actions_layout)

    def set_channels(
        self,
        channels_by_category: dict[str, dict[str, list[str]]],
        metadata: dict[str, ChannelMetadata]
    ) -> None:
        """Set the available channels."""
        self._channels = channels_by_category
        self._metadata = metadata
        self._rebuild_tree()

    def _rebuild_tree(self):
        """Rebuild the tree widget from channel data."""
        self.tree.blockSignals(True)
        self.tree.clear()

        search_text = self.search_edit.text().lower()

        for category, units in sorted(self._channels.items()):
            cat_item = QTreeWidgetItem([category, ""])
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)

            has_children = False

            for unit, channels in sorted(units.items()):
                unit_label = f"[{unit}]" if unit else "[No Unit]"
                unit_item = QTreeWidgetItem([unit_label, ""])
                unit_item.setFlags(unit_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)

                unit_has_children = False

                for channel in sorted(channels):
                    # Apply search filter
                    if search_text and search_text not in channel.lower():
                        meta = self._metadata.get(channel)
                        if meta and search_text not in meta.display_name.lower():
                            continue

                    meta = self._metadata.get(channel)
                    display_name = meta.display_name if meta else channel

                    ch_item = QTreeWidgetItem([display_name, ""])
                    ch_item.setData(0, Qt.ItemDataRole.UserRole, channel)
                    ch_item.setFlags(
                        ch_item.flags() |
                        Qt.ItemFlag.ItemIsUserCheckable
                    )
                    ch_item.setCheckState(
                        0,
                        Qt.CheckState.Checked if channel in self._selected else Qt.CheckState.Unchecked
                    )

                    # Add axis selector as text (Y1, Y2, Y3)
                    axis = self._axis_assignments.get(channel, 1)
                    ch_item.setText(1, f"Y{axis}")
                    ch_item.setData(1, Qt.ItemDataRole.UserRole, axis)

                    unit_item.addChild(ch_item)
                    unit_has_children = True

                if unit_has_children:
                    cat_item.addChild(unit_item)
                    has_children = True

            if has_children:
                self.tree.addTopLevelItem(cat_item)
                cat_item.setExpanded(True)

        self.tree.blockSignals(False)

    def _filter_channels(self, text: str):
        """Filter channels based on search text."""
        self._rebuild_tree()

    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        """Handle item check state change."""
        channel = item.data(0, Qt.ItemDataRole.UserRole)
        if not channel:
            return

        if column == 0:
            # Checkbox changed
            if item.checkState(0) == Qt.CheckState.Checked:
                self._selected.add(channel)
            else:
                self._selected.discard(channel)

            self.channels_selected.emit(list(self._selected))

    def _select_all(self):
        """Select all visible channels."""
        self._iterate_items(lambda item: item.setCheckState(0, Qt.CheckState.Checked))

    def _clear_selection(self):
        """Clear all selections."""
        self._selected.clear()
        self._axis_assignments.clear()
        self._iterate_items(lambda item: item.setCheckState(0, Qt.CheckState.Unchecked))
        self.channels_selected.emit([])

    def _iterate_items(self, func):
        """Iterate over all channel items and apply a function."""
        self.tree.blockSignals(True)

        for i in range(self.tree.topLevelItemCount()):
            cat_item = self.tree.topLevelItem(i)
            for j in range(cat_item.childCount()):
                unit_item = cat_item.child(j)
                for k in range(unit_item.childCount()):
                    ch_item = unit_item.child(k)
                    func(ch_item)
                    channel = ch_item.data(0, Qt.ItemDataRole.UserRole)
                    if channel:
                        if ch_item.checkState(0) == Qt.CheckState.Checked:
                            self._selected.add(channel)
                        else:
                            self._selected.discard(channel)

        self.tree.blockSignals(False)
        self.channels_selected.emit(list(self._selected))

    def get_selected_channels(self) -> list[str]:
        """Get list of selected channel names."""
        return list(self._selected)

    def get_axis_assignments(self) -> dict[str, int]:
        """Get the axis assignments for selected channels."""
        return dict(self._axis_assignments)

    def set_axis_for_channel(self, channel: str, axis: int):
        """Set the Y-axis assignment for a channel."""
        if 1 <= axis <= 3:
            self._axis_assignments[channel] = axis
            self._rebuild_tree()
            self.axis_assignment_changed.emit(channel, axis)

    def cycle_axis_for_channel(self, channel: str):
        """Cycle through Y1 -> Y2 -> Y3 -> Y1 for a channel."""
        current = self._axis_assignments.get(channel, 1)
        new_axis = (current % 3) + 1
        self.set_axis_for_channel(channel, new_axis)


class FilterPanel(QWidget):
    """Collapsible panel for filter controls."""

    def __init__(
        self,
        filter_manager: FilterManager,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.filter_manager = filter_manager
        self._current_test: Optional[Test] = None

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Collapsible frame
        self.frame = QFrame()
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame_layout = QVBoxLayout(self.frame)
        frame_layout.setContentsMargins(5, 5, 5, 5)

        # Header with collapse button
        header_layout = QHBoxLayout()
        self.collapse_btn = QPushButton("Filters")
        self.collapse_btn.setCheckable(True)
        self.collapse_btn.setChecked(True)
        self.collapse_btn.clicked.connect(self._toggle_collapse)
        header_layout.addWidget(self.collapse_btn)
        header_layout.addStretch()

        # Enable checkbox
        self.enable_check = QCheckBox("Enable Filters")
        self.enable_check.setChecked(True)
        self.enable_check.stateChanged.connect(self._on_enable_changed)
        header_layout.addWidget(self.enable_check)

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_filters)
        header_layout.addWidget(clear_btn)

        frame_layout.addLayout(header_layout)

        # Content (collapsible)
        self.content_widget = QWidget()
        content_layout = QGridLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Time range
        content_layout.addWidget(QLabel("Time Range:"), 0, 0)

        self.time_min_spin = QDoubleSpinBox()
        self.time_min_spin.setRange(-1e9, 1e9)
        self.time_min_spin.setDecimals(4)
        self.time_min_spin.setSpecialValueText("Min")
        self.time_min_spin.valueChanged.connect(self._on_time_changed)
        content_layout.addWidget(self.time_min_spin, 0, 1)

        content_layout.addWidget(QLabel("to"), 0, 2)

        self.time_max_spin = QDoubleSpinBox()
        self.time_max_spin.setRange(-1e9, 1e9)
        self.time_max_spin.setDecimals(4)
        self.time_max_spin.setSpecialValueText("Max")
        self.time_max_spin.valueChanged.connect(self._on_time_changed)
        content_layout.addWidget(self.time_max_spin, 0, 3)

        # Time slider
        self.time_slider = QSlider(Qt.Orientation.Horizontal)
        self.time_slider.setRange(0, 1000)
        self.time_slider.valueChanged.connect(self._on_slider_changed)
        content_layout.addWidget(self.time_slider, 1, 0, 1, 4)

        # Channel filter
        content_layout.addWidget(QLabel("Channel Filter:"), 2, 0)

        self.channel_combo = QComboBox()
        self.channel_combo.currentTextChanged.connect(self._on_channel_selected)
        content_layout.addWidget(self.channel_combo, 2, 1)

        self.chan_min_spin = QDoubleSpinBox()
        self.chan_min_spin.setRange(-1e9, 1e9)
        self.chan_min_spin.setDecimals(4)
        self.chan_min_spin.valueChanged.connect(self._on_channel_filter_changed)
        content_layout.addWidget(self.chan_min_spin, 2, 2)

        self.chan_max_spin = QDoubleSpinBox()
        self.chan_max_spin.setRange(-1e9, 1e9)
        self.chan_max_spin.setDecimals(4)
        self.chan_max_spin.valueChanged.connect(self._on_channel_filter_changed)
        content_layout.addWidget(self.chan_max_spin, 2, 3)

        frame_layout.addWidget(self.content_widget)
        main_layout.addWidget(self.frame)

        # Start collapsed
        self.setMaximumHeight(120)

    def _toggle_collapse(self):
        """Toggle the collapsed state."""
        collapsed = not self.collapse_btn.isChecked()
        self.content_widget.setVisible(not collapsed)

        if collapsed:
            self.setMaximumHeight(40)
        else:
            self.setMaximumHeight(120)

    def set_test(self, test: Optional[Test]) -> None:
        """Set the current test for filtering."""
        self._current_test = test

        if test is None:
            self.channel_combo.clear()
            return

        # Update channel combo
        self.channel_combo.clear()
        self.channel_combo.addItem("")  # No channel filter
        self.channel_combo.addItems(test.canonical_headers)

        # Update time range
        time_min, time_max = test.get_time_range()
        self.time_min_spin.blockSignals(True)
        self.time_max_spin.blockSignals(True)
        self.time_min_spin.setRange(time_min, time_max)
        self.time_max_spin.setRange(time_min, time_max)
        self.time_min_spin.setValue(time_min)
        self.time_max_spin.setValue(time_max)
        self.time_min_spin.blockSignals(False)
        self.time_max_spin.blockSignals(False)

        # Restore filter state
        fs = test.filter_state
        if fs.time_min is not None:
            self.time_min_spin.setValue(fs.time_min)
        if fs.time_max is not None:
            self.time_max_spin.setValue(fs.time_max)

        self.enable_check.setChecked(fs.enabled)

    def refresh(self):
        """Refresh the filter panel."""
        if self._current_test:
            self.set_test(self._current_test)

    def _on_enable_changed(self, state: int):
        """Handle enable checkbox change."""
        if self._current_test:
            self.filter_manager.set_filter_enabled(
                self._current_test.id,
                state == Qt.CheckState.Checked.value
            )

    def _on_time_changed(self):
        """Handle time range change."""
        if self._current_test:
            self.filter_manager.set_time_range(
                self._current_test.id,
                self.time_min_spin.value(),
                self.time_max_spin.value()
            )

    def _on_slider_changed(self, value: int):
        """Handle time slider change."""
        if not self._current_test:
            return

        time_min, time_max = self._current_test.get_time_range()
        duration = time_max - time_min

        # Slider represents the visible window start position
        window_size = duration * 0.1  # 10% window
        position = (value / 1000.0) * (duration - window_size)

        self.time_min_spin.blockSignals(True)
        self.time_max_spin.blockSignals(True)
        self.time_min_spin.setValue(time_min + position)
        self.time_max_spin.setValue(time_min + position + window_size)
        self.time_min_spin.blockSignals(False)
        self.time_max_spin.blockSignals(False)

        self._on_time_changed()

    def _on_channel_selected(self, channel: str):
        """Handle channel selection for value filter."""
        if not channel or not self._current_test:
            return

        # Get channel range
        from ..core import ChannelFilterHelper
        df = self._current_test.get_merged_dataframe(apply_filter=False)
        min_val, max_val = ChannelFilterHelper.compute_channel_range(df, channel)

        self.chan_min_spin.setRange(min_val, max_val)
        self.chan_max_spin.setRange(min_val, max_val)
        self.chan_min_spin.setValue(min_val)
        self.chan_max_spin.setValue(max_val)

    def _on_channel_filter_changed(self):
        """Handle channel value filter change."""
        if not self._current_test:
            return

        channel = self.channel_combo.currentText()
        if not channel:
            return

        self.filter_manager.set_channel_filter(
            self._current_test.id,
            channel,
            self.chan_min_spin.value(),
            self.chan_max_spin.value()
        )

    def _clear_filters(self):
        """Clear all filters."""
        if self._current_test:
            self.filter_manager.clear_filters(self._current_test.id)
            self.refresh()


class PlotContainer(QWidget):
    """Container for multiple plot panels."""

    def __init__(
        self,
        filter_manager: FilterManager,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.filter_manager = filter_manager

        self._plots: list[MultiAxisPlotWidget] = []
        self._settings: list[PlotSettings] = []
        self._selected_tests: list[str] = []
        self._selected_channels: list[str] = []
        self._compare_mode = CompareMode.OVERLAY
        self._compare_gap = 0.0

        self._setup_ui()
        self.add_plot()  # Start with one plot

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.layout.addWidget(self.splitter)

    @property
    def plot_count(self) -> int:
        """Get the number of plot panels."""
        return len(self._plots)

    def add_plot(self) -> None:
        """Add a new plot panel."""
        if len(self._plots) >= 3:
            return

        is_primary = len(self._plots) == 0
        plot = MultiAxisPlotWidget(
            is_primary=is_primary,
            filter_manager=self.filter_manager
        )

        settings = PlotSettings()
        self._plots.append(plot)
        self._settings.append(settings)

        self.splitter.addWidget(plot)

        # Connect crosshair sync
        plot.crosshair_moved.connect(self._sync_crosshairs)

        # Connect axis settings
        plot.axis_settings_requested.connect(self._show_axis_settings)

    def remove_plot(self) -> None:
        """Remove the last plot panel."""
        if len(self._plots) <= 1:
            return

        plot = self._plots.pop()
        self._settings.pop()
        plot.setParent(None)
        plot.deleteLater()

    def set_plot_count(self, count: int) -> None:
        """Set the number of plot panels."""
        count = max(1, min(3, count))

        while len(self._plots) < count:
            self.add_plot()
        while len(self._plots) > count:
            self.remove_plot()

    def set_selected_tests(self, test_ids: list[str]) -> None:
        """Set the selected tests for plotting."""
        self._selected_tests = test_ids
        for i, settings in enumerate(self._settings):
            settings.selected_tests = test_ids
        self.refresh_plots()

    def set_selected_channels(self, channels: list[str]) -> None:
        """Set the selected channels for plotting."""
        self._selected_channels = channels
        for i, settings in enumerate(self._settings):
            settings.selected_channels = channels
        self.refresh_plots()

    def set_channel_axis(self, channel: str, axis: int) -> None:
        """Set the Y-axis assignment for a channel (primary plot only)."""
        if self._plots:
            self._settings[0].channel_axis_map[channel] = axis
            self.refresh_plots()

    def set_compare_mode(self, mode: CompareMode, gap: float = 0.0) -> None:
        """Set the comparison mode."""
        self._compare_mode = mode
        self._compare_gap = gap
        self.refresh_plots()

    def refresh_plots(self) -> None:
        """Refresh all plots with current data."""
        for i, (plot, settings) in enumerate(zip(self._plots, self._settings)):
            plot.update_plot(
                test_ids=self._selected_tests,
                channels=self._selected_channels,
                settings=settings,
                compare_mode=self._compare_mode,
                compare_gap=self._compare_gap
            )

    def get_all_settings(self) -> list[PlotSettings]:
        """Get settings for all plots."""
        return list(self._settings)

    def restore_settings(self, settings_list: list[PlotSettings]) -> None:
        """Restore plot settings from a list."""
        for i, settings in enumerate(settings_list):
            if i < len(self._settings):
                self._settings[i] = settings
        self.refresh_plots()

    @Slot(float)
    def _sync_crosshairs(self, x_value: float):
        """Synchronize crosshairs across all plots."""
        for plot in self._plots:
            plot.set_crosshair_x(x_value, emit_signal=False)

    @Slot(int)
    def _show_axis_settings(self, plot_index: int):
        """Show axis settings dialog for a plot."""
        if plot_index >= len(self._settings):
            return

        settings = self._settings[plot_index]
        is_primary = plot_index == 0
        num_y_axes = 3 if is_primary else 1

        from .dialogs import AxisSettingsDialog

        dialog = AxisSettingsDialog(
            x_label=settings.x_label,
            x_unit=settings.x_unit,
            x_min=settings.x_min,
            x_max=settings.x_max,
            x_autoscale=settings.x_autoscale,
            y_labels=settings.y_labels,
            y_units=settings.y_units,
            y_mins=settings.y_mins,
            y_maxs=settings.y_maxs,
            y_autoscales=settings.y_autoscales,
            num_y_axes=num_y_axes,
            parent=self
        )

        if dialog.exec() == dialog.Accepted:
            result = dialog.get_result()
            settings.x_label = result["x_label"]
            settings.x_unit = result["x_unit"]
            settings.x_min = result["x_min"]
            settings.x_max = result["x_max"]
            settings.x_autoscale = result["x_autoscale"]
            settings.y_labels = result["y_labels"]
            settings.y_units = result["y_units"]
            settings.y_mins = result["y_mins"]
            settings.y_maxs = result["y_maxs"]
            settings.y_autoscales = result["y_autoscales"]

            self.refresh_plots()
