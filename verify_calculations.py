"""
Verify the synthetic data calculations
"""
import json
import numpy as np
from generate_test_detections import (
    Position, Velocity, lla_to_ecef, 
    calculate_bistatic_range, calculate_doppler
)

# Load test case 1
with open("test_detections/test_case_1_input.json", 'r') as f:
    detections = json.load(f)
    
with open("test_detections/test_case_1_truth.json", 'r') as f:
    truth = json.load(f)

print("=== VERIFICATION OF TEST CASE 1 ===\n")

# Extract positions
sensor1 = Position(detections["detection1"]["sensor_lat"], 
                  detections["detection1"]["sensor_lon"], 0)
ioo1 = Position(detections["detection1"]["ioo_lat"],
               detections["detection1"]["ioo_lon"], 0)

sensor2 = Position(detections["detection2"]["sensor_lat"],
                  detections["detection2"]["sensor_lon"], 0) 
ioo2 = Position(detections["detection2"]["ioo_lat"],
               detections["detection2"]["ioo_lon"], 0)

target = Position(truth["latitude"], truth["longitude"], truth["altitude"])
velocity = Velocity(truth["velocity_east"], truth["velocity_north"], truth["velocity_up"])

print("POSITIONS:")
print(f"  Sensor 1: ({sensor1.lat:.4f}, {sensor1.lon:.4f})")
print(f"  IoO 1: ({ioo1.lat:.4f}, {ioo1.lon:.4f})")
print(f"  Sensor 2: ({sensor2.lat:.4f}, {sensor2.lon:.4f})")
print(f"  IoO 2: ({ioo2.lat:.4f}, {ioo2.lon:.4f})")
print(f"  Target: ({target.lat:.4f}, {target.lon:.4f}, {target.alt:.0f}m)")
print(f"  Velocity: ({velocity.east:.1f}, {velocity.north:.1f}) m/s")

# Recalculate bistatic ranges
print("\nBISTATIC RANGE CALCULATIONS:")
range1_calc = calculate_bistatic_range(sensor1, ioo1, target)
range2_calc = calculate_bistatic_range(sensor2, ioo2, target)

print(f"  Detection 1:")
print(f"    Stored: {detections['detection1']['bistatic_range_km']:.5f} km")
print(f"    Recalculated: {range1_calc:.5f} km")
print(f"    Difference: {abs(range1_calc - detections['detection1']['bistatic_range_km'])*1000:.2f} m")

print(f"  Detection 2:")
print(f"    Stored: {detections['detection2']['bistatic_range_km']:.5f} km")
print(f"    Recalculated: {range2_calc:.5f} km")
print(f"    Difference: {abs(range2_calc - detections['detection2']['bistatic_range_km'])*1000:.2f} m")

# Recalculate Doppler
print("\nDOPPLER CALCULATIONS:")
doppler1_calc = calculate_doppler(sensor1, ioo1, target, velocity)
doppler2_calc = calculate_doppler(sensor2, ioo2, target, velocity)

print(f"  Detection 1:")
print(f"    Stored: {detections['detection1']['doppler_hz']:.5f} Hz")
print(f"    Recalculated: {doppler1_calc:.5f} Hz")
print(f"    Difference: {abs(doppler1_calc - detections['detection1']['doppler_hz']):.5f} Hz")

print(f"  Detection 2:")
print(f"    Stored: {detections['detection2']['doppler_hz']:.5f} Hz")
print(f"    Recalculated: {doppler2_calc:.5f} Hz")
print(f"    Difference: {abs(doppler2_calc - detections['detection2']['doppler_hz']):.5f} Hz")

# Check individual distances for detection 1
print("\nDETAILED DISTANCE BREAKDOWN (Detection 1):")
sensor1_ecef = lla_to_ecef(sensor1.lat, sensor1.lon, sensor1.alt)
ioo1_ecef = lla_to_ecef(ioo1.lat, ioo1.lon, ioo1.alt)
target_ecef = lla_to_ecef(target.lat, target.lon, target.alt)

d_ioo_target = np.linalg.norm(target_ecef - ioo1_ecef)
d_target_sensor = np.linalg.norm(sensor1_ecef - target_ecef) 
d_ioo_sensor = np.linalg.norm(sensor1_ecef - ioo1_ecef)

print(f"  IoO to Target: {d_ioo_target/1000:.2f} km")
print(f"  Target to Sensor: {d_target_sensor/1000:.2f} km")
print(f"  IoO to Sensor (baseline): {d_ioo_sensor/1000:.2f} km")
print(f"  Bistatic delay: {(d_ioo_target + d_target_sensor - d_ioo_sensor)/1000:.2f} km")