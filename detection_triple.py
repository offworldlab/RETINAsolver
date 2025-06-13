"""
Detection data structures for 3-detection telemetry solver
"""
import json
from dataclasses import dataclass
from typing import Tuple, Optional, List
from Geometry import Geometry


@dataclass
class Detection:
    """Single detection data"""
    sensor_lat: float
    sensor_lon: float
    ioo_lat: float
    ioo_lon: float
    freq_mhz: float
    timestamp: int
    bistatic_range_km: float
    doppler_hz: float
    
    def validate(self) -> bool:
        """Check data validity"""
        if not (-90 <= self.sensor_lat <= 90):
            return False
        if not (-180 <= self.sensor_lon <= 180):
            return False
        if not (-90 <= self.ioo_lat <= 90):
            return False
        if not (-180 <= self.ioo_lon <= 180):
            return False
        if self.freq_mhz <= 0:
            return False
        if self.bistatic_range_km <= 0:
            return False
        return True


@dataclass
class InitialGuess:
    """Optional initial guess for target position and velocity"""
    position_lla: Tuple[float, float, float]  # (lat, lon, alt)
    velocity_enu: Tuple[float, float, float]  # (east, north, up)
    
    def validate(self) -> bool:
        """Check initial guess validity"""
        lat, lon, alt = self.position_lla
        if not (-90 <= lat <= 90):
            return False
        if not (-180 <= lon <= 180):
            return False
        if not (0 <= alt <= 100000):  # 0 to 100km altitude
            return False
        
        east, north, up = self.velocity_enu
        if abs(east) > 1000 or abs(north) > 1000 or abs(up) > 1000:  # Reasonable velocity bounds
            return False
        
        return True


@dataclass
class DetectionTriple:
    """Container for three simultaneous detections"""
    detection1: Detection
    detection2: Detection
    detection3: Detection
    initial_guess: Optional[InitialGuess] = None
    
    @classmethod
    def from_json(cls, json_string: str) -> 'DetectionTriple':
        """Parse input JSON"""
        data = json.loads(json_string)
        
        det1_data = data['detection1']
        det1 = Detection(
            sensor_lat=det1_data['sensor_lat'],
            sensor_lon=det1_data['sensor_lon'],
            ioo_lat=det1_data['ioo_lat'],
            ioo_lon=det1_data['ioo_lon'],
            freq_mhz=det1_data['freq_mhz'],
            timestamp=det1_data['timestamp'],
            bistatic_range_km=det1_data['bistatic_range_km'],
            doppler_hz=det1_data['doppler_hz']
        )
        
        det2_data = data['detection2']
        det2 = Detection(
            sensor_lat=det2_data['sensor_lat'],
            sensor_lon=det2_data['sensor_lon'],
            ioo_lat=det2_data['ioo_lat'],
            ioo_lon=det2_data['ioo_lon'],
            freq_mhz=det2_data['freq_mhz'],
            timestamp=det2_data['timestamp'],
            bistatic_range_km=det2_data['bistatic_range_km'],
            doppler_hz=det2_data['doppler_hz']
        )
        
        det3_data = data['detection3']
        det3 = Detection(
            sensor_lat=det3_data['sensor_lat'],
            sensor_lon=det3_data['sensor_lon'],
            ioo_lat=det3_data['ioo_lat'],
            ioo_lon=det3_data['ioo_lon'],
            freq_mhz=det3_data['freq_mhz'],
            timestamp=det3_data['timestamp'],
            bistatic_range_km=det3_data['bistatic_range_km'],
            doppler_hz=det3_data['doppler_hz']
        )
        
        # Parse optional initial guess
        initial_guess = None
        if 'initial_guess' in data:
            ig_data = data['initial_guess']
            position_lla = (
                ig_data['position_lla']['lat'],
                ig_data['position_lla']['lon'],
                ig_data['position_lla']['alt']
            )
            velocity_enu = (
                ig_data['velocity_enu']['east'],
                ig_data['velocity_enu']['north'],
                ig_data['velocity_enu']['up']
            )
            initial_guess = InitialGuess(position_lla, velocity_enu)
        
        return cls(det1, det2, det3, initial_guess)
    
    def get_enu_origin(self) -> Tuple[float, float, float]:
        """Calculate centroid of three sensors in LLA"""
        lat = (self.detection1.sensor_lat + self.detection2.sensor_lat + self.detection3.sensor_lat) / 3
        lon = (self.detection1.sensor_lon + self.detection2.sensor_lon + self.detection3.sensor_lon) / 3
        alt = 0  # Sea level for origin
        return lat, lon, alt
    
    def get_all_detections(self) -> list:
        """Return all three detections as a list for easier iteration"""
        return [self.detection1, self.detection2, self.detection3]
    
    def get_initial_guess_enu(self) -> Optional[List[float]]:
        """Convert initial guess from LLA to ENU coordinates if available"""
        if self.initial_guess is None:
            return None
        
        # Get ENU origin (centroid of sensors)
        origin_lat, origin_lon, origin_alt = self.get_enu_origin()
        
        # Convert position from LLA to ENU
        lat, lon, alt = self.initial_guess.position_lla
        target_ecef = Geometry.lla2ecef(lat, lon, alt)
        target_enu = Geometry.ecef2enu(target_ecef[0], target_ecef[1], target_ecef[2],
                                       origin_lat, origin_lon, origin_alt)
        
        # Velocity is already in ENU
        east, north, up = self.initial_guess.velocity_enu
        
        return [target_enu[0], target_enu[1], target_enu[2], east, north, up]


def load_detections(json_file: str) -> DetectionTriple:
    """Load and validate input"""
    with open(json_file, 'r') as f:
        json_string = f.read()
    
    triple = DetectionTriple.from_json(json_string)
    
    if not triple.detection1.validate():
        raise ValueError("Detection 1 validation failed")
    if not triple.detection2.validate():
        raise ValueError("Detection 2 validation failed")
    if not triple.detection3.validate():
        raise ValueError("Detection 3 validation failed")
    
    if triple.initial_guess is not None and not triple.initial_guess.validate():
        raise ValueError("Initial guess validation failed")
    
    return triple