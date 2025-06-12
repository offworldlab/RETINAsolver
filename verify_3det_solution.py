#!/usr/bin/env python3
"""
Verify 3-detection solver solution against ground truth
"""

import json
import numpy as np
import subprocess
import sys


def verify_solution(input_file, truth_file):
    """Run solver and compare with ground truth"""
    
    # Run the solver
    result = subprocess.run(
        [sys.executable, "TelemetrySolver/main_3det.py", input_file],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Solver failed: {result.stderr}")
        return
    
    # Parse solver output
    try:
        solution = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"❌ Failed to parse solver output: {result.stdout}")
        return
    
    # Load ground truth
    with open(truth_file, 'r') as f:
        truth = json.load(f)
    
    if "error" in solution:
        print(f"❌ Solver error: {solution['error']}")
        return
    
    # Calculate errors (handle longitude wraparound)
    lat_error = abs(solution["latitude"] - truth["latitude"]) * 111111.0  # meters
    lon_diff = solution["longitude"] - truth["longitude"]
    # Handle longitude wraparound
    if lon_diff > 180:
        lon_diff -= 360
    elif lon_diff < -180:
        lon_diff += 360
    lon_error = abs(lon_diff) * 111111.0 * np.cos(np.radians(truth["latitude"]))
    position_error = np.sqrt(lat_error**2 + lon_error**2)
    alt_error = abs(solution["altitude"] - truth["altitude"])
    
    vel_east_error = abs(solution["velocity_east"] - truth["velocity_east"])
    vel_north_error = abs(solution["velocity_north"] - truth["velocity_north"])
    vel_up_error = abs(solution["velocity_up"] - truth["velocity_up"])
    velocity_error = np.sqrt(vel_east_error**2 + vel_north_error**2 + vel_up_error**2)
    
    # Display results
    print(f"\n{'='*60}")
    print(f"Case: {input_file}")
    print(f"{'='*60}")
    
    print(f"\nPOSITION COMPARISON:")
    print(f"{'':20} {'Solution':>15} {'Truth':>15} {'Error':>10}")
    print(f"{'-'*60}")
    print(f"{'Latitude (deg)':20} {solution['latitude']:>15.6f} {truth['latitude']:>15.6f}")
    print(f"{'Longitude (deg)':20} {solution['longitude']:>15.6f} {truth['longitude']:>15.6f}")
    print(f"{'Altitude (m)':20} {solution['altitude']:>15.1f} {truth['altitude']:>15.1f} {alt_error:>10.1f}")
    print(f"{'Horizontal (m)':20} {'-':>15} {'-':>15} {position_error:>10.1f}")
    
    print(f"\nVELOCITY COMPARISON:")
    print(f"{'':20} {'Solution':>15} {'Truth':>15} {'Error':>10}")
    print(f"{'-'*60}")
    print(f"{'East (m/s)':20} {solution['velocity_east']:>15.1f} {truth['velocity_east']:>15.1f} {vel_east_error:>10.1f}")
    print(f"{'North (m/s)':20} {solution['velocity_north']:>15.1f} {truth['velocity_north']:>15.1f} {vel_north_error:>10.1f}")
    print(f"{'Up (m/s)':20} {solution['velocity_up']:>15.1f} {truth['velocity_up']:>15.1f} {vel_up_error:>10.1f}")
    print(f"{'Total (m/s)':20} {'-':>15} {'-':>15} {velocity_error:>10.1f}")
    
    print(f"\nCONVERGENCE:")
    print(f"  Convergence metric: {solution['convergence_metric']:.2e} m")
    print(f"  Residuals: {[f'{r:.2e}' for r in solution['residuals']]}")
    
    # Overall assessment
    print(f"\nASSESSMENT:")
    if position_error < 50 and velocity_error < 10:
        print(f"✅ EXCELLENT: Position error {position_error:.1f}m, Velocity error {velocity_error:.1f}m/s")
    elif position_error < 200 and velocity_error < 50:
        print(f"✅ GOOD: Position error {position_error:.1f}m, Velocity error {velocity_error:.1f}m/s")
    else:
        print(f"⚠️  POOR: Position error {position_error:.1f}m, Velocity error {velocity_error:.1f}m/s")


def main():
    import glob
    
    # Find test cases
    test_cases = glob.glob("test_3detections/3det_case_*_input.json")
    test_cases.sort()
    
    print("=== VERIFYING 3-DETECTION SOLVER ACCURACY ===")
    
    for test_case in test_cases[:3]:  # Test first 3 cases
        truth_file = test_case.replace('_input.json', '_truth.json')
        verify_solution(test_case, truth_file)
    
    print(f"\n✅ Verification complete")


if __name__ == "__main__":
    main()