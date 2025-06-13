"""
Integration tests for telemetry solver
"""
import json
import tempfile
import subprocess
import os

from detection import DetectionPair, load_detections
from initial_guess import get_initial_guess
from lm_solver import solve_position_velocity


def test_end_to_end_valid():
    """Test complete pipeline with valid data"""
    # Create test data
    test_data = {
        "detection1": {
            "sensor_lat": 40.0,
            "sensor_lon": -74.0,
            "ioo_lat": 40.5,
            "ioo_lon": -73.5,
            "freq_mhz": 100.0,
            "timestamp": 1234567890,
            "bistatic_range_km": 100.0,
            "doppler_hz": -50.0
        },
        "detection2": {
            "sensor_lat": 41.0,
            "sensor_lon": -73.0,
            "ioo_lat": 40.5,
            "ioo_lon": -73.5,
            "freq_mhz": 100.0,
            "timestamp": 1234567890,
            "bistatic_range_km": 110.0,
            "doppler_hz": 30.0
        }
    }
    
    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_data, f)
        temp_file = f.name
    
    try:
        # Load and process
        detection_pair = load_detections(temp_file)
        initial = get_initial_guess(detection_pair)
        solution = solve_position_velocity(detection_pair, initial)
        
        # Check we got a solution
        assert solution is not None
        assert 'lat' in solution
        assert 'velocity_east' in solution
        
        print(f"✓ End-to-end test passed: lat={solution['lat']:.4f}, lon={solution['lon']:.4f}")
        
    finally:
        os.unlink(temp_file)


def test_command_line_interface():
    """Test CLI with valid data"""
    test_data = {
        "detection1": {
            "sensor_lat": 40.7128,
            "sensor_lon": -74.0060,
            "ioo_lat": 40.6892,
            "ioo_lon": -74.0445,
            "freq_mhz": 98.7,
            "timestamp": 1234567890123,
            "bistatic_range_km": 50.0,
            "doppler_hz": -20.0
        },
        "detection2": {
            "sensor_lat": 40.7580,
            "sensor_lon": -73.9855,
            "ioo_lat": 40.7489,
            "ioo_lon": -73.9680,
            "freq_mhz": 101.9,
            "timestamp": 1234567890123,
            "bistatic_range_km": 55.0,
            "doppler_hz": 15.0
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_data, f)
        temp_file = f.name
    
    try:
        # Run main.py
        result = subprocess.run(
            ['python', 'main.py', temp_file],
            capture_output=True,
            text=True,
            cwd='.'
        )
        
        # Check output
        assert result.returncode == 0
        output = json.loads(result.stdout)
        
        # Should have timestamp and position
        assert 'timestamp' in output
        assert output['timestamp'] == 1234567890123
        assert 'latitude' in output or 'error' in output
        
        print("✓ CLI test passed")
        
    finally:
        os.unlink(temp_file)


def test_no_solution_case():
    """Test case where solver cannot converge"""
    test_data = {
        "detection1": {
            "sensor_lat": 40.0,
            "sensor_lon": -74.0,
            "ioo_lat": 40.0,
            "ioo_lon": -74.0,
            "freq_mhz": 100.0,
            "timestamp": 1234567890,
            "bistatic_range_km": 0.1,  # Impossible range
            "doppler_hz": -10000.0  # Impossible Doppler
        },
        "detection2": {
            "sensor_lat": 41.0,
            "sensor_lon": -73.0,
            "ioo_lat": 41.0,
            "ioo_lon": -73.0,
            "freq_mhz": 100.0,
            "timestamp": 1234567890,
            "bistatic_range_km": 0.1,  # Impossible range
            "doppler_hz": 10000.0  # Impossible Doppler
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_data, f)
        temp_file = f.name
    
    try:
        # Run main.py
        result = subprocess.run(
            ['python', 'main.py', temp_file],
            capture_output=True,
            text=True,
            cwd='.'
        )
        
        # Should complete without error
        assert result.returncode == 0
        output = json.loads(result.stdout)
        
        # Should report no solution
        assert 'error' in output
        assert output['error'] == 'No Solution'
        
        print("✓ No solution case handled correctly")
        
    finally:
        os.unlink(temp_file)


def test_invalid_json():
    """Test handling of invalid JSON"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write("{ invalid json")
        temp_file = f.name
    
    try:
        result = subprocess.run(
            ['python', 'main.py', temp_file],
            capture_output=True,
            text=True,
            cwd='.'
        )
        
        # Should handle error gracefully
        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert 'error' in output
        
        print("✓ Invalid JSON handled correctly")
        
    finally:
        os.unlink(temp_file)


if __name__ == "__main__":
    test_end_to_end_valid()
    test_command_line_interface()
    test_no_solution_case()
    test_invalid_json()
    print("\nAll integration tests passed!")