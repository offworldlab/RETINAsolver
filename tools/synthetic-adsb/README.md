# Synthetic ADS-B Radar Simulation

This package simulates a synthetic ADS-B (Automatic Dependent Surveillance–Broadcast) environment for radar and aircraft tracking research or development. It provides tools to generate, process, and serve synthetic aircraft and radar data via HTTP APIs.

## Features

- **Synthetic ADS-B Server**: Simulates aircraft flying in a circular pattern and serves their positions in tar1090-compatible JSON format (`server.py`).
- **Bridge & Delay–Doppler Processing**: Polls the synthetic ADS-B feed, calls an external `adsb2dd` API to compute delay–Doppler measurements for three virtual radar receivers, and stores the results (`bridge.py`).
- **Radar API**: Exposes Flask-based API endpoints for each radar, providing access to computed measurements, radar status, and configuration (`radar_api.py`).
- **In-Memory Data Store**: Efficiently manages and cleans up radar measurement data (`radar_store.py`).
- **Testing**: Includes a test suite to verify server correctness and data format (`test_server.py`).

## Requirements

- Python 3.8+
- Flask 3.0.2
- Flask-CORS 4.0.0
- Requests 2.31.0
- python-dotenv 1.0.1

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Configuration

Both `server.py` and `bridge.py` are now configured via environment variables. You must create a `.env` file in the project root (see `.env.example` for a template). Example:

```ini
# --- For server.py ---
TX_LAT=-34.9810
TX_LON=138.7081
TX_ALT=750
FC_MHZ=204.64
RADIUS_DEG=0.05
ANGULAR_SPEED=0.01
ALT_BARO_FT=30000
ICAO_HEX=AEF123
HOST=0.0.0.0
PORT=5001

# --- For bridge.py ---
ADSB_JSON_HOST=http://localhost:5001
ADSB_JSON_PATH=/data/aircraft.json
ADSB2DD_URL=http://192.168.0.219:49155/api/dd
POLL_RATE_HZ=1.0
RADARS=[{"id": "rx1", "lat": -34.9192, "lon": 138.6027, "alt": 110}, {"id": "rx2", "lat": -34.9315, "lon": 138.6967, "alt": 408}, {"id": "rx3", "lat": -34.8414, "lon": 138.7237, "alt": 230}]
TX={"lat": -34.9810, "lon": 138.7081, "alt": 750}
FC_MHZ=204.64
```

**Note:** All variables are required. The bridge expects `RADARS` and `TX` as JSON strings.

## Usage

1. **Set up your environment**

   - Copy `.env.example` to `.env` and edit as needed.
   - Ensure all required variables are set.

2. **Start the Synthetic ADS-B Server**

   ```bash
   python server.py
   ```

   This will serve synthetic aircraft data at `http://<HOST>:<PORT>/data/aircraft.json` (default: `http://localhost:5001/data/aircraft.json`).

3. **Run the Bridge and Radar APIs**

   ```bash
   python bridge.py
   ```

   This will poll the synthetic ADS-B feed, compute delay–Doppler measurements, and start API endpoints for each radar.

4. **Access Radar Data**
   - Each radar exposes endpoints (e.g., `/data`, `/status`, `/api/detection`, `/api/config`) on its own port (default: 49158, 49159, 49160).

## Example

See `example.aircraft.json` for a sample of the synthetic ADS-B data format.

## License

MIT License
