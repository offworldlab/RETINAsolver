#!/usr/bin/env python3
"""
Analyze initial guess quality across multiple test cases
"""

import sys
sys.path.append('/Users/jehanazad/offworldlab/TelemetrySolver')

import json
import numpy as np
from detection import load_detections
from initial_guess import get_initial_guess
from Geometry import Geometry
import glob

def analyze_case(test_case_file):
    """Analyze one test case and return errors"""
    try:
        # Load detection data
        detection_pair = load_detections(test_case_file)
        
        # Load ground truth
        truth_file = test_case_file.replace('_input.json', '_truth.json')
        with open(truth_file, 'r') as f:
            truth = json.load(f)
        
        # Get ENU origin
        origin_lat, origin_lon, origin_alt = detection_pair.get_enu_origin()
        
        # Convert ground truth to ENU
        truth_ecef = Geometry.lla2ecef(truth["latitude"], truth["longitude"], truth["altitude"])
        truth_enu = Geometry.ecef2enu(truth_ecef[0], truth_ecef[1], truth_ecef[2],
                                      origin_lat, origin_lon, origin_alt)
        
        truth_state = [truth_enu[0], truth_enu[1], truth["velocity_east"], truth["velocity_north"]]
        
        # Get initial guess
        initial_guess = get_initial_guess(detection_pair)
        
        # Calculate errors
        position_error = np.sqrt((initial_guess[0] - truth_state[0])**2 + 
                                (initial_guess[1] - truth_state[1])**2)
        velocity_error = np.sqrt((initial_guess[2] - truth_state[2])**2 + 
                                (initial_guess[3] - truth_state[3])**2)
        
        return position_error, velocity_error, True
        
    except Exception as e:
        print(f"Error analyzing {test_case_file}: {e}")
        return None, None, False

def main():
    print("=== INITIAL GUESS QUALITY ACROSS ALL TEST CASES ===\n")
    
    # Find all test case input files
    test_files = glob.glob("/Users/jehanazad/offworldlab/test_detections/test_case_*_input.json")
    test_files.sort()
    
    results = []
    
    print(f"{'Case':>6} {'Pos Error (km)':>15} {'Vel Error (m/s)':>15} {'Status':>10}")
    print("-" * 60)
    
    for test_file in test_files:
        case_num = test_file.split('_')[-2]  # Extract case number
        pos_err, vel_err, success = analyze_case(test_file)
        
        if success:
            results.append((pos_err, vel_err))
            status = "✅" if pos_err < 20000 else "❌"
            print(f"{case_num:>6} {pos_err/1000:>15.1f} {vel_err:>15.1f} {status:>10}")
        else:
            print(f"{case_num:>6} {'ERROR':>15} {'ERROR':>15} {'❌':>10}")
    
    if results:
        pos_errors = [r[0] for r in results]
        vel_errors = [r[1] for r in results]
        
        print(f"\n{'='*60}")
        print(f"SUMMARY STATISTICS:")
        print(f"  Cases analyzed: {len(results)}")
        print(f"  Position errors:")
        print(f"    Mean: {np.mean(pos_errors)/1000:.1f} km")
        print(f"    Median: {np.median(pos_errors)/1000:.1f} km")
        print(f"    Min: {np.min(pos_errors)/1000:.1f} km")
        print(f"    Max: {np.max(pos_errors)/1000:.1f} km")
        print(f"  Velocity errors:")
        print(f"    Mean: {np.mean(vel_errors):.1f} m/s")
        print(f"    Median: {np.median(vel_errors):.1f} m/s")
        print(f"    Min: {np.min(vel_errors):.1f} m/s")
        print(f"    Max: {np.max(vel_errors):.1f} m/s")
        
        # Classification
        good_pos = sum(1 for p in pos_errors if p < 5000)
        fair_pos = sum(1 for p in pos_errors if 5000 <= p < 20000)
        poor_pos = sum(1 for p in pos_errors if p >= 20000)
        
        print(f"\n  Position guess quality:")
        print(f"    Good (<5km): {good_pos}/{len(results)} ({100*good_pos/len(results):.0f}%)")
        print(f"    Fair (5-20km): {fair_pos}/{len(results)} ({100*fair_pos/len(results):.0f}%)")
        print(f"    Poor (>20km): {poor_pos}/{len(results)} ({100*poor_pos/len(results):.0f}%)")
        
        print(f"\n  CONCLUSION:")
        if np.mean(pos_errors) > 50000:
            print(f"  ❌ Initial guess algorithm is POOR - average {np.mean(pos_errors)/1000:.0f}km from truth")
            print(f"  🔧 RECOMMENDATION: Improve initial guess using range measurements")
        elif np.mean(pos_errors) > 20000:
            print(f"  ⚠️  Initial guess algorithm is FAIR - average {np.mean(pos_errors)/1000:.0f}km from truth")
            print(f"  🔧 RECOMMENDATION: Consider using range information for better guess")
        else:
            print(f"  ✅ Initial guess algorithm is GOOD - average {np.mean(pos_errors)/1000:.0f}km from truth")
            
        print(f"\n  WHY THE ALGORITHM STRUGGLES:")
        print(f"  - Uses only geometric centers, ignores range measurements")
        print(f"  - Ellipse center method assumes target near sensor network")
        print(f"  - But our targets are 50-80km away from sensors!")
        print(f"  - The target is much further than the sensor baseline (1-5km)")

if __name__ == "__main__":
    main()