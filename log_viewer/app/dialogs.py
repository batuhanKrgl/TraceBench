"""
Dialog windows for the Log Viewer application.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core import (
    DataFile,
    HeaderDiff,
    HeaderMismatchStrategy,
    JoinStrategy,
    Test,
    TimeMode,
)


class HeaderDiffDialog(QDialog):
    """Dialog for handling header differences between files."""

    def __init__(self, diff: HeaderDiff, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.diff = diff
        self.strategy = HeaderMismatchStrategy.UNION
        self.mappings: dict[str, str] = {}

        self.setWindowTitle("Header Mismatch")
        self.setMinimumSize(500, 400)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Summary
        summary_label = QLabel(self.diff.get_summary())
        summary_label.setWordWrap(True)
        layout.addWidget(summary_label)

        # Strategy selection
        strategy_group = QGroupBox("Resolution Strategy")
        strategy_layout = QVBoxLayout(strategy_group)

        self.strict_radio = QRadioButton("Strict - Reject import")
        self.strict_radio.toggled.connect(
            lambda: self._set_strategy(HeaderMismatchStrategy.STRICT)
        )
        strategy_layout.addWidget(self.strict_radio)

        self.union_radio = QRadioButton(
            "Union - Add new headers, missing values become NaN"
        )
        self.union_radio.setChecked(True)
        self.union_radio.toggled.connect(
            lambda: self._set_strategy(HeaderMismatchStrategy.UNION)
        )
        strategy_layout.addWidget(self.union_radio)

        self.map_radio = QRadioButton("Map/Rename - Map columns below")
        self.map_radio.toggled.connect(
            lambda: self._set_strategy(HeaderMismatchStrategy.MAP)
        )
        strategy_layout.addWidget(self.map_radio)

        layout.addWidget(strategy_group)

        # Mapping table (for fuzzy matches and manual mapping)
        mapping_group = QGroupBox("Column Mapping")
        mapping_layout = QVBoxLayout(mapping_group)

        self.mapping_table = QTableWidget()
        self.mapping_table.setColumnCount(3)
        self.mapping_table.setHorizontalHeaderLabels(
            ["File Column", "Map To", "Similarity"]
        )
        self.mapping_table.horizontalHeader().setStretchLastSection(True)

        # Populate with fuzzy matches first, then extra headers
        rows = []
        for file_col, test_col in self.diff.fuzzy_matches.items():
            rows.append((file_col, test_col, "suggested"))

        for extra in self.diff.extra:
            if extra not in self.diff.fuzzy_matches:
                rows.append((extra, "", "new"))

        self.mapping_table.setRowCount(len(rows))

        for i, (file_col, map_to, status) in enumerate(rows):
            # File column (read-only)
            file_item = QTableWidgetItem(file_col)
            file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.mapping_table.setItem(i, 0, file_item)

            # Map to (editable combo or text)
            combo = QComboBox()
            combo.setEditable(True)
            combo.addItem("")  # Keep as-is option
            combo.addItems(self.diff.missing)
            if map_to:
                combo.setCurrentText(map_to)
            self.mapping_table.setCellWidget(i, 1, combo)

            # Status
            status_item = QTableWidgetItem(status)
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.mapping_table.setItem(i, 2, status_item)

        self.mapping_table.resizeColumnsToContents()
        mapping_layout.addWidget(self.mapping_table)

        layout.addWidget(mapping_group)

        # Missing headers list
        if self.diff.missing:
            missing_group = QGroupBox(f"Missing Headers ({len(self.diff.missing)})")
            missing_layout = QVBoxLayout(missing_group)

            missing_list = QListWidget()
            missing_list.addItems(self.diff.missing)
            missing_layout.addWidget(missing_list)

            layout.addWidget(missing_group)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _set_strategy(self, strategy: HeaderMismatchStrategy):
        self.strategy = strategy
        self.mapping_table.setEnabled(strategy == HeaderMismatchStrategy.MAP)

    def get_result(self) -> tuple[HeaderMismatchStrategy, dict[str, str]]:
        """Get the selected strategy and column mappings."""
        if self.strategy == HeaderMismatchStrategy.MAP:
            # Collect mappings from table
            for i in range(self.mapping_table.rowCount()):
                file_col = self.mapping_table.item(i, 0).text()
                combo = self.mapping_table.cellWidget(i, 1)
                map_to = combo.currentText().strip()
                if map_to:
                    self.mappings[file_col] = map_to

        return self.strategy, self.mappings


class JoinOptionsDialog(QDialog):
    """Dialog for selecting join/merge options when adding a headers file."""

    def __init__(
        self,
        test: Test,
        new_file: DataFile,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.test = test
        self.new_file = new_file

        self.setWindowTitle("Join Options")
        self.setMinimumSize(400, 300)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Info
        info = QLabel(
            f"Adding columns from '{self.new_file.filename}' to '{self.test.name}'"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # Join strategy
        strategy_group = QGroupBox("Join Strategy")
        strategy_layout = QVBoxLayout(strategy_group)

        self.nearest_radio = QRadioButton("Time Nearest - Join on nearest time match")
        self.nearest_radio.setChecked(True)
        strategy_layout.addWidget(self.nearest_radio)

        self.exact_radio = QRadioButton("Time Exact - Join on exact time match")
        strategy_layout.addWidget(self.exact_radio)

        self.key_radio = QRadioButton("Alternative Key - Use different column as key")
        strategy_layout.addWidget(self.key_radio)

        self.append_radio = QRadioButton("Append Segment - Don't join, append as separate segment")
        strategy_layout.addWidget(self.append_radio)

        layout.addWidget(strategy_group)

        # Options
        options_group = QGroupBox("Options")
        options_layout = QFormLayout(options_group)

        # Key column selection
        self.key_combo = QComboBox()
        common_cols = set(self.new_file.headers) & set(self.test.canonical_headers)
        self.key_combo.addItems(sorted(common_cols))
        self.key_combo.setEnabled(False)
        options_layout.addRow("Key Column:", self.key_combo)

        # Tolerance for nearest join
        self.tolerance_spin = QDoubleSpinBox()
        self.tolerance_spin.setRange(0.0, 10.0)
        self.tolerance_spin.setDecimals(4)
        self.tolerance_spin.setValue(0.001)
        self.tolerance_spin.setSuffix(" s")
        options_layout.addRow("Time Tolerance:", self.tolerance_spin)

        layout.addWidget(options_group)

        # Connect radio buttons to enable/disable options
        self.key_radio.toggled.connect(
            lambda checked: self.key_combo.setEnabled(checked)
        )
        self.nearest_radio.toggled.connect(
            lambda checked: self.tolerance_spin.setEnabled(checked)
        )

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_result(self) -> tuple[JoinStrategy, Optional[str], float]:
        """Get the selected join options."""
        if self.nearest_radio.isChecked():
            strategy = JoinStrategy.TIME_NEAREST
        elif self.exact_radio.isChecked():
            strategy = JoinStrategy.TIME_EXACT
        elif self.key_radio.isChecked():
            strategy = JoinStrategy.ALTERNATIVE_KEY
        else:
            strategy = JoinStrategy.APPEND_SEGMENT

        key = self.key_combo.currentText() if strategy == JoinStrategy.ALTERNATIVE_KEY else None
        tolerance = self.tolerance_spin.value()

        return strategy, key, tolerance


class TimeSettingsDialog(QDialog):
    """Dialog for configuring time settings for a data file."""

    def __init__(self, data_file: DataFile, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.data_file = data_file

        self.setWindowTitle(f"Time Settings - {data_file.filename}")
        self.setMinimumSize(400, 300)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Time column selection
        col_group = QGroupBox("Time Column")
        col_layout = QFormLayout(col_group)

        self.time_col_combo = QComboBox()
        self.time_col_combo.addItems(self.data_file.headers)
        if self.data_file.time_column:
            idx = self.time_col_combo.findText(self.data_file.time_column)
            if idx >= 0:
                self.time_col_combo.setCurrentIndex(idx)
        col_layout.addRow("Time Column:", self.time_col_combo)

        layout.addWidget(col_group)

        # Time mode
        mode_group = QGroupBox("Time Mode")
        mode_layout = QVBoxLayout(mode_group)

        self.absolute_radio = QRadioButton("Absolute - Use timestamp as-is")
        self.relative_radio = QRadioButton("Relative - Start from zero")
        self.offset_radio = QRadioButton("Custom Offset - Apply user-defined offset")

        if self.data_file.time_mode == TimeMode.ABSOLUTE:
            self.absolute_radio.setChecked(True)
        elif self.data_file.time_mode == TimeMode.RELATIVE:
            self.relative_radio.setChecked(True)
        else:
            self.offset_radio.setChecked(True)

        mode_layout.addWidget(self.absolute_radio)
        mode_layout.addWidget(self.relative_radio)
        mode_layout.addWidget(self.offset_radio)

        layout.addWidget(mode_group)

        # Offset and scale
        adjust_group = QGroupBox("Adjustments")
        adjust_layout = QFormLayout(adjust_group)

        self.offset_spin = QDoubleSpinBox()
        self.offset_spin.setRange(-1e9, 1e9)
        self.offset_spin.setDecimals(6)
        self.offset_spin.setValue(self.data_file.time_offset)
        self.offset_spin.setSuffix(" s")
        adjust_layout.addRow("Time Offset:", self.offset_spin)

        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(0.001, 1000.0)
        self.scale_spin.setDecimals(6)
        self.scale_spin.setValue(self.data_file.time_scale)
        adjust_layout.addRow("Time Scale:", self.scale_spin)

        layout.addWidget(adjust_group)

        # Preview
        preview_group = QGroupBox("Time Range Preview")
        preview_layout = QFormLayout(preview_group)

        self.preview_label = QLabel()
        self._update_preview()
        preview_layout.addRow("Current Range:", self.preview_label)

        layout.addWidget(preview_group)

        # Connect signals for preview update
        self.time_col_combo.currentTextChanged.connect(self._update_preview)
        self.absolute_radio.toggled.connect(self._update_preview)
        self.relative_radio.toggled.connect(self._update_preview)
        self.offset_radio.toggled.connect(self._update_preview)
        self.offset_spin.valueChanged.connect(self._update_preview)
        self.scale_spin.valueChanged.connect(self._update_preview)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._apply_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _update_preview(self):
        """Update the time range preview."""
        if self.data_file.dataframe is None:
            self.preview_label.setText("No data loaded")
            return

        time_col = self.time_col_combo.currentText()
        if time_col not in self.data_file.dataframe.columns:
            self.preview_label.setText("Invalid time column")
            return

        time_data = self.data_file.dataframe[time_col].values

        if self.relative_radio.isChecked() and len(time_data) > 0:
            time_data = time_data - time_data[0]

        time_data = (time_data + self.offset_spin.value()) * self.scale_spin.value()

        if len(time_data) > 0:
            min_t = float(time_data.min())
            max_t = float(time_data.max())
            self.preview_label.setText(f"{min_t:.3f} to {max_t:.3f} s")
        else:
            self.preview_label.setText("No data")

    def _apply_and_accept(self):
        """Apply settings and close dialog."""
        self.data_file.time_column = self.time_col_combo.currentText()

        if self.absolute_radio.isChecked():
            self.data_file.time_mode = TimeMode.ABSOLUTE
        elif self.relative_radio.isChecked():
            self.data_file.time_mode = TimeMode.RELATIVE
        else:
            self.data_file.time_mode = TimeMode.CUSTOM_OFFSET

        self.data_file.time_offset = self.offset_spin.value()
        self.data_file.time_scale = self.scale_spin.value()

        self.accept()


class AxisSettingsDialog(QDialog):
    """Dialog for configuring plot axis settings."""

    def __init__(
        self,
        x_label: str = "Time",
        x_unit: str = "s",
        x_min: Optional[float] = None,
        x_max: Optional[float] = None,
        x_autoscale: bool = True,
        y_labels: list[str] = None,
        y_units: list[str] = None,
        y_mins: list[Optional[float]] = None,
        y_maxs: list[Optional[float]] = None,
        y_autoscales: list[bool] = None,
        num_y_axes: int = 1,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self.x_label = x_label
        self.x_unit = x_unit
        self.x_min = x_min
        self.x_max = x_max
        self.x_autoscale = x_autoscale

        self.y_labels = y_labels or ["Y1", "Y2", "Y3"]
        self.y_units = y_units or ["", "", ""]
        self.y_mins = y_mins or [None, None, None]
        self.y_maxs = y_maxs or [None, None, None]
        self.y_autoscales = y_autoscales or [True, True, True]
        self.num_y_axes = num_y_axes

        self.setWindowTitle("Axis Settings")
        self.setMinimumSize(400, 500)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)

        # X-axis settings
        x_group = QGroupBox("X-Axis (Time)")
        x_layout = QFormLayout(x_group)

        self.x_label_edit = QLineEdit(self.x_label)
        x_layout.addRow("Label:", self.x_label_edit)

        self.x_unit_edit = QLineEdit(self.x_unit)
        x_layout.addRow("Unit:", self.x_unit_edit)

        self.x_min_spin = QDoubleSpinBox()
        self.x_min_spin.setRange(-1e9, 1e9)
        self.x_min_spin.setDecimals(4)
        if self.x_min is not None:
            self.x_min_spin.setValue(self.x_min)
        x_layout.addRow("Min:", self.x_min_spin)

        self.x_max_spin = QDoubleSpinBox()
        self.x_max_spin.setRange(-1e9, 1e9)
        self.x_max_spin.setDecimals(4)
        if self.x_max is not None:
            self.x_max_spin.setValue(self.x_max)
        x_layout.addRow("Max:", self.x_max_spin)

        from PySide6.QtWidgets import QCheckBox
        self.x_auto_check = QCheckBox("Autoscale")
        self.x_auto_check.setChecked(self.x_autoscale)
        x_layout.addRow("", self.x_auto_check)

        content_layout.addWidget(x_group)

        # Y-axis settings
        self.y_widgets = []

        for i in range(self.num_y_axes):
            y_group = QGroupBox(f"Y-Axis {i + 1}")
            y_layout = QFormLayout(y_group)

            label_edit = QLineEdit(self.y_labels[i] if i < len(self.y_labels) else f"Y{i+1}")
            y_layout.addRow("Label:", label_edit)

            unit_edit = QLineEdit(self.y_units[i] if i < len(self.y_units) else "")
            y_layout.addRow("Unit:", unit_edit)

            min_spin = QDoubleSpinBox()
            min_spin.setRange(-1e9, 1e9)
            min_spin.setDecimals(4)
            if i < len(self.y_mins) and self.y_mins[i] is not None:
                min_spin.setValue(self.y_mins[i])
            y_layout.addRow("Min:", min_spin)

            max_spin = QDoubleSpinBox()
            max_spin.setRange(-1e9, 1e9)
            max_spin.setDecimals(4)
            if i < len(self.y_maxs) and self.y_maxs[i] is not None:
                max_spin.setValue(self.y_maxs[i])
            y_layout.addRow("Max:", max_spin)

            auto_check = QCheckBox("Autoscale")
            auto_check.setChecked(
                self.y_autoscales[i] if i < len(self.y_autoscales) else True
            )
            y_layout.addRow("", auto_check)

            self.y_widgets.append({
                "label": label_edit,
                "unit": unit_edit,
                "min": min_spin,
                "max": max_spin,
                "auto": auto_check
            })

            content_layout.addWidget(y_group)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_result(self) -> dict:
        """Get the configured axis settings."""
        result = {
            "x_label": self.x_label_edit.text(),
            "x_unit": self.x_unit_edit.text(),
            "x_min": self.x_min_spin.value() if not self.x_auto_check.isChecked() else None,
            "x_max": self.x_max_spin.value() if not self.x_auto_check.isChecked() else None,
            "x_autoscale": self.x_auto_check.isChecked(),
            "y_labels": [],
            "y_units": [],
            "y_mins": [],
            "y_maxs": [],
            "y_autoscales": []
        }

        for w in self.y_widgets:
            result["y_labels"].append(w["label"].text())
            result["y_units"].append(w["unit"].text())
            result["y_mins"].append(
                w["min"].value() if not w["auto"].isChecked() else None
            )
            result["y_maxs"].append(
                w["max"].value() if not w["auto"].isChecked() else None
            )
            result["y_autoscales"].append(w["auto"].isChecked())

        return result
