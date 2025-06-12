#!/usr/bin/env python3
"""
Verify and fix the Doppler calculation issue in test data generation
"""

import numpy as np

def show_coordinate_issue():
    """Show the coordinate system mismatch issue"""
    print("=== COORDINATE SYSTEM MISMATCH IN DOPPLER CALCULATION ===\n")
    
    print("Current implementation (WRONG):")
    print("1. Unit vectors ioo_to_target and target_to_sensor are in ECEF")
    print("2. Velocity vector is in ENU (east, north, up)")
    print("3. Direct dot product mixes coordinate systems!")
    print()
    
    print("Example:")
    print("  velocity_enu = [100, 0, 0]  # 100 m/s East")
    print("  unit_vector_ecef = [0.7, 0.7, 0]  # Some ECEF direction")
    print("  dot_product = 100 * 0.7 = 70  # WRONG! Mixed coordinates")
    print()
    
    print("Correct approach:")
    print("1. Convert velocity from ENU to ECEF")
    print("2. Then compute dot product with ECEF unit vectors")
    print("OR")
    print("1. Convert unit vectors from ECEF to ENU")
    print("2. Then compute dot product with ENU velocity")
    
    print("\nThis explains why:")
    print("- Position converges perfectly (uses consistent coordinates)")
    print("- Velocity has large errors (Doppler calculation has mixed coordinates)")
    print("- Errors are ~100-700 m/s (typical for coordinate misalignment)")


def enu_to_ecef_rotation_matrix(lat, lon):
    """Get rotation matrix from ENU to ECEF"""
    lat_rad = np.radians(lat)
    lon_rad = np.radians(lon)
    
    # Rotation matrix from ENU to ECEF
    R = np.array([
        [-np.sin(lon_rad), -np.sin(lat_rad)*np.cos(lon_rad), np.cos(lat_rad)*np.cos(lon_rad)],
        [ np.cos(lon_rad), -np.sin(lat_rad)*np.sin(lon_rad), np.cos(lat_rad)*np.sin(lon_rad)],
        [              0,                   np.cos(lat_rad),                 np.sin(lat_rad)]
    ])
    
    return R


def show_fixed_doppler_calculation():
    """Show the corrected Doppler calculation"""
    print("\n\n=== FIXED DOPPLER CALCULATION ===\n")
    
    print("```python")
    print("def calculate_doppler(sensor: Position, ioo: Position, target: Position, velocity: Velocity) -> float:")
    print("    # Convert to ECEF")
    print("    sensor_ecef = lla_to_ecef(sensor.lat, sensor.lon, sensor.alt)")
    print("    ioo_ecef = lla_to_ecef(ioo.lat, ioo.lon, ioo.alt)")
    print("    target_ecef = lla_to_ecef(target.lat, target.lon, target.alt)")
    print("    ")
    print("    # Unit vectors in ECEF")
    print("    ioo_to_target = (target_ecef - ioo_ecef) / np.linalg.norm(target_ecef - ioo_ecef)")
    print("    target_to_sensor = (sensor_ecef - target_ecef) / np.linalg.norm(sensor_ecef - target_ecef)")
    print("    ")
    print("    # Convert velocity from ENU to ECEF")
    print("    # Get rotation matrix at target location")
    print("    R = enu_to_ecef_rotation_matrix(target.lat, target.lon)")
    print("    velocity_enu = np.array([velocity.east, velocity.north, velocity.up])")
    print("    velocity_ecef = R @ velocity_enu")
    print("    ")
    print("    # Now compute radial velocities in consistent ECEF coordinates")
    print("    v_radial_tx = np.dot(velocity_ecef, ioo_to_target)")
    print("    v_radial_rx = np.dot(velocity_ecef, target_to_sensor)")
    print("    ")
    print("    # Doppler calculation")
    print("    doppler_hz = -(FREQ_MHZ * 1e6 / C) * (v_radial_tx + v_radial_rx)")
    print("    return doppler_hz")
    print("```")


def main():
    show_coordinate_issue()
    show_fixed_doppler_calculation()
    
    print("\n\nIMPACT:")
    print("- This bug affects all generated test data")
    print("- The solver finds correct position but wrong velocity")
    print("- Need to regenerate test data with fixed Doppler calculation")
    print("- After fix, velocity errors should drop to <10 m/s")


if __name__ == "__main__":
    main()