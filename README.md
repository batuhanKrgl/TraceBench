# Log Viewer & Comparator

A multi-test, multi-header log viewer and comparator GUI application built with Python, PySide6, and pyqtgraph.

## Features

- **Multiple Tests Support**: Create and manage multiple test runs, each containing multiple data files
- **Multi-File Import**: Import multiple CSV/TSV/Excel files into a single test
- **Header Parsing**: Automatic parsing of channel names, units, and categories from header formats like `Temperature [C]` or `PRESS_bar`
- **Header Diff Dialog**: Smart detection of mismatched headers with fuzzy matching and mapping options
- **Time Alignment**: Support for absolute, relative, and custom offset time modes
- **Multi-Axis Plotting**: Primary plot supports up to 3 Y-axes for comparing different units
- **Crosshair & Readout**: Interactive crosshair with value readout, lockable for alignment
- **Filter Synchronization**: Filters applied to a dataset are synchronized across all plots
- **Comparison Modes**: Overlay (same time axis) or Concatenate (end-to-end with configurable gap)
- **Layout Persistence**: Save and load complete application state including tests, plots, and filters
- **Performance**: Efficient handling of large datasets (100k+ points) with downsampling

## Installation

### Requirements

- Python 3.11 or higher
- PySide6 (Qt 6)
- pyqtgraph
- pandas
- numpy
- openpyxl (for Excel support)
- rapidfuzz (for fuzzy header matching)

### Install from Source

```bash
# Clone the repository
cd TraceBench

# Install in development mode
pip install -e .

# Or install dependencies directly
pip install -r requirements.txt
```

## Quick Start

### Running the Application

```bash
# Using the installed entry point
log-viewer

# Or run directly
python -m log_viewer.app.main
```

### Generate Sample Data

```bash
# Generate sample CSV files for testing
python scripts/generate_sample_data.py -o sample_data

# Include large dataset for performance testing
python scripts/generate_sample_data.py -o sample_data --large
```

## Usage Guide

### Importing Data

1. **Create a New Test**:
   - Click "New Test" in the toolbar or use `Ctrl+N`
   - This creates an empty test container

2. **Import Files**:
   - Click "Import" or use `Ctrl+I`
   - Select one or more CSV/TSV/Excel files
   - Files are automatically parsed and added to a new test

3. **Add Files to Existing Test**:
   - Select a test in the left panel
   - Use File > Add Files to Test
   - Header differences will be detected and you can choose a resolution strategy

4. **Add Headers File (Merge Columns)**:
   - Select a test
   - Use File > Add Headers File
   - Choose a join strategy (Time Nearest, Time Exact, Alternative Key, or Append)
   - New columns will be merged with existing data

### Comparing Tests

1. **Overlay Mode** (default):
   - Tests are plotted on the same time axis
   - Useful for comparing similar test runs

2. **Concatenate Mode**:
   - Tests are placed end-to-end
   - Configure gap between tests via Compare > Set Concatenate Gap

### Plotting

1. **Select Channels**:
   - Use the right panel to browse channels by Category > Unit
   - Check channels to add them to the plot
   - For the primary plot, cycle through Y1/Y2/Y3 by clicking the axis column

2. **Multiple Plot Panels**:
   - Add up to 3 plot panels via View > Add Plot Panel
   - Each panel can show different channels
   - Crosshairs are synchronized across panels

3. **Axis Settings**:
   - Click "Axis Settings" on any plot
   - Configure labels, units, ranges, and autoscale options

### Filtering

1. **Time Range Filter**:
   - Use the filter panel at the top
   - Set min/max time or use the slider

2. **Channel Value Filter**:
   - Select a channel from the dropdown
   - Set min/max value constraints

3. **Filter Synchronization**:
   - Filters applied to a test automatically update all plots showing that test

### Crosshair & Readout

- **Hover**: Move mouse over plot to see crosshair and values
- **Lock**: Double-click or click "Lock Crosshair" to freeze position
- **Sync**: Crosshair position is synchronized across all plots

### Save/Load Layout

- **Save**: File > Save Layout (or `Ctrl+S`)
  - Saves complete state: tests, files, plots, filters, window size

- **Load**: File > Load Layout (or `Ctrl+O`)
  - Restores previous state
  - Missing files can be remapped to new locations

## Project Structure

```
TraceBench/
├── log_viewer/
│   ├── __init__.py
│   ├── app/                    # Qt UI components
│   │   ├── __init__.py
│   │   ├── main.py            # Entry point
│   │   ├── main_window.py     # Main application window
│   │   ├── dialogs.py         # Dialog windows
│   │   └── widgets.py         # UI widgets
│   ├── core/                   # Data model and logic
│   │   ├── __init__.py
│   │   ├── models.py          # Data classes
│   │   ├── io_handler.py      # File I/O
│   │   ├── merge_handler.py   # Merge/join logic
│   │   └── filter_manager.py  # Filter management
│   └── plot/                   # Plotting components
│       ├── __init__.py
│       └── plot_widget.py     # Multi-axis plot
├── tests/                      # Pytest tests
│   ├── test_header_diff.py
│   ├── test_time_offset.py
│   └── test_merge_join.py
├── scripts/
│   └── generate_sample_data.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_header_diff.py
```

## Header Parsing

The application automatically parses headers to extract:
- **Display Name**: Human-readable name
- **Unit**: Measurement unit
- **Category**: Channel category (Temperature, Pressure, etc.)

Supported formats:
- `Name [Unit]` - e.g., `Temperature [C]`
- `Name (Unit)` - e.g., `Pressure (bar)`
- `Name_Unit` - e.g., `TEMP_C`
- `Name.Unit` - e.g., `Flow.LPM`

## Configuration

### Layout File Format (JSON)

```json
{
  "version": "1.0",
  "tests": [...],
  "plot_count": 2,
  "plot_settings": [...],
  "compare_mode": "OVERLAY",
  "compare_gap": 0.0,
  "window_width": 1400,
  "window_height": 900
}
```

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| New Test | `Ctrl+N` |
| Import Files | `Ctrl+I` |
| Save Layout | `Ctrl+S` |
| Load Layout | `Ctrl+O` |
| Add Plot | `Ctrl+P` |
| Quit | `Ctrl+Q` |

## Troubleshooting

### Performance Issues with Large Files

- Enable downsampling (enabled by default)
- Reduce the number of visible channels
- Use time range filtering to limit displayed data

### Missing Dependencies

```bash
pip install PySide6 pyqtgraph pandas numpy openpyxl rapidfuzz
```

### File Import Errors

- Ensure files are valid CSV/TSV/Excel format
- Check encoding (UTF-8 recommended)
- Verify delimiter detection

## License

MIT License
