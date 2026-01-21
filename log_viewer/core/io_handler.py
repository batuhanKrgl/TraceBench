"""
File IO and header parsing for the Log Viewer application.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Optional

import pandas as pd
from rapidfuzz import fuzz

from .models import ChannelMetadata, DataFile, HeaderDiff, Test


# Category mappings for common channel types
CATEGORY_KEYWORDS = {
    "Temperature": ["temp", "temperature", "therm", "tc", "rtd"],
    "Pressure": ["press", "pressure", "psi", "bar", "kpa", "mpa"],
    "Flow": ["flow", "rate", "volume", "gpm", "lpm", "cfm"],
    "Voltage": ["volt", "voltage", "v", "mv", "potential"],
    "Current": ["current", "amp", "ampere", "ma", "ua"],
    "Speed": ["speed", "rpm", "velocity", "freq", "frequency", "hz"],
    "Position": ["pos", "position", "angle", "deg", "rad", "distance"],
    "Force": ["force", "torque", "load", "nm", "lbf", "newton"],
    "Time": ["time", "timestamp", "date", "elapsed"],
    "Acceleration": ["accel", "acceleration", "g", "vibration"],
    "Power": ["power", "watt", "kw", "hp", "energy"],
}

# Unit extraction patterns
UNIT_PATTERNS = [
    # Pattern: Name [Unit]
    re.compile(r"^(?P<name>.+?)\s*\[(?P<unit>[^\]]+)\]$"),
    # Pattern: Name (Unit)
    re.compile(r"^(?P<name>.+?)\s*\((?P<unit>[^)]+)\)$"),
    # Pattern: Name_Unit (e.g., TEMP_C, PRESS_PSI)
    re.compile(r"^(?P<name>.+?)_(?P<unit>[A-Za-z]{1,5})$"),
    # Pattern: Name.Unit
    re.compile(r"^(?P<name>.+?)\.(?P<unit>[A-Za-z]{1,5})$"),
]

# Known unit mappings
KNOWN_UNITS = {
    "c": "°C", "f": "°F", "k": "K",
    "bar": "bar", "psi": "psi", "kpa": "kPa", "mpa": "MPa", "pa": "Pa",
    "v": "V", "mv": "mV", "kv": "kV",
    "a": "A", "ma": "mA", "ua": "µA",
    "s": "s", "ms": "ms", "us": "µs", "min": "min", "h": "h",
    "m": "m", "mm": "mm", "cm": "cm", "km": "km", "in": "in", "ft": "ft",
    "kg": "kg", "g": "g", "mg": "mg", "lb": "lb",
    "n": "N", "kn": "kN", "lbf": "lbf",
    "nm": "N·m", "ftlb": "ft·lb",
    "rpm": "rpm", "hz": "Hz", "khz": "kHz",
    "l": "L", "ml": "mL", "gal": "gal",
    "lpm": "L/min", "gpm": "gal/min", "cfm": "ft³/min",
    "w": "W", "kw": "kW", "mw": "MW", "hp": "hp",
    "deg": "°", "rad": "rad",
    "%": "%", "pct": "%", "percent": "%",
}


class HeaderParser:
    """Pluggable header parser for extracting metadata from header names."""

    def __init__(self):
        self.custom_parsers: list[Callable[[str], Optional[ChannelMetadata]]] = []

    def add_parser(self, parser: Callable[[str], Optional[ChannelMetadata]]) -> None:
        """Add a custom parser function."""
        self.custom_parsers.append(parser)

    def parse(self, header: str) -> ChannelMetadata:
        """Parse a header string into channel metadata."""
        # Try custom parsers first
        for parser in self.custom_parsers:
            result = parser(header)
            if result:
                return result

        # Default parsing
        return self._default_parse(header)

    def _default_parse(self, header: str) -> ChannelMetadata:
        """Default header parsing logic."""
        original_name = header
        display_name = header
        unit = ""
        category = "Unknown"

        # Try unit extraction patterns
        for pattern in UNIT_PATTERNS:
            match = pattern.match(header)
            if match:
                display_name = match.group("name").strip()
                raw_unit = match.group("unit").strip()
                unit = KNOWN_UNITS.get(raw_unit.lower(), raw_unit)
                break

        # Clean up display name
        display_name = display_name.replace("_", " ").strip()

        # Infer category from name
        name_lower = display_name.lower()
        for cat, keywords in CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in name_lower:
                    category = cat
                    break
            if category != "Unknown":
                break

        return ChannelMetadata(
            original_name=original_name,
            display_name=display_name,
            unit=unit,
            category=category
        )


class FileReader:
    """Handles reading various file formats."""

    def __init__(self, header_parser: Optional[HeaderParser] = None):
        self.header_parser = header_parser or HeaderParser()

    def detect_delimiter(self, filepath: Path, encoding: str = "utf-8") -> str:
        """Detect the delimiter of a text file."""
        with open(filepath, "r", encoding=encoding, errors="replace") as f:
            # Read first few lines
            sample = ""
            for _ in range(10):
                line = f.readline()
                if not line:
                    break
                sample += line

        # Count potential delimiters
        delimiters = {",": 0, "\t": 0, ";": 0, "|": 0}
        for delim in delimiters:
            delimiters[delim] = sample.count(delim)

        # Return most common delimiter
        max_count = max(delimiters.values())
        if max_count == 0:
            return ","  # Default to comma

        for delim, count in delimiters.items():
            if count == max_count:
                return delim

        return ","

    def detect_encoding(self, filepath: Path) -> str:
        """Detect file encoding."""
        encodings = ["utf-8", "utf-16", "latin-1", "cp1252", "iso-8859-1"]

        for enc in encodings:
            try:
                with open(filepath, "r", encoding=enc) as f:
                    f.read(1024)
                return enc
            except (UnicodeDecodeError, UnicodeError):
                continue

        return "utf-8"  # Default fallback

    def detect_time_column(self, df: pd.DataFrame) -> Optional[str]:
        """Try to detect the time column in a dataframe."""
        time_keywords = ["time", "timestamp", "date", "elapsed", "t", "seconds", "sec", "ms"]

        for col in df.columns:
            col_lower = col.lower()
            for kw in time_keywords:
                if kw in col_lower:
                    return col

        # If no keyword match, assume first column is time
        if len(df.columns) > 0:
            return df.columns[0]

        return None

    def read_file(self, filepath: Path | str) -> DataFile:
        """Read a data file and return a DataFile object."""
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        suffix = filepath.suffix.lower()

        if suffix in [".csv", ".txt", ".tsv", ".dat"]:
            return self._read_text_file(filepath)
        elif suffix in [".xlsx", ".xls"]:
            return self._read_excel_file(filepath)
        else:
            # Try as text file
            return self._read_text_file(filepath)

    def _read_text_file(self, filepath: Path) -> DataFile:
        """Read a text-based data file (CSV/TSV/etc.)."""
        encoding = self.detect_encoding(filepath)
        delimiter = self.detect_delimiter(filepath, encoding)

        # Read dataframe
        df = pd.read_csv(
            filepath,
            delimiter=delimiter,
            encoding=encoding,
            low_memory=False
        )

        # Create DataFile
        data_file = DataFile(
            filepath=filepath,
            filename=filepath.name,
            delimiter=delimiter,
            encoding=encoding,
            headers=list(df.columns),
            dataframe=df
        )

        # Parse channel metadata
        for header in df.columns:
            data_file.channel_metadata[header] = self.header_parser.parse(header)

        # Detect time column
        time_col = self.detect_time_column(df)
        if time_col:
            data_file.time_column = time_col

        return data_file

    def _read_excel_file(self, filepath: Path, sheet_name: int | str = 0) -> DataFile:
        """Read an Excel file."""
        df = pd.read_excel(filepath, sheet_name=sheet_name)

        data_file = DataFile(
            filepath=filepath,
            filename=filepath.name,
            delimiter=",",  # N/A for Excel
            encoding="utf-8",
            headers=list(df.columns),
            dataframe=df
        )

        # Parse channel metadata
        for header in df.columns:
            data_file.channel_metadata[header] = self.header_parser.parse(header)

        # Detect time column
        time_col = self.detect_time_column(df)
        if time_col:
            data_file.time_column = time_col

        return data_file

    def reload_file(self, data_file: DataFile) -> bool:
        """Reload data from the file path."""
        if not data_file.filepath.exists():
            return False

        suffix = data_file.filepath.suffix.lower()

        try:
            if suffix in [".csv", ".txt", ".tsv", ".dat"]:
                df = pd.read_csv(
                    data_file.filepath,
                    delimiter=data_file.delimiter,
                    encoding=data_file.encoding,
                    low_memory=False
                )
            elif suffix in [".xlsx", ".xls"]:
                df = pd.read_excel(data_file.filepath)
            else:
                df = pd.read_csv(
                    data_file.filepath,
                    delimiter=data_file.delimiter,
                    encoding=data_file.encoding,
                    low_memory=False
                )

            data_file.dataframe = df
            data_file.headers = list(df.columns)
            return True

        except Exception:
            return False


def compute_header_diff(
    test_headers: list[str],
    file_headers: list[str],
    fuzzy_threshold: int = 80
) -> HeaderDiff:
    """
    Compute differences between test headers and file headers.

    Args:
        test_headers: Canonical headers from the test
        file_headers: Headers from the new file
        fuzzy_threshold: Minimum similarity score for fuzzy matching (0-100)

    Returns:
        HeaderDiff object with missing, extra, matched, and fuzzy matches
    """
    test_set = set(test_headers)
    file_set = set(file_headers)

    matched = list(test_set & file_set)
    missing = list(test_set - file_set)
    extra = list(file_set - test_set)

    # Find fuzzy matches for extra headers
    fuzzy_matches: dict[str, str] = {}

    for extra_h in extra:
        best_match = None
        best_score = 0

        for missing_h in missing:
            # Use token sort ratio for better matching
            score = fuzz.token_sort_ratio(extra_h.lower(), missing_h.lower())
            if score > best_score and score >= fuzzy_threshold:
                best_score = score
                best_match = missing_h

        if best_match:
            fuzzy_matches[extra_h] = best_match

    return HeaderDiff(
        missing=sorted(missing),
        extra=sorted(extra),
        matched=sorted(matched),
        fuzzy_matches=fuzzy_matches
    )


def apply_header_mapping(
    data_file: DataFile,
    column_mapping: dict[str, str]
) -> None:
    """
    Apply column name mapping to a data file.

    Args:
        data_file: The data file to modify
        column_mapping: Dict mapping old_name -> new_name
    """
    if data_file.dataframe is None:
        return

    # Rename columns in dataframe
    data_file.dataframe.rename(columns=column_mapping, inplace=True)

    # Update headers list
    data_file.headers = list(data_file.dataframe.columns)

    # Update channel metadata
    new_metadata: dict[str, ChannelMetadata] = {}
    for old_name, new_name in column_mapping.items():
        if old_name in data_file.channel_metadata:
            meta = data_file.channel_metadata[old_name]
            meta.original_name = new_name  # Update original name too
            new_metadata[new_name] = meta

    # Keep unmapped metadata and add renamed
    for name, meta in data_file.channel_metadata.items():
        if name not in column_mapping:
            new_metadata[name] = meta

    data_file.channel_metadata = new_metadata

    # Update time column if renamed
    if data_file.time_column in column_mapping:
        data_file.time_column = column_mapping[data_file.time_column]
