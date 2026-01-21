"""
Main Window for the Log Viewer application.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QProgressDialog,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..core import (
    AppLayout,
    CompareMode,
    FileReader,
    FilterManager,
    PlotSettings,
    Test,
)
from .dialogs import (
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


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Log Viewer & Comparator")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        # Core data
        self.tests: list[Test] = []
        self.file_reader = FileReader()
        self.filter_manager = FilterManager(self)

        # Comparison settings
        self.compare_mode = CompareMode.OVERLAY
        self.compare_gap = 0.0

        # UI components (will be set up in _setup_ui)
        self.test_tree: Optional[TestTreeWidget] = None
        self.channel_selector: Optional[ChannelSelector] = None
        self.filter_panel: Optional[FilterPanel] = None
        self.plot_container: Optional[PlotContainer] = None

        self._setup_ui()
        self._setup_menus()
        self._setup_toolbar()
        self._setup_connections()

        # Status bar
        self.statusBar().showMessage("Ready")

    def _setup_ui(self):
        """Set up the main UI layout."""
        # Central widget with splitter
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create main splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.main_splitter)

        # Left dock: Tests/DataFiles tree
        self.test_tree = TestTreeWidget()
        left_dock = QDockWidget("Tests && Files", self)
        left_dock.setWidget(self.test_tree)
        left_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        left_dock.setMinimumWidth(200)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, left_dock)

        # Center: Plot area + Filter panel (collapsible on top)
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        # Filter panel (collapsible)
        self.filter_panel = FilterPanel(self.filter_manager)
        center_layout.addWidget(self.filter_panel)

        # Plot container
        self.plot_container = PlotContainer(self.filter_manager)
        center_layout.addWidget(self.plot_container, 1)

        self.main_splitter.addWidget(center_widget)

        # Right dock: Channel selector
        self.channel_selector = ChannelSelector()
        right_dock = QDockWidget("Channels", self)
        right_dock.setWidget(self.channel_selector)
        right_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        right_dock.setMinimumWidth(250)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, right_dock)

    def _setup_menus(self):
        """Set up the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        new_test_action = QAction("New Test", self)
        new_test_action.setShortcut(QKeySequence.StandardKey.New)
        new_test_action.triggered.connect(self.on_new_test)
        file_menu.addAction(new_test_action)

        import_files_action = QAction("Import Files...", self)
        import_files_action.setShortcut(QKeySequence("Ctrl+I"))
        import_files_action.triggered.connect(self.on_import_files)
        file_menu.addAction(import_files_action)

        add_files_action = QAction("Add Files to Test...", self)
        add_files_action.triggered.connect(self.on_add_files_to_test)
        file_menu.addAction(add_files_action)

        add_headers_action = QAction("Add Headers File...", self)
        add_headers_action.triggered.connect(self.on_add_headers_file)
        file_menu.addAction(add_headers_action)

        file_menu.addSeparator()

        save_layout_action = QAction("Save Layout...", self)
        save_layout_action.setShortcut(QKeySequence.StandardKey.Save)
        save_layout_action.triggered.connect(self.on_save_layout)
        file_menu.addAction(save_layout_action)

        load_layout_action = QAction("Load Layout...", self)
        load_layout_action.setShortcut(QKeySequence.StandardKey.Open)
        load_layout_action.triggered.connect(self.on_load_layout)
        file_menu.addAction(load_layout_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")

        time_settings_action = QAction("Time Settings...", self)
        time_settings_action.triggered.connect(self.on_time_settings)
        edit_menu.addAction(time_settings_action)

        clear_filters_action = QAction("Clear All Filters", self)
        clear_filters_action.triggered.connect(self.on_clear_filters)
        edit_menu.addAction(clear_filters_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        add_plot_action = QAction("Add Plot Panel", self)
        add_plot_action.setShortcut(QKeySequence("Ctrl+P"))
        add_plot_action.triggered.connect(self.on_add_plot)
        view_menu.addAction(add_plot_action)

        remove_plot_action = QAction("Remove Plot Panel", self)
        remove_plot_action.triggered.connect(self.on_remove_plot)
        view_menu.addAction(remove_plot_action)

        view_menu.addSeparator()

        self.toggle_filter_action = QAction("Show Filter Panel", self)
        self.toggle_filter_action.setCheckable(True)
        self.toggle_filter_action.setChecked(True)
        self.toggle_filter_action.triggered.connect(self.on_toggle_filter_panel)
        view_menu.addAction(self.toggle_filter_action)

        # Compare menu
        compare_menu = menubar.addMenu("&Compare")

        overlay_action = QAction("Overlay Mode", self)
        overlay_action.setCheckable(True)
        overlay_action.setChecked(True)
        overlay_action.triggered.connect(lambda: self.set_compare_mode(CompareMode.OVERLAY))
        compare_menu.addAction(overlay_action)

        concat_action = QAction("Concatenate Mode", self)
        concat_action.setCheckable(True)
        concat_action.triggered.connect(lambda: self.set_compare_mode(CompareMode.CONCATENATE))
        compare_menu.addAction(concat_action)

        # Group actions
        self.compare_action_group = [overlay_action, concat_action]

        compare_menu.addSeparator()

        set_gap_action = QAction("Set Concatenate Gap...", self)
        set_gap_action.triggered.connect(self.on_set_compare_gap)
        compare_menu.addAction(set_gap_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self.on_about)
        help_menu.addAction(about_action)

    def _setup_toolbar(self):
        """Set up the toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        toolbar.addAction("New Test", self.on_new_test)
        toolbar.addAction("Import", self.on_import_files)
        toolbar.addSeparator()
        toolbar.addAction("Add Plot", self.on_add_plot)
        toolbar.addSeparator()
        toolbar.addAction("Save", self.on_save_layout)
        toolbar.addAction("Load", self.on_load_layout)

    def _setup_connections(self):
        """Set up signal/slot connections."""
        # Test tree signals
        self.test_tree.test_selected.connect(self.on_test_selected)
        self.test_tree.file_selected.connect(self.on_file_selected)
        self.test_tree.delete_requested.connect(self.on_delete_item)

        # Channel selector signals
        self.channel_selector.channels_selected.connect(self.on_channels_selected)
        self.channel_selector.axis_assignment_changed.connect(self.on_axis_assignment_changed)

        # Filter manager signals
        self.filter_manager.filter_changed.connect(self.on_filter_changed)

    def _update_channel_selector(self):
        """Update channel selector with channels from selected tests."""
        selected_tests = self.test_tree.get_selected_tests()
        if not selected_tests:
            self.channel_selector.set_channels({}, {})
            return

        # Combine channels from selected tests
        all_channels: list[str] = []
        metadata: dict = {}

        for test_id in selected_tests:
            test = self._get_test_by_id(test_id)
            if test:
                for ch in test.canonical_headers:
                    if ch not in all_channels:
                        all_channels.append(ch)
                        if ch in test.canonical_metadata:
                            metadata[ch] = test.canonical_metadata[ch]

        # Organize by category
        by_category = {}
        for ch in all_channels:
            meta = metadata.get(ch)
            cat = meta.category if meta else "Unknown"
            unit = meta.unit if meta else ""

            if cat not in by_category:
                by_category[cat] = {}
            if unit not in by_category[cat]:
                by_category[cat][unit] = []
            by_category[cat][unit].append(ch)

        self.channel_selector.set_channels(by_category, metadata)

    def _get_test_by_id(self, test_id: str) -> Optional[Test]:
        """Get a test by its ID."""
        for test in self.tests:
            if test.id == test_id:
                return test
        return None

    # =========================================================================
    # Slots
    # =========================================================================

    @Slot()
    def on_new_test(self):
        """Create a new empty test."""
        test = Test(name=f"Test {len(self.tests) + 1}")
        self.tests.append(test)
        self.filter_manager.register_test(test)
        self.test_tree.add_test(test)
        self.statusBar().showMessage(f"Created new test: {test.name}")

    @Slot()
    def on_import_files(self):
        """Import files into a new test."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Import Data Files",
            "",
            "Data Files (*.csv *.tsv *.txt *.xlsx *.xls);;All Files (*)"
        )

        if not files:
            return

        # Create new test
        test = Test(name=f"Test {len(self.tests) + 1}")

        # Show progress
        progress = QProgressDialog("Importing files...", "Cancel", 0, len(files), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        for i, filepath in enumerate(files):
            if progress.wasCanceled():
                break

            progress.setValue(i)
            progress.setLabelText(f"Importing {Path(filepath).name}...")

            try:
                data_file = self.file_reader.read_file(filepath)
                test.add_data_file(data_file)

                # Set primary time column if not set
                if not test.primary_time_column and data_file.time_column:
                    test.primary_time_column = data_file.time_column

            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Import Error",
                    f"Failed to import {filepath}:\n{str(e)}"
                )

        progress.close()

        if test.data_files:
            self.tests.append(test)
            self.filter_manager.register_test(test)
            self.test_tree.add_test(test)
            self._update_channel_selector()
            self.statusBar().showMessage(
                f"Imported {len(test.data_files)} file(s) into {test.name}"
            )

    @Slot()
    def on_add_files_to_test(self):
        """Add files to an existing test."""
        selected = self.test_tree.get_selected_tests()
        if not selected:
            QMessageBox.information(
                self, "No Test Selected",
                "Please select a test first."
            )
            return

        test = self._get_test_by_id(selected[0])
        if not test:
            return

        files, _ = QFileDialog.getOpenFileNames(
            self,
            f"Add Files to {test.name}",
            "",
            "Data Files (*.csv *.tsv *.txt *.xlsx *.xls);;All Files (*)"
        )

        if not files:
            return

        for filepath in files:
            try:
                data_file = self.file_reader.read_file(filepath)

                # Check header compatibility
                if test.canonical_headers:
                    from ..core import compute_header_diff
                    diff = compute_header_diff(test.canonical_headers, data_file.headers)

                    if diff.has_differences:
                        dialog = HeaderDiffDialog(diff, self)
                        result = dialog.exec()

                        if result == HeaderDiffDialog.Rejected:
                            continue

                        strategy, mappings = dialog.get_result()
                        if mappings:
                            from ..core import apply_header_mapping
                            apply_header_mapping(data_file, mappings)

                test.add_data_file(data_file)
                self.test_tree.refresh_test(test)

            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Import Error",
                    f"Failed to add {filepath}:\n{str(e)}"
                )

        self._update_channel_selector()
        self.statusBar().showMessage(f"Added files to {test.name}")

    @Slot()
    def on_add_headers_file(self):
        """Add a headers file (merge additional columns) to a test."""
        selected = self.test_tree.get_selected_tests()
        if not selected:
            QMessageBox.information(
                self, "No Test Selected",
                "Please select a test first."
            )
            return

        test = self._get_test_by_id(selected[0])
        if not test:
            return

        filepath, _ = QFileDialog.getOpenFileName(
            self,
            f"Add Headers File to {test.name}",
            "",
            "Data Files (*.csv *.tsv *.txt *.xlsx *.xls);;All Files (*)"
        )

        if not filepath:
            return

        try:
            data_file = self.file_reader.read_file(filepath)

            # Show join options dialog
            dialog = JoinOptionsDialog(test, data_file, self)
            if dialog.exec() == JoinOptionsDialog.Accepted:
                join_strategy, join_key, tolerance = dialog.get_result()

                from ..core import add_headers_file_to_test
                add_headers_file_to_test(
                    test, data_file,
                    join_strategy=join_strategy,
                    join_key=join_key,
                    join_tolerance=tolerance
                )

                self.test_tree.refresh_test(test)
                self._update_channel_selector()
                self.statusBar().showMessage(f"Added headers from {data_file.filename}")

        except Exception as e:
            QMessageBox.warning(
                self,
                "Import Error",
                f"Failed to add headers file:\n{str(e)}"
            )

    @Slot()
    def on_save_layout(self):
        """Save current layout to a JSON file."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Layout",
            "",
            "JSON Files (*.json)"
        )

        if not filepath:
            return

        if not filepath.endswith(".json"):
            filepath += ".json"

        layout = AppLayout(
            tests=self.tests,
            plot_count=self.plot_container.plot_count,
            plot_settings=self.plot_container.get_all_settings(),
            compare_mode=self.compare_mode,
            compare_gap=self.compare_gap,
            window_width=self.width(),
            window_height=self.height()
        )

        try:
            with open(filepath, "w") as f:
                json.dump(layout.to_dict(), f, indent=2)

            self.statusBar().showMessage(f"Layout saved to {filepath}")

        except Exception as e:
            QMessageBox.warning(
                self,
                "Save Error",
                f"Failed to save layout:\n{str(e)}"
            )

    @Slot()
    def on_load_layout(self):
        """Load layout from a JSON file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Load Layout",
            "",
            "JSON Files (*.json)"
        )

        if not filepath:
            return

        try:
            with open(filepath, "r") as f:
                data = json.load(f)

            layout = AppLayout.from_dict(data)

            # Clear current state
            self.tests.clear()
            self.test_tree.clear()

            # Reload files with path remapping if needed
            for test in layout.tests:
                missing_files = []

                for data_file in test.data_files:
                    if not data_file.filepath.exists():
                        missing_files.append(data_file)
                    else:
                        # Reload the data
                        self.file_reader.reload_file(data_file)

                # Handle missing files
                for data_file in missing_files:
                    result = QMessageBox.question(
                        self,
                        "File Not Found",
                        f"File not found: {data_file.filepath}\n\n"
                        "Would you like to locate it?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )

                    if result == QMessageBox.StandardButton.Yes:
                        new_path, _ = QFileDialog.getOpenFileName(
                            self,
                            f"Locate {data_file.filename}",
                            "",
                            "Data Files (*.csv *.tsv *.txt *.xlsx *.xls);;All Files (*)"
                        )

                        if new_path:
                            data_file.filepath = Path(new_path)
                            self.file_reader.reload_file(data_file)

                self.tests.append(test)
                self.filter_manager.register_test(test)
                self.test_tree.add_test(test)

            # Restore compare mode
            self.compare_mode = layout.compare_mode
            self.compare_gap = layout.compare_gap
            for action in self.compare_action_group:
                action.setChecked(False)
            if self.compare_mode == CompareMode.OVERLAY:
                self.compare_action_group[0].setChecked(True)
            else:
                self.compare_action_group[1].setChecked(True)

            # Restore plot count and settings
            self.plot_container.set_plot_count(layout.plot_count)
            self.plot_container.restore_settings(layout.plot_settings)

            # Restore window size
            self.resize(layout.window_width, layout.window_height)

            self._update_channel_selector()
            self.statusBar().showMessage(f"Layout loaded from {filepath}")

        except Exception as e:
            QMessageBox.warning(
                self,
                "Load Error",
                f"Failed to load layout:\n{str(e)}"
            )

    @Slot()
    def on_time_settings(self):
        """Open time settings dialog for selected test/file."""
        selected_tests = self.test_tree.get_selected_tests()
        selected_file = self.test_tree.get_selected_file()

        if selected_file:
            # Find the data file
            for test in self.tests:
                df = test.get_data_file(selected_file)
                if df:
                    dialog = TimeSettingsDialog(df, self)
                    if dialog.exec() == TimeSettingsDialog.Accepted:
                        self.plot_container.refresh_plots()
                    return

        elif selected_tests:
            test = self._get_test_by_id(selected_tests[0])
            if test and test.data_files:
                dialog = TimeSettingsDialog(test.data_files[0], self)
                if dialog.exec() == TimeSettingsDialog.Accepted:
                    self.plot_container.refresh_plots()

    @Slot()
    def on_clear_filters(self):
        """Clear all filters for all tests."""
        for test in self.tests:
            self.filter_manager.clear_filters(test.id)
        self.filter_panel.refresh()
        self.statusBar().showMessage("All filters cleared")

    @Slot()
    def on_add_plot(self):
        """Add a new plot panel."""
        if self.plot_container.plot_count < 3:
            self.plot_container.add_plot()
            self.statusBar().showMessage(
                f"Added plot panel ({self.plot_container.plot_count}/3)"
            )
        else:
            self.statusBar().showMessage("Maximum 3 plot panels allowed")

    @Slot()
    def on_remove_plot(self):
        """Remove the last plot panel."""
        if self.plot_container.plot_count > 1:
            self.plot_container.remove_plot()
            self.statusBar().showMessage(
                f"Removed plot panel ({self.plot_container.plot_count}/3)"
            )
        else:
            self.statusBar().showMessage("At least 1 plot panel required")

    @Slot()
    def on_toggle_filter_panel(self):
        """Toggle the filter panel visibility."""
        visible = self.toggle_filter_action.isChecked()
        self.filter_panel.setVisible(visible)

    def set_compare_mode(self, mode: CompareMode):
        """Set the comparison mode."""
        self.compare_mode = mode

        # Update menu checkboxes
        for action in self.compare_action_group:
            action.setChecked(False)
        if mode == CompareMode.OVERLAY:
            self.compare_action_group[0].setChecked(True)
        else:
            self.compare_action_group[1].setChecked(True)

        # Update plot container
        self.plot_container.set_compare_mode(mode, self.compare_gap)
        self.statusBar().showMessage(f"Compare mode: {mode.name}")

    @Slot()
    def on_set_compare_gap(self):
        """Set the gap for concatenate mode."""
        from PySide6.QtWidgets import QInputDialog

        gap, ok = QInputDialog.getDouble(
            self,
            "Set Concatenate Gap",
            "Gap between tests (seconds):",
            self.compare_gap,
            0.0, 10000.0, 2
        )

        if ok:
            self.compare_gap = gap
            self.plot_container.set_compare_mode(self.compare_mode, gap)
            self.statusBar().showMessage(f"Concatenate gap set to {gap}s")

    @Slot()
    def on_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Log Viewer",
            "Log Viewer & Comparator\n\n"
            "A multi-test, multi-header data viewer and comparator.\n\n"
            "Features:\n"
            "- Multiple tests with multiple data files\n"
            "- Header parsing and mapping\n"
            "- Time alignment and synchronization\n"
            "- Multi-axis plotting (up to 3 Y-axes)\n"
            "- Crosshair and value readout\n"
            "- Filter synchronization\n"
            "- Layout save/load"
        )

    @Slot(str)
    def on_test_selected(self, test_id: str):
        """Handle test selection in tree."""
        self._update_channel_selector()
        self.filter_panel.set_test(self._get_test_by_id(test_id))

        # Update plot container with selected test
        self.plot_container.set_selected_tests([test_id])

    @Slot(str)
    def on_file_selected(self, file_id: str):
        """Handle file selection in tree."""
        pass  # Could show file details

    @Slot(str)
    def on_delete_item(self, item_id: str):
        """Handle delete request from tree."""
        # Check if it's a test
        test = self._get_test_by_id(item_id)
        if test:
            result = QMessageBox.question(
                self,
                "Delete Test",
                f"Delete test '{test.name}' and all its data?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if result == QMessageBox.StandardButton.Yes:
                self.filter_manager.unregister_test(test.id)
                self.tests.remove(test)
                self.test_tree.remove_test(test.id)
                self._update_channel_selector()
            return

        # Check if it's a file
        for test in self.tests:
            if test.remove_data_file(item_id):
                self.test_tree.refresh_test(test)
                self._update_channel_selector()
                return

    @Slot(list)
    def on_channels_selected(self, channels: list[str]):
        """Handle channel selection change."""
        self.plot_container.set_selected_channels(channels)

    @Slot(str, int)
    def on_axis_assignment_changed(self, channel: str, axis: int):
        """Handle axis assignment change for a channel."""
        self.plot_container.set_channel_axis(channel, axis)

    @Slot(str)
    def on_filter_changed(self, test_id: str):
        """Handle filter change for a test."""
        self.plot_container.refresh_plots()

    def get_tests(self) -> list[Test]:
        """Get all tests."""
        return self.tests

    def closeEvent(self, event):
        """Handle window close."""
        # Could prompt to save layout
        event.accept()
