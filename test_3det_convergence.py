#!/usr/bin/env python3
"""
Test convergence rate of 3-detection system with ellipse-based initial guess
"""

import json
import numpy as np
import subprocess
import sys
import glob
import os


def test_case(input_file, truth_file):
    """Test a single case and return results"""
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
                "error": f"Solver failed with return code {result.returncode}",
                "stderr": result.stderr
            }
        
        # Parse solver output
        try:
            solution = json.loads(result.stdout)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Failed to parse solver output",
                "stdout": result.stdout
            }
        
        # Load ground truth
        with open(truth_file, 'r') as f:
            truth = json.load(f)
        
        # Check if solver converged
        if "error" in solution:
            return {
                "success": False,
                "error": f"Solver error: {solution['error']}"
            }
        
        # Calculate errors (handle longitude wraparound)
        lat_error = abs(solution["latitude"] - truth["latitude"]) * 111111.0
        lon_diff = solution["longitude"] - truth["longitude"]
        if lon_diff > 180:
            lon_diff -= 360
        elif lon_diff < -180:
            lon_diff += 360
        lon_error = abs(lon_diff) * 111111.0 * np.cos(np.radians(truth["latitude"]))
        position_error_m = np.sqrt(lat_error**2 + lon_error**2)
        alt_error = abs(solution["altitude"] - truth["altitude"])
        
        # 3D position error
        position_error_3d = np.sqrt(lat_error**2 + lon_error**2 + alt_error**2)
        
        # Velocity errors
        vel_east_error = abs(solution["velocity_east"] - truth["velocity_east"])
        vel_north_error = abs(solution["velocity_north"] - truth["velocity_north"])
        vel_up_error = abs(solution["velocity_up"] - truth["velocity_up"])
        velocity_error = np.sqrt(vel_east_error**2 + vel_north_error**2 + vel_up_error**2)
        
        return {
            "success": True,
            "position_error_m": position_error_m,
            "position_error_3d": position_error_3d,
            "altitude_error": alt_error,
            "velocity_error_m_s": velocity_error,
            "convergence_metric": solution["convergence_metric"],
            "converged": bool(position_error_3d < 200.0)
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
    print("=== 3-DETECTION CONVERGENCE RATE TEST ===\\n")
    
    # Find all test cases
    input_files = glob.glob("test_3detections_new/3det_case_*_input.json")
    input_files.sort()
    
    if not input_files:
        print("No test cases found!")
        return
    
    results = []
    successful_cases = []
    failed_cases = []
    
    print(f"{'Case':>4} {'Status':>10} {'Pos Error (m)':>15} {'Alt Error (m)':>15} {'Vel Error (m/s)':>15} {'Notes':>20}")
    print("-" * 100)
    
    for input_file in input_files:
        case_num = int(input_file.split('_')[-2])
        truth_file = input_file.replace('_input.json', '_truth.json')
        
        if not os.path.exists(truth_file):
            print(f"{case_num:>4} {'❌ ERROR':>10} {'N/A':>15} {'N/A':>15} {'N/A':>15} {'No truth file':>20}")
            continue
        
        result = test_case(input_file, truth_file)
        results.append(result)
        
        if result["success"] and result.get("converged", False):
            successful_cases.append(case_num)
            pos_error = result["position_error_m"]
            alt_error = result["altitude_error"]
            vel_error = result["velocity_error_m_s"]
            status = "✅ SUCCESS"
            notes = f"Conv: {result['convergence_metric']:.1e}m"
            print(f"{case_num:>4} {status:>10} {pos_error:>15.1f} {alt_error:>15.1f} {vel_error:>15.1f} {notes:>20}")
        else:
            failed_cases.append(case_num)
            if result["success"]:
                pos_error = result.get("position_error_m", 0)
                alt_error = result.get("altitude_error", 0)
                vel_error = result.get("velocity_error_m_s", 0)
                status = "❌ FAILED"
                notes = "Did not converge"
                print(f"{case_num:>4} {status:>10} {pos_error:>15.0f} {alt_error:>15.0f} {vel_error:>15.1f} {notes:>20}")
            else:
                error = result.get("error", "Unknown error")
                print(f"{case_num:>4} {'❌ ERROR':>10} {'N/A':>15} {'N/A':>15} {'N/A':>15} {error[:20]:>20}")
    
    # Summary statistics
    print(f"\\n{'='*100}")
    print(f"CONVERGENCE SUMMARY:")
    print(f"  Total test cases: {len(results)}")
    print(f"  Successful cases: {len(successful_cases)} ({len(successful_cases)/len(results)*100:.0f}%)")
    print(f"  Failed cases: {len(failed_cases)} ({len(failed_cases)/len(results)*100:.0f}%)")
    
    if successful_cases:
        print(f"  Successful case numbers: {successful_cases}")
        
        # Calculate statistics for successful cases
        successful_results = [r for r in results if r.get("success", False) and r.get("converged", False)]
        if successful_results:
            pos_errors = [r["position_error_m"] for r in successful_results]
            alt_errors = [r["altitude_error"] for r in successful_results]
            vel_errors = [r["velocity_error_m_s"] for r in successful_results]
            
            print(f"\\n  SUCCESSFUL CASES STATISTICS:")
            print(f"    Position (horizontal):")
            print(f"      Mean: {np.mean(pos_errors):.1f} m")
            print(f"      Median: {np.median(pos_errors):.1f} m")
            print(f"      Max: {np.max(pos_errors):.1f} m")
            print(f"    Altitude:")
            print(f"      Mean: {np.mean(alt_errors):.1f} m")
            print(f"      Median: {np.median(alt_errors):.1f} m")
            print(f"      Max: {np.max(alt_errors):.1f} m")
            print(f"    Velocity:")
            print(f"      Mean: {np.mean(vel_errors):.1f} m/s")
            print(f"      Median: {np.median(vel_errors):.1f} m/s")
            print(f"      Max: {np.max(vel_errors):.1f} m/s")
    
    print(f"\\n{'='*100}")
    print(f"ANALYSIS:")
    
    success_rate = len(successful_cases) / len(results) * 100 if results else 0
    
    if success_rate >= 90:
        print(f"✅ EXCELLENT: {success_rate:.0f}% convergence rate")
        print(f"   3-detection system is highly reliable")
    elif success_rate >= 70:
        print(f"✅ GOOD: {success_rate:.0f}% convergence rate")
        print(f"   3-detection system significantly improves on 2-detection")
    elif success_rate >= 50:
        print(f"⚠️  MODERATE: {success_rate:.0f}% convergence rate")
        print(f"   3-detection system shows improvement but needs refinement")
    else:
        print(f"❌ POOR: {success_rate:.0f}% convergence rate")
        print(f"   3-detection system needs algorithm improvements")
    
    print(f"\\nCOMPARISON TO 2-DETECTION:")
    print(f"  2-detection (original): 10% success rate")
    print(f"  2-detection (optimized): 40% success rate")
    print(f"  3-detection: {success_rate:.0f}% success rate")


if __name__ == "__main__":
    main()