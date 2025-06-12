#!/usr/bin/env python3
"""
Comprehensive testing of the 3-detection system
Tests different aspects: initial guess quality, solver robustness, velocity accuracy
"""

import json
import numpy as np
import subprocess
import sys
import os
import glob
from typing import Dict, List, Tuple

# Import modules for direct testing
sys.path.append('/Users/jehanazad/offworldlab/TelemetrySolver')
from detection_triple import load_detections
from initial_guess_3det_truth import (
    get_initial_guess_ellipse_method,
    get_initial_guess_from_truth
)
from lm_solver_3det import solve_position_velocity_3d
from Geometry import Geometry


def test_initial_guess_quality(test_cases: List[Tuple[str, str]]) -> None:
    """Test the quality of ellipse-based initial guesses"""
    print("\n=== INITIAL GUESS QUALITY ANALYSIS ===")
    print(f"{'Case':>4} {'Position Error (km)':>20} {'Altitude Guess (km)':>20} {'True Alt (km)':>15}")
    print("-" * 70)
    
    errors = []
    
    for input_file, truth_file in test_cases[:5]:
        case_num = int(input_file.split('_')[-2])
        
        # Load detection and truth
        triple = load_detections(input_file)
        with open(truth_file, 'r') as f:
            truth = json.load(f)
        
        # Get initial guess
        guess = get_initial_guess_ellipse_method(triple)
        
        # Convert truth to ENU for comparison
        origin = triple.get_enu_origin()
        truth_ecef = Geometry.lla2ecef(truth["latitude"], truth["longitude"], truth["altitude"])
        truth_enu = Geometry.ecef2enu(truth_ecef[0], truth_ecef[1], truth_ecef[2],
                                      origin[0], origin[1], origin[2])
        
        # Calculate position error
        pos_error = np.sqrt((guess[0] - truth_enu[0])**2 + 
                           (guess[1] - truth_enu[1])**2 + 
                           (guess[2] - truth_enu[2])**2)
        errors.append(pos_error)
        
        print(f"{case_num:>4} {pos_error/1000:>20.1f} {guess[2]/1000:>20.1f} {truth['altitude']/1000:>15.1f}")
    
    print(f"\nAverage initial guess error: {np.mean(errors)/1000:.1f} km")
    print(f"Note: Ellipse method assumes 5km altitude, actual varies 0-30km")


def test_solver_with_different_initial_guesses(test_cases: List[Tuple[str, str]]) -> None:
    """Test solver convergence with different initial guess strategies"""
    print("\n\n=== SOLVER CONVERGENCE WITH DIFFERENT INITIAL GUESSES ===")
    
    strategies = [
        ("Ellipse (5km)", lambda t, tf: get_initial_guess_ellipse_method(t)),
        ("Ellipse (10km)", lambda t, tf: modify_altitude(get_initial_guess_ellipse_method(t), 10000)),
        ("Random offset", lambda t, tf: add_random_offset(get_initial_guess_ellipse_method(t))),
        ("Truth + noise", lambda t, tf: get_initial_guess_from_truth(t, tf))
    ]
    
    for strategy_name, strategy_func in strategies:
        print(f"\n{strategy_name} Initial Guess:")
        print(f"{'Case':>4} {'Converged':>10} {'Pos Error (m)':>15} {'Vel Error (m/s)':>15}")
        print("-" * 50)
        
        converged = 0
        for input_file, truth_file in test_cases[:5]:
            case_num = int(input_file.split('_')[-2])
            
            # Load detection
            triple = load_detections(input_file)
            
            # Get initial guess using strategy
            initial_guess = strategy_func(triple, truth_file)
            
            # Solve
            solution = solve_position_velocity_3d(triple, initial_guess)
            
            if solution:
                # Load truth and calculate errors
                with open(truth_file, 'r') as f:
                    truth = json.load(f)
                
                pos_error, vel_error = calculate_errors(solution, truth)
                converged += 1
                print(f"{case_num:>4} {'✓':>10} {pos_error:>15.1f} {vel_error:>15.1f}")
            else:
                print(f"{case_num:>4} {'✗':>10} {'N/A':>15} {'N/A':>15}")
        
        print(f"Convergence rate: {converged}/5 ({converged*20}%)")


def modify_altitude(guess: List[float], new_altitude: float) -> List[float]:
    """Modify the altitude component of initial guess"""
    modified = guess.copy()
    modified[2] = new_altitude
    return modified


def add_random_offset(guess: List[float]) -> List[float]:
    """Add random offset to initial guess"""
    modified = guess.copy()
    # Add up to 10km position offset
    modified[0] += np.random.uniform(-10000, 10000)
    modified[1] += np.random.uniform(-10000, 10000)
    modified[2] += np.random.uniform(-5000, 5000)
    # Add small velocity
    modified[3] = np.random.uniform(-50, 50)
    modified[4] = np.random.uniform(-50, 50)
    modified[5] = np.random.uniform(-10, 10)
    return modified


def calculate_errors(solution: Dict, truth: Dict) -> Tuple[float, float]:
    """Calculate position and velocity errors"""
    # Position error (handle longitude wraparound)
    lat_error = abs(solution["lat"] - truth["latitude"]) * 111111.0
    lon_diff = solution["lon"] - truth["longitude"]
    if lon_diff > 180:
        lon_diff -= 360
    elif lon_diff < -180:
        lon_diff += 360
    lon_error = abs(lon_diff) * 111111.0 * np.cos(np.radians(truth["latitude"]))
    alt_error = abs(solution["alt"] - truth["altitude"])
    pos_error = np.sqrt(lat_error**2 + lon_error**2 + alt_error**2)
    
    # Velocity error
    vel_east_error = abs(solution["velocity_east"] - truth["velocity_east"])
    vel_north_error = abs(solution["velocity_north"] - truth["velocity_north"])
    vel_up_error = abs(solution["velocity_up"] - truth["velocity_up"])
    vel_error = np.sqrt(vel_east_error**2 + vel_north_error**2 + vel_up_error**2)
    
    return pos_error, vel_error


def test_velocity_accuracy(test_cases: List[Tuple[str, str]]) -> None:
    """Analyze velocity estimation accuracy"""
    print("\n\n=== VELOCITY ESTIMATION ANALYSIS ===")
    
    vel_errors = {'east': [], 'north': [], 'up': [], 'total': []}
    
    for input_file, truth_file in test_cases:
        # Run solver
        triple = load_detections(input_file)
        initial_guess = get_initial_guess_ellipse_method(triple)
        solution = solve_position_velocity_3d(triple, initial_guess)
        
        if solution:
            with open(truth_file, 'r') as f:
                truth = json.load(f)
            
            # Component errors
            vel_errors['east'].append(solution["velocity_east"] - truth["velocity_east"])
            vel_errors['north'].append(solution["velocity_north"] - truth["velocity_north"])
            vel_errors['up'].append(solution["velocity_up"] - truth["velocity_up"])
            
            _, vel_total = calculate_errors(solution, truth)
            vel_errors['total'].append(vel_total)
    
    print(f"Velocity Error Statistics (m/s):")
    print(f"{'Component':>10} {'Mean':>10} {'Std Dev':>10} {'Max Abs':>10}")
    print("-" * 45)
    
    for component in ['east', 'north', 'up', 'total']:
        if vel_errors[component]:
            errors = vel_errors[component]
            mean = np.mean(errors)
            std = np.std(errors)
            max_abs = np.max(np.abs(errors))
            print(f"{component:>10} {mean:>10.1f} {std:>10.1f} {max_abs:>10.1f}")
    
    print(f"\nNote: Large velocity errors despite good position accuracy")
    print(f"      This suggests Doppler measurement or modeling issues")


def test_residual_analysis(test_cases: List[Tuple[str, str]]) -> None:
    """Analyze solver residuals"""
    print("\n\n=== RESIDUAL ANALYSIS ===")
    
    all_residuals = []
    
    for input_file, truth_file in test_cases[:5]:
        case_num = int(input_file.split('_')[-2])
        
        # Run solver
        triple = load_detections(input_file)
        initial_guess = get_initial_guess_ellipse_method(triple)
        solution = solve_position_velocity_3d(triple, initial_guess)
        
        if solution and 'residuals' in solution:
            residuals = solution['residuals']
            all_residuals.append(residuals)
            
            print(f"\nCase {case_num} residuals:")
            print(f"  Range residuals (m): {residuals[0]:.2e}, {residuals[2]:.2e}, {residuals[4]:.2e}")
            print(f"  Doppler residuals (Hz): {residuals[1]:.2e}, {residuals[3]:.2e}, {residuals[5]:.2e}")
    
    if all_residuals:
        all_residuals = np.array(all_residuals)
        print(f"\nRMS Residuals across cases:")
        print(f"  Range: {np.sqrt(np.mean(all_residuals[:, [0,2,4]]**2)):.2e} m")
        print(f"  Doppler: {np.sqrt(np.mean(all_residuals[:, [1,3,5]]**2)):.2e} Hz")


def test_geometry_impact(test_cases: List[Tuple[str, str]]) -> None:
    """Analyze impact of sensor-IoO geometry on convergence"""
    print("\n\n=== GEOMETRY IMPACT ANALYSIS ===")
    
    # Load summary to get geometry info
    summary_file = os.path.dirname(test_cases[0][0]) + "/test_summary.json"
    if os.path.exists(summary_file):
        with open(summary_file, 'r') as f:
            summary = json.load(f)
        
        print(f"{'Case':>4} {'Max Baseline (km)':>18} {'Config':>15} {'Converged':>10}")
        print("-" * 50)
        
        for case in summary['cases'][:10]:
            case_num = case['case_number']
            max_baseline = case['max_baseline_km']
            config = str(case['sensor_ioo_pairs'])
            
            # Check if converged
            input_file = f"{os.path.dirname(test_cases[0][0])}/3det_case_{case_num}_input.json"
            triple = load_detections(input_file)
            initial_guess = get_initial_guess_ellipse_method(triple)
            solution = solve_position_velocity_3d(triple, initial_guess)
            
            converged = "✓" if solution else "✗"
            print(f"{case_num:>4} {max_baseline:>18.1f} {config:>15} {converged:>10}")


def main():
    # Find test cases
    test_dir = "test_3detections_new"
    input_files = sorted(glob.glob(f"{test_dir}/3det_case_*_input.json"))
    
    if not input_files:
        print("No test cases found!")
        return
    
    # Create test case pairs
    test_cases = []
    for input_file in input_files:
        truth_file = input_file.replace('_input.json', '_truth.json')
        if os.path.exists(truth_file):
            test_cases.append((input_file, truth_file))
    
    print("=== COMPREHENSIVE 3-DETECTION SYSTEM TEST ===")
    print(f"Testing with {len(test_cases)} cases from {test_dir}")
    
    # Run all tests
    test_initial_guess_quality(test_cases)
    test_solver_with_different_initial_guesses(test_cases)
    test_velocity_accuracy(test_cases)
    test_residual_analysis(test_cases)
    test_geometry_impact(test_cases)
    
    print("\n\n✅ Comprehensive testing complete!")


if __name__ == "__main__":
    main()