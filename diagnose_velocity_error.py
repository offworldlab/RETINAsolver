#!/usr/bin/env python3
"""
Diagnose why velocity estimates have large errors despite perfect position estimates
"""

import json
import numpy as np
import sys
sys.path.append('/Users/jehanazad/offworldlab/TelemetrySolver')

from detection_triple import load_detections
from initial_guess_3det_truth import get_initial_guess_ellipse_method
from lm_solver_3det import solve_position_velocity_3d, doppler_residual
from Geometry import Geometry


def analyze_doppler_sensitivity():
    """Analyze how sensitive Doppler is to velocity errors"""
    print("=== DOPPLER SENSITIVITY ANALYSIS ===\n")
    
    # Test parameters
    freq_hz = 100e6  # 100 MHz
    c = 299792458.0  # m/s
    
    # Typical geometry
    ioo_enu = (0, 0, 0)
    sensor_enu = (10000, 10000, 0)
    target_enu = (20000, 20000, 5000)
    
    # Unit vectors
    ioo_to_target = np.array(target_enu) - np.array(ioo_enu)
    ioo_to_target_unit = ioo_to_target / np.linalg.norm(ioo_to_target)
    
    target_to_sensor = np.array(sensor_enu) - np.array(target_enu)
    target_to_sensor_unit = target_to_sensor / np.linalg.norm(target_to_sensor)
    
    print("Geometry:")
    print(f"  IoO-Target distance: {np.linalg.norm(ioo_to_target)/1000:.1f} km")
    print(f"  Target-Sensor distance: {np.linalg.norm(target_to_sensor)/1000:.1f} km")
    
    # Test different velocities
    print("\nDoppler vs Velocity:")
    print(f"{'Velocity (m/s)':>15} {'Doppler (Hz)':>15} {'Hz per m/s':>15}")
    print("-" * 50)
    
    for v in [0, 100, 200, 300]:
        velocity = np.array([v, 0, 0])  # East velocity only
        v_radial_ioo = np.dot(velocity, ioo_to_target_unit)
        v_radial_sensor = np.dot(velocity, target_to_sensor_unit)
        doppler = -(freq_hz / c) * (v_radial_ioo + v_radial_sensor)
        
        sensitivity = abs(doppler / v) if v > 0 else 0
        print(f"{v:>15.0f} {doppler:>15.1f} {sensitivity:>15.3f}")
    
    print(f"\nTypical Doppler sensitivity: ~0.2-0.3 Hz per m/s")
    print(f"So 100 m/s velocity error → ~20-30 Hz Doppler error")


def check_measurement_precision(test_file):
    """Check if measurements have sufficient precision"""
    print("\n\n=== MEASUREMENT PRECISION CHECK ===\n")
    
    with open(test_file, 'r') as f:
        data = json.load(f)
    
    print("Doppler measurements:")
    for i in range(1, 4):
        doppler = data[f'detection{i}']['doppler_hz']
        print(f"  Detection {i}: {doppler:.5f} Hz")
    
    print("\nBistatic range measurements:")
    for i in range(1, 4):
        range_km = data[f'detection{i}']['bistatic_range_km']
        print(f"  Detection {i}: {range_km:.5f} km = {range_km*1000:.2f} m")
    
    print("\nNote: Measurements stored with 5 decimal places")
    print("      This gives ~0.00001 Hz Doppler precision")
    print("      But velocity errors are 100-700 m/s!")


def test_doppler_calculation_accuracy():
    """Test if our Doppler calculation matches the test data"""
    print("\n\n=== DOPPLER CALCULATION VERIFICATION ===\n")
    
    test_input = "/Users/jehanazad/offworldlab/test_3detections_new/3det_case_1_input.json"
    test_truth = "/Users/jehanazad/offworldlab/test_3detections_new/3det_case_1_truth.json"
    
    # Load data
    triple = load_detections(test_input)
    with open(test_truth, 'r') as f:
        truth = json.load(f)
    
    # Get ENU origin
    origin = triple.get_enu_origin()
    
    # Convert truth to ENU
    truth_ecef = Geometry.lla2ecef(truth["latitude"], truth["longitude"], truth["altitude"])
    truth_enu = Geometry.ecef2enu(truth_ecef[0], truth_ecef[1], truth_ecef[2],
                                  origin[0], origin[1], origin[2])
    
    # True state
    true_state = [
        truth_enu[0], truth_enu[1], truth_enu[2],
        truth["velocity_east"], truth["velocity_north"], truth["velocity_up"]
    ]
    
    print("True state:")
    print(f"  Position: ({true_state[0]/1000:.1f}, {true_state[1]/1000:.1f}, {true_state[2]/1000:.1f}) km")
    print(f"  Velocity: ({true_state[3]:.1f}, {true_state[4]:.1f}, {true_state[5]:.1f}) m/s")
    
    # Calculate expected Doppler for each detection
    print("\nDoppler comparison:")
    print(f"{'Detection':>10} {'Measured (Hz)':>15} {'Calculated (Hz)':>15} {'Error (Hz)':>12}")
    print("-" * 55)
    
    for i, detection in enumerate(triple.get_all_detections()):
        # Convert positions to ENU
        sensor_ecef = Geometry.lla2ecef(detection.sensor_lat, detection.sensor_lon, 0)
        ioo_ecef = Geometry.lla2ecef(detection.ioo_lat, detection.ioo_lon, 0)
        
        sensor_enu = Geometry.ecef2enu(sensor_ecef[0], sensor_ecef[1], sensor_ecef[2],
                                      origin[0], origin[1], origin[2])
        ioo_enu = Geometry.ecef2enu(ioo_ecef[0], ioo_ecef[1], ioo_ecef[2],
                                    origin[0], origin[1], origin[2])
        
        # Calculate Doppler residual (should be ~0 for true state)
        freq_hz = detection.freq_mhz * 1e6
        residual = doppler_residual(true_state, ioo_enu, sensor_enu, freq_hz, detection.doppler_hz)
        
        # Calculate expected Doppler
        calculated_doppler = detection.doppler_hz + residual
        
        print(f"{i+1:>10} {detection.doppler_hz:>15.5f} {calculated_doppler:>15.5f} {residual:>12.5f}")
    
    print("\nIf errors are large, there's a mismatch in Doppler calculation!")


def test_solver_with_perturbed_velocity():
    """Test how solver responds to velocity perturbations"""
    print("\n\n=== VELOCITY PERTURBATION TEST ===\n")
    
    test_input = "/Users/jehanazad/offworldlab/test_3detections_new/3det_case_1_input.json"
    test_truth = "/Users/jehanazad/offworldlab/test_3detections_new/3det_case_1_truth.json"
    
    # Load data
    triple = load_detections(test_input)
    with open(test_truth, 'r') as f:
        truth = json.load(f)
    
    # Get truth-based initial guess
    from initial_guess_3det_truth import get_initial_guess_from_truth
    true_guess = get_initial_guess_from_truth(triple, test_truth)
    
    print("Testing solver with perturbed initial velocity guesses:")
    print(f"{'Velocity Perturbation':>25} {'Solution Vel Error (m/s)':>25}")
    print("-" * 55)
    
    # Test different velocity perturbations
    for vel_offset in [0, 50, 100, 200]:
        perturbed_guess = true_guess.copy()
        perturbed_guess[3] += vel_offset  # Perturb east velocity
        
        solution = solve_position_velocity_3d(triple, perturbed_guess)
        
        if solution:
            vel_error = np.sqrt(
                (solution["velocity_east"] - truth["velocity_east"])**2 +
                (solution["velocity_north"] - truth["velocity_north"])**2 +
                (solution["velocity_up"] - truth["velocity_up"])**2
            )
            print(f"{f'+{vel_offset} m/s east':>25} {vel_error:>25.1f}")
        else:
            print(f"{f'+{vel_offset} m/s east':>25} {'No convergence':>25}")


def main():
    test_file = "/Users/jehanazad/offworldlab/test_3detections_new/3det_case_1_input.json"
    
    print("=== VELOCITY ERROR DIAGNOSIS ===\n")
    
    analyze_doppler_sensitivity()
    check_measurement_precision(test_file)
    test_doppler_calculation_accuracy()
    test_solver_with_perturbed_velocity()
    
    print("\n\nCONCLUSION:")
    print("The large velocity errors despite perfect position accuracy suggest:")
    print("1. The solver may be finding a different local minimum for velocity")
    print("2. There might be an issue with the Doppler calculation or sign convention")
    print("3. The test data generation might have inconsistent velocity/Doppler values")


if __name__ == "__main__":
    main()