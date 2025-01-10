#!/usr/bin/env python3

import os
import time
import requests
import logging
from deluge_client import DelugeRPCClient
import schedule
from datetime import datetime

# ---------------------------------------------------------------------
# LOGGING SETUP
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("/app/seederr.log"),  # Log to file
        logging.StreamHandler()  # Log to stdout
    ]
)

# Scheduler function to run `main`
def run_scheduled_task():
    logging.info(f"Running scheduled task at {datetime.now()}")
    try:
        main()
    except Exception as e:
        logging.error(f"Error during scheduled task: {e}")


def main():
    logging.info("----- Starting seederr_8 script -----")

    # ---------------------------------------------------------------------
    # CONFIGURATION
    # ---------------------------------------------------------------------
    DELUGE_WEB_URL = os.environ.get("DELUGE_WEB_URL", "http://127.0.0.1:8112")
    DELUGE_WEB_PASSWORD = os.environ.get("DELUGE_WEB_PASSWORD", "secret")
    DELUGE_HOST = os.environ.get("DELUGE_HOST", "127.0.0.1")
    DELUGE_PORT = int(os.environ.get("DELUGE_PORT", 58846))
    DELUGE_USERNAME = os.environ.get("DELUGE_USERNAME", "localclient")
    DELUGE_PASSWORD = os.environ.get("DELUGE_PASSWORD", "secret")

    # Torrent removal criteria
    MIN_AGE_SECONDS = int(os.environ.get("MIN_AGE_SECONDS", 1209600))
    current_time = int(time.time())

    # ---------------------------------------------------------------------
    # Connect to Deluge WebUI
    # ---------------------------------------------------------------------
    session = requests.Session()
    login_payload = {
        "method": "auth.login",
        "params": [DELUGE_WEB_PASSWORD],
        "id": 1
    }

    try:
        login_resp = session.post(f"{DELUGE_WEB_URL}/json", json=login_payload)
        login_resp.raise_for_status()
    except Exception as e:
        logging.error("WebUI login request failed: %s", e)
        return

    login_json = login_resp.json()
    if not login_json.get("result"):
        logging.error("WebUI login unsuccessful. Response: %s", login_json)
        return

    logging.info("WebUI login successful at %s", DELUGE_WEB_URL)

    # Request torrent info
    fields = ["name", "hash", "progress", "time_added"]
    update_payload = {
        "method": "web.update_ui",
        "params": [fields, {}],
        "id": 2
    }

    try:
        update_resp = session.post(f"{DELUGE_WEB_URL}/json", json=update_payload)
        update_resp.raise_for_status()
    except Exception as e:
        logging.error("web.update_ui request failed: %s", e)
        return

    update_data = update_resp.json()
    if update_data.get("error"):
        logging.error("Deluge WebUI reported error: %s", update_data["error"])
        return

    torrents_web = update_data.get("result", {}).get("torrents", {})
    logging.info("Fetched %d torrents from Deluge WebUI.", len(torrents_web))

    # ---------------------------------------------------------------------
    # Connect to Daemon RPC
    # ---------------------------------------------------------------------
    try:
        rpc_client = DelugeRPCClient(DELUGE_HOST, DELUGE_PORT, DELUGE_USERNAME, DELUGE_PASSWORD)
        rpc_client.connect()
        logging.info("Connected to Deluge daemon at %s:%d", DELUGE_HOST, DELUGE_PORT)
    except Exception as e:
        logging.error("Daemon RPC connection failed: %s", e)
        return

    # ---------------------------------------------------------------------
    # Remove old completed torrents
    # ---------------------------------------------------------------------
    for torrent_hash, info in torrents_web.items():
        name = info.get("name", "Unknown")
        progress = info.get("progress", 0.0)
        time_added = info.get("time_added", 0)
        age_seconds = current_time - time_added

        logging.info(
            "Checking torrent: %s (Hash: %s, Progress: %.1f%%, Age: %ds)",
            name, torrent_hash, progress, age_seconds
        )

        if progress >= 100.0 and age_seconds >= MIN_AGE_SECONDS:
            logging.info("Removing %s (age >= %d seconds).", name, MIN_AGE_SECONDS)
            try:
                rpc_client.call("core.remove_torrent", torrent_hash, True)
                logging.info("Successfully removed %s via daemon RPC.", name)
            except Exception as err:
                logging.error("Error removing %s: %s", name, err)
        else:
            logging.info("Not removing %s", name)

    logging.info("----- Finished seederr_8 script -----\n")


# ---------------------------------------------------------------------
# Schedule the Script Based on User Configuration
# ---------------------------------------------------------------------
if __name__ == "__main__":
    # Get the interval (in seconds) for running the script
    TASK_INTERVAL_SECONDS = int(os.environ.get("TASK_INTERVAL_SECONDS", 300))  # Default: 300s (5 minutes)

    # Add a task to the scheduler
    schedule.every(TASK_INTERVAL_SECONDS).seconds.do(run_scheduled_task)

    logging.info("Scheduler started with an interval of %d seconds.", TASK_INTERVAL_SECONDS)

    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(1)
