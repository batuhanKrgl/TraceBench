"""
Core module for Log Viewer application.
Contains data models, IO handlers, merge logic, and filter management.
"""

from .models import (
    AppLayout,
    ChannelMetadata,
    CompareMode,
    DataFile,
    FilterState,
    HeaderDiff,
    HeaderMismatchStrategy,
    JoinStrategy,
    PlotSettings,
    Test,
    TimeMode,
)
from .io_handler import (
    FileReader,
    HeaderParser,
    apply_header_mapping,
    compute_header_diff,
)
from .merge_handler import (
    DataMerger,
    TestComparer,
    TimeAligner,
    add_headers_file_to_test,
    compute_time_offset_for_concat,
)
from .filter_manager import (
    ChannelFilterHelper,
    FilterManager,
    TimeRangeHelper,
)

__all__ = [
    # Models
    "AppLayout",
    "ChannelMetadata",
    "CompareMode",
    "DataFile",
    "FilterState",
    "HeaderDiff",
    "HeaderMismatchStrategy",
    "JoinStrategy",
    "PlotSettings",
    "Test",
    "TimeMode",
    # IO
    "FileReader",
    "HeaderParser",
    "apply_header_mapping",
    "compute_header_diff",
    # Merge
    "DataMerger",
    "TestComparer",
    "TimeAligner",
    "add_headers_file_to_test",
    "compute_time_offset_for_concat",
    # Filter
    "ChannelFilterHelper",
    "FilterManager",
    "TimeRangeHelper",
]
