"""
Core data models for the Log Viewer application.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd


class TimeMode(Enum):
    """Time handling modes for DataFiles."""
    ABSOLUTE = auto()       # Use absolute timestamp as-is
    RELATIVE = auto()       # Relative seconds from start
    CUSTOM_OFFSET = auto()  # User-defined offset in seconds


class JoinStrategy(Enum):
    """Strategies for joining/merging data files."""
    TIME_NEAREST = auto()      # Join on nearest time with tolerance
    TIME_EXACT = auto()        # Exact time match
    ALTERNATIVE_KEY = auto()   # User-selected alternative key
    APPEND_SEGMENT = auto()    # Append as separate segment


class HeaderMismatchStrategy(Enum):
    """Strategies for handling header mismatches."""
    STRICT = auto()   # Reject import
    UNION = auto()    # Add new headers, missing become NaN
    MAP = auto()      # User maps/renames columns


class CompareMode(Enum):
    """Modes for comparing multiple tests."""
    OVERLAY = auto()           # Same time axis overlay
    CONCATENATE = auto()       # End-to-end with gap


@dataclass
class ChannelMetadata:
    """Metadata for a single channel/header."""
    original_name: str
    display_name: str
    unit: str = ""
    category: str = "Unknown"
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "original_name": self.original_name,
            "display_name": self.display_name,
            "unit": self.unit,
            "category": self.category,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChannelMetadata:
        """Deserialize from dictionary."""
        return cls(
            original_name=data["original_name"],
            display_name=data["display_name"],
            unit=data.get("unit", ""),
            category=data.get("category", "Unknown"),
            description=data.get("description", "")
        )


@dataclass
class FilterState:
    """Global filter state for a dataset/test."""
    time_min: Optional[float] = None
    time_max: Optional[float] = None
    channel_filters: dict[str, tuple[Optional[float], Optional[float]]] = field(default_factory=dict)
    text_search: str = ""
    category_filter: list[str] = field(default_factory=list)
    unit_filter: list[str] = field(default_factory=list)
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "time_min": self.time_min,
            "time_max": self.time_max,
            "channel_filters": self.channel_filters,
            "text_search": self.text_search,
            "category_filter": self.category_filter,
            "unit_filter": self.unit_filter,
            "enabled": self.enabled
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FilterState:
        """Deserialize from dictionary."""
        return cls(
            time_min=data.get("time_min"),
            time_max=data.get("time_max"),
            channel_filters=data.get("channel_filters", {}),
            text_search=data.get("text_search", ""),
            category_filter=data.get("category_filter", []),
            unit_filter=data.get("unit_filter", []),
            enabled=data.get("enabled", True)
        )

    def apply_to_dataframe(self, df: pd.DataFrame, time_column: str) -> pd.DataFrame:
        """Apply filters to a dataframe and return filtered copy."""
        if not self.enabled or df.empty:
            return df

        mask = pd.Series(True, index=df.index)

        # Time range filter
        if time_column in df.columns:
            if self.time_min is not None:
                mask &= df[time_column] >= self.time_min
            if self.time_max is not None:
                mask &= df[time_column] <= self.time_max

        # Channel value filters
        for channel, (min_val, max_val) in self.channel_filters.items():
            if channel in df.columns:
                if min_val is not None:
                    mask &= df[channel] >= min_val
                if max_val is not None:
                    mask &= df[channel] <= max_val

        return df[mask].copy()


@dataclass
class DataFile:
    """Represents a single imported data file."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    filepath: Path = field(default_factory=Path)
    filename: str = ""
    delimiter: str = ","
    encoding: str = "utf-8"

    # Header metadata
    headers: list[str] = field(default_factory=list)
    channel_metadata: dict[str, ChannelMetadata] = field(default_factory=dict)

    # Data storage
    dataframe: Optional[pd.DataFrame] = None

    # Time column settings
    time_column: str = ""
    time_mode: TimeMode = TimeMode.RELATIVE
    time_offset: float = 0.0  # User-defined offset in seconds
    time_scale: float = 1.0   # Scale factor (e.g., for ms to s conversion)

    # Join settings (when this file was added to an existing test)
    join_strategy: Optional[JoinStrategy] = None
    join_key: Optional[str] = None
    join_tolerance: float = 0.001  # For nearest join

    def __post_init__(self):
        if isinstance(self.filepath, str):
            self.filepath = Path(self.filepath)
        if not self.filename and self.filepath:
            self.filename = self.filepath.name

    def get_time_data(self) -> Optional[np.ndarray]:
        """Get time data with offset and scale applied."""
        if self.dataframe is None or self.time_column not in self.dataframe.columns:
            return None

        time_data = self.dataframe[self.time_column].values.astype(float)

        if self.time_mode == TimeMode.RELATIVE:
            time_data = time_data - time_data[0] if len(time_data) > 0 else time_data

        return (time_data + self.time_offset) * self.time_scale

    def get_plot_time(self) -> Optional[np.ndarray]:
        """Get time data ready for plotting (with all transformations)."""
        return self.get_time_data()

    def get_time_range(self) -> tuple[float, float]:
        """Get the time range (min, max) after transformations."""
        time_data = self.get_time_data()
        if time_data is None or len(time_data) == 0:
            return (0.0, 0.0)
        return (float(np.min(time_data)), float(np.max(time_data)))

    def get_channel_data(self, channel: str) -> Optional[np.ndarray]:
        """Get data for a specific channel."""
        if self.dataframe is None or channel not in self.dataframe.columns:
            return None
        return self.dataframe[channel].values

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary (without dataframe)."""
        return {
            "id": self.id,
            "filepath": str(self.filepath),
            "filename": self.filename,
            "delimiter": self.delimiter,
            "encoding": self.encoding,
            "headers": self.headers,
            "channel_metadata": {k: v.to_dict() for k, v in self.channel_metadata.items()},
            "time_column": self.time_column,
            "time_mode": self.time_mode.name,
            "time_offset": self.time_offset,
            "time_scale": self.time_scale,
            "join_strategy": self.join_strategy.name if self.join_strategy else None,
            "join_key": self.join_key,
            "join_tolerance": self.join_tolerance
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DataFile:
        """Deserialize from dictionary."""
        df = cls(
            id=data.get("id", str(uuid.uuid4())),
            filepath=Path(data["filepath"]),
            filename=data.get("filename", ""),
            delimiter=data.get("delimiter", ","),
            encoding=data.get("encoding", "utf-8"),
            headers=data.get("headers", []),
            time_column=data.get("time_column", ""),
            time_mode=TimeMode[data.get("time_mode", "RELATIVE")],
            time_offset=data.get("time_offset", 0.0),
            time_scale=data.get("time_scale", 1.0),
            join_strategy=JoinStrategy[data["join_strategy"]] if data.get("join_strategy") else None,
            join_key=data.get("join_key"),
            join_tolerance=data.get("join_tolerance", 0.001)
        )

        # Restore channel metadata
        for k, v in data.get("channel_metadata", {}).items():
            df.channel_metadata[k] = ChannelMetadata.from_dict(v)

        return df


@dataclass
class Test:
    """Represents a test run containing multiple data files."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "New Test"
    description: str = ""

    # Data files in this test
    data_files: list[DataFile] = field(default_factory=list)

    # Canonical header schema (union of all headers)
    canonical_headers: list[str] = field(default_factory=list)
    canonical_metadata: dict[str, ChannelMetadata] = field(default_factory=dict)

    # Primary time column for the test
    primary_time_column: str = ""

    # Filter state
    filter_state: FilterState = field(default_factory=FilterState)

    # Comparison settings
    compare_time_offset: float = 0.0  # Offset when used in concatenate mode

    # Color for this test in plots
    color: str = "#1f77b4"

    def add_data_file(self, data_file: DataFile) -> None:
        """Add a data file to this test."""
        self.data_files.append(data_file)
        self._update_canonical_headers()

    def remove_data_file(self, file_id: str) -> bool:
        """Remove a data file by ID."""
        for i, df in enumerate(self.data_files):
            if df.id == file_id:
                self.data_files.pop(i)
                self._update_canonical_headers()
                return True
        return False

    def get_data_file(self, file_id: str) -> Optional[DataFile]:
        """Get a data file by ID."""
        for df in self.data_files:
            if df.id == file_id:
                return df
        return None

    def _update_canonical_headers(self) -> None:
        """Update canonical headers from all data files."""
        all_headers = set()
        for df in self.data_files:
            all_headers.update(df.headers)

        # Preserve order: existing headers first, then new ones
        new_headers = []
        for h in self.canonical_headers:
            if h in all_headers:
                new_headers.append(h)
        for h in all_headers:
            if h not in new_headers:
                new_headers.append(h)

        self.canonical_headers = new_headers

        # Update metadata
        for df in self.data_files:
            for h, meta in df.channel_metadata.items():
                if h not in self.canonical_metadata:
                    self.canonical_metadata[h] = meta

    def get_merged_dataframe(self, apply_filter: bool = True) -> pd.DataFrame:
        """Get merged dataframe from all data files with time alignment."""
        if not self.data_files:
            return pd.DataFrame()

        # Start with first file
        result = None
        time_col = self.primary_time_column or self.data_files[0].time_column

        for df in self.data_files:
            if df.dataframe is None:
                continue

            # Create a copy with plot time
            temp_df = df.dataframe.copy()
            plot_time = df.get_plot_time()
            if plot_time is not None and time_col in temp_df.columns:
                temp_df["_plot_time_"] = plot_time
            elif time_col in temp_df.columns:
                temp_df["_plot_time_"] = temp_df[time_col]

            if result is None:
                result = temp_df
            else:
                # Merge based on join strategy
                if df.join_strategy == JoinStrategy.APPEND_SEGMENT:
                    # Append as separate segment
                    result = pd.concat([result, temp_df], ignore_index=True)
                elif df.join_strategy == JoinStrategy.TIME_NEAREST:
                    # Nearest time merge
                    result = pd.merge_asof(
                        result.sort_values("_plot_time_"),
                        temp_df.sort_values("_plot_time_"),
                        on="_plot_time_",
                        tolerance=df.join_tolerance,
                        direction="nearest"
                    )
                else:
                    # Default: left join on plot time
                    result = pd.merge(
                        result, temp_df,
                        on="_plot_time_",
                        how="outer",
                        suffixes=("", "_dup")
                    )
                    # Remove duplicate columns
                    result = result[[c for c in result.columns if not c.endswith("_dup")]]

        if result is None:
            return pd.DataFrame()

        # Sort by time
        if "_plot_time_" in result.columns:
            result = result.sort_values("_plot_time_").reset_index(drop=True)

        # Apply filter if requested
        if apply_filter and self.filter_state.enabled:
            result = self.filter_state.apply_to_dataframe(result, "_plot_time_")

        return result

    def get_time_range(self) -> tuple[float, float]:
        """Get overall time range for this test."""
        min_t, max_t = float('inf'), float('-inf')
        for df in self.data_files:
            t_min, t_max = df.get_time_range()
            min_t = min(min_t, t_min)
            max_t = max(max_t, t_max)
        if min_t == float('inf'):
            return (0.0, 0.0)
        return (min_t, max_t)

    def get_channels_by_category(self) -> dict[str, dict[str, list[str]]]:
        """Get channels organized by category -> unit -> channel names."""
        result: dict[str, dict[str, list[str]]] = {}

        for header in self.canonical_headers:
            meta = self.canonical_metadata.get(header)
            if meta:
                category = meta.category or "Unknown"
                unit = meta.unit or "No Unit"
            else:
                category = "Unknown"
                unit = "No Unit"

            if category not in result:
                result[category] = {}
            if unit not in result[category]:
                result[category][unit] = []
            result[category][unit].append(header)

        return result

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "data_files": [df.to_dict() for df in self.data_files],
            "canonical_headers": self.canonical_headers,
            "canonical_metadata": {k: v.to_dict() for k, v in self.canonical_metadata.items()},
            "primary_time_column": self.primary_time_column,
            "filter_state": self.filter_state.to_dict(),
            "compare_time_offset": self.compare_time_offset,
            "color": self.color
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Test:
        """Deserialize from dictionary."""
        test = cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "New Test"),
            description=data.get("description", ""),
            canonical_headers=data.get("canonical_headers", []),
            primary_time_column=data.get("primary_time_column", ""),
            compare_time_offset=data.get("compare_time_offset", 0.0),
            color=data.get("color", "#1f77b4")
        )

        # Restore data files
        for df_data in data.get("data_files", []):
            test.data_files.append(DataFile.from_dict(df_data))

        # Restore metadata
        for k, v in data.get("canonical_metadata", {}).items():
            test.canonical_metadata[k] = ChannelMetadata.from_dict(v)

        # Restore filter state
        if "filter_state" in data:
            test.filter_state = FilterState.from_dict(data["filter_state"])

        return test


@dataclass
class HeaderDiff:
    """Represents differences between two header sets."""
    missing: list[str] = field(default_factory=list)    # In test but not in file
    extra: list[str] = field(default_factory=list)      # In file but not in test
    matched: list[str] = field(default_factory=list)    # Exact matches
    fuzzy_matches: dict[str, str] = field(default_factory=dict)  # file_header -> test_header suggestions

    @property
    def has_differences(self) -> bool:
        """Check if there are any differences."""
        return bool(self.missing or self.extra)

    def get_summary(self) -> str:
        """Get a human-readable summary of differences."""
        parts = []
        if self.missing:
            parts.append(f"Missing {len(self.missing)} headers: {', '.join(self.missing[:5])}")
            if len(self.missing) > 5:
                parts[-1] += f"... (+{len(self.missing) - 5} more)"
        if self.extra:
            parts.append(f"Extra {len(self.extra)} headers: {', '.join(self.extra[:5])}")
            if len(self.extra) > 5:
                parts[-1] += f"... (+{len(self.extra) - 5} more)"
        if self.fuzzy_matches:
            parts.append(f"Possible renames: {len(self.fuzzy_matches)}")
        return "; ".join(parts) if parts else "Headers match exactly"


@dataclass
class PlotSettings:
    """Settings for a single plot panel."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Selected tests/datasets
    selected_tests: list[str] = field(default_factory=list)  # Test IDs

    # Selected channels with axis assignment (for plot #1)
    # channel_name -> axis (1, 2, or 3)
    channel_axis_map: dict[str, int] = field(default_factory=dict)

    # Selected channels (simple list for plot #2 and #3)
    selected_channels: list[str] = field(default_factory=list)

    # Axis settings
    x_label: str = "Time"
    x_unit: str = "s"
    x_min: Optional[float] = None
    x_max: Optional[float] = None
    x_autoscale: bool = True

    # Y-axis settings (up to 3 for plot #1)
    y_labels: list[str] = field(default_factory=lambda: ["Y1", "Y2", "Y3"])
    y_units: list[str] = field(default_factory=lambda: ["", "", ""])
    y_mins: list[Optional[float]] = field(default_factory=lambda: [None, None, None])
    y_maxs: list[Optional[float]] = field(default_factory=lambda: [None, None, None])
    y_autoscales: list[bool] = field(default_factory=lambda: [True, True, True])

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "selected_tests": self.selected_tests,
            "channel_axis_map": self.channel_axis_map,
            "selected_channels": self.selected_channels,
            "x_label": self.x_label,
            "x_unit": self.x_unit,
            "x_min": self.x_min,
            "x_max": self.x_max,
            "x_autoscale": self.x_autoscale,
            "y_labels": self.y_labels,
            "y_units": self.y_units,
            "y_mins": self.y_mins,
            "y_maxs": self.y_maxs,
            "y_autoscales": self.y_autoscales
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlotSettings:
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            selected_tests=data.get("selected_tests", []),
            channel_axis_map=data.get("channel_axis_map", {}),
            selected_channels=data.get("selected_channels", []),
            x_label=data.get("x_label", "Time"),
            x_unit=data.get("x_unit", "s"),
            x_min=data.get("x_min"),
            x_max=data.get("x_max"),
            x_autoscale=data.get("x_autoscale", True),
            y_labels=data.get("y_labels", ["Y1", "Y2", "Y3"]),
            y_units=data.get("y_units", ["", "", ""]),
            y_mins=data.get("y_mins", [None, None, None]),
            y_maxs=data.get("y_maxs", [None, None, None]),
            y_autoscales=data.get("y_autoscales", [True, True, True])
        )


@dataclass
class AppLayout:
    """Application layout state for save/load."""
    tests: list[Test] = field(default_factory=list)
    plot_count: int = 1
    plot_settings: list[PlotSettings] = field(default_factory=list)
    compare_mode: CompareMode = CompareMode.OVERLAY
    compare_gap: float = 0.0

    # Window geometry
    window_width: int = 1400
    window_height: int = 900

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "version": "1.0",
            "tests": [t.to_dict() for t in self.tests],
            "plot_count": self.plot_count,
            "plot_settings": [p.to_dict() for p in self.plot_settings],
            "compare_mode": self.compare_mode.name,
            "compare_gap": self.compare_gap,
            "window_width": self.window_width,
            "window_height": self.window_height
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppLayout:
        """Deserialize from dictionary."""
        layout = cls(
            plot_count=data.get("plot_count", 1),
            compare_mode=CompareMode[data.get("compare_mode", "OVERLAY")],
            compare_gap=data.get("compare_gap", 0.0),
            window_width=data.get("window_width", 1400),
            window_height=data.get("window_height", 900)
        )

        # Restore tests
        for t_data in data.get("tests", []):
            layout.tests.append(Test.from_dict(t_data))

        # Restore plot settings
        for p_data in data.get("plot_settings", []):
            layout.plot_settings.append(PlotSettings.from_dict(p_data))

        return layout
