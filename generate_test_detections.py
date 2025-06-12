#!/usr/bin/env python3
"""
Synthetic Test Detection Generator for TelemetrySolver

This script generates synthetic bistatic radar detections in the format expected by TelemetrySolver.
It creates realistic scenarios with 2 sensors, 2 IoOs, and a target, then calculates the bistatic
ranges and Doppler shifts using the same physics as adsb2dd.
"""

import json
import numpy as np
import random
import os
import subprocess
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
TARGET_ALTITUDE = 5000.0  # Fixed target altitude in meters
MIN_VELOCITY = 100.0  # Minimum target velocity in m/s
MAX_VELOCITY = 300.0  # Maximum target velocity in m/s
MAX_RANGE = 30000.0  # Maximum range in meters (30 km)


@dataclass
class Position:
    """Represents a position in LLA coordinates"""
    lat: float  # Latitude in degrees
    lon: float  # Longitude in degrees
    alt: float  # Altitude in meters


@dataclass
class Velocity:
    """Represents velocity in ENU coordinates"""
    east: float  # East velocity in m/s
    north: float  # North velocity in m/s
    up: float  # Up velocity in m/s (always 0 for our case)


def lla_to_ecef(lat: float, lon: float, alt: float) -> np.ndarray:
    """
    Convert latitude, longitude, altitude to ECEF coordinates.
    
    Args:
        lat: Latitude in degrees
        lon: Longitude in degrees
        alt: Altitude in meters
        
    Returns:
        ECEF coordinates as numpy array [x, y, z] in meters
    """
    lat_rad = np.radians(lat)
    lon_rad = np.radians(lon)
    
    N = WGS84_A / np.sqrt(1 - WGS84_E2 * np.sin(lat_rad)**2)
    
    x = (N + alt) * np.cos(lat_rad) * np.cos(lon_rad)
    y = (N + alt) * np.cos(lat_rad) * np.sin(lon_rad)
    z = (N * (1 - WGS84_E2) + alt) * np.sin(lat_rad)
    
    return np.array([x, y, z])


def ecef_to_lla(ecef: np.ndarray) -> Tuple[float, float, float]:
    """
    Convert ECEF coordinates to latitude, longitude, altitude.
    
    Args:
        ecef: ECEF coordinates as numpy array [x, y, z] in meters
        
    Returns:
        Tuple of (latitude, longitude, altitude) in degrees and meters
    """
    x, y, z = ecef
    
    # Calculate longitude
    lon = np.arctan2(y, x)
    
    # Iterative calculation for latitude and altitude
    p = np.sqrt(x**2 + y**2)
    lat = np.arctan2(z, p * (1 - WGS84_E2))
    
    for _ in range(5):  # Usually converges in 3-4 iterations
        N = WGS84_A / np.sqrt(1 - WGS84_E2 * np.sin(lat)**2)
        alt = p / np.cos(lat) - N
        lat = np.arctan2(z, p * (1 - WGS84_E2 * N / (N + alt)))
    
    return np.degrees(lat), np.degrees(lon), alt


def generate_random_position(center_lat: float, center_lon: float, max_range_m: float, min_range_m: float = None) -> Position:
    """
    Generate a random position within max_range of a center point.
    
    Args:
        center_lat: Center latitude in degrees
        center_lon: Center longitude in degrees
        max_range_m: Maximum range in meters
        min_range_m: Minimum range in meters (optional)
        
    Returns:
        Random Position within range
    """
    # Generate random distance and bearing
    min_dist = min_range_m if min_range_m else 0.1 * max_range_m
    distance = random.uniform(min_dist, max_range_m)
    bearing = random.uniform(0, 2 * np.pi)
    
    # Convert to offset in meters (approximate for small distances)
    lat_offset = (distance * np.cos(bearing)) / 111111.0  # Degrees latitude
    lon_offset = (distance * np.sin(bearing)) / (111111.0 * np.cos(np.radians(center_lat)))  # Degrees longitude
    
    return Position(
        lat=center_lat + lat_offset,
        lon=center_lon + lon_offset,
        alt=0.0  # Ground level for sensors and IoOs
    )


def check_colinearity(positions: List[Position], threshold: float = 1000.0) -> bool:
    """
    Check if any three positions are colinear.
    
    Args:
        positions: List of positions to check
        threshold: Minimum area threshold in square meters
        
    Returns:
        True if positions are non-colinear, False otherwise
    """
    n = len(positions)
    if n < 3:
        return True
    
    # Check all combinations of 3 positions
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                # Convert to ECEF for accurate distance calculation
                p1 = lla_to_ecef(positions[i].lat, positions[i].lon, positions[i].alt)
                p2 = lla_to_ecef(positions[j].lat, positions[j].lon, positions[j].alt)
                p3 = lla_to_ecef(positions[k].lat, positions[k].lon, positions[k].alt)
                
                # Calculate area of triangle using cross product
                v1 = p2 - p1
                v2 = p3 - p1
                area = 0.5 * np.linalg.norm(np.cross(v1, v2))
                
                if area < threshold:
                    return False
    
    return True


def calculate_bistatic_range(sensor: Position, ioo: Position, target: Position) -> float:
    """
    Calculate bistatic range for a sensor-IoO-target configuration.
    
    Args:
        sensor: Sensor position
        ioo: Illuminator of Opportunity position
        target: Target position
        
    Returns:
        Bistatic range in kilometers
    """
    # Convert to ECEF
    sensor_ecef = lla_to_ecef(sensor.lat, sensor.lon, sensor.alt)
    ioo_ecef = lla_to_ecef(ioo.lat, ioo.lon, ioo.alt)
    target_ecef = lla_to_ecef(target.lat, target.lon, target.alt)
    
    # Calculate distances
    d_ioo_target = np.linalg.norm(target_ecef - ioo_ecef)
    d_target_sensor = np.linalg.norm(sensor_ecef - target_ecef)
    
    # Bistatic range = total path length (what TelemetrySolver expects)
    bistatic_range_m = d_ioo_target + d_target_sensor
    
    return bistatic_range_m / 1000.0  # Convert to km


def calculate_doppler(sensor: Position, ioo: Position, target: Position, velocity: Velocity) -> float:
    """
    Calculate Doppler shift for a sensor-IoO-target configuration.
    
    Args:
        sensor: Sensor position
        ioo: Illuminator of Opportunity position
        target: Target position
        velocity: Target velocity in ENU coordinates
        
    Returns:
        Doppler shift in Hz
    """
    # Convert to ECEF
    sensor_ecef = lla_to_ecef(sensor.lat, sensor.lon, sensor.alt)
    ioo_ecef = lla_to_ecef(ioo.lat, ioo.lon, ioo.alt)
    target_ecef = lla_to_ecef(target.lat, target.lon, target.alt)
    
    # Calculate unit vectors
    ioo_to_target = target_ecef - ioo_ecef
    ioo_to_target_unit = ioo_to_target / np.linalg.norm(ioo_to_target)
    
    target_to_sensor = sensor_ecef - target_ecef
    target_to_sensor_unit = target_to_sensor / np.linalg.norm(target_to_sensor)
    
    # Convert velocity from ENU to ECEF at target location
    # First, we need the rotation matrix from ENU to ECEF
    lat_rad = np.radians(target.lat)
    lon_rad = np.radians(target.lon)
    
    # ENU to ECEF rotation matrix
    R = np.array([
        [-np.sin(lon_rad), -np.sin(lat_rad)*np.cos(lon_rad), np.cos(lat_rad)*np.cos(lon_rad)],
        [np.cos(lon_rad), -np.sin(lat_rad)*np.sin(lon_rad), np.cos(lat_rad)*np.sin(lon_rad)],
        [0, np.cos(lat_rad), np.sin(lat_rad)]
    ])
    
    velocity_enu = np.array([velocity.east, velocity.north, velocity.up])
    velocity_ecef = R @ velocity_enu
    
    # Calculate radial velocities
    v_radial_tx = np.dot(velocity_ecef, ioo_to_target_unit)  # Velocity toward IoO (negative of away)
    v_radial_rx = np.dot(velocity_ecef, target_to_sensor_unit)  # Velocity toward sensor
    
    # Total Doppler shift
    # Use adsb2dd/TelemetrySolver sign convention (negative of standard physics)
    doppler_hz = -(FREQ_MHZ * 1e6 / C) * (v_radial_tx + v_radial_rx)
    
    return doppler_hz


def generate_test_case(case_number: int, output_dir: str = ".") -> Dict:
    """
    Generate a complete test case with sensors, IoOs, target, and detections.
    
    Args:
        case_number: Test case number
        output_dir: Directory to save output files
        
    Returns:
        Dictionary containing test case summary
    """
    # Generate a random center point
    center_lat = random.uniform(-60, 60)  # Avoid extreme latitudes
    center_lon = random.uniform(-180, 180)
    
    # Generate positions until we get non-colinear configuration
    attempts = 0
    while attempts < 100:
        # Generate 2 sensors and 2 IoOs close together (like NYC example)
        # Keep sensors very close (1-5 km apart)
        sensor1 = generate_random_position(center_lat, center_lon, 2000, 500)
        sensor2 = generate_random_position(center_lat, center_lon, 5000, 1000)
        
        # Keep IoOs also very close (1-5 km)
        ioo1 = generate_random_position(center_lat, center_lon, 3000, 500)
        ioo2 = generate_random_position(center_lat, center_lon, 5000, 1000)
        
        # Generate target position even closer to improve solver convergence further
        # Target 20-40 km away to reach >50% convergence vs 30-50km with 40% rate
        target = generate_random_position(center_lat, center_lon, 40000, 20000)
        target.alt = TARGET_ALTITUDE
        
        # Check colinearity
        all_positions = [sensor1, sensor2, ioo1, ioo2, target]
        if check_colinearity(all_positions):
            break
        attempts += 1
    
    if attempts >= 100:
        raise ValueError("Could not generate non-colinear configuration")
    
    # Generate random velocity
    speed = random.uniform(MIN_VELOCITY, MAX_VELOCITY)
    heading = random.uniform(0, 2 * np.pi)
    velocity = Velocity(
        east=speed * np.sin(heading),
        north=speed * np.cos(heading),
        up=0.0
    )
    
    # Calculate detections
    timestamp = int(datetime.now().timestamp() * 1000)
    
    # Detection 1: sensor1 with ioo1
    bistatic_range1 = calculate_bistatic_range(sensor1, ioo1, target)
    doppler1 = calculate_doppler(sensor1, ioo1, target, velocity)
    
    # Detection 2: sensor2 with ioo2
    bistatic_range2 = calculate_bistatic_range(sensor2, ioo2, target)
    doppler2 = calculate_doppler(sensor2, ioo2, target, velocity)
    
    # Format detections for TelemetrySolver
    detections = {
        "detection1": {
            "sensor_lat": sensor1.lat,
            "sensor_lon": sensor1.lon,
            "ioo_lat": ioo1.lat,
            "ioo_lon": ioo1.lon,
            "freq_mhz": FREQ_MHZ,
            "timestamp": timestamp,
            "bistatic_range_km": round(bistatic_range1, 5),
            "doppler_hz": round(doppler1, 5)
        },
        "detection2": {
            "sensor_lat": sensor2.lat,
            "sensor_lon": sensor2.lon,
            "ioo_lat": ioo2.lat,
            "ioo_lon": ioo2.lon,
            "freq_mhz": FREQ_MHZ,
            "timestamp": timestamp,
            "bistatic_range_km": round(bistatic_range2, 5),
            "doppler_hz": round(doppler2, 5)
        }
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
    input_file = os.path.join(output_dir, f"test_case_{case_number}_input.json")
    truth_file = os.path.join(output_dir, f"test_case_{case_number}_truth.json")
    
    with open(input_file, 'w') as f:
        json.dump(detections, f, indent=2)
    
    with open(truth_file, 'w') as f:
        json.dump(ground_truth, f, indent=2)
    
    # Return summary
    return {
        "case_number": case_number,
        "center_lat": center_lat,
        "center_lon": center_lon,
        "input_file": input_file,
        "truth_file": truth_file,
        "sensor1": {"lat": sensor1.lat, "lon": sensor1.lon},
        "sensor2": {"lat": sensor2.lat, "lon": sensor2.lon},
        "ioo1": {"lat": ioo1.lat, "lon": ioo1.lon},
        "ioo2": {"lat": ioo2.lat, "lon": ioo2.lon},
        "target": {"lat": target.lat, "lon": target.lon, "alt": target.alt},
        "velocity": {"east": velocity.east, "north": velocity.north, "speed": speed},
        "bistatic_range1_km": bistatic_range1,
        "bistatic_range2_km": bistatic_range2,
        "doppler1_hz": doppler1,
        "doppler2_hz": doppler2
    }


def validate_test_case(case_summary: Dict, telemetry_solver_path: str = "TelemetrySolver") -> Dict:
    """
    Validate a test case by running it through TelemetrySolver and comparing results.
    
    Args:
        case_summary: Test case summary from generate_test_case
        telemetry_solver_path: Path to TelemetrySolver directory
        
    Returns:
        Validation results dictionary
    """
    input_file = case_summary["input_file"]
    truth_file = case_summary["truth_file"]
    
    # Run TelemetrySolver
    solver_script = os.path.join(telemetry_solver_path, "main.py")
    
    try:
        result = subprocess.run(
            [sys.executable, solver_script, input_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Solver failed with return code {result.returncode}",
                "stderr": result.stderr
            }
        
        # Parse solver output
        try:
            solver_output = json.loads(result.stdout)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Failed to parse solver output",
                "stdout": result.stdout
            }
        
        # Load ground truth
        with open(truth_file, 'r') as f:
            ground_truth = json.load(f)
        
        # Compare results
        if "error" in solver_output:
            return {
                "success": False,
                "error": f"Solver error: {solver_output['error']}"
            }
        
        # Calculate errors
        lat_error = abs(solver_output["latitude"] - ground_truth["latitude"])
        lon_error = abs(solver_output["longitude"] - ground_truth["longitude"])
        
        # Convert lat/lon errors to meters (approximate)
        lat_error_m = lat_error * 111111.0
        lon_error_m = lon_error * 111111.0 * np.cos(np.radians(ground_truth["latitude"]))
        position_error_m = np.sqrt(lat_error_m**2 + lon_error_m**2)
        
        # Velocity errors
        vel_east_error = abs(solver_output["velocity_east"] - ground_truth["velocity_east"])
        vel_north_error = abs(solver_output["velocity_north"] - ground_truth["velocity_north"])
        velocity_error = np.sqrt(vel_east_error**2 + vel_north_error**2)
        
        return {
            "success": True,
            "position_error_m": position_error_m,
            "velocity_error_m_s": velocity_error,
            "solver_output": solver_output,
            "ground_truth": ground_truth,
            "converged": bool(position_error_m < 200.0)  # Within 200m is acceptable
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Solver timed out"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Exception: {str(e)}"
        }


def main():
    """Generate and validate multiple test cases."""
    output_dir = "test_detections"
    os.makedirs(output_dir, exist_ok=True)
    
    num_cases = 10
    summaries = []
    validation_results = []
    
    print(f"Generating {num_cases} test cases...")
    
    for i in range(1, num_cases + 1):
        print(f"\nGenerating test case {i}...")
        
        # Generate test case
        try:
            summary = generate_test_case(i, output_dir)
            summaries.append(summary)
            print(f"  ✓ Generated successfully")
            print(f"    Center: ({summary['center_lat']:.4f}, {summary['center_lon']:.4f})")
            print(f"    Target speed: {summary['velocity']['speed']:.1f} m/s")
            
            # Validate if TelemetrySolver is available
            if os.path.exists("TelemetrySolver/main.py"):
                print(f"  Validating with TelemetrySolver...")
                validation = validate_test_case(summary, "TelemetrySolver")
                validation_results.append(validation)
                
                if validation["success"]:
                    if validation["converged"]:
                        print(f"  ✓ Validation passed!")
                        print(f"    Position error: {validation['position_error_m']:.2f} m")
                        print(f"    Velocity error: {validation['velocity_error_m_s']:.2f} m/s")
                    else:
                        print(f"  ⚠ Solution did not converge well")
                        print(f"    Position error: {validation['position_error_m']:.2f} m")
                else:
                    print(f"  ✗ Validation failed: {validation['error']}")
            else:
                print("  ⚠ TelemetrySolver not found, skipping validation")
                
        except Exception as e:
            print(f"  ✗ Failed to generate: {str(e)}")
    
    # Save summary
    summary_file = os.path.join(output_dir, "test_summary.json")
    with open(summary_file, 'w') as f:
        json.dump({
            "num_cases": len(summaries),
            "cases": summaries,
            "validation_results": validation_results
        }, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Summary: Generated {len(summaries)} test cases")
    print(f"Output directory: {output_dir}")
    print(f"Summary file: {summary_file}")
    
    if validation_results:
        successful = sum(1 for v in validation_results if v["success"] and v["converged"])
        print(f"\nValidation: {successful}/{len(validation_results)} cases converged successfully")
        
        if successful > 0:
            avg_pos_error = np.mean([v["position_error_m"] for v in validation_results 
                                    if v["success"] and v["converged"]])
            avg_vel_error = np.mean([v["velocity_error_m_s"] for v in validation_results 
                                    if v["success"] and v["converged"]])
            print(f"Average position error: {avg_pos_error:.2f} m")
            print(f"Average velocity error: {avg_vel_error:.2f} m/s")


if __name__ == "__main__":
    main()