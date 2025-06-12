#!/usr/bin/env python3
"""
Test reused geometry cases with truth-based initial guess
"""

import json
import numpy as np
import subprocess
import sys
import glob
import os

def test_case_with_truth(input_file, truth_file):
    """Test a single case with truth-based initial guess"""
    try:
        # Run solver with truth-based initial guess
        result = subprocess.run(
            [sys.executable, "TelemetrySolver/main_with_truth.py", input_file, truth_file],
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
        
        # Load ground truth for comparison
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
    print("=== TESTING REUSED GEOMETRY WITH TRUTH-BASED INITIAL GUESS ===\\n")
    
    # Find all reused geometry test case files
    input_files = glob.glob("test_detections_reused/reused_case_*_input.json")
    input_files.sort()
    
    results = []
    successful_cases = []
    failed_cases = []
    
    print(f"{'Case':>4} {'Original':>8} {'Status':>10} {'Pos Error (m)':>15} {'Vel Error (m/s)':>15} {'Notes':>20}")
    print("-" * 90)
    
    # Load mapping from reused cases to original geometries
    with open("test_detections_reused/reused_geometry_summary.json", 'r') as f:
        summary = json.load(f)
    
    case_to_original = {}
    for case in summary["cases"]:
        case_to_original[case["case_number"]] = case["original_geometry"]
    
    for input_file in input_files:
        case_num = int(input_file.split('_')[-2])  # Extract case number
        truth_file = input_file.replace('_input.json', '_truth.json')
        original_geom = case_to_original.get(case_num, "?")
        
        if not os.path.exists(truth_file):
            print(f"{case_num:>4} {original_geom:>8} {'❌ ERROR':>10} {'N/A':>15} {'N/A':>15} {'No truth file':>20}")
            continue
        
        result = test_case_with_truth(input_file, truth_file)
        results.append(result)
        
        if result["success"] and result.get("converged", False):
            successful_cases.append(case_num)
            pos_error = result["position_error_m"]
            vel_error = result["velocity_error_m_s"]
            status = "✅ SUCCESS"
            notes = "Converged"
            print(f"{case_num:>4} {original_geom:>8} {status:>10} {pos_error:>15.1f} {vel_error:>15.1f} {notes:>20}")
        else:
            failed_cases.append(case_num)
            if result["success"]:
                pos_error = result.get("position_error_m", 0)
                vel_error = result.get("velocity_error_m_s", 0)
                status = "❌ FAILED"
                if pos_error > 100000:
                    notes = "No convergence"
                else:
                    notes = f"Poor accuracy"
                print(f"{case_num:>4} {original_geom:>8} {status:>10} {pos_error:>15.0f} {vel_error:>15.1f} {notes:>20}")
            else:
                error = result.get("error", "Unknown error")
                print(f"{case_num:>4} {original_geom:>8} {'❌ ERROR':>10} {'N/A':>15} {'N/A':>15} {error[:20]:>20}")
    
    print(f"\\n{'='*90}")
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
            vel_errors = [r["velocity_error_m_s"] for r in successful_results]
            
            print(f"\\n  SUCCESSFUL CASES STATISTICS:")
            print(f"    Average position error: {sum(pos_errors)/len(pos_errors):.1f} m")
            print(f"    Average velocity error: {sum(vel_errors)/len(vel_errors):.1f} m/s")
            
            # Analyze by original geometry
            successful_by_geom = {}
            for case_num in successful_cases:
                orig_geom = case_to_original.get(case_num, "?")
                if orig_geom not in successful_by_geom:
                    successful_by_geom[orig_geom] = []
                successful_by_geom[orig_geom].append(case_num)
            
            print(f"\\n  SUCCESS BY ORIGINAL GEOMETRY:")
            for orig_geom, cases in successful_by_geom.items():
                print(f"    Original case {orig_geom}: {len(cases)} successful reused cases")
    
    if failed_cases:
        print(f"  Failed case numbers: {failed_cases}")
    
    print(f"\\n{'='*90}")
    print(f"ANALYSIS:")
    
    success_rate = len(successful_cases) / len(results) * 100 if results else 0
    
    print(f"\\nCOMPARISON:")
    print(f"  Reused geometry (standard guess): 20% success rate")
    print(f"  Reused geometry (truth guess): {success_rate:.0f}% success rate")
    print(f"  Original data (standard guess): 40% success rate")
    print(f"  Original data (truth guess): 50% success rate")
    
    if success_rate > 50:
        print(f"\\n✅ CONCLUSION: Reused geometries with truth guess work better than original")
        print(f"   This suggests target placement is more important than sensor geometry")
    elif success_rate > 20:
        print(f"\\n⚠️  CONCLUSION: Truth-based guess helps reused geometries but not as much")
        print(f"   Some sensor geometries may be inherently better than others")
    else:
        print(f"\\n❌ CONCLUSION: Even truth-based guess doesn't help reused geometries much")
        print(f"   This suggests fundamental solver issues with certain geometries")

if __name__ == "__main__":
    main()