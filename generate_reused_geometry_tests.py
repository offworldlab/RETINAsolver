#!/usr/bin/env python3
"""
Generate new test cases reusing existing sensor/IoO positions but with new targets
"""

import json
import numpy as np
import random
import os
import subprocess
import sys
import glob
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
    """Convert latitude, longitude, altitude to ECEF coordinates."""
    lat_rad = np.radians(lat)
    lon_rad = np.radians(lon)
    
    N = WGS84_A / np.sqrt(1 - WGS84_E2 * np.sin(lat_rad)**2)
    
    x = (N + alt) * np.cos(lat_rad) * np.cos(lon_rad)
    y = (N + alt) * np.cos(lat_rad) * np.sin(lon_rad)
    z = (N * (1 - WGS84_E2) + alt) * np.sin(lat_rad)
    
    return np.array([x, y, z])


def generate_random_position(center_lat: float, center_lon: float, max_range_m: float, min_range_m: float = None) -> Position:
    """Generate a random position within max_range of a center point."""
    min_dist = min_range_m if min_range_m else 0.1 * max_range_m
    distance = random.uniform(min_dist, max_range_m)
    bearing = random.uniform(0, 2 * np.pi)
    
    # Convert to offset in meters (approximate for small distances)
    lat_offset = (distance * np.cos(bearing)) / 111111.0  # Degrees latitude
    lon_offset = (distance * np.sin(bearing)) / (111111.0 * np.cos(np.radians(center_lat)))  # Degrees longitude
    
    return Position(
        lat=center_lat + lat_offset,
        lon=center_lon + lon_offset,
        alt=TARGET_ALTITUDE
    )


def calculate_bistatic_range(sensor: Position, ioo: Position, target: Position) -> float:
    """Calculate bistatic range for a sensor-IoO-target configuration."""
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
    """Calculate Doppler shift for a sensor-IoO-target configuration."""
    # Convert to ECEF
    sensor_ecef = lla_to_ecef(sensor.lat, sensor.lon, sensor.alt)
    ioo_ecef = lla_to_ecef(ioo.lat, ioo.lon, ioo.alt)
    target_ecef = lla_to_ecef(target.lat, target.lon, target.alt)
    
    # Unit vectors
    ioo_to_target = (target_ecef - ioo_ecef) / np.linalg.norm(target_ecef - ioo_ecef)
    target_to_sensor = (sensor_ecef - target_ecef) / np.linalg.norm(sensor_ecef - target_ecef)
    
    # Velocity vector in ECEF (approximate conversion from ENU)
    # For simplicity, assume small area where ENU ≈ ECEF differences
    velocity_ecef = np.array([velocity.east, velocity.north, velocity.up])
    
    # Radial velocities
    v_radial_tx = np.dot(velocity_ecef, ioo_to_target)
    v_radial_rx = np.dot(velocity_ecef, target_to_sensor)
    
    # Use adsb2dd/TelemetrySolver sign convention (negative of standard physics)
    doppler_hz = -(FREQ_MHZ * 1e6 / C) * (v_radial_tx + v_radial_rx)
    
    return doppler_hz


def load_existing_geometry(test_case_dir: str = "test_detections") -> List[Dict]:
    """Load sensor and IoO positions from existing test cases."""
    geometries = []
    
    input_files = glob.glob(f"{test_case_dir}/test_case_*_input.json")
    input_files.sort()
    
    for input_file in input_files:
        case_num = input_file.split('_')[-2]
        
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        geometry = {
            "case_number": int(case_num),
            "sensor1": {
                "lat": data["detection1"]["sensor_lat"],
                "lon": data["detection1"]["sensor_lon"]
            },
            "sensor2": {
                "lat": data["detection2"]["sensor_lat"],
                "lon": data["detection2"]["sensor_lon"]
            },
            "ioo1": {
                "lat": data["detection1"]["ioo_lat"],
                "lon": data["detection1"]["ioo_lon"]
            },
            "ioo2": {
                "lat": data["detection2"]["ioo_lat"],
                "lon": data["detection2"]["ioo_lon"]
            }
        }
        geometries.append(geometry)
    
    return geometries


def generate_test_case_with_geometry(geometry: Dict, new_case_number: int, output_dir: str = ".") -> Dict:
    """Generate a test case using existing sensor/IoO geometry but new target."""
    
    # Extract positions
    sensor1 = Position(geometry["sensor1"]["lat"], geometry["sensor1"]["lon"], 0.0)
    sensor2 = Position(geometry["sensor2"]["lat"], geometry["sensor2"]["lon"], 0.0)
    ioo1 = Position(geometry["ioo1"]["lat"], geometry["ioo1"]["lon"], 0.0)
    ioo2 = Position(geometry["ioo2"]["lat"], geometry["ioo2"]["lon"], 0.0)
    
    # Calculate center point for target generation
    center_lat = (sensor1.lat + sensor2.lat + ioo1.lat + ioo2.lat) / 4
    center_lon = (sensor1.lon + sensor2.lon + ioo1.lon + ioo2.lon) / 4
    
    # Generate new target position (30-50km range for better convergence)
    target = generate_random_position(center_lat, center_lon, 50000, 30000)
    
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
    input_file = os.path.join(output_dir, f"reused_case_{new_case_number}_input.json")
    truth_file = os.path.join(output_dir, f"reused_case_{new_case_number}_truth.json")
    
    with open(input_file, 'w') as f:
        json.dump(detections, f, indent=2)
    
    with open(truth_file, 'w') as f:
        json.dump(ground_truth, f, indent=2)
    
    return {
        "case_number": new_case_number,
        "original_geometry": geometry["case_number"],
        "input_file": input_file,
        "truth_file": truth_file,
        "target": {"lat": target.lat, "lon": target.lon, "alt": target.alt},
        "velocity": {"east": velocity.east, "north": velocity.north, "speed": speed},
        "bistatic_range1_km": bistatic_range1,
        "bistatic_range2_km": bistatic_range2,
        "doppler1_hz": doppler1,
        "doppler2_hz": doppler2
    }


def validate_test_case(case_summary: Dict, telemetry_solver_path: str = "TelemetrySolver") -> Dict:
    """Validate a test case by running it through TelemetrySolver."""
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
        
        # Check if solver converged
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
            "converged": bool(position_error_m < 200.0)  # Within 200m threshold
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Solver timed out"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate test cases with reused sensor/IoO geometry')
    parser.add_argument('--num-targets', type=int, default=3, help='Number of new targets per geometry')
    parser.add_argument('--source-dir', default='test_detections', help='Directory with existing test cases')
    parser.add_argument('--output-dir', default='test_detections_reused', help='Output directory')
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load existing geometries
    print(f"Loading existing sensor/IoO geometries from {args.source_dir}...")
    geometries = load_existing_geometry(args.source_dir)
    print(f"Found {len(geometries)} existing geometries")
    
    # Generate new test cases
    all_cases = []
    all_validations = []
    successful_count = 0
    
    case_counter = 1
    
    for geometry in geometries:
        print(f"\\nUsing geometry from original case {geometry['case_number']}:")
        
        for target_num in range(args.num_targets):
            print(f"  Generating target {target_num + 1}/{args.num_targets}...")
            
            try:
                # Generate test case
                case_summary = generate_test_case_with_geometry(geometry, case_counter, args.output_dir)
                all_cases.append(case_summary)
                
                print(f"    ✓ Generated case {case_counter}")
                print(f"      Target speed: {case_summary['velocity']['speed']:.1f} m/s")
                
                # Validate with solver
                print(f"    Validating with TelemetrySolver...")
                validation = validate_test_case(case_summary)
                all_validations.append(validation)
                
                if validation["success"] and validation.get("converged", False):
                    successful_count += 1
                    pos_error = validation["position_error_m"]
                    vel_error = validation["velocity_error_m_s"]
                    print(f"    ✅ Validation passed!")
                    print(f"      Position error: {pos_error:.2f} m")
                    print(f"      Velocity error: {vel_error:.2f} m/s")
                else:
                    pos_error = validation.get("position_error_m", 0)
                    print(f"    ⚠ Solution did not converge well")
                    print(f"      Position error: {pos_error:.2f} m")
                
                case_counter += 1
                
            except Exception as e:
                print(f"    ❌ Error generating case: {e}")
                continue
    
    # Save summary
    summary = {
        "source_directory": args.source_dir,
        "num_targets_per_geometry": args.num_targets,
        "total_cases": len(all_cases),
        "successful_cases": successful_count,
        "success_rate": successful_count / len(all_cases) * 100 if all_cases else 0,
        "cases": all_cases,
        "validation_results": all_validations
    }
    
    summary_file = os.path.join(args.output_dir, "reused_geometry_summary.json")
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\\n{'='*60}")
    print(f"Summary: Generated {len(all_cases)} test cases using reused geometries")
    print(f"Output directory: {args.output_dir}")
    print(f"Summary file: {summary_file}")
    print(f"\\nValidation: {successful_count}/{len(all_cases)} cases converged successfully")
    if successful_count > 0:
        successful_validations = [v for v in all_validations if v.get("success", False) and v.get("converged", False)]
        avg_pos_error = sum(v["position_error_m"] for v in successful_validations) / len(successful_validations)
        avg_vel_error = sum(v["velocity_error_m_s"] for v in successful_validations) / len(successful_validations)
        print(f"Average position error: {avg_pos_error:.2f} m")
        print(f"Average velocity error: {avg_vel_error:.2f} m/s")
    print(f"Success rate: {successful_count / len(all_cases) * 100:.0f}%")


if __name__ == "__main__":
    main()