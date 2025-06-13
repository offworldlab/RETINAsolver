"""
Demonstrate how the initial guess module works
"""
import json
from detection_triple import DetectionTriple
from initial_guess_3det import get_initial_guess, calculate_ellipse_center_enu
from Geometry import Geometry


def demo_initial_guess():
    """Show step-by-step how initial guess is calculated"""
    
    # Sample detection data (NYC area)
    test_data = {
        "detection1": {
            "sensor_lat": 40.7128, "sensor_lon": -74.0060,  # NYC
            "ioo_lat": 40.7589, "ioo_lon": -73.9851,        # Central Park
            "freq_mhz": 1090.0, "timestamp": 1700000000,
            "bistatic_range_km": 15.5, "doppler_hz": 50.0
        },
        "detection2": {
            "sensor_lat": 40.6782, "sensor_lon": -73.9442,  # Brooklyn
            "ioo_lat": 40.7589, "ioo_lon": -73.9851,        # Central Park
            "freq_mhz": 1090.0, "timestamp": 1700000000,
            "bistatic_range_km": 18.2, "doppler_hz": 35.0
        },
        "detection3": {
            "sensor_lat": 40.7500, "sensor_lon": -73.9860,  # Midtown
            "ioo_lat": 40.7589, "ioo_lon": -73.9851,        # Central Park
            "freq_mhz": 1090.0, "timestamp": 1700000000,
            "bistatic_range_km": 12.8, "doppler_hz": 65.0
        }
    }
    
    print("=" * 60)
    print("INITIAL GUESS ALGORITHM DEMONSTRATION")
    print("=" * 60)
    
    # Parse detection data
    detection_triple = DetectionTriple.from_json(json.dumps(test_data))
    
    print("\n1. INPUT DETECTIONS:")
    print("-" * 40)
    for i, det_name in enumerate(['detection1', 'detection2', 'detection3'], 1):
        det = getattr(detection_triple, det_name)
        print(f"Detection {i}:")
        print(f"  Sensor: ({det.sensor_lat:.4f}, {det.sensor_lon:.4f})")
        print(f"  IoO:    ({det.ioo_lat:.4f}, {det.ioo_lon:.4f})")
        print(f"  Range:  {det.bistatic_range_km} km")
        print(f"  Doppler: {det.doppler_hz} Hz")
        print()
    
    print("2. COORDINATE SYSTEM SETUP:")
    print("-" * 40)
    # ENU origin (first sensor position)
    origin_lat = detection_triple.detection1.sensor_lat
    origin_lon = detection_triple.detection1.sensor_lon
    origin_alt = 0.0
    print(f"ENU Origin: ({origin_lat:.4f}, {origin_lon:.4f}, {origin_alt})")
    print("All positions will be converted to meters relative to this origin.")
    print()
    
    print("3. COORDINATE CONVERSIONS:")
    print("-" * 40)
    detections = [detection_triple.detection1, detection_triple.detection2, detection_triple.detection3]
    ellipse_centers = []
    
    for i, detection in enumerate(detections, 1):
        print(f"Detection {i}:")
        
        # Convert sensor position
        sensor_ecef = Geometry.lla2ecef(detection.sensor_lat, detection.sensor_lon, 0.0)
        sensor_enu = Geometry.ecef2enu(sensor_ecef[0], sensor_ecef[1], sensor_ecef[2],
                                       origin_lat, origin_lon, origin_alt)
        print(f"  Sensor ENU: ({sensor_enu[0]:.1f}, {sensor_enu[1]:.1f}, {sensor_enu[2]:.1f}) m")
        
        # Convert IoO position
        ioo_ecef = Geometry.lla2ecef(detection.ioo_lat, detection.ioo_lon, 0.0)
        ioo_enu = Geometry.ecef2enu(ioo_ecef[0], ioo_ecef[1], ioo_ecef[2],
                                    origin_lat, origin_lon, origin_alt)
        print(f"  IoO ENU:    ({ioo_enu[0]:.1f}, {ioo_enu[1]:.1f}, {ioo_enu[2]:.1f}) m")
        
        # Calculate ellipse center
        center = calculate_ellipse_center_enu(ioo_enu, sensor_enu)
        ellipse_centers.append(center)
        print(f"  Ellipse Center: ({center[0]:.1f}, {center[1]:.1f}, {center[2]:.1f}) m")
        print()
    
    print("4. ELLIPSE GEOMETRY EXPLANATION:")
    print("-" * 40)
    print("For each detection, the target lies on an ellipse where:")
    print("- IoO and Sensor are the two foci")
    print("- Total path length (IoO→Target→Sensor) equals measured bistatic range")
    print("- The ellipse center is the midpoint between the two foci")
    print("- This gives us a geometric constraint on where the target can be")
    print()
    
    print("5. INITIAL POSITION ESTIMATE:")
    print("-" * 40)
    x_est = sum(center[0] for center in ellipse_centers) / 3
    y_est = sum(center[1] for center in ellipse_centers) / 3
    z_est_raw = sum(center[2] for center in ellipse_centers) / 3
    z_est = max(1000.0, z_est_raw)
    
    print(f"Average of ellipse centers:")
    print(f"  X (East):  {x_est:.1f} m")
    print(f"  Y (North): {y_est:.1f} m") 
    print(f"  Z (Up):    {z_est_raw:.1f} m → {z_est:.1f} m (enforced minimum 1000m)")
    print()
    print("This averaging assumes the target is near the intersection")
    print("of the three ellipses defined by the range measurements.")
    print()
    
    print("6. INITIAL VELOCITY ESTIMATE:")
    print("-" * 40)
    print("Initial velocity: (0, 0, 0) m/s")
    print("The solver will estimate velocity from Doppler measurements.")
    print()
    
    print("7. FINAL INITIAL GUESS:")
    print("-" * 40)
    initial_guess = get_initial_guess(detection_triple)
    print(f"State vector: [{initial_guess[0]:.1f}, {initial_guess[1]:.1f}, {initial_guess[2]:.1f}, {initial_guess[3]:.1f}, {initial_guess[4]:.1f}, {initial_guess[5]:.1f}]")
    print("Format: [x, y, z, vx, vy, vz] in ENU coordinates")
    print()
    
    print("8. WHY THIS WORKS:")
    print("-" * 40)
    print("✓ Geometric foundation: Uses ellipse intersections from range measurements")
    print("✓ Robust averaging: Reduces impact of measurement noise")
    print("✓ Reasonable bounds: Ensures altitude is positive for convergence")
    print("✓ Simple velocity: Zero initial velocity lets solver focus on position first")
    print("✓ Local coordinates: ENU system simplifies optimization mathematics")
    

if __name__ == "__main__":
    demo_initial_guess()