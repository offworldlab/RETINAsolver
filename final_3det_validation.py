#!/usr/bin/env python3
"""
Final comprehensive validation of the 3-detection system
Tests convergence, accuracy, robustness, and edge cases
"""

import json
import numpy as np
import subprocess
import sys
import glob
import os
import time

sys.path.append('/Users/jehanazad/offworldlab/TelemetrySolver')
from detection_triple import load_detections
from initial_guess_3det_truth import get_initial_guess_ellipse_method
from lm_solver_3det import solve_position_velocity_3d


def test_case_detailed(input_file, truth_file):
    """Test a case and return detailed metrics"""
    start_time = time.time()
    
    try:
        # Run solver via command line
        result = subprocess.run(
            [sys.executable, "TelemetrySolver/main_3det.py", input_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        solve_time = time.time() - start_time
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Solver failed: {result.stderr}",
                "solve_time": solve_time
            }
        
        # Parse solution
        solution = json.loads(result.stdout)
        
        # Load truth
        with open(truth_file, 'r') as f:
            truth = json.load(f)
        
        if "error" in solution:
            return {
                "success": False,
                "error": f"Solver error: {solution['error']}",
                "solve_time": solve_time
            }
        
        # Calculate errors with proper longitude wraparound
        lat_error = abs(solution["latitude"] - truth["latitude"]) * 111111.0
        lon_diff = solution["longitude"] - truth["longitude"]
        if lon_diff > 180:
            lon_diff -= 360
        elif lon_diff < -180:
            lon_diff += 360
        lon_error = abs(lon_diff) * 111111.0 * np.cos(np.radians(truth["latitude"]))
        alt_error = abs(solution["altitude"] - truth["altitude"])
        
        position_error_3d = np.sqrt(lat_error**2 + lon_error**2 + alt_error**2)
        
        # Velocity component errors
        vel_east_error = solution["velocity_east"] - truth["velocity_east"]
        vel_north_error = solution["velocity_north"] - truth["velocity_north"]
        vel_up_error = solution["velocity_up"] - truth["velocity_up"]
        velocity_error = np.sqrt(vel_east_error**2 + vel_north_error**2 + vel_up_error**2)
        
        # Extract residuals
        residuals = solution.get("residuals", [0]*6)
        range_residuals = [abs(residuals[i]) for i in [0, 2, 4]]
        doppler_residuals = [abs(residuals[i]) for i in [1, 3, 5]]
        
        return {
            "success": True,
            "converged": position_error_3d < 200.0,
            "position_error_3d": position_error_3d,
            "altitude_error": alt_error,
            "velocity_error": velocity_error,
            "velocity_components": {
                "east": vel_east_error,
                "north": vel_north_error,
                "up": vel_up_error
            },
            "max_range_residual": max(range_residuals) if range_residuals else 0,
            "max_doppler_residual": max(doppler_residuals) if doppler_residuals else 0,
            "convergence_metric": solution.get("convergence_metric", 0),
            "solve_time": solve_time,
            "true_altitude": truth["altitude"],
            "true_speed": np.sqrt(truth["velocity_east"]**2 + truth["velocity_north"]**2 + truth["velocity_up"]**2)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "solve_time": time.time() - start_time
        }


def test_initial_guess_impact(test_cases):
    """Test how far off the initial guess can be and still converge"""
    print("\n=== INITIAL GUESS ROBUSTNESS TEST ===")
    print("Testing convergence with increasingly poor initial guesses...")
    
    # Use first test case
    input_file, truth_file = test_cases[0]
    triple = load_detections(input_file)
    
    # Get baseline initial guess
    base_guess = get_initial_guess_ellipse_method(triple)
    
    print(f"\n{'Position Offset (km)':>20} {'Converged':>10} {'Error (m)':>10}")
    print("-" * 45)
    
    # Test with different position offsets
    for offset_km in [0, 5, 10, 20, 30, 40, 50]:
        # Add offset to initial guess
        modified_guess = base_guess.copy()
        modified_guess[0] += offset_km * 1000  # Add offset in meters
        
        # Solve
        solution = solve_position_velocity_3d(triple, modified_guess)
        
        if solution:
            print(f"{offset_km:>20} {'✓':>10} {solution['convergence_metric']:>10.1f}")
        else:
            print(f"{offset_km:>20} {'✗':>10} {'N/A':>10}")


def analyze_altitude_distribution(results):
    """Analyze performance across different altitudes"""
    print("\n=== ALTITUDE PERFORMANCE ANALYSIS ===")
    
    # Group by altitude ranges
    altitude_bins = {
        "0-5km": [],
        "5-10km": [],
        "10-20km": [],
        "20-30km": []
    }
    
    for r in results:
        if r["success"] and "true_altitude" in r:
            alt_km = r["true_altitude"] / 1000
            if alt_km < 5:
                altitude_bins["0-5km"].append(r)
            elif alt_km < 10:
                altitude_bins["5-10km"].append(r)
            elif alt_km < 20:
                altitude_bins["10-20km"].append(r)
            else:
                altitude_bins["20-30km"].append(r)
    
    print(f"\n{'Altitude Range':>15} {'Cases':>8} {'Conv %':>8} {'Pos Err (m)':>12} {'Vel Err (m/s)':>14}")
    print("-" * 65)
    
    for range_name, cases in altitude_bins.items():
        if cases:
            converged = sum(1 for c in cases if c.get("converged", False))
            conv_rate = converged / len(cases) * 100
            
            # Stats for converged cases
            conv_cases = [c for c in cases if c.get("converged", False)]
            if conv_cases:
                avg_pos = np.mean([c["position_error_3d"] for c in conv_cases])
                avg_vel = np.mean([c["velocity_error"] for c in conv_cases])
                print(f"{range_name:>15} {len(cases):>8} {conv_rate:>7.0f}% {avg_pos:>12.1f} {avg_vel:>14.1f}")
            else:
                print(f"{range_name:>15} {len(cases):>8} {conv_rate:>7.0f}% {'N/A':>12} {'N/A':>14}")


def main():
    print("=== FINAL 3-DETECTION SYSTEM VALIDATION ===")
    print("Testing with 20 fresh cases with proper Doppler calculation\n")
    
    # Find test cases
    test_dir = "test_3detections_final"
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
    
    print(f"Found {len(test_cases)} test cases")
    
    # Test all cases
    results = []
    print(f"\n{'Case':>4} {'Conv':>6} {'Pos(m)':>8} {'Alt(m)':>8} {'Vel(m/s)':>10} {'Time(s)':>8} {'Target Alt(km)':>15}")
    print("-" * 75)
    
    total_time = 0
    for i, (input_file, truth_file) in enumerate(test_cases):
        case_num = i + 1
        result = test_case_detailed(input_file, truth_file)
        results.append(result)
        total_time += result.get("solve_time", 0)
        
        if result["success"]:
            conv = "✓" if result.get("converged", False) else "✗"
            pos_err = result["position_error_3d"]
            alt_err = result["altitude_error"]
            vel_err = result["velocity_error"]
            solve_time = result["solve_time"]
            true_alt = result["true_altitude"] / 1000
            print(f"{case_num:>4} {conv:>6} {pos_err:>8.1f} {alt_err:>8.1f} {vel_err:>10.1f} {solve_time:>8.2f} {true_alt:>15.1f}")
        else:
            print(f"{case_num:>4} {'ERR':>6} {'N/A':>8} {'N/A':>8} {'N/A':>10} {result['solve_time']:>8.2f} {'N/A':>15}")
    
    # Summary statistics
    successful = [r for r in results if r.get("success", False)]
    converged = [r for r in successful if r.get("converged", False)]
    
    print(f"\n{'='*75}")
    print("OVERALL PERFORMANCE:")
    print(f"  Total cases: {len(results)}")
    print(f"  Successful runs: {len(successful)} ({len(successful)/len(results)*100:.0f}%)")
    print(f"  Converged: {len(converged)} ({len(converged)/len(results)*100:.0f}%)")
    print(f"  Average solve time: {total_time/len(results):.2f} seconds")
    
    if converged:
        # Position accuracy
        pos_errors = [r["position_error_3d"] for r in converged]
        alt_errors = [r["altitude_error"] for r in converged]
        print(f"\nPOSITION ACCURACY (converged cases):")
        print(f"  Horizontal+Vertical error: {np.mean(pos_errors):.2f} ± {np.std(pos_errors):.2f} m")
        print(f"  Altitude error: {np.mean(alt_errors):.2f} ± {np.std(alt_errors):.2f} m")
        print(f"  Max position error: {np.max(pos_errors):.2f} m")
        
        # Velocity accuracy
        vel_errors = [r["velocity_error"] for r in converged]
        print(f"\nVELOCITY ACCURACY (converged cases):")
        print(f"  Total error: {np.mean(vel_errors):.2f} ± {np.std(vel_errors):.2f} m/s")
        print(f"  Max velocity error: {np.max(vel_errors):.2f} m/s")
        
        # Component analysis
        east_errors = [r["velocity_components"]["east"] for r in converged]
        north_errors = [r["velocity_components"]["north"] for r in converged]
        up_errors = [r["velocity_components"]["up"] for r in converged]
        print(f"\n  Component errors (mean ± std):")
        print(f"    East:  {np.mean(east_errors):>6.2f} ± {np.std(east_errors):>5.2f} m/s")
        print(f"    North: {np.mean(north_errors):>6.2f} ± {np.std(north_errors):>5.2f} m/s")
        print(f"    Up:    {np.mean(up_errors):>6.2f} ± {np.std(up_errors):>5.2f} m/s")
        
        # Residuals
        range_residuals = [r["max_range_residual"] for r in converged]
        doppler_residuals = [r["max_doppler_residual"] for r in converged]
        print(f"\nRESDIUALS:")
        print(f"  Max range residual: {np.max(range_residuals):.2e} m")
        print(f"  Max Doppler residual: {np.max(doppler_residuals):.2e} Hz")
    
    # Additional analyses
    test_initial_guess_impact(test_cases)
    analyze_altitude_distribution(results)
    
    # Final verdict
    print(f"\n{'='*75}")
    print("FINAL VERDICT:")
    conv_rate = len(converged) / len(results) * 100 if results else 0
    
    if conv_rate >= 95 and converged:
        avg_pos = np.mean([r["position_error_3d"] for r in converged])
        avg_vel = np.mean([r["velocity_error"] for r in converged])
        
        if avg_pos < 1.0 and avg_vel < 1.0:
            print("✅ EXCEPTIONAL: System achieves sub-meter position and velocity accuracy!")
        elif avg_pos < 10.0 and avg_vel < 10.0:
            print("✅ EXCELLENT: System meets high precision requirements")
        else:
            print("✅ GOOD: System performs well with room for improvement")
    elif conv_rate >= 80:
        print("⚠️  ACCEPTABLE: Good convergence rate but not robust enough")
    else:
        print("❌ NEEDS WORK: Convergence rate too low for production use")
    
    print(f"\nKey metrics:")
    print(f"  - {conv_rate:.0f}% convergence rate")
    if converged:
        print(f"  - {np.mean([r['position_error_3d'] for r in converged]):.2f}m average position error")
        print(f"  - {np.mean([r['velocity_error'] for r in converged]):.2f} m/s average velocity error")


if __name__ == "__main__":
    main()