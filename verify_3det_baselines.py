#!/usr/bin/env python3
"""
Verify that generated 3-detection test cases meet baseline constraints
"""

import json
import numpy as np
from generate_3detection_tests import (
    calculate_baseline_angle, calculate_baseline_length,
    lla_to_ecef, Position
)


def verify_test_case(case_file):
    """Verify baseline constraints for a test case."""
    with open(case_file, 'r') as f:
        data = json.load(f)
    
    # Extract sensor and IoO positions
    sensors = []
    ioos = []
    
    for i in range(1, 4):
        det = data[f'detection{i}']
        sensor = Position(det['sensor_lat'], det['sensor_lon'], 0)
        ioo = Position(det['ioo_lat'], det['ioo_lon'], 0)
        sensors.append(sensor)
        ioos.append(ioo)
    
    print(f"\nAnalyzing {case_file}:")
    
    # Check baseline lengths
    print("\nBaseline lengths:")
    for i in range(3):
        length = calculate_baseline_length(sensors[i], ioos[i])
        status = "✓" if length <= 30000 else "✗"
        print(f"  Detection {i+1}: {length/1000:.1f} km {status}")
    
    # Check baseline angles
    print("\nBaseline angles:")
    for i in range(3):
        for j in range(i+1, 3):
            angle = calculate_baseline_angle(sensors[i], ioos[i], sensors[j], ioos[j])
            status = "✓" if angle >= 30 else "✗"
            print(f"  Detection {i+1} vs {j+1}: {angle:.1f}° {status}")
    
    # Show IoO sharing pattern
    unique_ioos = {}
    for i in range(3):
        ioo_key = f"{ioos[i].lat:.6f},{ioos[i].lon:.6f}"
        if ioo_key not in unique_ioos:
            unique_ioos[ioo_key] = []
        unique_ioos[ioo_key].append(i+1)
    
    print("\nIoO sharing pattern:")
    for ioo_key, detections in unique_ioos.items():
        print(f"  IoO at {ioo_key}: used by detections {detections}")


def main():
    import glob
    
    # Find all 3-detection test cases
    test_files = glob.glob("test_3detections/3det_case_*_input.json")
    test_files.sort()
    
    print("=== VERIFYING 3-DETECTION BASELINE CONSTRAINTS ===")
    
    for test_file in test_files:
        verify_test_case(test_file)
    
    print("\n✅ Baseline verification complete")


if __name__ == "__main__":
    main()