#!/usr/bin/env python3
"""
test_server.py

Tests for the synthetic ADSB server, verifying:
1. Server starts and responds
2. Data format matches expected schema
3. Aircraft position calculations are correct
4. Response timing is appropriate
"""

import unittest
import requests
import time
import math
from server import TX_LAT, TX_LON, RADIUS_DEG, ANGULAR_SPEED, ALT_BARO_FT, ICAO_HEX, PORT
import threading
from server import run_server

class TestSyntheticADSB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start the server in a separate thread
        cls.server_thread = threading.Thread(target=run_server, daemon=True)
        cls.server_thread.start()
        time.sleep(1)  # Give server time to start
        
        cls.base_url = f"http://localhost:{PORT}"
        cls.endpoint = f"{cls.base_url}/data/aircraft.json"

    def test_server_responds(self):
        """Verify the server responds with 200 OK"""
        response = requests.get(self.endpoint)
        self.assertEqual(response.status_code, 200)

    def test_data_format(self):
        """Verify the response matches the expected schema"""
        response = requests.get(self.endpoint)
        data = response.json()
        
        # Check top-level structure
        self.assertIn("now", data)
        self.assertIn("aircraft", data)
        self.assertIsInstance(data["aircraft"], list)
        
        # Check aircraft data
        aircraft = data["aircraft"][0]
        self.assertEqual(aircraft["hex"], ICAO_HEX)
        self.assertIsInstance(aircraft["lat"], float)
        self.assertIsInstance(aircraft["lon"], float)
        self.assertEqual(aircraft["alt_baro"], ALT_BARO_FT)
        self.assertEqual(aircraft["seen_pos"], 0)

    def test_position_calculation(self):
        """Verify aircraft position follows the expected circular pattern"""
        response = requests.get(self.endpoint)
        data = response.json()
        aircraft = data["aircraft"][0]
        
        # Calculate expected position
        now = data["now"]
        theta = (now * ANGULAR_SPEED) % (2 * math.pi)
        expected_lat = TX_LAT + RADIUS_DEG * math.cos(theta)
        expected_lon = TX_LON + RADIUS_DEG * math.sin(theta)
        
        # Allow for small floating point differences
        self.assertAlmostEqual(aircraft["lat"], expected_lat, places=6)
        self.assertAlmostEqual(aircraft["lon"], expected_lon, places=6)

    def test_response_timing(self):
        """Verify response timing is appropriate"""
        start_time = time.time()
        response = requests.get(self.endpoint)
        end_time = time.time()
        
        # Response should be quick (less than 100ms)
        self.assertLess(end_time - start_time, 0.1)
        
        # Server timestamp should be close to current time
        data = response.json()
        self.assertAlmostEqual(data["now"], time.time(), delta=1.0)

if __name__ == "__main__":
    unittest.main() 