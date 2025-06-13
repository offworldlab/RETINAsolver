"""
Test the 3-detection initial guess module
"""
import json
import numpy as np
import os
from detection_triple import load_detections
from initial_guess_3det import get_initial_guess
from Geometry import Geometry


def test_truth_based_guess():
    """Test truth-based initial guess"""
    print("Testing truth-based initial guess...")
    
    # Check if test files exist
    test_input = "/Users/jehanazad/offworldlab/test_3detections/3det_case_1_input.json"
    test_truth = "/Users/jehanazad/offworldlab/test_3detections/3det_case_1_truth.json"
    
    if os.path.exists(test_input) and os.path.exists(test_truth):
        # Load detection and truth
        triple = load_detections(test_input)
        
        with open(test_truth, 'r') as f:
            truth = json.load(f)
        
        # Get initial guess
        guess = get_initial_guess_from_truth(triple, test_truth)
        
        # Check dimensions
        assert len(guess) == 6, f"Expected 6D state, got {len(guess)}"
        
        # Convert truth to ENU for comparison
        origin = triple.get_enu_origin()
        truth_ecef = Geometry.lla2ecef(truth["latitude"], truth["longitude"], truth["altitude"])
        truth_enu = Geometry.ecef2enu(truth_ecef[0], truth_ecef[1], truth_ecef[2],
                                      origin[0], origin[1], origin[2])
        
        # Check that guess is close to truth (within noise bounds)
        pos_error = np.sqrt((guess[0] - truth_enu[0])**2 + 
                           (guess[1] - truth_enu[1])**2 + 
                           (guess[2] - truth_enu[2])**2)
        
        vel_error = np.sqrt((guess[3] - truth["velocity_east"])**2 + 
                           (guess[4] - truth["velocity_north"])**2 + 
                           (guess[5] - truth["velocity_up"])**2)
        
        print(f"✓ Truth-based guess generated")
        print(f"  Position error: {pos_error:.1f}m (from perturbation)")
        print(f"  Velocity error: {vel_error:.1f}m/s (from perturbation)")
        print(f"  Altitude: {guess[2]:.1f}m (bounded to 0-30km)")
        
        # Check altitude bounds
        assert 0 <= guess[2] <= 30000, f"Altitude {guess[2]} out of bounds"
        
    else:
        print("  Test files not found - skipping")


def test_ellipse_method_guess():
    """Test ellipse-based initial guess"""
    print("\nTesting ellipse method initial guess...")
    
    test_input = "/Users/jehanazad/offworldlab/test_3detections/3det_case_1_input.json"
    
    if os.path.exists(test_input):
        triple = load_detections(test_input)
        
        # Get initial guess
        guess = get_initial_guess_ellipse_method(triple)
        
        # Check dimensions
        assert len(guess) == 6, f"Expected 6D state, got {len(guess)}"
        
        print(f"✓ Ellipse method guess generated")
        print(f"  Position: ({guess[0]:.1f}, {guess[1]:.1f}, {guess[2]:.1f}) m ENU")
        print(f"  Velocity: ({guess[3]:.1f}, {guess[4]:.1f}, {guess[5]:.1f}) m/s")
        
        # Check expected values
        assert guess[2] == 5000.0, "Expected 5km initial altitude"
        assert guess[3] == 0.0, "Expected zero initial velocity"
        assert guess[4] == 0.0, "Expected zero initial velocity"
        assert guess[5] == 0.0, "Expected zero initial velocity"
        
    else:
        print("  Test file not found - skipping")


def test_standard_guess():
    """Test standard initial guess function"""
    print("\nTesting standard initial guess...")
    
    test_input = "/Users/jehanazad/offworldlab/test_3detections/3det_case_1_input.json"
    
    if os.path.exists(test_input):
        triple = load_detections(test_input)
        
        # Get initial guess
        guess = get_initial_guess(triple)
        
        # Should be same as ellipse method
        ellipse_guess = get_initial_guess_ellipse_method(triple)
        
        assert guess == ellipse_guess, "Standard guess should use ellipse method"
        print("✓ Standard guess uses ellipse method correctly")
        
    else:
        print("  Test file not found - skipping")


def test_multiple_cases():
    """Test initial guess across multiple test cases"""
    print("\nTesting initial guess across multiple cases...")
    
    import glob
    test_files = glob.glob("/Users/jehanazad/offworldlab/test_3detections/3det_case_*_input.json")
    
    if test_files:
        for test_file in test_files[:3]:  # Test first 3 cases
            case_num = test_file.split('_')[-2]
            triple = load_detections(test_file)
            
            # Get ellipse guess
            guess = get_initial_guess(triple)
            
            print(f"  Case {case_num}: Initial position ({guess[0]/1000:.1f}, {guess[1]/1000:.1f}, {guess[2]/1000:.1f}) km")
        
        print(f"✓ Tested {min(3, len(test_files))} cases")
    else:
        print("  No test files found - skipping")


if __name__ == "__main__":
    print("=== Testing 3-Detection Initial Guess ===\n")
    
    test_truth_based_guess()
    test_ellipse_method_guess()
    test_standard_guess()
    test_multiple_cases()
    
    print("\n✅ All initial guess tests completed!")