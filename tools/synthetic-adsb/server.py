#!/usr/bin/env python3
"""
synthetic_adsb_server.py

A Flask-based HTTP server that serves synthetic ADS-B data in tar1090 format.
Simulates one aircraft flying in a circular pattern around Mount Lofty (–34.9810, 138.7081),
at a constant barometric altitude, updating once per second.

Endpoint:
  GET /data/aircraft.json

Response schema:
{
  "now": <epoch seconds float>,
  "aircraft": [
    {
      "hex": <string>,         # ICAO hex address
      "lat": <float>,          # degrees
      "lon": <float>,          # degrees
      "alt_baro": <int>,       # feet
      "alt_geom": <int>,        # feet
      "flight": <string>,      # Synthetic flight number with padding
      "seen_pos": 0
    },
    … (more aircraft)
  ]
}
"""

import time
import math
import threading
import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()


def require_env_var(var_name):
    value = os.environ.get(var_name)
    if value is None or value == "":
        raise EnvironmentError(
            f"Required environment variable '{var_name}' is missing or empty."
        )
    return value


REQUIRED_ENV_VARS = [
    "TX_LAT",
    "TX_LON",
    "TX_ALT",
    "FC_MHZ",
    "RADIUS_DEG",
    "ANGULAR_SPEED",
    "ALT_BARO_FT",
    "ICAO_HEX",
    "HOST",
    "PORT",
]
for var in REQUIRED_ENV_VARS:
    require_env_var(var)

TX_LAT = float(os.environ.get("TX_LAT"))
TX_LON = float(os.environ.get("TX_LON"))
TX_ALT = int(os.environ.get("TX_ALT"))
FC_MHZ = float(os.environ.get("FC_MHZ"))

RADIUS_DEG = float(os.environ.get("RADIUS_DEG"))
ANGULAR_SPEED = float(os.environ.get("ANGULAR_SPEED"))
ALT_BARO_FT = int(os.environ.get("ALT_BARO_FT"))
ICAO_HEX = os.environ.get("ICAO_HEX")

HOST = os.environ.get("HOST")
PORT = int(os.environ.get("PORT"))

app = Flask(__name__)
CORS(app)


@app.route("/data/aircraft.json")
def serve_synthetic_adsb():
    """
    Generate one circular-flight aircraft at the current time.
    """
    now = time.time()
    theta = (now * ANGULAR_SPEED) % (2 * math.pi)

    lat = TX_LAT + RADIUS_DEG * math.cos(theta)
    lon = TX_LON + RADIUS_DEG * math.sin(theta)

    aircraft = {
        "hex": ICAO_HEX,
        "lat": round(lat, 6),
        "lon": round(lon, 6),
        "alt_baro": ALT_BARO_FT,
        "alt_geom": ALT_BARO_FT
        + 100,  # Geometric altitude is typically slightly higher
        "flight": "SYN001  ",
        "seen_pos": 0,
    }

    return jsonify({"now": now, "aircraft": [aircraft]})


def run_server():
    app.run(host=HOST, port=PORT, threaded=True)


if __name__ == "__main__":
    print(
        f"[synthetic_adsb_server] starting on http://{HOST}:{PORT}/data/aircraft.json"
    )
    threading.Thread(target=run_server, daemon=True).start()

    try:
        # Keep the main thread alive
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\n[synthetic_adsb_server] shutting down.")
