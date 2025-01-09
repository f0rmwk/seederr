#!/usr/bin/env python3

import os
import time
import requests
import logging
from deluge_client import DelugeRPCClient

def main():
    # ---------------------------------------------------------------------
    # LOGGING SETUP
    # ---------------------------------------------------------------------
    LOGFILE = os.environ.get("SEEDERR_LOGFILE", "/var/log/seederr.log")
    logging.basicConfig(
        filename=LOGFILE,
        filemode='a',
        format='%(asctime)s [%(levelname)s] %(message)s',
        level=logging.INFO
    )
    logging.info("----- Starting Seederr Script -----")

    # ---------------------------------------------------------------------
    # CONFIGURATION
    # ---------------------------------------------------------------------
    DELUGE_WEB_URL = os.environ.get("DELUGE_WEB_URL", "http://localhost:8112")
    DELUGE_WEB_PASSWORD = os.environ.get("DELUGE_WEB_PASSWORD", "")

    DELUGE_HOST = os.environ.get("DELUGE_HOST", "localhost")
    DELUGE_PORT = int(os.environ.get("DELUGE_PORT", 58846))
    DELUGE_USERNAME = os.environ.get("DELUGE_USERNAME", "localclient")
    DELUGE_PASSWORD = os.environ.get("DELUGE_PASSWORD", "")

    MIN_AGE_SECONDS = int(os.environ.get("MIN_AGE_SECONDS", 1209600))  # Default: 14 days
    current_time = int(time.time())

    logging.info("Configuration: DELUGE_WEB_URL=%s, DELUGE_HOST=%s:%d, MIN_AGE_SECONDS=%d",
                 DELUGE_WEB_URL, DELUGE_HOST, DELUGE_PORT, MIN_AGE_SECONDS)

    # ---------------------------------------------------------------------
    # 1) Connect to Deluge WebUI
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
        login_json = login_resp.json()
        if not login_json.get("result"):
            raise ValueError("WebUI login unsuccessful.")
        logging.info("WebUI login successful.")
    except Exception as e:
        logging.error("Error connecting to Deluge WebUI: %s", e)
        return

    fields = ["name", "hash", "progress", "time_added"]
    update_payload = {
        "method": "web.update_ui",
        "params": [fields, {}],
        "id": 2
    }
    try:
        update_resp = session.post(f"{DELUGE_WEB_URL}/json", json=update_payload)
        update_resp.raise_for_status()
        update_data = update_resp.json()
        torrents_web = update_data.get("result", {}).get("torrents", {})
        logging.info("Fetched %d torrents from WebUI.", len(torrents_web))
    except Exception as e:
        logging.error("Error fetching torrents from WebUI: %s", e)
        return

    # ---------------------------------------------------------------------
    # 2) Connect to Deluge Daemon RPC
    # ---------------------------------------------------------------------
    try:
        rpc_client = DelugeRPCClient(DELUGE_HOST, DELUGE_PORT, DELUGE_USERNAME, DELUGE_PASSWORD)
        rpc_client.connect()
        logging.info("Connected to Deluge Daemon RPC.")
    except Exception as e:
        logging.error("Error connecting to Daemon RPC: %s", e)
        return

    # ---------------------------------------------------------------------
    # 3) Process and Remove Torrents
    # ---------------------------------------------------------------------
    for torrent_hash, info in torrents_web.items():
        name = info.get("name", "Unknown")
        progress = info.get("progress", 0.0)
        time_added = info.get("time_added", 0)
        age_seconds = current_time - time_added

        logging.info("Checking torrent: %s (Progress: %.1f%%, Age: %ds)", name, progress, age_seconds)

        if progress >= 100.0 and age_seconds >= MIN_AGE_SECONDS:
            logging.info("Removing torrent: %s", name)
            try:
                rpc_client.call("core.remove_torrent", torrent_hash, True)
                logging.info("Removed torrent: %s", name)
            except Exception as e:
                logging.error("Error removing torrent %s: %s", name, e)
        else:
            logging.info("Not removing torrent: %s", name)

    logging.info("----- Finished Seederr Script -----\n")

if __name__ == "__main__":
    main()
