#!/usr/bin/env python3
"""
bridge.py

Polls a synthetic ADS-B JSON feed, calls adsb2dd to compute delay–Doppler
for each of three virtual radars, and stores the results for API access.
"""

import time
import requests
import socket
import logging
import os
import json
from radar_store import RadarStore
from radar_api import RadarAPI
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()


def require_env_var(var_name):
    value = os.environ.get(var_name)
    if value is None or value == "":
        raise EnvironmentError(
            f"Required environment variable '{var_name}' is missing or empty."
        )
    return value


REQUIRED_ENV_VARS = [
    "ADSB_JSON_HOST",
    "ADSB_JSON_PATH",
    "ADSB2DD_URL",
    "POLL_RATE_HZ",
    "RADARS",
    "TX",
    "FC_MHZ",
]
for var in REQUIRED_ENV_VARS:
    require_env_var(var)

ADSB_JSON_HOST = os.environ.get("ADSB_JSON_HOST")
ADSB_JSON_PATH = os.environ.get("ADSB_JSON_PATH")

ADSB2DD_URL = os.environ.get("ADSB2DD_URL")

POLL_RATE_HZ = float(os.environ.get("POLL_RATE_HZ"))

try:
    RADARS = json.loads(os.environ.get("RADARS"))
except json.JSONDecodeError:
    logger.error("Failed to parse RADARS from environment variable. Exiting.")
    raise

try:
    TX = json.loads(os.environ.get("TX"))
except json.JSONDecodeError:
    logger.error("Failed to parse TX from environment variable. Exiting.")
    raise

FC_MHZ = float(os.environ.get("FC_MHZ"))


def check_port_open(host, port, timeout=1):
    """Check if a port is open on the given host."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.error(f"Error checking port {port} on {host}: {e}")
        return False


def fetch_adsb():
    """Fetch synthetic ADS-B JSON from the local server."""
    try:
        # First check if the port is open
        if not check_port_open("localhost", 5001):
            logger.error(
                "Port 5001 is not open on localhost. Is the ADS-B server running?"
            )
            return None

        logger.info(
            f"Attempting to fetch ADS-B data from {ADSB_JSON_HOST}{ADSB_JSON_PATH}"
        )
        resp = requests.get(f"{ADSB_JSON_HOST}{ADSB_JSON_PATH}", timeout=5)
        resp.raise_for_status()
        logger.info("Successfully fetched ADS-B data")
        return resp.json()
    except requests.exceptions.Timeout:
        logger.error(
            "Timeout while fetching ADS-B data. Server might be overloaded or not responding."
        )
        return None
    except requests.exceptions.ConnectionError:
        logger.error(
            "Connection error while fetching ADS-B data. Server might not be running."
        )
        return None
    except Exception as e:
        logger.error(f"Unexpected error while fetching ADS-B data: {e}")
        return None


def build_adsb2dd_url(radar):
    """Construct the query URL for adsb2dd for one radar."""
    params = {
        "rx": f"{radar['lat']},{radar['lon']},{radar['alt']}",
        "tx": f"{TX['lat']},{TX['lon']},{TX['alt']}",
        "fc": FC_MHZ,
        "server": ADSB_JSON_HOST,
    }
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{ADSB2DD_URL}?{qs}"


def query_adsb2dd_for(radar):
    """Call adsb2dd and return its JSON (hex → {timestamp, delay, doppler})."""
    url = build_adsb2dd_url(radar)
    print(url)
    resp = requests.get(url, timeout=5)
    resp.raise_for_status()
    return resp.json()


def main():
    config = {
        "ADSB_JSON_HOST": ADSB_JSON_HOST,
        "ADSB_JSON_PATH": ADSB_JSON_PATH,
        "ADSB2DD_URL": ADSB2DD_URL,
        "POLL_RATE_HZ": POLL_RATE_HZ,
        "RADARS": RADARS,
        "TX": TX,
        "FC_MHZ": FC_MHZ,
    }

    store = RadarStore()
    api = RadarAPI(store, config)

    api.start()
    logger.info("Started radar API servers")

    loop_delay = 1.0 / POLL_RATE_HZ
    logger.info(f"Starting bridge; polling at {POLL_RATE_HZ} Hz")

    try:
        while True:
            t_start = time.time()
            try:
                adsb_data = fetch_adsb()
                if adsb_data is None:
                    logger.warning(
                        "Skipping this iteration due to failed ADS-B data fetch"
                    )
                    time.sleep(loop_delay)
                    continue

                for radar in RADARS:
                    try:
                        dd = query_adsb2dd_for(radar)
                        for meas in dd.values():
                            store.add_measurement(
                                radar_id=radar["id"],
                                delay=meas["delay"],
                                doppler=meas["doppler"],
                            )
                    except Exception as e:
                        logger.error(f"Error processing radar {radar['id']}: {e}")

            except Exception as e:
                logger.error(f"Error in main loop: {e}")

            elapsed = time.time() - t_start
            to_sleep = loop_delay - elapsed
            if to_sleep > 0:
                time.sleep(to_sleep)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
        api.stop()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
