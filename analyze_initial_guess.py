#!/usr/bin/env python3
"""
Analyze the initial guess used by TelemetrySolver and how far it is from ground truth
"""

import sys
sys.path.append('/Users/jehanazad/offworldlab/TelemetrySolver')

import json
import numpy as np
from detection import load_detections
from initial_guess import get_initial_guess
from Geometry import Geometry

def analyze_initial_guess(test_case_file):
    """Analyze initial guess vs ground truth for a test case"""
    
    print(f"=== INITIAL GUESS ANALYSIS ===\n")
    print(f"Test case: {test_case_file}")
    
    # Load detection data
    detection_pair = load_detections(test_case_file)
    
    # Load ground truth
    truth_file = test_case_file.replace('_input.json', '_truth.json')
    with open(truth_file, 'r') as f:
        truth = json.load(f)
    
    # Get ENU origin (midpoint of sensors)
    origin_lat, origin_lon, origin_alt = detection_pair.get_enu_origin()
    print(f"ENU Origin: ({origin_lat:.6f}, {origin_lon:.6f}, {origin_alt:.1f})")
    
    # Convert ground truth to ENU
    truth_ecef = Geometry.lla2ecef(truth["latitude"], truth["longitude"], truth["altitude"])
    truth_enu = Geometry.ecef2enu(truth_ecef[0], truth_ecef[1], truth_ecef[2],
                                  origin_lat, origin_lon, origin_alt)
    
    truth_state = [truth_enu[0], truth_enu[1], truth["velocity_east"], truth["velocity_north"]]
    
    # Get initial guess
    initial_guess = get_initial_guess(detection_pair)
    
    print(f"\nSENSOR POSITIONS:")
    print(f"  Sensor 1: ({detection_pair.detection1.sensor_lat:.6f}, {detection_pair.detection1.sensor_lon:.6f})")
    print(f"  Sensor 2: ({detection_pair.detection2.sensor_lat:.6f}, {detection_pair.detection2.sensor_lon:.6f})")
    
    print(f"\nIOO POSITIONS:")
    print(f"  IoO 1: ({detection_pair.detection1.ioo_lat:.6f}, {detection_pair.detection1.ioo_lon:.6f})")
    print(f"  IoO 2: ({detection_pair.detection2.ioo_lat:.6f}, {detection_pair.detection2.ioo_lon:.6f})")
    
    print(f"\nINITIAL GUESS ALGORITHM:")
    print(f"1. Calculate ellipse centers (midpoint between IoO and Sensor for each detection)")
    print(f"2. Average the two ellipse centers")
    print(f"3. Set initial velocity to zero")
    
    # Let's manually trace through the algorithm
    print(f"\nSTEP-BY-STEP CALCULATION:")
    
    # Convert positions to ENU for detailed analysis
    sensor1_ecef = Geometry.lla2ecef(detection_pair.detection1.sensor_lat, 
                                     detection_pair.detection1.sensor_lon, 0)
    ioo1_ecef = Geometry.lla2ecef(detection_pair.detection1.ioo_lat,
                                  detection_pair.detection1.ioo_lon, 0)
    
    sensor1_enu = Geometry.ecef2enu(sensor1_ecef[0], sensor1_ecef[1], sensor1_ecef[2],
                                   origin_lat, origin_lon, origin_alt)
    ioo1_enu = Geometry.ecef2enu(ioo1_ecef[0], ioo1_ecef[1], ioo1_ecef[2],
                                 origin_lat, origin_lon, origin_alt)
    
    sensor2_ecef = Geometry.lla2ecef(detection_pair.detection2.sensor_lat,
                                     detection_pair.detection2.sensor_lon, 0)
    ioo2_ecef = Geometry.lla2ecef(detection_pair.detection2.ioo_lat,
                                  detection_pair.detection2.ioo_lon, 0)
    
    sensor2_enu = Geometry.ecef2enu(sensor2_ecef[0], sensor2_ecef[1], sensor2_ecef[2],
                                   origin_lat, origin_lon, origin_alt)
    ioo2_enu = Geometry.ecef2enu(ioo2_ecef[0], ioo2_ecef[1], ioo2_ecef[2],
                                 origin_lat, origin_lon, origin_alt)
    
    # Calculate ellipse centers
    center1_x = (ioo1_enu[0] + sensor1_enu[0]) / 2
    center1_y = (ioo1_enu[1] + sensor1_enu[1]) / 2
    center2_x = (ioo2_enu[0] + sensor2_enu[0]) / 2
    center2_y = (ioo2_enu[1] + sensor2_enu[1]) / 2
    
    print(f"  Detection 1 ellipse center: ({center1_x:.1f}, {center1_y:.1f}) ENU")
    print(f"  Detection 2 ellipse center: ({center2_x:.1f}, {center2_y:.1f}) ENU")
    
    avg_x = (center1_x + center2_x) / 2
    avg_y = (center1_y + center2_y) / 2
    
    print(f"  Average center (initial guess): ({avg_x:.1f}, {avg_y:.1f}) ENU")
    
    print(f"\nRESULTS:")
    print(f"{'':20} {'Initial Guess':>15} {'Ground Truth':>15} {'Error':>15}")
    print("-" * 70)
    print(f"{'Position X (m)':20} {initial_guess[0]:15.1f} {truth_state[0]:15.1f} {initial_guess[0] - truth_state[0]:15.1f}")
    print(f"{'Position Y (m)':20} {initial_guess[1]:15.1f} {truth_state[1]:15.1f} {initial_guess[1] - truth_state[1]:15.1f}")
    print(f"{'Velocity X (m/s)':20} {initial_guess[2]:15.1f} {truth_state[2]:15.1f} {initial_guess[2] - truth_state[2]:15.1f}")
    print(f"{'Velocity Y (m/s)':20} {initial_guess[3]:15.1f} {truth_state[3]:15.1f} {initial_guess[3] - truth_state[3]:15.1f}")
    
    # Calculate distance errors
    position_error = np.sqrt((initial_guess[0] - truth_state[0])**2 + 
                            (initial_guess[1] - truth_state[1])**2)
    velocity_error = np.sqrt((initial_guess[2] - truth_state[2])**2 + 
                            (initial_guess[3] - truth_state[3])**2)
    
    print(f"\n{'Position Error (m)':20} {position_error:15.1f}")
    print(f"{'Velocity Error (m/s)':20} {velocity_error:15.1f}")
    
    print(f"\nASSESSMENT:")
    if position_error < 1000:
        print(f"✅ Position: Excellent initial guess ({position_error:.0f}m from truth)")
    elif position_error < 5000:
        print(f"⚠️  Position: Good initial guess ({position_error:.0f}m from truth)")
    elif position_error < 20000:
        print(f"⚠️  Position: Fair initial guess ({position_error:.0f}m from truth)")
    else:
        print(f"❌ Position: Poor initial guess ({position_error:.0f}m from truth)")
    
    if velocity_error < 50:
        print(f"✅ Velocity: Excellent initial guess ({velocity_error:.0f} m/s from truth)")
    elif velocity_error < 200:
        print(f"⚠️  Velocity: Good initial guess ({velocity_error:.0f} m/s from truth)")
    else:
        print(f"❌ Velocity: Poor initial guess ({velocity_error:.0f} m/s from truth)")
    
    print(f"\nINITIAL GUESS ALGORITHM EVALUATION:")
    print(f"The algorithm assumes target is at the average of ellipse centers.")
    print(f"This is geometrically reasonable but doesn't use the range/Doppler measurements.")
    print(f"- Ellipse centers are midpoints between IoO-Sensor pairs")
    print(f"- This gives a rough position estimate within the sensor network")
    print(f"- Zero velocity assumption is conservative")
    
    # Check how far sensors/IoOs are from the target
    target_to_sensor1 = np.sqrt((truth_enu[0] - sensor1_enu[0])**2 + (truth_enu[1] - sensor1_enu[1])**2)
    target_to_sensor2 = np.sqrt((truth_enu[0] - sensor2_enu[0])**2 + (truth_enu[1] - sensor2_enu[1])**2)
    target_to_ioo1 = np.sqrt((truth_enu[0] - ioo1_enu[0])**2 + (truth_enu[1] - ioo1_enu[1])**2)
    target_to_ioo2 = np.sqrt((truth_enu[0] - ioo2_enu[0])**2 + (truth_enu[1] - ioo2_enu[1])**2)
    
    print(f"\nGEOMETRY CONTEXT:")
    print(f"  Target to Sensor 1: {target_to_sensor1/1000:.1f} km")
    print(f"  Target to Sensor 2: {target_to_sensor2/1000:.1f} km")
    print(f"  Target to IoO 1: {target_to_ioo1/1000:.1f} km")
    print(f"  Target to IoO 2: {target_to_ioo2/1000:.1f} km")
    
    return position_error, velocity_error

if __name__ == "__main__":
    # Analyze the successful test case
    test_case = "/Users/jehanazad/offworldlab/test_detections/test_case_10_input.json"
    analyze_initial_guess(test_case)