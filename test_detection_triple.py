"""
Test the DetectionTriple data structure
"""
import json
import pytest
from detection_triple import Detection, DetectionTriple, load_detections


def test_single_detection_validation():
    """Test Detection validation"""
    # Valid detection
    valid_det = Detection(
        sensor_lat=40.7128,
        sensor_lon=-74.0060,
        ioo_lat=40.7580,
        ioo_lon=-73.9855,
        freq_mhz=100.0,
        timestamp=1234567890,
        bistatic_range_km=150.5,
        doppler_hz=-125.3
    )
    assert valid_det.validate() == True
    
    # Invalid latitude
    invalid_lat = Detection(
        sensor_lat=91.0,  # Invalid
        sensor_lon=-74.0060,
        ioo_lat=40.7580,
        ioo_lon=-73.9855,
        freq_mhz=100.0,
        timestamp=1234567890,
        bistatic_range_km=150.5,
        doppler_hz=-125.3
    )
    assert invalid_lat.validate() == False
    
    # Invalid frequency
    invalid_freq = Detection(
        sensor_lat=40.7128,
        sensor_lon=-74.0060,
        ioo_lat=40.7580,
        ioo_lon=-73.9855,
        freq_mhz=-100.0,  # Invalid
        timestamp=1234567890,
        bistatic_range_km=150.5,
        doppler_hz=-125.3
    )
    assert invalid_freq.validate() == False
    
    print("✓ Single detection validation tests passed")


def test_detection_triple_creation():
    """Test DetectionTriple creation and methods"""
    # Create test JSON
    test_data = {
        "detection1": {
            "sensor_lat": 40.7128,
            "sensor_lon": -74.0060,
            "ioo_lat": 40.7580,
            "ioo_lon": -73.9855,
            "freq_mhz": 100.0,
            "timestamp": 1234567890,
            "bistatic_range_km": 150.5,
            "doppler_hz": -125.3
        },
        "detection2": {
            "sensor_lat": 40.6892,
            "sensor_lon": -74.0445,
            "ioo_lat": 40.7580,
            "ioo_lon": -73.9855,
            "freq_mhz": 100.0,
            "timestamp": 1234567890,
            "bistatic_range_km": 148.2,
            "doppler_hz": -130.1
        },
        "detection3": {
            "sensor_lat": 40.7489,
            "sensor_lon": -73.9680,
            "ioo_lat": 40.7580,
            "ioo_lon": -73.9855,
            "freq_mhz": 100.0,
            "timestamp": 1234567890,
            "bistatic_range_km": 152.1,
            "doppler_hz": -118.7
        }
    }
    
    json_string = json.dumps(test_data)
    triple = DetectionTriple.from_json(json_string)
    
    # Test data loaded correctly
    assert triple.detection1.sensor_lat == 40.7128
    assert triple.detection2.sensor_lat == 40.6892
    assert triple.detection3.sensor_lat == 40.7489
    
    # Test get_all_detections
    all_dets = triple.get_all_detections()
    assert len(all_dets) == 3
    assert all_dets[0] == triple.detection1
    assert all_dets[1] == triple.detection2
    assert all_dets[2] == triple.detection3
    
    # Test ENU origin calculation
    origin_lat, origin_lon, origin_alt = triple.get_enu_origin()
    expected_lat = (40.7128 + 40.6892 + 40.7489) / 3
    expected_lon = (-74.0060 + -74.0445 + -73.9680) / 3
    
    assert abs(origin_lat - expected_lat) < 1e-6
    assert abs(origin_lon - expected_lon) < 1e-6
    assert origin_alt == 0
    
    print("✓ DetectionTriple creation and methods tests passed")


def test_load_detections():
    """Test loading detections from file"""
    # Create test file
    test_data = {
        "detection1": {
            "sensor_lat": 40.7128,
            "sensor_lon": -74.0060,
            "ioo_lat": 40.7580,
            "ioo_lon": -73.9855,
            "freq_mhz": 100.0,
            "timestamp": 1234567890,
            "bistatic_range_km": 150.5,
            "doppler_hz": -125.3
        },
        "detection2": {
            "sensor_lat": 40.6892,
            "sensor_lon": -74.0445,
            "ioo_lat": 40.7580,
            "ioo_lon": -73.9855,
            "freq_mhz": 100.0,
            "timestamp": 1234567890,
            "bistatic_range_km": 148.2,
            "doppler_hz": -130.1
        },
        "detection3": {
            "sensor_lat": 40.7489,
            "sensor_lon": -73.9680,
            "ioo_lat": 40.6892,
            "ioo_lon": -74.0445,
            "freq_mhz": 100.0,
            "timestamp": 1234567890,
            "bistatic_range_km": 152.1,
            "doppler_hz": -118.7
        }
    }
    
    # Save to file
    test_file = "test_triple_detections.json"
    with open(test_file, 'w') as f:
        json.dump(test_data, f)
    
    # Load and test
    triple = load_detections(test_file)
    assert triple.detection1.sensor_lat == 40.7128
    assert triple.detection2.sensor_lat == 40.6892
    assert triple.detection3.sensor_lat == 40.7489
    
    # Test with invalid data
    invalid_data = test_data.copy()
    invalid_data["detection2"]["sensor_lat"] = 91.0  # Invalid
    
    with open(test_file, 'w') as f:
        json.dump(invalid_data, f)
    
    try:
        load_detections(test_file)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Detection 2 validation failed" in str(e)
    
    # Clean up
    import os
    os.remove(test_file)
    
    print("✓ File loading tests passed")


def test_backward_compatibility():
    """Test that old DetectionPair format is NOT compatible"""
    # Old 2-detection format
    old_data = {
        "detection1": {
            "sensor_lat": 40.7128,
            "sensor_lon": -74.0060,
            "ioo_lat": 40.7580,
            "ioo_lon": -73.9855,
            "freq_mhz": 100.0,
            "timestamp": 1234567890,
            "bistatic_range_km": 150.5,
            "doppler_hz": -125.3
        },
        "detection2": {
            "sensor_lat": 40.6892,
            "sensor_lon": -74.0445,
            "ioo_lat": 40.7580,
            "ioo_lon": -73.9855,
            "freq_mhz": 100.0,
            "timestamp": 1234567890,
            "bistatic_range_km": 148.2,
            "doppler_hz": -130.1
        }
    }
    
    json_string = json.dumps(old_data)
    try:
        DetectionTriple.from_json(json_string)
        assert False, "Should have raised KeyError for missing detection3"
    except KeyError:
        pass  # Expected
    
    print("✓ Backward compatibility test passed (correctly rejects 2-detection format)")


if __name__ == "__main__":
    print("=== Testing DetectionTriple Data Structure ===\n")
    
    test_single_detection_validation()
    test_detection_triple_creation()
    test_load_detections()
    test_backward_compatibility()
    
    print("\n✅ All tests passed!")