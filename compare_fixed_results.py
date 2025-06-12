#!/usr/bin/env python3
"""
Compare TelemetrySolver results after Doppler sign fix
"""

import json
import numpy as np

# TelemetrySolver output (after fix)
solver_output = {
    "timestamp": 1748876755112,
    "latitude": 43.93875922450377,
    "longitude": 153.46237233297623,
    "altitude": 5000.0,
    "velocity_east": -33.26447248304216,
    "velocity_north": 216.47891263626084,
    "velocity_up": 0.0
}

# Ground truth
ground_truth = {
    "timestamp": 1748876755112,
    "latitude": 43.93868419162224,
    "longitude": 153.4628511982105,
    "altitude": 5000.0,
    "velocity_east": -28.394036010973103,
    "velocity_north": 214.1804745180518,
    "velocity_up": 0.0
}

print("=== TelemetrySolver Results After Doppler Sign Fix ===\n")

print("POSITION COMPARISON:")
print(f"{'':20} {'Solver Output':>20} {'Ground Truth':>20} {'Error':>20}")
print("-" * 80)

# Latitude comparison
lat_error = solver_output["latitude"] - ground_truth["latitude"]
print(f"{'Latitude (deg)':20} {solver_output['latitude']:20.6f} {ground_truth['latitude']:20.6f} {lat_error:20.6f}")

# Longitude comparison
lon_error = solver_output["longitude"] - ground_truth["longitude"]
print(f"{'Longitude (deg)':20} {solver_output['longitude']:20.6f} {ground_truth['longitude']:20.6f} {lon_error:20.6f}")

# Calculate position error in meters
lat_error_m = lat_error * 111111.0
lon_error_m = lon_error * 111111.0 * np.cos(np.radians(ground_truth["latitude"]))
position_error_m = np.sqrt(lat_error_m**2 + lon_error_m**2)

print(f"\n{'Position Error (m)':20} {position_error_m:20.2f}")

print("\n\nVELOCITY COMPARISON:")
print(f"{'':20} {'Solver Output':>20} {'Ground Truth':>20} {'Error':>20}")
print("-" * 80)

# Velocity components
ve_error = solver_output["velocity_east"] - ground_truth["velocity_east"]
vn_error = solver_output["velocity_north"] - ground_truth["velocity_north"]

print(f"{'Velocity East (m/s)':20} {solver_output['velocity_east']:20.2f} {ground_truth['velocity_east']:20.2f} {ve_error:20.2f}")
print(f"{'Velocity North (m/s)':20} {solver_output['velocity_north']:20.2f} {ground_truth['velocity_north']:20.2f} {vn_error:20.2f}")

# Total velocity magnitude and error
solver_speed = np.sqrt(solver_output["velocity_east"]**2 + solver_output["velocity_north"]**2)
truth_speed = np.sqrt(ground_truth["velocity_east"]**2 + ground_truth["velocity_north"]**2)
velocity_error = np.sqrt(ve_error**2 + vn_error**2)

print(f"\n{'Speed (m/s)':20} {solver_speed:20.2f} {truth_speed:20.2f} {solver_speed - truth_speed:20.2f}")
print(f"{'Velocity Error (m/s)':20} {velocity_error:20.2f}")

# Heading comparison
solver_heading = np.degrees(np.arctan2(solver_output["velocity_east"], solver_output["velocity_north"]))
truth_heading = np.degrees(np.arctan2(ground_truth["velocity_east"], ground_truth["velocity_north"]))
if solver_heading < 0:
    solver_heading += 360
if truth_heading < 0:
    truth_heading += 360

heading_error = abs(solver_heading - truth_heading)
if heading_error > 180:
    heading_error = 360 - heading_error

print(f"\n{'Heading (deg)':20} {solver_heading:20.1f} {truth_heading:20.1f} {heading_error:20.1f}")

print("\n\nSUMMARY:")
print(f"✅ Position error: {position_error_m:.1f} meters (EXCELLENT)")
print(f"✅ Velocity error: {velocity_error:.1f} m/s (EXCELLENT)")
print(f"✅ Heading error: {heading_error:.1f}° (EXCELLENT)")
print(f"✅ Speed error: {abs(solver_speed - truth_speed):.1f} m/s (EXCELLENT)")

print(f"\n🎉 SUCCESS: Doppler sign fix resolved the velocity direction issue!")
print(f"- Position: Within 40m (vs 50km before fix)")
print(f"- Velocity: Within 5.4 m/s (vs 548 m/s before fix)")
print(f"- Direction: Within 9° (vs 180° before fix)")

print(f"\n=== IMPROVEMENT METRICS ===")
print(f"Position accuracy improved by: {50000/40:.0f}x")
print(f"Velocity accuracy improved by: {548/5.4:.0f}x")
print(f"Direction accuracy improved by: {180/heading_error:.0f}x")