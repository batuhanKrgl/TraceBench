"""
Tests for header diff logic.
"""
import pytest

from log_viewer.core import compute_header_diff, HeaderDiff


class TestHeaderDiff:
    """Tests for compute_header_diff function."""

    def test_exact_match(self):
        """Test headers that match exactly."""
        test_headers = ["Time", "Temp", "Pressure"]
        file_headers = ["Time", "Temp", "Pressure"]

        diff = compute_header_diff(test_headers, file_headers)

        assert not diff.has_differences
        assert diff.missing == []
        assert diff.extra == []
        assert set(diff.matched) == {"Time", "Temp", "Pressure"}

    def test_missing_headers(self):
        """Test when file is missing headers from test."""
        test_headers = ["Time", "Temp", "Pressure", "Flow"]
        file_headers = ["Time", "Temp"]

        diff = compute_header_diff(test_headers, file_headers)

        assert diff.has_differences
        assert set(diff.missing) == {"Pressure", "Flow"}
        assert diff.extra == []

    def test_extra_headers(self):
        """Test when file has extra headers not in test."""
        test_headers = ["Time", "Temp"]
        file_headers = ["Time", "Temp", "Voltage", "Current"]

        diff = compute_header_diff(test_headers, file_headers)

        assert diff.has_differences
        assert diff.missing == []
        assert set(diff.extra) == {"Voltage", "Current"}

    def test_mixed_differences(self):
        """Test when there are both missing and extra headers."""
        test_headers = ["Time", "Temp", "Pressure"]
        file_headers = ["Time", "Temp", "Voltage"]

        diff = compute_header_diff(test_headers, file_headers)

        assert diff.has_differences
        assert diff.missing == ["Pressure"]
        assert diff.extra == ["Voltage"]
        assert set(diff.matched) == {"Time", "Temp"}

    def test_fuzzy_match_exact(self):
        """Test fuzzy matching with high similarity."""
        test_headers = ["Temperature_1", "Pressure_Main"]
        file_headers = ["Temperature_1", "Pressure_main"]  # Case difference

        diff = compute_header_diff(test_headers, file_headers, fuzzy_threshold=80)

        # Should find fuzzy match between Pressure_Main and Pressure_main
        assert "Pressure_main" in diff.extra
        assert "Pressure_Main" in diff.missing
        assert "Pressure_main" in diff.fuzzy_matches
        assert diff.fuzzy_matches["Pressure_main"] == "Pressure_Main"

    def test_fuzzy_match_renamed(self):
        """Test fuzzy matching with renamed columns."""
        test_headers = ["Temperature_Sensor_1", "Pressure_Gauge_A"]
        file_headers = ["Temp_Sensor_1", "Press_Gauge_A"]

        diff = compute_header_diff(test_headers, file_headers, fuzzy_threshold=70)

        # Should find fuzzy matches for similar names
        assert len(diff.fuzzy_matches) > 0

    def test_no_fuzzy_match_below_threshold(self):
        """Test that fuzzy matches aren't found below threshold."""
        test_headers = ["Temperature"]
        file_headers = ["Voltage"]  # Completely different

        diff = compute_header_diff(test_headers, file_headers, fuzzy_threshold=80)

        assert "Voltage" not in diff.fuzzy_matches

    def test_empty_headers(self):
        """Test with empty header lists."""
        diff = compute_header_diff([], [])
        assert not diff.has_differences
        assert diff.matched == []

        diff = compute_header_diff(["Time"], [])
        assert diff.has_differences
        assert diff.missing == ["Time"]

        diff = compute_header_diff([], ["Time"])
        assert diff.has_differences
        assert diff.extra == ["Time"]

    def test_summary(self):
        """Test get_summary method."""
        test_headers = ["A", "B", "C"]
        file_headers = ["A", "D", "E"]

        diff = compute_header_diff(test_headers, file_headers)

        summary = diff.get_summary()
        assert "Missing" in summary
        assert "Extra" in summary

    def test_summary_exact_match(self):
        """Test summary when headers match exactly."""
        test_headers = ["A", "B"]
        file_headers = ["A", "B"]

        diff = compute_header_diff(test_headers, file_headers)

        summary = diff.get_summary()
        assert "match exactly" in summary.lower()
