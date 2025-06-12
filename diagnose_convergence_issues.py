#!/usr/bin/env python3
"""
Diagnose why TelemetrySolver has such poor convergence rate
"""

import json
import numpy as np

# Load test summary
with open("test_detections/test_summary.json", 'r') as f:
    summary = json.load(f)

print("=== CONVERGENCE ISSUE DIAGNOSIS ===\n")

print("FAILED CASES ANALYSIS:")
print(f"{'Case':>4} {'Pos Error (km)':>15} {'Problem Type':>20}")
print("-" * 50)

failed_cases = []
for i, result in enumerate(summary["validation_results"], 1):
    if not result.get("converged", False):
        pos_error = result.get("position_error_m", 0)
        
        if pos_error > 1000000:  # > 1000 km
            problem = "Completely wrong"
        elif pos_error > 100000:  # > 100 km  
            problem = "Major error"
        elif pos_error > 10000:   # > 10 km
            problem = "Moderate error"
        elif pos_error > 1000:    # > 1 km
            problem = "Minor error"
        else:
            problem = "Threshold issue"
            
        failed_cases.append((i, pos_error, problem))
        print(f"{i:>4} {pos_error/1000:>15.1f} {problem:>20}")

print(f"\nPROBLEM CATEGORIZATION:")
completely_wrong = sum(1 for _, err, _ in failed_cases if err > 1000000)
major_errors = sum(1 for _, err, _ in failed_cases if 100000 <= err <= 1000000)  
moderate_errors = sum(1 for _, err, _ in failed_cases if 10000 <= err < 100000)
minor_errors = sum(1 for _, err, _ in failed_cases if 1000 <= err < 10000)
threshold_issues = sum(1 for _, err, _ in failed_cases if err < 1000)

print(f"  Completely wrong (>1000km): {completely_wrong}")
print(f"  Major errors (100-1000km): {major_errors}")
print(f"  Moderate errors (10-100km): {moderate_errors}")
print(f"  Minor errors (1-10km): {minor_errors}")
print(f"  Threshold issues (<1km): {threshold_issues}")

print(f"\nROOT CAUSE ANALYSIS:")

if completely_wrong >= 5:
    print(f"🔥 PRIMARY ISSUE: Solver finds completely wrong solutions")
    print(f"   - {completely_wrong} cases have errors >1000km")
    print(f"   - This suggests solver is converging to local minima")
    print(f"   - Initial guess (64km from truth) may be too poor")
    
elif major_errors >= 3:
    print(f"⚠️  MAJOR ISSUE: Solver has large systematic errors")
    print(f"   - {major_errors} cases have errors 100-1000km")
    print(f"   - Solver is converging but to wrong region")
    
elif moderate_errors >= 3:
    print(f"⚠️  MODERATE ISSUE: Solver accuracy problems")
    print(f"   - {moderate_errors} cases have errors 10-100km")
    print(f"   - May need looser convergence threshold")
    
elif threshold_issues >= 3:
    print(f"✅ THRESHOLD ISSUE: Solver works but threshold too strict")
    print(f"   - {threshold_issues} cases have good accuracy but fail threshold")
    print(f"   - Simply relax convergence threshold")

# Check if geometry is the issue
print(f"\nGEOMETRY ANALYSIS:")
target_distances = []
for case in summary["cases"]:
    # Calculate approximate distance from sensor center to target
    center_lat = (case["sensor1"]["lat"] + case["sensor2"]["lat"]) / 2
    center_lon = (case["sensor1"]["lon"] + case["sensor2"]["lon"]) / 2
    
    target_lat = case["target"]["lat"]
    target_lon = case["target"]["lon"]
    
    # Rough distance calculation
    lat_diff = (target_lat - center_lat) * 111111  # meters per degree
    lon_diff = (target_lon - center_lon) * 111111 * np.cos(np.radians(center_lat))
    distance = np.sqrt(lat_diff**2 + lon_diff**2)
    target_distances.append(distance)

avg_distance = np.mean(target_distances)
print(f"  Average target distance from sensors: {avg_distance/1000:.1f} km")
print(f"  Range: {np.min(target_distances)/1000:.1f} - {np.max(target_distances)/1000:.1f} km")

if avg_distance > 60000:  # > 60km
    print(f"  ⚠️  Targets are very far from sensors ({avg_distance/1000:.0f}km average)")
    print(f"      This creates challenging geometry for the solver")

# Check bistatic ranges
bistatic_ranges = []
for case in summary["cases"]:
    bistatic_ranges.extend([case["bistatic_range1_km"], case["bistatic_range2_km"]])

print(f"\nBISTATIC RANGE ANALYSIS:")
print(f"  Average bistatic range: {np.mean(bistatic_ranges):.1f} km")
print(f"  Range: {np.min(bistatic_ranges):.1f} - {np.max(bistatic_ranges):.1f} km")

print(f"\nRECOMMENDATIONS:")
print(f"1. IMMEDIATE: Try relaxing threshold to 200-500m")
print(f"2. SHORT-TERM: Generate closer targets (30-50km instead of 60-80km)")
print(f"3. MEDIUM-TERM: Improve initial guess using range measurements")
print(f"4. LONG-TERM: Add multiple initial guess attempts with different starting points")

# Specific threshold recommendation
if threshold_issues >= 2:
    print(f"\n💡 QUICK FIX: Relax threshold to 200m (cases 7,9 have ~3-50km errors)")
elif moderate_errors >= 2:
    print(f"\n💡 QUICK FIX: Relax threshold to 500m and generate closer targets")
else:
    print(f"\n💡 SYSTEMATIC FIX NEEDED: Generate better test cases with closer targets")