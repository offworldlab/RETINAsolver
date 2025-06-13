"""
Main program for 3-detection telemetry solver
"""
import sys
import json
import argparse
from typing import Dict

from detection_triple import load_detections
from initial_guess_3det import get_initial_guess
from lm_solver_3det import solve_position_velocity_3d


def main():
    """Main entry point"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='3-Detection telemetry solver for bistatic passive radar')
    parser.add_argument('input_file', help='JSON file containing 3 detection data')
    args = parser.parse_args()
    
    try:
        # Load detections
        detection_triple = load_detections(args.input_file)
        
        # Get initial guess (6D) - use provided guess if available, otherwise generate one
        provided_guess = detection_triple.get_initial_guess_enu()
        if provided_guess is not None:
            initial_guess = provided_guess
            print(f"Using provided initial guess: pos=({initial_guess[0]:.1f}, {initial_guess[1]:.1f}, {initial_guess[2]:.1f}) vel=({initial_guess[3]:.1f}, {initial_guess[4]:.1f}, {initial_guess[5]:.1f})", file=sys.stderr)
        else:
            initial_guess = get_initial_guess(detection_triple)
            print(f"Using generated initial guess: pos=({initial_guess[0]:.1f}, {initial_guess[1]:.1f}, {initial_guess[2]:.1f}) vel=({initial_guess[3]:.1f}, {initial_guess[4]:.1f}, {initial_guess[5]:.1f})", file=sys.stderr)
        
        # Solve for position and velocity
        solution = solve_position_velocity_3d(detection_triple, initial_guess)
        
        if solution is None:
            # No convergence
            output = {"error": "No Solution"}
        else:
            # Format output
            output = {
                "timestamp": detection_triple.detection1.timestamp,
                "latitude": solution['lat'],
                "longitude": solution['lon'],
                "altitude": solution['alt'],
                "velocity_east": solution['velocity_east'],
                "velocity_north": solution['velocity_north'],
                "velocity_up": solution['velocity_up'],
                "convergence_metric": solution['convergence_metric'],
                "residuals": solution['residuals']
            }
        
        # Print JSON output
        print(json.dumps(output, indent=2))
        
    except Exception as e:
        # Handle errors
        error_output = {"error": str(e)}
        print(json.dumps(error_output, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()