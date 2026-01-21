"""
Tests for merge/join logic for "header add" file.
"""
import numpy as np
import pandas as pd
import pytest

from log_viewer.core import (
    DataFile,
    JoinStrategy,
    Test,
    add_headers_file_to_test,
)
from log_viewer.core.merge_handler import DataMerger


class TestDataMerger:
    """Tests for DataMerger class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Base dataframe
        self.base_df = pd.DataFrame({
            "Time": [0.0, 1.0, 2.0, 3.0, 4.0],
            "Temp": [20.0, 21.0, 22.0, 23.0, 24.0],
            "Pressure": [1.0, 1.1, 1.2, 1.3, 1.4]
        })

        # New dataframe with additional columns
        self.new_df = pd.DataFrame({
            "Time": [0.0, 1.0, 2.0, 3.0, 4.0],
            "Voltage": [12.0, 12.1, 12.2, 12.1, 12.0],
            "Current": [1.5, 1.6, 1.7, 1.6, 1.5]
        })

        # Dataframe with offset time
        self.offset_df = pd.DataFrame({
            "Time": [0.5, 1.5, 2.5, 3.5],
            "Speed": [1000, 1100, 1050, 1000]
        })

    def test_merge_on_time_exact(self):
        """Test exact time merge."""
        result = DataMerger.merge_on_time_exact(
            self.base_df, self.new_df, "Time"
        )

        assert "Temp" in result.columns
        assert "Pressure" in result.columns
        assert "Voltage" in result.columns
        assert "Current" in result.columns
        assert len(result) == 5

    def test_merge_on_time_nearest(self):
        """Test nearest time merge."""
        result = DataMerger.merge_on_time_nearest(
            self.base_df, self.offset_df, "Time",
            tolerance=0.6,
            direction="nearest"
        )

        assert "Temp" in result.columns
        assert "Speed" in result.columns
        # Not all rows will have Speed values due to tolerance
        assert len(result) == 5

    def test_merge_on_time_nearest_no_tolerance(self):
        """Test nearest merge with tight tolerance."""
        result = DataMerger.merge_on_time_nearest(
            self.base_df, self.offset_df, "Time",
            tolerance=0.1,  # Very tight
            direction="nearest"
        )

        # Speed should be NaN for most rows
        assert "Speed" in result.columns
        assert result["Speed"].isna().sum() > 0

    def test_merge_on_alternative_key(self):
        """Test merge on alternative key column."""
        base = pd.DataFrame({
            "ID": [1, 2, 3, 4],
            "Value_A": [10, 20, 30, 40]
        })
        new = pd.DataFrame({
            "ID": [1, 2, 3, 4],
            "Value_B": [100, 200, 300, 400]
        })

        result = DataMerger.merge_on_alternative_key(base, new, "ID")

        assert "Value_A" in result.columns
        assert "Value_B" in result.columns
        assert len(result) == 4

    def test_append_as_segment(self):
        """Test appending as separate segment."""
        base = pd.DataFrame({
            "Time": [0.0, 1.0, 2.0],
            "Value": [10, 20, 30]
        })
        new = pd.DataFrame({
            "Time": [0.0, 1.0, 2.0],
            "Value": [40, 50, 60]
        })

        result = DataMerger.append_as_segment(base, new, "Time", time_offset=3.0)

        assert len(result) == 6
        # New segment should have time offset applied
        assert result["Time"].max() == pytest.approx(5.0)

    def test_append_preserves_all_data(self):
        """Test that append preserves all data points."""
        base = pd.DataFrame({
            "Time": [0.0, 1.0],
            "A": [1, 2]
        })
        new = pd.DataFrame({
            "Time": [0.0, 1.0],
            "B": [3, 4]  # Different column
        })

        result = DataMerger.append_as_segment(base, new, "Time")

        assert len(result) == 4
        assert "A" in result.columns
        assert "B" in result.columns

    def test_duplicate_columns_handling(self):
        """Test that duplicate columns (except key) are handled."""
        base = pd.DataFrame({
            "Time": [0.0, 1.0, 2.0],
            "Value": [10, 20, 30]
        })
        new = pd.DataFrame({
            "Time": [0.0, 1.0, 2.0],
            "Value": [100, 200, 300],  # Same column name
            "NewCol": [1, 2, 3]
        })

        result = DataMerger.merge_on_time_exact(base, new, "Time")

        # Should keep Value from base, add NewCol
        assert "Value" in result.columns
        assert "NewCol" in result.columns
        # Value should be from base
        assert list(result["Value"]) == [10, 20, 30]


class TestAddHeadersFileToTest:
    """Tests for add_headers_file_to_test function."""

    def test_add_headers_basic(self):
        """Test adding headers file to a test."""
        # Create test with initial file
        test = Test(name="Test")
        initial_file = DataFile()
        initial_file.dataframe = pd.DataFrame({
            "Time": [0.0, 1.0, 2.0],
            "Temp": [20.0, 21.0, 22.0]
        })
        initial_file.time_column = "Time"
        initial_file.headers = ["Time", "Temp"]
        test.add_data_file(initial_file)
        test.primary_time_column = "Time"

        # Create headers file
        headers_file = DataFile()
        headers_file.dataframe = pd.DataFrame({
            "Time": [0.0, 1.0, 2.0],
            "Voltage": [12.0, 12.1, 12.2]
        })
        headers_file.time_column = "Time"
        headers_file.headers = ["Time", "Voltage"]

        # Add headers file
        add_headers_file_to_test(
            test, headers_file,
            join_strategy=JoinStrategy.TIME_NEAREST,
            join_tolerance=0.1
        )

        # Verify
        assert len(test.data_files) == 2
        assert "Voltage" in test.canonical_headers
        assert headers_file.join_strategy == JoinStrategy.TIME_NEAREST

    def test_add_headers_with_append_segment(self):
        """Test adding headers as separate segment."""
        test = Test(name="Test")
        initial_file = DataFile()
        initial_file.dataframe = pd.DataFrame({
            "Time": [0.0, 1.0, 2.0],
            "Value": [10, 20, 30]
        })
        initial_file.time_column = "Time"
        initial_file.headers = ["Time", "Value"]
        test.add_data_file(initial_file)

        # Headers file with non-overlapping time
        headers_file = DataFile()
        headers_file.dataframe = pd.DataFrame({
            "Time": [10.0, 11.0, 12.0],
            "Value": [100, 200, 300]
        })
        headers_file.time_column = "Time"
        headers_file.headers = ["Time", "Value"]

        add_headers_file_to_test(
            test, headers_file,
            join_strategy=JoinStrategy.APPEND_SEGMENT
        )

        assert len(test.data_files) == 2
        assert headers_file.join_strategy == JoinStrategy.APPEND_SEGMENT

    def test_add_headers_updates_canonical(self):
        """Test that canonical headers are updated."""
        test = Test(name="Test")
        initial_file = DataFile()
        initial_file.dataframe = pd.DataFrame({
            "Time": [0.0, 1.0],
            "A": [1, 2]
        })
        initial_file.headers = ["Time", "A"]
        test.add_data_file(initial_file)

        headers_file = DataFile()
        headers_file.dataframe = pd.DataFrame({
            "Time": [0.0, 1.0],
            "B": [3, 4],
            "C": [5, 6]
        })
        headers_file.headers = ["Time", "B", "C"]

        add_headers_file_to_test(test, headers_file, JoinStrategy.TIME_EXACT)

        # Should have all columns
        assert "Time" in test.canonical_headers
        assert "A" in test.canonical_headers
        assert "B" in test.canonical_headers
        assert "C" in test.canonical_headers


class TestTestMergedDataframe:
    """Tests for Test.get_merged_dataframe method."""

    def test_single_file(self):
        """Test merged dataframe with single file."""
        test = Test(name="Test")
        df = DataFile()
        df.dataframe = pd.DataFrame({
            "Time": [0.0, 1.0, 2.0],
            "Value": [10, 20, 30]
        })
        df.time_column = "Time"
        test.add_data_file(df)
        test.primary_time_column = "Time"

        result = test.get_merged_dataframe(apply_filter=False)

        assert "_plot_time_" in result.columns
        assert "Value" in result.columns
        assert len(result) == 3

    def test_multiple_files_time_nearest(self):
        """Test merging multiple files with nearest time."""
        test = Test(name="Test")

        # First file
        df1 = DataFile()
        df1.dataframe = pd.DataFrame({
            "Time": [0.0, 1.0, 2.0],
            "A": [10, 20, 30]
        })
        df1.time_column = "Time"
        df1.headers = ["Time", "A"]
        test.add_data_file(df1)
        test.primary_time_column = "Time"

        # Second file with join strategy
        df2 = DataFile()
        df2.dataframe = pd.DataFrame({
            "Time": [0.0, 1.0, 2.0],
            "B": [100, 200, 300]
        })
        df2.time_column = "Time"
        df2.headers = ["Time", "B"]
        df2.join_strategy = JoinStrategy.TIME_NEAREST
        df2.join_tolerance = 0.1
        test.add_data_file(df2)

        result = test.get_merged_dataframe(apply_filter=False)

        assert "A" in result.columns
        assert "B" in result.columns

    def test_merged_dataframe_sorted_by_time(self):
        """Test that merged dataframe is sorted by time."""
        test = Test(name="Test")

        df1 = DataFile()
        df1.dataframe = pd.DataFrame({
            "Time": [2.0, 0.0, 1.0],  # Unsorted
            "Value": [30, 10, 20]
        })
        df1.time_column = "Time"
        test.add_data_file(df1)
        test.primary_time_column = "Time"

        result = test.get_merged_dataframe(apply_filter=False)

        # Should be sorted by time
        times = result["_plot_time_"].values
        assert list(times) == sorted(times)
