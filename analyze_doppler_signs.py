#!/usr/bin/env python3
"""
Analyze why TelemetrySolver has sign errors in velocity estimation
"""

import json
import numpy as np
from generate_test_detections import calculate_doppler, Position, Velocity

print("=== DOPPLER SIGN ANALYSIS ===\n")

# Load a successful test case
with open("test_detections/test_case_6_input.json", 'r') as f:
    detections = json.load(f)
    
with open("test_detections/test_case_6_truth.json", 'r') as f:
    truth = json.load(f)

print("CASE 6 DATA:")
print(f"True velocity: east={truth['velocity_east']:.1f}, north={truth['velocity_north']:.1f}")
print(f"Solver velocity: east=186.9, north=19.2")
print(f"Error: Magnitude correct but signs flipped!\n")

# Extract positions for analysis
sensor1 = Position(detections["detection1"]["sensor_lat"], 
                  detections["detection1"]["sensor_lon"], 0)
ioo1 = Position(detections["detection1"]["ioo_lat"],
               detections["detection1"]["ioo_lon"], 0)
target = Position(truth["latitude"], truth["longitude"], truth["altitude"])
velocity = Velocity(truth["velocity_east"], truth["velocity_north"], 0)

print("=== DOPPLER CALCULATION COMPARISON ===\n")

print("1. SYNTHETIC DATA GENERATOR (generate_test_detections.py):")
print("   Line 232: v_radial_tx = np.dot(velocity_ecef, ioo_to_target_unit)")
print("   Line 233: v_radial_rx = np.dot(velocity_ecef, target_to_sensor_unit)")
print("   Line 237: doppler_hz = (FREQ_MHZ * 1e6 / C) * (v_radial_tx + v_radial_rx)")
print("   → NO negative sign applied")

print("\n2. TELEMETRY SOLVER (lm_solver.py):")
print("   Line 58: v_radial_ioo = np.dot(target_vel, unit_ioo_target)")
print("   Line 59: v_radial_sensor = np.dot(target_vel, unit_target_sensor)")
print("   Line 63: doppler_ratio = -(v_radial_ioo + v_radial_sensor) / c")
print("   Line 64: calculated_doppler = freq_hz * doppler_ratio")
print("   → NEGATIVE sign applied!")

print("\n=== KEY DIFFERENCE ===")
print("The TelemetrySolver applies a negative sign to the Doppler calculation:")
print("Line 63: doppler_ratio = -(v_radial_ioo + v_radial_sensor) / c")
print("\nComment says: 'Negative sign because FDOA is frequency difference (direct - reflected)'")

print("\n=== SIGN CONVENTION ANALYSIS ===")

# Let's manually calculate both ways
print("\nManual calculation for Detection 1:")

# Our generator's method (no negative sign)
doppler_generated = calculate_doppler(sensor1, ioo1, target, velocity)
print(f"Generated Doppler (no neg): {doppler_generated:.5f} Hz")
print(f"Stored in file: {detections['detection1']['doppler_hz']:.5f} Hz")

# TelemetrySolver's method (with negative sign)
doppler_solver_convention = -doppler_generated
print(f"With TelemetrySolver neg sign: {doppler_solver_convention:.5f} Hz")

print(f"\n=== ROOT CAUSE ANALYSIS ===")
print("1. **Sign Convention Mismatch**:")
print("   - Generator: Uses standard Doppler formula")
print("   - Solver: Applies additional negative sign for 'FDOA' convention")

print("\n2. **FDOA vs Standard Doppler**:")
print("   - FDOA = Frequency Difference of Arrival")
print("   - Standard bistatic Doppler: f_received = f_transmitted * (1 + v_radial/c)")
print("   - FDOA convention may be: f_direct - f_reflected")

print("\n3. **Vector Direction Analysis**:")
print("   Both use same unit vector calculations:")
print("   - ioo_to_target: target_pos - ioo_pos (same)")
print("   - target_to_sensor: sensor_pos - target_pos (same)")
print("   - But solver adds negative sign to final result")

print("\n4. **Why Velocity Signs Flip**:")
print("   - If Doppler measurements have wrong sign convention")
print("   - Solver optimizes to match wrong-sign Doppler")
print("   - Resulting velocity has flipped signs to compensate")
print("   - Position can still be correct because geometry constraints dominate")

print("\n=== VERIFICATION NEEDED ===")
print("Check if removing the negative sign in TelemetrySolver fixes the issue:")
print("Line 63 in lm_solver.py should be:")
print("doppler_ratio = (v_radial_ioo + v_radial_sensor) / c  # Remove minus sign")

print("\n=== ALTERNATIVE THEORY ===")
print("The solver comment mentions 'direct - reflected' frequency difference.")
print("This suggests FDOA interpretation where:")
print("- Direct path: IoO → Sensor")
print("- Reflected path: IoO → Target → Sensor") 
print("- FDOA = f_direct - f_reflected")
print("But our generator creates standard bistatic Doppler, not FDOA!")

print("\n=== RECOMMENDATION ===")
print("Either:")
print("1. Remove negative sign from TelemetrySolver (if using standard Doppler)")
print("2. Or modify generator to produce FDOA measurements")
print("3. Or clarify which convention is intended for the system")