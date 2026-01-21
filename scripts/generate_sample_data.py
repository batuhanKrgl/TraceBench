#!/usr/bin/env python3
"""
Sample data generator for testing the Log Viewer application.

Generates synthetic CSV files with:
- Time + multiple channels with units
- Second file adding extra headers
- A second test with different start time
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def generate_sine_wave(t: np.ndarray, freq: float, amp: float, phase: float = 0.0) -> np.ndarray:
    """Generate a sine wave."""
    return amp * np.sin(2 * np.pi * freq * t + phase)


def generate_noise(size: int, scale: float = 0.1) -> np.ndarray:
    """Generate random noise."""
    return np.random.normal(0, scale, size)


def generate_test1_main(output_path: Path, num_points: int = 10000):
    """
    Generate main data file for Test 1.

    Contains: Time, Temperature, Pressure, Flow channels.
    """
    # Time from 0 to 100 seconds
    time = np.linspace(0, 100, num_points)

    # Temperature channels (with units in brackets)
    temp1 = 25 + 10 * np.sin(2 * np.pi * 0.05 * time) + generate_noise(num_points, 0.5)
    temp2 = 30 + 8 * np.sin(2 * np.pi * 0.03 * time + 0.5) + generate_noise(num_points, 0.4)

    # Pressure channels
    press1 = 1.0 + 0.2 * np.sin(2 * np.pi * 0.1 * time) + generate_noise(num_points, 0.02)
    press2 = 2.5 + 0.3 * np.sin(2 * np.pi * 0.08 * time + 1.0) + generate_noise(num_points, 0.03)

    # Flow channels
    flow1 = 100 + 20 * np.sin(2 * np.pi * 0.02 * time) + generate_noise(num_points, 2)

    df = pd.DataFrame({
        "Time [s]": time,
        "Temperature_1 [C]": temp1,
        "Temperature_2 [C]": temp2,
        "Pressure_1 [bar]": press1,
        "Pressure_2 [bar]": press2,
        "Flow_Rate [L/min]": flow1,
    })

    df.to_csv(output_path, index=False)
    print(f"Generated: {output_path} ({num_points} points, {len(df.columns)} columns)")


def generate_test1_extra_headers(output_path: Path, num_points: int = 10000):
    """
    Generate extra headers file for Test 1.

    Contains additional channels that can be merged with the main file.
    """
    # Same time base
    time = np.linspace(0, 100, num_points)

    # Voltage channels
    volt1 = 12.0 + 0.5 * np.sin(2 * np.pi * 0.15 * time) + generate_noise(num_points, 0.05)
    volt2 = 5.0 + 0.1 * np.sin(2 * np.pi * 0.2 * time) + generate_noise(num_points, 0.02)

    # Current channels
    curr1 = 1.5 + 0.3 * np.sin(2 * np.pi * 0.12 * time + 0.3) + generate_noise(num_points, 0.05)

    # RPM channel
    rpm = 3000 + 500 * np.sin(2 * np.pi * 0.01 * time) + generate_noise(num_points, 50)

    df = pd.DataFrame({
        "Time [s]": time,
        "Voltage_Main [V]": volt1,
        "Voltage_Aux [V]": volt2,
        "Current_Main [A]": curr1,
        "Motor_Speed [rpm]": rpm,
    })

    df.to_csv(output_path, index=False)
    print(f"Generated: {output_path} ({num_points} points, {len(df.columns)} columns)")


def generate_test2(output_path: Path, num_points: int = 8000):
    """
    Generate data file for Test 2.

    Has a different start time and slightly different characteristics.
    """
    # Time from 50 to 130 seconds (different start time)
    time = np.linspace(50, 130, num_points)

    # Temperature channels (slightly different patterns)
    temp1 = 28 + 12 * np.sin(2 * np.pi * 0.06 * time) + generate_noise(num_points, 0.6)
    temp2 = 32 + 9 * np.sin(2 * np.pi * 0.04 * time + 0.3) + generate_noise(num_points, 0.5)

    # Pressure channels
    press1 = 1.2 + 0.25 * np.sin(2 * np.pi * 0.12 * time) + generate_noise(num_points, 0.025)
    press2 = 2.8 + 0.35 * np.sin(2 * np.pi * 0.09 * time + 0.8) + generate_noise(num_points, 0.035)

    # Flow channels
    flow1 = 110 + 25 * np.sin(2 * np.pi * 0.025 * time) + generate_noise(num_points, 2.5)

    df = pd.DataFrame({
        "Time [s]": time,
        "Temperature_1 [C]": temp1,
        "Temperature_2 [C]": temp2,
        "Pressure_1 [bar]": press1,
        "Pressure_2 [bar]": press2,
        "Flow_Rate [L/min]": flow1,
    })

    df.to_csv(output_path, index=False)
    print(f"Generated: {output_path} ({num_points} points, {len(df.columns)} columns)")


def generate_large_dataset(output_path: Path, num_points: int = 500000):
    """
    Generate a large dataset for performance testing.
    """
    print(f"Generating large dataset with {num_points} points...")

    time = np.linspace(0, 1000, num_points)

    # Multiple temperature channels
    data = {"Time [s]": time}

    for i in range(10):
        freq = 0.01 + i * 0.005
        amp = 10 + i * 2
        phase = i * 0.3
        base = 20 + i * 5
        data[f"Temperature_{i+1} [C]"] = (
            base + amp * np.sin(2 * np.pi * freq * time + phase) +
            generate_noise(num_points, 0.5)
        )

    for i in range(5):
        freq = 0.02 + i * 0.01
        amp = 0.3 + i * 0.1
        phase = i * 0.5
        base = 1.0 + i * 0.5
        data[f"Pressure_{i+1} [bar]"] = (
            base + amp * np.sin(2 * np.pi * freq * time + phase) +
            generate_noise(num_points, 0.02)
        )

    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)
    print(f"Generated: {output_path} ({num_points} points, {len(df.columns)} columns)")


def generate_mismatched_headers(output_path: Path, num_points: int = 5000):
    """
    Generate a file with mismatched/renamed headers for testing header diff.
    """
    time = np.linspace(0, 50, num_points)

    # Some matching headers, some renamed, some new
    df = pd.DataFrame({
        "Time [s]": time,
        "Temp_1 [C]": 25 + 10 * np.sin(2 * np.pi * 0.05 * time),  # Renamed from Temperature_1
        "Temperature_2 [C]": 30 + 8 * np.sin(2 * np.pi * 0.03 * time),  # Matches
        "Pressure_Main [bar]": 1.0 + 0.2 * np.sin(2 * np.pi * 0.1 * time),  # Renamed
        "New_Sensor [mV]": 500 + 100 * np.sin(2 * np.pi * 0.07 * time),  # New
    })

    df.to_csv(output_path, index=False)
    print(f"Generated: {output_path} ({num_points} points, {len(df.columns)} columns)")


def main():
    parser = argparse.ArgumentParser(description="Generate sample data for Log Viewer")
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=Path("sample_data"),
        help="Output directory for generated files"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate all sample files including large dataset"
    )
    parser.add_argument(
        "--large",
        action="store_true",
        help="Generate large dataset for performance testing"
    )

    args = parser.parse_args()

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Generate standard test files
    generate_test1_main(args.output_dir / "test1_main.csv")
    generate_test1_extra_headers(args.output_dir / "test1_extra_headers.csv")
    generate_test2(args.output_dir / "test2.csv")
    generate_mismatched_headers(args.output_dir / "test1_mismatched.csv")

    if args.all or args.large:
        generate_large_dataset(args.output_dir / "large_dataset.csv")

    print(f"\nAll files generated in: {args.output_dir.absolute()}")
    print("\nUsage guide:")
    print("1. Import 'test1_main.csv' as a new test")
    print("2. Add 'test1_extra_headers.csv' as additional headers to the same test")
    print("3. Create a second test with 'test2.csv' to compare")
    print("4. Use 'test1_mismatched.csv' to test header diff dialog")


if __name__ == "__main__":
    main()
