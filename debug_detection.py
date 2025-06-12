#!/usr/bin/env python3
"""
Debug script to understand bistatic range calculations and why TelemetrySolver isn't converging.
"""

import json
import numpy as np
from generate_test_detections import (
    lla_to_ecef, Position, calculate_bistatic_range,
    WGS84_A, WGS84_E2
)


def analyze_test_case(filename):
    """Analyze a test case to understand the geometry."""
    with open(filename, 'r') as f:
        data = json.load(f)
    
    print(f"\nAnalyzing: {filename}")
    print("="*60)
    
    for det_name, det in data.items():
        print(f"\n{det_name}:")
        sensor = Position(det['sensor_lat'], det['sensor_lon'], 0)
        ioo = Position(det['ioo_lat'], det['ioo_lon'], 0)
        
        # Calculate baseline distance
        sensor_ecef = lla_to_ecef(sensor.lat, sensor.lon, sensor.alt)
        ioo_ecef = lla_to_ecef(ioo.lat, ioo.lon, ioo.alt)
        baseline_km = np.linalg.norm(sensor_ecef - ioo_ecef) / 1000
        
        print(f"  Sensor: ({sensor.lat:.4f}, {sensor.lon:.4f})")
        print(f"  IoO: ({ioo.lat:.4f}, {ioo.lon:.4f})")
        print(f"  Baseline distance: {baseline_km:.2f} km")
        print(f"  Bistatic range: {det['bistatic_range_km']:.2f} km")
        print(f"  Doppler: {det['doppler_hz']:.2f} Hz")
        
        # The bistatic range tells us the target is on an ellipse
        # with foci at sensor and IoO
        print(f"  → Target is {det['bistatic_range_km']:.2f} km further than direct path")


def compare_with_reference():
    """Compare with the reference test_data.json"""
    print("\nReference test_data.json:")
    analyze_test_case("TelemetrySolver/test_data.json")
    
    print("\n\nGenerated test cases:")
    # Analyze a few generated cases
    for i in [1, 8]:
        try:
            analyze_test_case(f"test_detections/test_case_{i}_input.json")
        except:
            pass


if __name__ == "__main__":
    compare_with_reference()