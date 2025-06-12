#!/usr/bin/env python3
"""
Compare TelemetrySolver output with ground truth
"""

import json
import numpy as np

# TelemetrySolver output
solver_output = {
    "timestamp": 1748874773403,
    "latitude": 27.168539631168855,
    "longitude": 29.265995656183478,
    "altitude": 5000.0,
    "velocity_east": -238.62080418251512,
    "velocity_north": -141.42510026333287,
    "velocity_up": 0.0
}

# Ground truth
ground_truth = {
    "timestamp": 1748874773403,
    "latitude": 27.168764702913624,
    "longitude": 29.266614226894617,
    "altitude": 5000.0,
    "velocity_east": 225.71381410929274,
    "velocity_north": 149.9443211757126,
    "velocity_up": 0.0
}

print("=== TelemetrySolver Test Case 1 Comparison ===\n")

print("POSITION COMPARISON:")
print(f"{'':20} {'Solver Output':>20} {'Ground Truth':>20} {'Error':>20}")
print("-" * 80)

# Latitude comparison
lat_error = solver_output["latitude"] - ground_truth["latitude"]
print(f"{'Latitude (deg)':20} {solver_output['latitude']:20.6f} {ground_truth['latitude']:20.6f} {lat_error:20.6f}")

# Longitude comparison - handle wraparound
solver_lon = solver_output["longitude"]
truth_lon = ground_truth["longitude"]
# Normalize solver longitude to [-180, 180]
if solver_lon > 180:
    solver_lon = solver_lon - 360
lon_error = solver_lon - truth_lon
print(f"{'Longitude (deg)':20} {solver_lon:20.6f} {truth_lon:20.6f} {lon_error:20.6f}")

# Calculate position error in meters
lat_error_m = lat_error * 111111.0  # Approximate meters per degree latitude
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

# Total velocity magnitude
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

print(f"\n{'Heading (deg)':20} {solver_heading:20.1f} {truth_heading:20.1f} {solver_heading - truth_heading:20.1f}")

print("\n\nSUMMARY:")
print(f"- Position error: {position_error_m:.0f} meters ({position_error_m/1000:.1f} km)")
print(f"- Velocity error: {velocity_error:.0f} m/s")
print(f"- Solver converged: {'No' if position_error_m > 100 else 'Yes'}")

# Show on map
print(f"\n\nGEOGRAPHIC CONTEXT:")
print(f"- Test location: Northern Atlantic (near Iceland)")
print(f"- Solver placed target {position_error_m/1000:.1f} km away from true position")
print(f"- Solver velocity is {solver_speed:.0f} m/s vs truth {truth_speed:.0f} m/s")
print(f"- This represents a {(solver_speed/truth_speed - 1)*100:.0f}% velocity magnitude error")