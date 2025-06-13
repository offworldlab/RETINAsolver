"""
radar_store.py

Manages in-memory storage of radar measurements with automatic cleanup of old data.
"""

import time
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class RadarMeasurement:
    """Represents a single radar measurement."""
    timestamp: float
    delay: float  # in km
    doppler: float  # in Hz

class RadarStore:
    """Manages in-memory storage of radar measurements."""
    
    def __init__(self, max_age_seconds: float = 300):  # 5 minutes default
        """
        Initialize the radar store.
        
        Args:
            max_age_seconds: Maximum age of stored measurements in seconds
        """
        self._store: Dict[str, List[RadarMeasurement]] = {
            "rx1": [],
            "rx2": [],
            "rx3": []
        }
        self.max_age_seconds = max_age_seconds
        self._last_cleanup = time.time()
    
    def add_measurement(self, radar_id: str, delay: float, doppler: float) -> None:
        """
        Add a new measurement for a radar.
        
        Args:
            radar_id: ID of the radar (rx1, rx2, or rx3)
            delay: Delay measurement in km
            doppler: Doppler measurement in Hz
        """
        if radar_id not in self._store:
            logger.error(f"Invalid radar ID: {radar_id}")
            return
            
        measurement = RadarMeasurement(
            timestamp=time.time(),
            delay=delay,
            doppler=doppler
        )
        self._store[radar_id].append(measurement)
        self._cleanup_if_needed()
    
    def get_measurements(self, radar_id: str) -> List[RadarMeasurement]:
        """
        Get all valid measurements for a radar.
        
        Args:
            radar_id: ID of the radar (rx1, rx2, or rx3)
            
        Returns:
            List of valid measurements for the radar
        """
        if radar_id not in self._store:
            logger.error(f"Invalid radar ID: {radar_id}")
            return []
            
        self._cleanup_if_needed()
        return self._store[radar_id].copy()
    
    def get_latest_measurement(self, radar_id: str) -> Optional[RadarMeasurement]:
        """
        Get the most recent measurement for a radar.
        
        Args:
            radar_id: ID of the radar (rx1, rx2, or rx3)
            
        Returns:
            Most recent measurement or None if no measurements exist
        """
        measurements = self.get_measurements(radar_id)
        return measurements[-1] if measurements else None
    
    def _cleanup_if_needed(self) -> None:
        """Remove measurements older than max_age_seconds."""
        current_time = time.time()
        
        # Only cleanup every 10 seconds to avoid excessive processing
        if current_time - self._last_cleanup < 10:
            return
            
        cutoff_time = current_time - self.max_age_seconds
        
        for radar_id in self._store:
            self._store[radar_id] = [
                m for m in self._store[radar_id]
                if m.timestamp > cutoff_time
            ]
            
        self._last_cleanup = current_time
        logger.debug("Cleaned up old measurements")
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get the number of measurements stored for each radar.
        
        Returns:
            Dictionary mapping radar IDs to their measurement counts
        """
        return {
            radar_id: len(measurements)
            for radar_id, measurements in self._store.items()
        } 