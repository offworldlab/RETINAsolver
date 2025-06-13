"""
Initial guess module for 3-detection telemetry solver
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from typing import List, Tuple
from detection_triple import DetectionTriple
from Geometry import Geometry


def calculate_ellipse_center_enu(ioo_enu: Tuple[float, float, float], 
                                sensor_enu: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Return midpoint between ellipse foci in ENU"""
    center_x = (ioo_enu[0] + sensor_enu[0]) / 2
    center_y = (ioo_enu[1] + sensor_enu[1]) / 2
    center_z = (ioo_enu[2] + sensor_enu[2]) / 2
    return center_x, center_y, center_z


def get_initial_guess(detection_triple: DetectionTriple) -> List[float]:
    """
    Calculate initial position and velocity estimate for 3 detections
    Returns: [x, y, z, vx, vy, vz] in ENU coordinates
    """
    # Get ENU origin (first sensor position)
    origin_lat = detection_triple.detection1.sensor_lat
    origin_lon = detection_triple.detection1.sensor_lon
    origin_alt = 0.0  # Assume sea level
    
    # Convert all sensor and IoO positions to ENU
    detections = [detection_triple.detection1, detection_triple.detection2, detection_triple.detection3]
    ellipse_centers = []
    
    for detection in detections:
        # Convert sensor position to ECEF then ENU
        sensor_ecef = Geometry.lla2ecef(detection.sensor_lat, detection.sensor_lon, 0.0)
        sensor_enu = Geometry.ecef2enu(sensor_ecef[0], sensor_ecef[1], sensor_ecef[2],
                                       origin_lat, origin_lon, origin_alt)
        
        # Convert IoO position to ECEF then ENU  
        ioo_ecef = Geometry.lla2ecef(detection.ioo_lat, detection.ioo_lon, 0.0)
        ioo_enu = Geometry.ecef2enu(ioo_ecef[0], ioo_ecef[1], ioo_ecef[2],
                                    origin_lat, origin_lon, origin_alt)
        
        # Calculate ellipse center (midpoint between foci)
        center = calculate_ellipse_center_enu(ioo_enu, sensor_enu)
        ellipse_centers.append(center)
    
    # Initial position estimate: average of ellipse centers
    x_est = sum(center[0] for center in ellipse_centers) / 3
    y_est = sum(center[1] for center in ellipse_centers) / 3
    z_est = max(1000.0, sum(center[2] for center in ellipse_centers) / 3)  # Ensure positive altitude, default to 1km
    
    # Initial velocity estimate: zero velocity
    vx_est = 0.0
    vy_est = 0.0
    vz_est = 0.0
    
    return [x_est, y_est, z_est, vx_est, vy_est, vz_est]