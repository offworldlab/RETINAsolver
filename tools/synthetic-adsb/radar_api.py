"""
radar_api.py

Flask-based API server for serving radar measurements.
Each radar has its own dedicated port and endpoint.
"""

from flask import Flask, jsonify
from typing import Dict, Any
import threading
import logging
from radar_store import RadarStore
from flask_cors import CORS

logger = logging.getLogger(__name__)


class RadarAPI:
    """Manages API servers for each radar."""

    def __init__(self, store: RadarStore, config: Dict[str, Any]):
        """
        Initialize the API servers.

        Args:
            store: RadarStore instance to use for data
            config: Configuration dictionary containing radar and system settings
        """
        self.store = store
        self.config = config
        self.servers: Dict[str, Flask] = {}
        self.threads: Dict[str, threading.Thread] = {}

        # Port configuration for each radar
        self.ports = {"rx1": 49158, "rx2": 49159, "rx3": 49160}

    def start(self) -> None:
        """Start API servers for all radars."""
        for radar_id in self.ports:
            self._start_server(radar_id)

    def stop(self) -> None:
        """Stop all API servers."""
        for thread in self.threads.values():
            thread.join(timeout=1.0)

    def _start_server(self, radar_id: str) -> None:
        """
        Start an API server for a specific radar.

        Args:
            radar_id: ID of the radar to serve
        """
        app = Flask(f"radar_api_{radar_id}")
        CORS(app)  # This enables CORS for all routes and origins by default

        @app.route("/data")
        def get_data():
            """Get all measurements for this radar."""
            measurements = self.store.get_measurements(radar_id)
            latest = self.store.get_latest_measurement(radar_id)

            return jsonify(
                {
                    "radar_id": radar_id,
                    "measurements": [
                        {
                            "timestamp": m.timestamp,
                            "delay": m.delay,
                            "doppler": m.doppler,
                        }
                        for m in measurements
                    ],
                    "last_update": latest.timestamp if latest else None,
                    "count": len(measurements),
                }
            )

        @app.route("/status")
        def get_status():
            """Get status information for this radar."""
            latest = self.store.get_latest_measurement(radar_id)
            stats = self.store.get_stats()

            return jsonify(
                {
                    "radar_id": radar_id,
                    "last_update": latest.timestamp if latest else None,
                    "measurement_count": stats[radar_id],
                    "is_active": latest is not None,
                }
            )

        @app.route("/api/detection")
        def get_detection():
            """Get detection data in the format required by 3lips."""
            measurements = self.store.get_measurements(radar_id)

            if not measurements:
                return jsonify({"timestamp": 0, "delay": [], "doppler": []})

            # Get the most recent timestamp
            latest = measurements[-1].timestamp

            delays = [m.delay for m in measurements]
            dopplers = [m.doppler for m in measurements]

            return jsonify({"timestamp": latest, "delay": delays, "doppler": dopplers})

        @app.route("/api/config")
        def get_config():
            """Get configuration information for this radar."""
            # Find the radar configuration for this endpoint
            radar_config = next(
                (r for r in self.config["RADARS"] if r["id"] == radar_id), None
            )

            if not radar_config:
                return jsonify({"error": "Radar configuration not found"}), 404

            # Convert frequency from MHz to Hz
            fc_hz = self.config["FC_MHZ"] * 1e6

            return jsonify(
                {
                    "location": {
                        "rx": {
                            "name": radar_id,
                            "latitude": radar_config["lat"],
                            "longitude": radar_config["lon"],
                            "altitude": radar_config["alt"],
                        },
                        "tx": {
                            "name": "tx",
                            "latitude": self.config["TX"]["lat"],
                            "longitude": self.config["TX"]["lon"],
                            "altitude": self.config["TX"]["alt"],
                        },
                    },
                    "capture": {"fc": fc_hz},
                    "truth": {"adsb": {"tar1090": self.config["ADSB_JSON_HOST"]}},
                }
            )

        def run_server():
            """Run the Flask server."""
            try:
                app.run(host="0.0.0.0", port=self.ports[radar_id])
            except Exception as e:
                logger.error(f"Error running API server for {radar_id}: {e}")

        # Store the server and start it in a thread
        self.servers[radar_id] = app
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        self.threads[radar_id] = thread

        logger.info(f"Started API server for {radar_id} on port {self.ports[radar_id]}")
