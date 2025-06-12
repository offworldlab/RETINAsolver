#!/usr/bin/env python3
"""
Test the 3-detection system with fixed Doppler calculation
"""

import json
import numpy as np
import subprocess
import sys
import glob
import os


def test_case(input_file, truth_file):
    """Test a single case and return detailed results"""
    try:
        # Run solver
        result = subprocess.run(
            [sys.executable, "TelemetrySolver/main_3det.py", input_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Solver failed: {result.stderr}"
            }
        
        # Parse solution
        solution = json.loads(result.stdout)
        
        # Load truth
        with open(truth_file, 'r') as f:
            truth = json.load(f)
        
        if "error" in solution:
            return {
                "success": False,
                "error": f"Solver error: {solution['error']}"
            }
        
        # Calculate errors
        lat_error = abs(solution["latitude"] - truth["latitude"]) * 111111.0
        lon_diff = solution["longitude"] - truth["longitude"]
        if lon_diff > 180:
            lon_diff -= 360
        elif lon_diff < -180:
            lon_diff += 360
        lon_error = abs(lon_diff) * 111111.0 * np.cos(np.radians(truth["latitude"]))
        alt_error = abs(solution["altitude"] - truth["altitude"])
        
        position_error_3d = np.sqrt(lat_error**2 + lon_error**2 + alt_error**2)
        
        # Velocity errors
        vel_east_error = solution["velocity_east"] - truth["velocity_east"]
        vel_north_error = solution["velocity_north"] - truth["velocity_north"]
        vel_up_error = solution["velocity_up"] - truth["velocity_up"]
        velocity_error = np.sqrt(vel_east_error**2 + vel_north_error**2 + vel_up_error**2)
        
        return {
            "success": True,
            "position_error_3d": position_error_3d,
            "velocity_error": velocity_error,
            "velocity_components": {
                "east_error": vel_east_error,
                "north_error": vel_north_error,
                "up_error": vel_up_error
            },
            "convergence_metric": solution.get("convergence_metric", 0),
            "converged": position_error_3d < 200.0
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def main():
    print("=== TESTING 3-DETECTION SYSTEM WITH FIXED DOPPLER ===\\n")
    
    # Find test cases
    test_dir = "test_3detections_fixed"
    input_files = sorted(glob.glob(f"{test_dir}/3det_case_*_input.json"))
    
    if not input_files:
        print("No test cases found!")
        return
    
    results = []
    converged_count = 0
    
    print(f"{'Case':>4} {'Status':>10} {'Pos Error (m)':>15} {'Vel Error (m/s)':>15} {'E/N/U Vel Errors':>30}")
    print("-" * 90)
    
    for input_file in input_files:
        case_num = int(input_file.split('_')[-2])
        truth_file = input_file.replace('_input.json', '_truth.json')
        
        result = test_case(input_file, truth_file)
        results.append(result)
        
        if result["success"] and result.get("converged", False):
            converged_count += 1
            pos_err = result["position_error_3d"]
            vel_err = result["velocity_error"]
            vel_components = result["velocity_components"]
            status = "✅ SUCCESS"
            vel_str = f"({vel_components['east_error']:6.1f}, {vel_components['north_error']:6.1f}, {vel_components['up_error']:6.1f})"
            print(f"{case_num:>4} {status:>10} {pos_err:>15.1f} {vel_err:>15.1f} {vel_str:>30}")
        else:
            if result["success"]:
                status = "❌ FAILED"
                pos_err = result.get("position_error_3d", 0)
                print(f"{case_num:>4} {status:>10} {pos_err:>15.0f} {'N/A':>15} {'N/A':>30}")
            else:
                status = "❌ ERROR"
                error = result.get("error", "Unknown")[:20]
                print(f"{case_num:>4} {status:>10} {'N/A':>15} {'N/A':>15} {error:>30}")
    
    # Summary
    print(f"\\n{'='*90}")
    print(f"SUMMARY:")
    print(f"  Total cases: {len(results)}")
    print(f"  Converged: {converged_count} ({converged_count/len(results)*100:.0f}%)")
    
    # Statistics for successful cases
    successful = [r for r in results if r.get("success", False) and r.get("converged", False)]
    if successful:
        pos_errors = [r["position_error_3d"] for r in successful]
        vel_errors = [r["velocity_error"] for r in successful]
        
        print(f"\\n  SUCCESSFUL CASES:")
        print(f"    Position error: {np.mean(pos_errors):.1f} ± {np.std(pos_errors):.1f} m (mean ± std)")
        print(f"    Velocity error: {np.mean(vel_errors):.1f} ± {np.std(vel_errors):.1f} m/s")
        
        # Check if velocity improved
        if np.mean(vel_errors) < 50:
            print(f"\\n✅ DOPPLER FIX SUCCESSFUL!")
            print(f"   Velocity errors reduced from 100-700 m/s to {np.mean(vel_errors):.0f} m/s average")
        else:
            print(f"\\n⚠️  Velocity errors still high: {np.mean(vel_errors):.0f} m/s average")
    
    print(f"\\nCOMPARISON:")
    print(f"  Before fix: 100% convergence, 328 m/s avg velocity error")
    print(f"  After fix: {converged_count/len(results)*100:.0f}% convergence, ", end="")
    if successful:
        print(f"{np.mean(vel_errors):.0f} m/s avg velocity error")
    else:
        print("N/A")


if __name__ == "__main__":
    main()