"""
Filter management system for the Log Viewer application.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

import numpy as np
import pandas as pd
from PySide6.QtCore import QObject, Signal

from .models import FilterState, Test


class FilterManager(QObject):
    """
    Manages filter state and synchronization across plots.

    Emits signals when filters change so plots can update.
    """

    # Signal emitted when a test's filter changes
    filter_changed = Signal(str)  # test_id

    # Signal emitted when any filter changes
    any_filter_changed = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._tests: dict[str, Test] = {}
        self._listeners: list[Callable[[str], None]] = []

    def register_test(self, test: Test) -> None:
        """Register a test with the filter manager."""
        self._tests[test.id] = test

    def unregister_test(self, test_id: str) -> None:
        """Unregister a test from the filter manager."""
        if test_id in self._tests:
            del self._tests[test_id]

    def get_test(self, test_id: str) -> Optional[Test]:
        """Get a test by ID."""
        return self._tests.get(test_id)

    def get_filter_state(self, test_id: str) -> Optional[FilterState]:
        """Get filter state for a test."""
        test = self._tests.get(test_id)
        if test:
            return test.filter_state
        return None

    def set_time_range(
        self,
        test_id: str,
        time_min: Optional[float],
        time_max: Optional[float]
    ) -> None:
        """Set time range filter for a test."""
        test = self._tests.get(test_id)
        if test:
            test.filter_state.time_min = time_min
            test.filter_state.time_max = time_max
            self._emit_change(test_id)

    def set_channel_filter(
        self,
        test_id: str,
        channel: str,
        min_val: Optional[float],
        max_val: Optional[float]
    ) -> None:
        """Set channel value filter for a test."""
        test = self._tests.get(test_id)
        if test:
            if min_val is None and max_val is None:
                # Remove filter if both are None
                test.filter_state.channel_filters.pop(channel, None)
            else:
                test.filter_state.channel_filters[channel] = (min_val, max_val)
            self._emit_change(test_id)

    def set_text_search(self, test_id: str, search_text: str) -> None:
        """Set text search filter for a test."""
        test = self._tests.get(test_id)
        if test:
            test.filter_state.text_search = search_text
            self._emit_change(test_id)

    def set_category_filter(self, test_id: str, categories: list[str]) -> None:
        """Set category filter for a test."""
        test = self._tests.get(test_id)
        if test:
            test.filter_state.category_filter = categories
            self._emit_change(test_id)

    def set_unit_filter(self, test_id: str, units: list[str]) -> None:
        """Set unit filter for a test."""
        test = self._tests.get(test_id)
        if test:
            test.filter_state.unit_filter = units
            self._emit_change(test_id)

    def set_filter_enabled(self, test_id: str, enabled: bool) -> None:
        """Enable or disable filtering for a test."""
        test = self._tests.get(test_id)
        if test:
            test.filter_state.enabled = enabled
            self._emit_change(test_id)

    def clear_filters(self, test_id: str) -> None:
        """Clear all filters for a test."""
        test = self._tests.get(test_id)
        if test:
            test.filter_state = FilterState()
            self._emit_change(test_id)

    def apply_filter_to_dataframe(
        self,
        test_id: str,
        df: pd.DataFrame,
        time_column: str = "_plot_time_"
    ) -> pd.DataFrame:
        """
        Apply filter to a dataframe.

        Args:
            test_id: Test ID to get filter from
            df: Dataframe to filter
            time_column: Name of time column

        Returns:
            Filtered dataframe
        """
        filter_state = self.get_filter_state(test_id)
        if filter_state is None or not filter_state.enabled:
            return df

        return filter_state.apply_to_dataframe(df, time_column)

    def get_filtered_channels(
        self,
        test_id: str,
        all_channels: list[str]
    ) -> list[str]:
        """
        Get list of channels that pass the text/category/unit filters.

        Args:
            test_id: Test ID
            all_channels: Full list of channel names

        Returns:
            Filtered list of channel names
        """
        test = self._tests.get(test_id)
        if not test:
            return all_channels

        fs = test.filter_state
        result = []

        for ch in all_channels:
            # Text search filter
            if fs.text_search:
                if fs.text_search.lower() not in ch.lower():
                    # Check display name too
                    meta = test.canonical_metadata.get(ch)
                    if meta and fs.text_search.lower() not in meta.display_name.lower():
                        continue

            # Category filter
            if fs.category_filter:
                meta = test.canonical_metadata.get(ch)
                if meta and meta.category not in fs.category_filter:
                    continue

            # Unit filter
            if fs.unit_filter:
                meta = test.canonical_metadata.get(ch)
                if meta and meta.unit not in fs.unit_filter:
                    continue

            result.append(ch)

        return result

    def _emit_change(self, test_id: str) -> None:
        """Emit filter change signals."""
        self.filter_changed.emit(test_id)
        self.any_filter_changed.emit()

        # Notify listeners
        for listener in self._listeners:
            listener(test_id)

    def add_listener(self, callback: Callable[[str], None]) -> None:
        """Add a listener callback for filter changes."""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[str], None]) -> None:
        """Remove a listener callback."""
        if callback in self._listeners:
            self._listeners.remove(callback)


class ChannelFilterHelper:
    """Helper class for computing channel value ranges and statistics."""

    @staticmethod
    def compute_channel_range(df: pd.DataFrame, channel: str) -> tuple[float, float]:
        """Compute the min/max range of a channel."""
        if channel not in df.columns:
            return (0.0, 1.0)

        values = df[channel].dropna()
        if len(values) == 0:
            return (0.0, 1.0)

        return (float(values.min()), float(values.max()))

    @staticmethod
    def compute_channel_stats(
        df: pd.DataFrame,
        channel: str
    ) -> dict[str, float]:
        """Compute statistics for a channel."""
        if channel not in df.columns:
            return {}

        values = df[channel].dropna()
        if len(values) == 0:
            return {}

        return {
            "min": float(values.min()),
            "max": float(values.max()),
            "mean": float(values.mean()),
            "std": float(values.std()),
            "median": float(values.median()),
            "count": int(len(values))
        }

    @staticmethod
    def get_filter_mask(
        df: pd.DataFrame,
        channel: str,
        min_val: Optional[float],
        max_val: Optional[float]
    ) -> pd.Series:
        """Get a boolean mask for channel value filtering."""
        if channel not in df.columns:
            return pd.Series(True, index=df.index)

        mask = pd.Series(True, index=df.index)

        if min_val is not None:
            mask &= df[channel] >= min_val
        if max_val is not None:
            mask &= df[channel] <= max_val

        return mask


class TimeRangeHelper:
    """Helper class for time range operations."""

    @staticmethod
    def compute_time_range(df: pd.DataFrame, time_column: str) -> tuple[float, float]:
        """Compute the time range of a dataframe."""
        if time_column not in df.columns:
            return (0.0, 1.0)

        times = df[time_column].dropna()
        if len(times) == 0:
            return (0.0, 1.0)

        return (float(times.min()), float(times.max()))

    @staticmethod
    def snap_to_nice_range(
        min_val: float,
        max_val: float,
        num_divisions: int = 10
    ) -> tuple[float, float]:
        """
        Snap a range to nice round numbers.

        Args:
            min_val: Minimum value
            max_val: Maximum value
            num_divisions: Approximate number of divisions

        Returns:
            (nice_min, nice_max) tuple
        """
        range_size = max_val - min_val
        if range_size <= 0:
            return (min_val - 1, max_val + 1)

        # Find a nice step size
        rough_step = range_size / num_divisions
        magnitude = 10 ** np.floor(np.log10(rough_step))
        residual = rough_step / magnitude

        if residual > 5:
            nice_step = 10 * magnitude
        elif residual > 2:
            nice_step = 5 * magnitude
        elif residual > 1:
            nice_step = 2 * magnitude
        else:
            nice_step = magnitude

        nice_min = np.floor(min_val / nice_step) * nice_step
        nice_max = np.ceil(max_val / nice_step) * nice_step

        return (float(nice_min), float(nice_max))
