#!/usr/bin/env python3
"""
Check the actual convergence rate of TelemetrySolver
"""

import json

# Load the test summary
with open("test_detections/test_summary.json", 'r') as f:
    summary = json.load(f)

print("=== TELEMETRYSOLVER CONVERGENCE ANALYSIS ===\n")

total_cases = len(summary["validation_results"])
successful_cases = []
failed_cases = []

print(f"{'Case':>4} {'Status':>10} {'Pos Error (m)':>15} {'Vel Error (m/s)':>15} {'Notes':>20}")
print("-" * 80)

for i, result in enumerate(summary["validation_results"], 1):
    if result["success"]:
        pos_error = result["position_error_m"]
        vel_error = result["velocity_error_m_s"]
        converged = result.get("converged", False)
        
        if converged:
            successful_cases.append(i)
            status = "✅ SUCCESS"
            notes = "Converged"
        else:
            failed_cases.append(i)
            status = "❌ FAILED"
            if pos_error > 100000:
                notes = "No convergence"
            else:
                notes = f"Poor accuracy"
        
        print(f"{i:>4} {status:>10} {pos_error:>15.0f} {vel_error:>15.1f} {notes:>20}")
    else:
        failed_cases.append(i)
        error = result.get("error", "Unknown error")
        print(f"{i:>4} {'❌ ERROR':>10} {'N/A':>15} {'N/A':>15} {error[:20]:>20}")

print(f"\n{'='*80}")
print(f"CONVERGENCE SUMMARY:")
print(f"  Total test cases: {total_cases}")
print(f"  Successful cases: {len(successful_cases)} ({len(successful_cases)/total_cases*100:.0f}%)")
print(f"  Failed cases: {len(failed_cases)} ({len(failed_cases)/total_cases*100:.0f}%)")

if successful_cases:
    print(f"  Successful case numbers: {successful_cases}")
    
    # Calculate statistics for successful cases
    successful_results = [summary["validation_results"][i-1] for i in successful_cases]
    pos_errors = [r["position_error_m"] for r in successful_results]
    vel_errors = [r["velocity_error_m_s"] for r in successful_results]
    
    print(f"\n  SUCCESSFUL CASES STATISTICS:")
    print(f"    Average position error: {sum(pos_errors)/len(pos_errors):.1f} m")
    print(f"    Average velocity error: {sum(vel_errors)/len(vel_errors):.1f} m/s")

if failed_cases:
    print(f"  Failed case numbers: {failed_cases}")

print(f"\n{'='*80}")
print(f"ANALYSIS:")

if len(successful_cases) == 1:
    print(f"❌ SEVERE ISSUE: Only 1 out of {total_cases} cases converging (10% success rate)")
    print(f"   This indicates a fundamental problem with:")
    print(f"   - Test case geometry (targets too far from sensors?)")
    print(f"   - Solver convergence threshold (75m might still be too strict)")
    print(f"   - Initial guess quality (64km average error)")
    print(f"   - Measurement noise/precision")
elif len(successful_cases) < total_cases // 2:
    print(f"⚠️  LOW SUCCESS RATE: {len(successful_cases)}/{total_cases} cases converging")
    print(f"   Consider adjusting solver parameters or test case generation")
else:
    print(f"✅ GOOD SUCCESS RATE: {len(successful_cases)}/{total_cases} cases converging")

print(f"\nRECOMMENDATIONS:")
print(f"1. Try relaxing convergence threshold to 100-200m")
print(f"2. Generate test cases with targets closer to sensors (20-40km instead of 50-80km)")
print(f"3. Improve initial guess algorithm using range measurements")
print(f"4. Check if there are numerical precision issues in the solver")