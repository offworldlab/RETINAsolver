"""
Test convergence of the 3-detection solver
"""
import json
import numpy as np
from detection_triple import DetectionTriple
from initial_guess_3det import get_initial_guess
from lm_solver_3det import solve_position_velocity_3d


def test_solver_convergence():
    """Test if the solver converges on synthetic data"""
    
    # Create test detection data (NYC area)
    test_data = {
        "detection1": {
            "sensor_lat": 40.7128,
            "sensor_lon": -74.0060,
            "ioo_lat": 40.7589,
            "ioo_lon": -73.9851,
            "freq_mhz": 1090.0,
            "timestamp": 1700000000,
            "bistatic_range_km": 15.5,
            "doppler_hz": 50.0
        },
        "detection2": {
            "sensor_lat": 40.6782,
            "sensor_lon": -73.9442,
            "ioo_lat": 40.7589,
            "ioo_lon": -73.9851,
            "freq_mhz": 1090.0,
            "timestamp": 1700000000,
            "bistatic_range_km": 18.2,
            "doppler_hz": 35.0
        },
        "detection3": {
            "sensor_lat": 40.7500,
            "sensor_lon": -73.9860,
            "ioo_lat": 40.7589,
            "ioo_lon": -73.9851,
            "freq_mhz": 1090.0,
            "timestamp": 1700000000,
            "bistatic_range_km": 12.8,
            "doppler_hz": 65.0
        }
    }
    
    # Parse detection data
    detection_triple = DetectionTriple.from_json(json.dumps(test_data))
    
    # Get initial guess
    print("Getting initial guess...")
    initial_guess = get_initial_guess(detection_triple)
    print(f"Initial guess: {initial_guess}")
    
    # Solve for position and velocity
    print("Running solver...")
    solution = solve_position_velocity_3d(detection_triple, initial_guess)
    
    if solution is None:
        print("❌ Solver failed to converge")
        return False
    else:
        print("✅ Solver converged!")
        print(f"Position: lat={solution['lat']:.6f}, lon={solution['lon']:.6f}, alt={solution['alt']:.1f}m")
        print(f"Velocity: E={solution['velocity_east']:.1f}, N={solution['velocity_north']:.1f}, U={solution['velocity_up']:.1f} m/s")
        print(f"Convergence metric: {solution['convergence_metric']}")
        print(f"Final residuals: {solution['residuals']}")
        return True


def run_multiple_convergence_tests():
    """Run multiple tests with different scenarios"""
    
    test_scenarios = [
        # Test 1: Close range
        {
            "name": "Close range test",
            "detection1": {"sensor_lat": 40.7128, "sensor_lon": -74.0060, "ioo_lat": 40.7589, "ioo_lon": -73.9851, "freq_mhz": 1090.0, "timestamp": 1700000000, "bistatic_range_km": 8.5, "doppler_hz": 25.0},
            "detection2": {"sensor_lat": 40.6782, "sensor_lon": -73.9442, "ioo_lat": 40.7589, "ioo_lon": -73.9851, "freq_mhz": 1090.0, "timestamp": 1700000000, "bistatic_range_km": 12.2, "doppler_hz": 15.0},
            "detection3": {"sensor_lat": 40.7500, "sensor_lon": -73.9860, "ioo_lat": 40.7589, "ioo_lon": -73.9851, "freq_mhz": 1090.0, "timestamp": 1700000000, "bistatic_range_km": 6.8, "doppler_hz": 35.0}
        },
        # Test 2: Medium range  
        {
            "name": "Medium range test",
            "detection1": {"sensor_lat": 40.7128, "sensor_lon": -74.0060, "ioo_lat": 40.7589, "ioo_lon": -73.9851, "freq_mhz": 1090.0, "timestamp": 1700000000, "bistatic_range_km": 25.5, "doppler_hz": 150.0},
            "detection2": {"sensor_lat": 40.6782, "sensor_lon": -73.9442, "ioo_lat": 40.7589, "ioo_lon": -73.9851, "freq_mhz": 1090.0, "timestamp": 1700000000, "bistatic_range_km": 28.2, "doppler_hz": 125.0},
            "detection3": {"sensor_lat": 40.7500, "sensor_lon": -73.9860, "ioo_lat": 40.7589, "ioo_lon": -73.9851, "freq_mhz": 1090.0, "timestamp": 1700000000, "bistatic_range_km": 22.8, "doppler_hz": 175.0}
        }
    ]
    
    convergence_results = []
    
    for i, scenario in enumerate(test_scenarios):
        print(f"\n{'='*50}")
        print(f"Test {i+1}: {scenario['name']}")
        print(f"{'='*50}")
        
        # Create detection triple
        detection_triple = DetectionTriple.from_json(json.dumps(scenario))
        
        try:
            # Get initial guess
            initial_guess = get_initial_guess(detection_triple)
            print(f"Initial guess: {initial_guess}")
            
            # Solve
            solution = solve_position_velocity_3d(detection_triple, initial_guess)
            
            if solution is None:
                print("❌ Failed to converge")
                convergence_results.append({"test": scenario['name'], "converged": False})
            else:
                print("✅ Converged successfully")
                print(f"Position: lat={solution['lat']:.6f}, lon={solution['lon']:.6f}, alt={solution['alt']:.1f}m")
                print(f"Velocity: E={solution['velocity_east']:.1f}, N={solution['velocity_north']:.1f}, U={solution['velocity_up']:.1f} m/s")
                print(f"Convergence metric: {solution['convergence_metric']}")
                convergence_results.append({
                    "test": scenario['name'], 
                    "converged": True,
                    "convergence_metric": solution['convergence_metric'],
                    "residuals": solution['residuals']
                })
                
        except Exception as e:
            print(f"❌ Error: {e}")
            convergence_results.append({"test": scenario['name'], "converged": False, "error": str(e)})
    
    # Summary
    print(f"\n{'='*50}")
    print("CONVERGENCE SUMMARY")
    print(f"{'='*50}")
    
    converged_count = sum(1 for r in convergence_results if r.get('converged', False))
    total_tests = len(convergence_results)
    
    print(f"Tests run: {total_tests}")
    print(f"Converged: {converged_count}")
    print(f"Failed: {total_tests - converged_count}")
    print(f"Success rate: {converged_count/total_tests*100:.1f}%")
    
    for result in convergence_results:
        status = "✅" if result.get('converged', False) else "❌"
        print(f"{status} {result['test']}")
        if result.get('converged', False) and 'convergence_metric' in result:
            print(f"   Convergence metric: {result['convergence_metric']}")
    
    return convergence_results


if __name__ == "__main__":
    run_multiple_convergence_tests()