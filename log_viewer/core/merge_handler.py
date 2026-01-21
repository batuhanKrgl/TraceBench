"""
Merge/Join and Time Alignment logic for the Log Viewer application.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from .models import CompareMode, DataFile, JoinStrategy, Test, TimeMode


class TimeAligner:
    """Handles time alignment between data files and tests."""

    @staticmethod
    def compute_relative_time(
        time_data: np.ndarray,
        reference_start: float = 0.0
    ) -> np.ndarray:
        """
        Convert absolute time to relative time from start.

        Args:
            time_data: Array of time values
            reference_start: Optional reference start time (default: use first value)

        Returns:
            Array of relative time values
        """
        if len(time_data) == 0:
            return time_data

        start = reference_start if reference_start != 0.0 else time_data[0]
        return time_data - start

    @staticmethod
    def apply_offset(time_data: np.ndarray, offset: float) -> np.ndarray:
        """Apply a time offset to time data."""
        return time_data + offset

    @staticmethod
    def apply_scale(time_data: np.ndarray, scale: float) -> np.ndarray:
        """Apply a scale factor to time data."""
        return time_data * scale

    @staticmethod
    def compute_concatenate_offset(
        test_a: Test,
        test_b: Test,
        gap: float = 0.0
    ) -> float:
        """
        Compute the time offset needed for end-to-end concatenation.

        When concatenating Test B after Test A, offset B's time so it starts
        right after A ends.

        Args:
            test_a: First test (ends first)
            test_b: Second test (to be appended)
            gap: Gap to add between tests (default 0)

        Returns:
            Offset to apply to test_b's time
        """
        _, end_a = test_a.get_time_range()
        start_b, _ = test_b.get_time_range()

        return (end_a - start_b) + gap


class DataMerger:
    """Handles merging and joining of data files."""

    @staticmethod
    def merge_on_time_nearest(
        base_df: pd.DataFrame,
        new_df: pd.DataFrame,
        time_column: str,
        tolerance: float = 0.001,
        direction: str = "nearest"
    ) -> pd.DataFrame:
        """
        Merge two dataframes using nearest time matching.

        Args:
            base_df: Base dataframe
            new_df: New dataframe to merge
            time_column: Name of time column
            tolerance: Maximum time difference for matching
            direction: 'nearest', 'forward', or 'backward'

        Returns:
            Merged dataframe
        """
        # Ensure both dataframes are sorted by time
        base_sorted = base_df.sort_values(time_column).reset_index(drop=True)
        new_sorted = new_df.sort_values(time_column).reset_index(drop=True)

        # Handle duplicate columns (except time)
        new_cols = []
        for col in new_sorted.columns:
            if col == time_column:
                new_cols.append(col)
            elif col in base_sorted.columns:
                # Skip duplicate columns from new_df
                continue
            else:
                new_cols.append(col)

        new_sorted = new_sorted[new_cols]

        # Perform merge_asof
        result = pd.merge_asof(
            base_sorted,
            new_sorted,
            on=time_column,
            tolerance=tolerance,
            direction=direction
        )

        return result

    @staticmethod
    def merge_on_time_exact(
        base_df: pd.DataFrame,
        new_df: pd.DataFrame,
        time_column: str
    ) -> pd.DataFrame:
        """
        Merge two dataframes using exact time matching.

        Args:
            base_df: Base dataframe
            new_df: New dataframe to merge
            time_column: Name of time column

        Returns:
            Merged dataframe
        """
        # Handle duplicate columns
        new_cols = [time_column]
        for col in new_df.columns:
            if col != time_column and col not in base_df.columns:
                new_cols.append(col)

        new_df_filtered = new_df[new_cols]

        result = pd.merge(
            base_df,
            new_df_filtered,
            on=time_column,
            how="outer"
        ).sort_values(time_column).reset_index(drop=True)

        return result

    @staticmethod
    def merge_on_alternative_key(
        base_df: pd.DataFrame,
        new_df: pd.DataFrame,
        key_column: str,
        how: str = "outer"
    ) -> pd.DataFrame:
        """
        Merge two dataframes using an alternative key column.

        Args:
            base_df: Base dataframe
            new_df: New dataframe to merge
            key_column: Column to use as join key
            how: Join type ('outer', 'inner', 'left', 'right')

        Returns:
            Merged dataframe
        """
        # Handle duplicate columns
        new_cols = [key_column]
        for col in new_df.columns:
            if col != key_column and col not in base_df.columns:
                new_cols.append(col)

        new_df_filtered = new_df[new_cols]

        result = pd.merge(
            base_df,
            new_df_filtered,
            on=key_column,
            how=how
        )

        return result

    @staticmethod
    def append_as_segment(
        base_df: pd.DataFrame,
        new_df: pd.DataFrame,
        time_column: str,
        time_offset: float = 0.0
    ) -> pd.DataFrame:
        """
        Append new dataframe as a separate segment (no merging).

        Args:
            base_df: Base dataframe
            new_df: New dataframe to append
            time_column: Time column name
            time_offset: Offset to add to new_df's time values

        Returns:
            Concatenated dataframe
        """
        # Apply time offset to new dataframe
        new_df_copy = new_df.copy()
        if time_column in new_df_copy.columns and time_offset != 0.0:
            new_df_copy[time_column] = new_df_copy[time_column] + time_offset

        # Concatenate
        result = pd.concat([base_df, new_df_copy], ignore_index=True)

        # Sort by time
        if time_column in result.columns:
            result = result.sort_values(time_column).reset_index(drop=True)

        return result


class TestComparer:
    """Handles comparison between multiple tests."""

    def __init__(self, mode: CompareMode = CompareMode.OVERLAY, gap: float = 0.0):
        self.mode = mode
        self.gap = gap

    def prepare_tests_for_comparison(
        self,
        tests: list[Test],
        selected_channels: list[str]
    ) -> dict[str, pd.DataFrame]:
        """
        Prepare test data for comparison plotting.

        Args:
            tests: List of tests to compare
            selected_channels: Channels to include

        Returns:
            Dict mapping test_id -> prepared dataframe
        """
        result: dict[str, pd.DataFrame] = {}

        if self.mode == CompareMode.OVERLAY:
            # Simple overlay - no time modification
            for test in tests:
                df = test.get_merged_dataframe(apply_filter=True)
                if df.empty:
                    continue

                # Select only needed columns
                cols_to_keep = ["_plot_time_"]
                for ch in selected_channels:
                    if ch in df.columns:
                        cols_to_keep.append(ch)

                result[test.id] = df[cols_to_keep].copy()

        elif self.mode == CompareMode.CONCATENATE:
            # End-to-end concatenation with offsets
            cumulative_offset = 0.0

            for i, test in enumerate(tests):
                df = test.get_merged_dataframe(apply_filter=True)
                if df.empty:
                    continue

                # Select only needed columns
                cols_to_keep = ["_plot_time_"]
                for ch in selected_channels:
                    if ch in df.columns:
                        cols_to_keep.append(ch)

                df_copy = df[cols_to_keep].copy()

                if i > 0:
                    # Apply cumulative offset
                    df_copy["_plot_time_"] = df_copy["_plot_time_"] + cumulative_offset

                # Store the prepared dataframe
                result[test.id] = df_copy

                # Update cumulative offset for next test
                if "_plot_time_" in df_copy.columns:
                    time_range = df_copy["_plot_time_"].max() - df_copy["_plot_time_"].min()
                    end_time = df_copy["_plot_time_"].max()
                    cumulative_offset = end_time + self.gap

        return result

    def get_combined_time_range(
        self,
        tests: list[Test]
    ) -> tuple[float, float]:
        """
        Get the combined time range for all tests based on compare mode.

        Args:
            tests: List of tests

        Returns:
            (min_time, max_time) tuple
        """
        if not tests:
            return (0.0, 1.0)

        if self.mode == CompareMode.OVERLAY:
            min_t = float('inf')
            max_t = float('-inf')
            for test in tests:
                t_min, t_max = test.get_time_range()
                min_t = min(min_t, t_min)
                max_t = max(max_t, t_max)
            return (min_t, max_t)

        elif self.mode == CompareMode.CONCATENATE:
            cumulative = 0.0
            for i, test in enumerate(tests):
                t_min, t_max = test.get_time_range()
                duration = t_max - t_min
                if i > 0:
                    cumulative += self.gap
                cumulative += duration

            return (0.0, cumulative)

        return (0.0, 1.0)


def add_headers_file_to_test(
    test: Test,
    new_file: DataFile,
    join_strategy: JoinStrategy = JoinStrategy.TIME_NEAREST,
    join_key: Optional[str] = None,
    join_tolerance: float = 0.001
) -> None:
    """
    Add a "headers file" to an existing test.
    This merges the new file's columns into the test's existing data.

    Args:
        test: Target test
        new_file: New data file to add
        join_strategy: How to join the data
        join_key: Column to use as join key (if not using time)
        join_tolerance: Tolerance for nearest join
    """
    # Set join parameters on the new file
    new_file.join_strategy = join_strategy
    new_file.join_key = join_key
    new_file.join_tolerance = join_tolerance

    # Add file to test
    test.add_data_file(new_file)


def compute_time_offset_for_concat(
    end_time: float,
    start_time: float,
    gap: float = 0.0
) -> float:
    """
    Compute the time offset needed for concatenating two time series.

    Args:
        end_time: End time of the first series
        start_time: Start time of the second series
        gap: Desired gap between series

    Returns:
        Offset to add to second series
    """
    return (end_time - start_time) + gap
