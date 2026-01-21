"""
Tests for time offset and concatenation logic.
"""
import numpy as np
import pandas as pd
import pytest

from log_viewer.core import (
    DataFile,
    Test,
    TimeMode,
    CompareMode,
)
from log_viewer.core.merge_handler import (
    TimeAligner,
    TestComparer,
    compute_time_offset_for_concat,
)


class TestTimeAligner:
    """Tests for TimeAligner class."""

    def test_compute_relative_time(self):
        """Test converting absolute to relative time."""
        time_data = np.array([100.0, 101.0, 102.0, 103.0, 104.0])

        relative = TimeAligner.compute_relative_time(time_data)

        expected = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        np.testing.assert_array_almost_equal(relative, expected)

    def test_compute_relative_time_with_reference(self):
        """Test relative time with custom reference."""
        time_data = np.array([100.0, 101.0, 102.0])

        relative = TimeAligner.compute_relative_time(time_data, reference_start=98.0)

        expected = np.array([2.0, 3.0, 4.0])
        np.testing.assert_array_almost_equal(relative, expected)

    def test_apply_offset(self):
        """Test applying time offset."""
        time_data = np.array([0.0, 1.0, 2.0])

        offset_data = TimeAligner.apply_offset(time_data, 10.0)

        expected = np.array([10.0, 11.0, 12.0])
        np.testing.assert_array_almost_equal(offset_data, expected)

    def test_apply_scale(self):
        """Test applying time scale."""
        time_data = np.array([0.0, 1.0, 2.0])

        scaled_data = TimeAligner.apply_scale(time_data, 1000.0)  # Convert s to ms

        expected = np.array([0.0, 1000.0, 2000.0])
        np.testing.assert_array_almost_equal(scaled_data, expected)

    def test_compute_concatenate_offset(self):
        """Test computing offset for concatenation."""
        # Create test A: 0 to 10 seconds
        test_a = Test(name="Test A")
        df_a = DataFile()
        df_a.dataframe = pd.DataFrame({
            "Time": np.linspace(0, 10, 100),
            "Value": np.random.randn(100)
        })
        df_a.time_column = "Time"
        df_a.time_mode = TimeMode.ABSOLUTE
        test_a.add_data_file(df_a)

        # Create test B: 5 to 15 seconds
        test_b = Test(name="Test B")
        df_b = DataFile()
        df_b.dataframe = pd.DataFrame({
            "Time": np.linspace(5, 15, 100),
            "Value": np.random.randn(100)
        })
        df_b.time_column = "Time"
        df_b.time_mode = TimeMode.ABSOLUTE
        test_b.add_data_file(df_b)

        # Compute offset with no gap
        offset = TimeAligner.compute_concatenate_offset(test_a, test_b, gap=0.0)

        # Test B should start at 10 (end of A), so offset = 10 - 5 = 5
        assert offset == pytest.approx(5.0, rel=0.01)

    def test_compute_concatenate_offset_with_gap(self):
        """Test concatenation offset with a gap."""
        test_a = Test(name="Test A")
        df_a = DataFile()
        df_a.dataframe = pd.DataFrame({
            "Time": np.linspace(0, 10, 100),
            "Value": np.random.randn(100)
        })
        df_a.time_column = "Time"
        test_a.add_data_file(df_a)

        test_b = Test(name="Test B")
        df_b = DataFile()
        df_b.dataframe = pd.DataFrame({
            "Time": np.linspace(0, 5, 50),
            "Value": np.random.randn(50)
        })
        df_b.time_column = "Time"
        test_b.add_data_file(df_b)

        offset = TimeAligner.compute_concatenate_offset(test_a, test_b, gap=2.0)

        # Test B starts at 0, A ends at 10, gap of 2
        # Offset = (10 - 0) + 2 = 12
        assert offset == pytest.approx(12.0, rel=0.01)


class TestComputeTimeOffsetForConcat:
    """Tests for compute_time_offset_for_concat function."""

    def test_basic_offset(self):
        """Test basic time offset calculation."""
        offset = compute_time_offset_for_concat(
            end_time=100.0,
            start_time=0.0,
            gap=0.0
        )
        assert offset == pytest.approx(100.0)

    def test_offset_with_gap(self):
        """Test offset with gap."""
        offset = compute_time_offset_for_concat(
            end_time=100.0,
            start_time=0.0,
            gap=5.0
        )
        assert offset == pytest.approx(105.0)

    def test_offset_overlapping_times(self):
        """Test offset when second series starts before first ends."""
        offset = compute_time_offset_for_concat(
            end_time=100.0,
            start_time=50.0,  # Starts in the middle of first
            gap=0.0
        )
        assert offset == pytest.approx(50.0)

    def test_negative_gap_overlap(self):
        """Test negative gap for overlap."""
        offset = compute_time_offset_for_concat(
            end_time=100.0,
            start_time=0.0,
            gap=-10.0
        )
        assert offset == pytest.approx(90.0)


class TestTestComparer:
    """Tests for TestComparer class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create test 1
        self.test1 = Test(name="Test 1")
        df1 = DataFile()
        df1.dataframe = pd.DataFrame({
            "Time": np.linspace(0, 10, 100),
            "Channel_A": np.sin(np.linspace(0, 10, 100)),
            "Channel_B": np.cos(np.linspace(0, 10, 100))
        })
        df1.time_column = "Time"
        df1.time_mode = TimeMode.RELATIVE
        self.test1.add_data_file(df1)
        self.test1.primary_time_column = "Time"

        # Create test 2
        self.test2 = Test(name="Test 2")
        df2 = DataFile()
        df2.dataframe = pd.DataFrame({
            "Time": np.linspace(0, 8, 80),
            "Channel_A": 2 * np.sin(np.linspace(0, 8, 80)),
            "Channel_B": 2 * np.cos(np.linspace(0, 8, 80))
        })
        df2.time_column = "Time"
        df2.time_mode = TimeMode.RELATIVE
        self.test2.add_data_file(df2)
        self.test2.primary_time_column = "Time"

    def test_overlay_mode(self):
        """Test overlay comparison mode."""
        comparer = TestComparer(mode=CompareMode.OVERLAY)

        result = comparer.prepare_tests_for_comparison(
            [self.test1, self.test2],
            ["Channel_A"]
        )

        # Should have data for both tests
        assert len(result) == 2

        # Time should be unchanged
        for test_id, df in result.items():
            assert "_plot_time_" in df.columns
            assert "Channel_A" in df.columns

    def test_concatenate_mode(self):
        """Test concatenate comparison mode."""
        comparer = TestComparer(mode=CompareMode.CONCATENATE, gap=1.0)

        result = comparer.prepare_tests_for_comparison(
            [self.test1, self.test2],
            ["Channel_A"]
        )

        # Get dataframes
        df1 = result[self.test1.id]
        df2 = result[self.test2.id]

        # Test 1 should be unchanged (starts at 0)
        assert df1["_plot_time_"].min() == pytest.approx(0.0, abs=0.1)
        assert df1["_plot_time_"].max() == pytest.approx(10.0, abs=0.1)

        # Test 2 should be offset to start after test 1 + gap
        # Test 1 ends at 10, gap is 1, so test 2 should start at 11
        assert df2["_plot_time_"].min() == pytest.approx(11.0, abs=0.2)

    def test_combined_time_range_overlay(self):
        """Test combined time range in overlay mode."""
        comparer = TestComparer(mode=CompareMode.OVERLAY)

        time_range = comparer.get_combined_time_range([self.test1, self.test2])

        # Should cover both tests
        assert time_range[0] == pytest.approx(0.0, abs=0.1)
        assert time_range[1] == pytest.approx(10.0, abs=0.1)  # Max of both

    def test_combined_time_range_concatenate(self):
        """Test combined time range in concatenate mode."""
        comparer = TestComparer(mode=CompareMode.CONCATENATE, gap=1.0)

        time_range = comparer.get_combined_time_range([self.test1, self.test2])

        # Test 1: 10s, gap: 1s, Test 2: 8s = 19s total
        assert time_range[0] == pytest.approx(0.0, abs=0.1)
        assert time_range[1] == pytest.approx(19.0, abs=0.5)

    def test_empty_tests(self):
        """Test with empty test list."""
        comparer = TestComparer(mode=CompareMode.OVERLAY)

        result = comparer.prepare_tests_for_comparison([], ["Channel_A"])
        assert len(result) == 0

        time_range = comparer.get_combined_time_range([])
        assert time_range == (0.0, 1.0)
