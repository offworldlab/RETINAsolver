#!/usr/bin/env python3
"""
FIXED: Synthetic Test Detection Generator for 3-Detection TelemetrySolver
Fixes coordinate system mismatch in Doppler calculation
"""

import json
import numpy as np
import random
import os
import sys
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
from datetime import datetime


# Constants
WGS84_A = 6378137.0  # Semi-major axis in meters
WGS84_B = 6356752.314245  # Semi-minor axis in meters
WGS84_E2 = 1 - (WGS84_B**2 / WGS84_A**2)  # First eccentricity squared
C = 299792458.0  # Speed of light in m/s
FREQ_MHZ = 100.0  # Transmission frequency in MHz

# Constraints
MIN_BASELINE_ANGLE_DEG = 30.0
MAX_BASELINE_LENGTH_M = 30000.0
MIN_ALTITUDE_M = 0.0
MAX_ALTITUDE_M = 30000.0
MIN_VELOCITY = 50.0
MAX_VELOCITY = 500.0
MIN_VERTICAL_VELOCITY = -50.0
MAX_VERTICAL_VELOCITY = 50.0


@dataclass
class Position:
    """Represents a position in LLA coordinates"""
    lat: float
    lon: float
    alt: float


@dataclass
class Velocity:
    """Represents velocity in ENU coordinates"""
    east: float
    north: float
    up: float


def lla_to_ecef(lat: float, lon: float, alt: float) -> np.ndarray:
    """Convert latitude, longitude, altitude to ECEF coordinates."""
    lat_rad = np.radians(lat)
    lon_rad = np.radians(lon)
    
    N = WGS84_A / np.sqrt(1 - WGS84_E2 * np.sin(lat_rad)**2)
    
    x = (N + alt) * np.cos(lat_rad) * np.cos(lon_rad)
    y = (N + alt) * np.cos(lat_rad) * np.sin(lon_rad)
    z = (N * (1 - WGS84_E2) + alt) * np.sin(lat_rad)
    
    return np.array([x, y, z])


def enu_to_ecef_rotation_matrix(lat: float, lon: float) -> np.ndarray:
    """Get rotation matrix from ENU to ECEF at given location"""
    lat_rad = np.radians(lat)
    lon_rad = np.radians(lon)
    
    # Rotation matrix from ENU to ECEF
    R = np.array([
        [-np.sin(lon_rad), -np.sin(lat_rad)*np.cos(lon_rad), np.cos(lat_rad)*np.cos(lon_rad)],
        [ np.cos(lon_rad), -np.sin(lat_rad)*np.sin(lon_rad), np.cos(lat_rad)*np.sin(lon_rad)],
        [              0,                   np.cos(lat_rad),                 np.sin(lat_rad)]
    ])
    
    return R


def calculate_baseline_angle(sensor1: Position, ioo1: Position, 
                           sensor2: Position, ioo2: Position) -> float:
    """Calculate angle between two sensor-IoO baselines in degrees."""
    s1_ecef = lla_to_ecef(sensor1.lat, sensor1.lon, sensor1.alt)
    i1_ecef = lla_to_ecef(ioo1.lat, ioo1.lon, ioo1.alt)
    s2_ecef = lla_to_ecef(sensor2.lat, sensor2.lon, sensor2.alt)
    i2_ecef = lla_to_ecef(ioo2.lat, ioo2.lon, ioo2.alt)
    
    baseline1 = i1_ecef - s1_ecef
    baseline2 = i2_ecef - s2_ecef
    
    baseline1_norm = baseline1 / np.linalg.norm(baseline1)
    baseline2_norm = baseline2 / np.linalg.norm(baseline2)
    
    cos_angle = np.dot(baseline1_norm, baseline2_norm)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    angle_rad = np.arccos(cos_angle)
    angle_deg = np.degrees(angle_rad)
    
    return angle_deg


def calculate_baseline_length(sensor: Position, ioo: Position) -> float:
    """Calculate distance between sensor and IoO in meters."""
    s_ecef = lla_to_ecef(sensor.lat, sensor.lon, sensor.alt)
    i_ecef = lla_to_ecef(ioo.lat, ioo.lon, ioo.alt)
    return np.linalg.norm(i_ecef - s_ecef)


def validate_baselines(sensors: List[Position], ioos: List[Position], 
                      sensor_ioo_pairs: List[Tuple[int, int]]) -> Tuple[bool, str]:
    """Validate baseline constraints"""
    # Check baseline lengths
    for sensor_idx, ioo_idx in sensor_ioo_pairs:
        baseline_length = calculate_baseline_length(sensors[sensor_idx], ioos[ioo_idx])
        if baseline_length > MAX_BASELINE_LENGTH_M:
            return False, f"Baseline {sensor_idx}-{ioo_idx} too long: {baseline_length/1000:.1f}km"
    
    # Check baseline angles
    for i in range(len(sensor_ioo_pairs)):
        for j in range(i + 1, len(sensor_ioo_pairs)):
            s1_idx, i1_idx = sensor_ioo_pairs[i]
            s2_idx, i2_idx = sensor_ioo_pairs[j]
            
            angle = calculate_baseline_angle(
                sensors[s1_idx], ioos[i1_idx],
                sensors[s2_idx], ioos[i2_idx]
            )
            
            if angle < MIN_BASELINE_ANGLE_DEG:
                return False, f"Baseline angle {angle:.1f}° < {MIN_BASELINE_ANGLE_DEG}° minimum"
    
    return True, ""


def generate_random_position(center_lat: float, center_lon: float, 
                           max_range_m: float, min_range_m: float = None,
                           min_alt_m: float = 0, max_alt_m: float = 0) -> Position:
    """Generate a random position within range of center."""
    min_dist = min_range_m if min_range_m else 0.1 * max_range_m
    distance = random.uniform(min_dist, max_range_m)
    bearing = random.uniform(0, 2 * np.pi)
    
    lat_offset = (distance * np.cos(bearing)) / 111111.0
    lon_offset = (distance * np.sin(bearing)) / (111111.0 * np.cos(np.radians(center_lat)))
    
    alt = random.uniform(min_alt_m, max_alt_m)
    
    return Position(
        lat=center_lat + lat_offset,
        lon=center_lon + lon_offset,
        alt=alt
    )


def calculate_bistatic_range(sensor: Position, ioo: Position, target: Position) -> float:
    """Calculate bistatic range for a sensor-IoO-target configuration."""
    sensor_ecef = lla_to_ecef(sensor.lat, sensor.lon, sensor.alt)
    ioo_ecef = lla_to_ecef(ioo.lat, ioo.lon, ioo.alt)
    target_ecef = lla_to_ecef(target.lat, target.lon, target.alt)
    
    d_ioo_target = np.linalg.norm(target_ecef - ioo_ecef)
    d_target_sensor = np.linalg.norm(sensor_ecef - target_ecef)
    
    bistatic_range_m = d_ioo_target + d_target_sensor
    return bistatic_range_m / 1000.0  # Convert to km


def calculate_doppler(sensor: Position, ioo: Position, target: Position, velocity: Velocity) -> float:
    """
    FIXED: Calculate Doppler shift with proper coordinate transformation
    """
    # Convert to ECEF
    sensor_ecef = lla_to_ecef(sensor.lat, sensor.lon, sensor.alt)
    ioo_ecef = lla_to_ecef(ioo.lat, ioo.lon, ioo.alt)
    target_ecef = lla_to_ecef(target.lat, target.lon, target.alt)
    
    # Unit vectors in ECEF
    ioo_to_target = (target_ecef - ioo_ecef) / np.linalg.norm(target_ecef - ioo_ecef)
    target_to_sensor = (sensor_ecef - target_ecef) / np.linalg.norm(sensor_ecef - target_ecef)
    
    # Convert velocity from ENU to ECEF
    # Get rotation matrix at target location
    R = enu_to_ecef_rotation_matrix(target.lat, target.lon)
    velocity_enu = np.array([velocity.east, velocity.north, velocity.up])
    velocity_ecef = R @ velocity_enu
    
    # Radial velocities in consistent ECEF coordinates
    v_radial_tx = np.dot(velocity_ecef, ioo_to_target)
    v_radial_rx = np.dot(velocity_ecef, target_to_sensor)
    
    # Doppler with adsb2dd sign convention
    doppler_hz = -(FREQ_MHZ * 1e6 / C) * (v_radial_tx + v_radial_rx)
    
    return doppler_hz


def generate_sensor_ioo_configuration(center_lat: float, center_lon: float) -> Tuple[List[Position], List[Position], List[Tuple[int, int]]]:
    """Generate 3 sensors and IoOs with valid baseline constraints."""
    max_attempts = 1000
    
    for attempt in range(max_attempts):
        # Generate 3 sensors close together (2-8 km apart)
        sensors = []
        for i in range(3):
            sensor = generate_random_position(center_lat, center_lon, 8000, 2000)
            sensors.append(sensor)
        
        # Generate 2 IoOs (mixed configuration)
        ioos = []
        for i in range(2):
            ioo = generate_random_position(center_lat, center_lon, 15000, 5000)
            ioos.append(ioo)
        
        # Try different pairing configurations
        configurations = [
            [(0, 0), (1, 0), (2, 1)],  # Sensors 0,1 use IoO 0; Sensor 2 uses IoO 1
            [(0, 0), (1, 1), (2, 1)],  # Sensor 0 uses IoO 0; Sensors 1,2 use IoO 1
            [(0, 1), (1, 0), (2, 1)],  # Mixed configuration
        ]
        
        for config in configurations:
            valid, error = validate_baselines(sensors, ioos, config)
            if valid:
                return sensors, ioos, config
    
    raise ValueError(f"Could not generate valid sensor-IoO configuration after {max_attempts} attempts")


def generate_test_case(case_number: int, output_dir: str = ".") -> Dict:
    """Generate a complete 3-detection test case."""
    # Random center point
    center_lat = random.uniform(-60, 60)
    center_lon = random.uniform(-180, 180)
    
    # Generate valid sensor-IoO configuration
    sensors, ioos, sensor_ioo_pairs = generate_sensor_ioo_configuration(center_lat, center_lon)
    
    # Calculate longest baseline for target constraint
    baseline_lengths = []
    for sensor_idx, ioo_idx in sensor_ioo_pairs:
        length = calculate_baseline_length(sensors[sensor_idx], ioos[ioo_idx])
        baseline_lengths.append(length)
    max_baseline = max(baseline_lengths)
    
    # Generate target within 2x longest baseline
    max_target_range = 2 * max_baseline
    target = generate_random_position(
        center_lat, center_lon, 
        max_target_range, max_target_range * 0.3,
        MIN_ALTITUDE_M, MAX_ALTITUDE_M
    )
    
    # Generate velocity with vertical component
    horizontal_speed = random.uniform(MIN_VELOCITY, MAX_VELOCITY)
    heading = random.uniform(0, 2 * np.pi)
    vertical_velocity = random.uniform(MIN_VERTICAL_VELOCITY, MAX_VERTICAL_VELOCITY)
    
    velocity = Velocity(
        east=horizontal_speed * np.sin(heading),
        north=horizontal_speed * np.cos(heading),
        up=vertical_velocity
    )
    
    # Calculate detections
    timestamp = int(datetime.now().timestamp() * 1000)
    
    detections = {}
    for i, (sensor_idx, ioo_idx) in enumerate(sensor_ioo_pairs):
        sensor = sensors[sensor_idx]
        ioo = ioos[ioo_idx]
        
        bistatic_range = calculate_bistatic_range(sensor, ioo, target)
        doppler = calculate_doppler(sensor, ioo, target, velocity)
        
        detections[f"detection{i+1}"] = {
            "sensor_lat": sensor.lat,
            "sensor_lon": sensor.lon,
            "ioo_lat": ioo.lat,
            "ioo_lon": ioo.lon,
            "freq_mhz": FREQ_MHZ,
            "timestamp": timestamp,
            "bistatic_range_km": round(bistatic_range, 5),
            "doppler_hz": round(doppler, 5)
        }
    
    # Ground truth
    ground_truth = {
        "timestamp": timestamp,
        "latitude": target.lat,
        "longitude": target.lon,
        "altitude": target.alt,
        "velocity_east": velocity.east,
        "velocity_north": velocity.north,
        "velocity_up": velocity.up
    }
    
    # Save files
    input_file = os.path.join(output_dir, f"3det_case_{case_number}_input.json")
    truth_file = os.path.join(output_dir, f"3det_case_{case_number}_truth.json")
    
    with open(input_file, 'w') as f:
        json.dump(detections, f, indent=2)
    
    with open(truth_file, 'w') as f:
        json.dump(ground_truth, f, indent=2)
    
    return {
        "case_number": case_number,
        "input_file": input_file,
        "truth_file": truth_file,
        "center_lat": center_lat,
        "center_lon": center_lon,
        "sensors": [(s.lat, s.lon) for s in sensors],
        "ioos": [(i.lat, i.lon) for i in ioos],
        "sensor_ioo_pairs": sensor_ioo_pairs,
        "baseline_lengths_km": [l/1000 for l in baseline_lengths],
        "max_baseline_km": max_baseline/1000,
        "target": {"lat": target.lat, "lon": target.lon, "alt": target.alt},
        "velocity": {
            "east": velocity.east, 
            "north": velocity.north, 
            "up": velocity.up,
            "horizontal_speed": horizontal_speed
        }
    }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate 3-detection test cases with FIXED Doppler calculation')
    parser.add_argument('--num-cases', type=int, default=5, help='Number of test cases')
    parser.add_argument('--output-dir', default='test_3detections_fixed', help='Output directory')
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    print(f"Generating {args.num_cases} test cases with FIXED Doppler calculation...\n")
    
    all_cases = []
    
    for i in range(1, args.num_cases + 1):
        try:
            print(f"Generating test case {i}...")
            case_summary = generate_test_case(i, args.output_dir)
            all_cases.append(case_summary)
            
            print(f"  ✓ Generated successfully")
            print(f"    Center: ({case_summary['center_lat']:.4f}, {case_summary['center_lon']:.4f})")
            print(f"    Target altitude: {case_summary['target']['alt']:.0f} m")
            print(f"    Horizontal speed: {case_summary['velocity']['horizontal_speed']:.1f} m/s")
            print(f"    Vertical velocity: {case_summary['velocity']['up']:.1f} m/s")
            print(f"    Max baseline: {case_summary['max_baseline_km']:.1f} km")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    # Save summary
    summary = {
        "num_cases": len(all_cases),
        "cases": all_cases,
        "doppler_calculation": "FIXED - proper ENU to ECEF transformation"
    }
    
    summary_file = os.path.join(args.output_dir, "test_summary.json")
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Summary: Generated {len(all_cases)} test cases with FIXED Doppler")
    print(f"Output directory: {args.output_dir}")
    print(f"Summary file: {summary_file}")


if __name__ == "__main__":
    main()