"""
Levenberg-Marquardt solver module for 3-detection telemetry solver
Solves for full 6D state: [x, y, z, vx, vy, vz]
"""
import numpy as np
from scipy.optimize import least_squares
from typing import List, Optional, Tuple
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from detection_triple import DetectionTriple
from Geometry import Geometry


def distance_3d(p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
    """Calculate Euclidean distance between two 3D points"""
    return np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2 + (p2[2] - p1[2])**2)


def bistatic_range_residual(state: List[float], ioo_enu: Tuple[float, float, float],
                           sensor_enu: Tuple[float, float, float], 
                           measured_range_m: float) -> float:
    """Calculate range residual for full 3D position"""
    # Extract position from state (now includes z)
    target_pos = (state[0], state[1], state[2])
    
    # Calculate bistatic range
    range_ioo_target = distance_3d(ioo_enu, target_pos)
    range_target_sensor = distance_3d(target_pos, sensor_enu)
    calculated_range = range_ioo_target + range_target_sensor
    
    return calculated_range - measured_range_m


def doppler_residual(state: List[float], ioo_enu: Tuple[float, float, float],
                    sensor_enu: Tuple[float, float, float],
                    freq_hz: float, measured_doppler_hz: float) -> float:
    """Calculate Doppler residual with full 3D velocity"""
    # Extract position and velocity from state
    target_pos = np.array([state[0], state[1], state[2]])
    target_vel = np.array([state[3], state[4], state[5]])
    
    # Speed of light
    c = 299792458.0  # m/s
    
    # Calculate unit vectors
    # IoO to target
    ioo_to_target = target_pos - np.array(ioo_enu)
    dist_ioo_target = np.linalg.norm(ioo_to_target)
    unit_ioo_target = ioo_to_target / dist_ioo_target
    
    # Target to sensor
    target_to_sensor = np.array(sensor_enu) - target_pos
    dist_target_sensor = np.linalg.norm(target_to_sensor)
    unit_target_sensor = target_to_sensor / dist_target_sensor
    
    # Radial velocities
    v_radial_ioo = np.dot(target_vel, unit_ioo_target)
    v_radial_sensor = np.dot(target_vel, unit_target_sensor)
    
    # Bistatic Doppler
    # Negative sign because FDOA is frequency difference (direct - reflected)
    doppler_ratio = -(v_radial_ioo + v_radial_sensor) / c
    calculated_doppler = freq_hz * doppler_ratio
    
    return calculated_doppler - measured_doppler_hz


def residual_function(state: List[float], detection_triple: DetectionTriple, 
                     enu_origin: Tuple[float, float, float]) -> np.ndarray:
    """Calculate all residuals for the 3-detection system (6 equations)"""
    origin_lat, origin_lon, origin_alt = enu_origin
    
    residuals = []
    
    # Process all 3 detections
    for detection in detection_triple.get_all_detections():
        # Convert sensor and IoO to ENU
        sensor_ecef = Geometry.lla2ecef(detection.sensor_lat, detection.sensor_lon, 0)
        ioo_ecef = Geometry.lla2ecef(detection.ioo_lat, detection.ioo_lon, 0)
        
        sensor_enu = Geometry.ecef2enu(sensor_ecef[0], sensor_ecef[1], sensor_ecef[2],
                                      origin_lat, origin_lon, origin_alt)
        ioo_enu = Geometry.ecef2enu(ioo_ecef[0], ioo_ecef[1], ioo_ecef[2],
                                    origin_lat, origin_lon, origin_alt)
        
        # Convert measurements
        range_m = detection.bistatic_range_km * 1000
        freq_hz = detection.freq_mhz * 1e6
        
        # Add residuals for this detection
        residuals.append(bistatic_range_residual(state, ioo_enu, sensor_enu, range_m))
        residuals.append(doppler_residual(state, ioo_enu, sensor_enu, freq_hz, 
                                         detection.doppler_hz))
    
    return np.array(residuals)


def altitude_bounds(state: List[float]) -> List[float]:
    """
    Soft constraint for altitude bounds (0-30km)
    Returns penalty values that increase as altitude goes out of bounds
    """
    z = state[2]  # altitude in meters
    
    penalties = []
    
    # Lower bound (0m)
    if z < 0:
        penalties.append(-z * 0.1)  # Penalty proportional to negative altitude
    
    # Upper bound (30km)
    if z > 30000:
        penalties.append((z - 30000) * 0.1)  # Penalty for exceeding 30km
    
    return penalties


def residual_function_with_bounds(state: List[float], detection_triple: DetectionTriple, 
                                 enu_origin: Tuple[float, float, float]) -> np.ndarray:
    """Residual function with altitude bounds as soft constraints"""
    # Get measurement residuals
    measurement_residuals = residual_function(state, detection_triple, enu_origin)
    
    # Get altitude penalties
    altitude_penalties = altitude_bounds(state)
    
    # Combine all residuals
    if altitude_penalties:
        return np.concatenate([measurement_residuals, altitude_penalties])
    else:
        return measurement_residuals


def solve_position_velocity_3d(detection_triple: DetectionTriple, 
                              initial_guess: List[float]) -> Optional[dict]:
    """
    Solve for 3D position and velocity using Levenberg-Marquardt
    State vector: [x, y, z, vx, vy, vz]
    Returns solution dict or None if failed
    """
    enu_origin = detection_triple.get_enu_origin()
    
    # Bounds for least_squares (hard constraints)
    # Position bounds: reasonable ENU range
    # Velocity bounds: reasonable speeds
    lower_bounds = [-1e6, -1e6, 0, -1000, -1000, -200]  # z >= 0m, vz >= -200 m/s
    upper_bounds = [1e6, 1e6, 30000, 1000, 1000, 200]   # z <= 30km, vz <= 200 m/s
    
    # Run optimization with bounds
    # Use 'trf' (Trust Region Reflective) method which supports bounds
    result = least_squares(
        residual_function_with_bounds,
        initial_guess,
        args=(detection_triple, enu_origin),
        method='trf',  # Changed from 'lm' to support bounds
        bounds=(lower_bounds, upper_bounds),
        ftol=1e-6,
        xtol=1e-6,
        max_nfev=1000  # Maximum function evaluations
    )
    
    if not result.success:
        return None
    
    # Extract solution
    x_enu, y_enu, z_enu, vx_enu, vy_enu, vz_enu = result.x
    
    # Convert position from ENU to ECEF then to LLA
    origin_lat, origin_lon, origin_alt = enu_origin
    target_ecef = Geometry.enu2ecef(x_enu, y_enu, z_enu,
                                    origin_lat, origin_lon, origin_alt)
    target_lla = Geometry.ecef2lla(target_ecef[0], target_ecef[1], target_ecef[2])
    
    # Check convergence (position error < 200m)
    # Only check measurement residuals, not altitude penalties
    measurement_residuals = residual_function(result.x, detection_triple, enu_origin)
    range_residuals = [abs(measurement_residuals[i]) for i in range(0, 6, 2)]  # Every other is range
    if max(range_residuals) > 200.0:
        return None
    
    return {
        'lat': target_lla[0],
        'lon': target_lla[1],
        'alt': target_lla[2],
        'velocity_east': vx_enu,
        'velocity_north': vy_enu,
        'velocity_up': vz_enu,
        'residuals': measurement_residuals.tolist(),
        'convergence_metric': max(range_residuals)
    }