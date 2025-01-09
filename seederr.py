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
    # You can change this file path or name as needed (absolute path if you want)
    LOGFILE = os.environ.get("SEEDERR_LOGFILE", "seederr.log")
    logging.basicConfig(
        filename="/seederr.log",  # <--- Absolute path here
        filemode='a',  # append mode
        format='%(asctime)s [%(levelname)s] %(message)s',
        level=logging.INFO
    )

    # This will also write a brief message to the log every time the script starts
    logging.info("----- Starting seederr_7 script -----")

    # ---------------------------------------------------------------------
    # CONFIGURATION: WebUI + Daemon
    # ---------------------------------------------------------------------
    DELUGE_WEB_URL      = os.environ.get("DELUGE_WEB_URL", "http://localhost:8112")
    DELUGE_WEB_PASSWORD = os.environ.get("DELUGE_WEB_PASSWORD", "")

    DELUGE_HOST         = os.environ.get("DELUGE_HOST", "")
    DELUGE_PORT         = int(os.environ.get("DELUGE_PORT", 58846))
    DELUGE_USERNAME     = os.environ.get("DELUGE_USERNAME", "localclient")
    DELUGE_PASSWORD     = os.environ.get("DELUGE_PASSWORD", "")

    # If not specified, default to 14 days (in seconds)
    MIN_AGE_SECONDS = int(os.environ.get("MIN_AGE_SECONDS", 1209600))
    current_time = int(time.time())

    # ---------------------------------------------------------------------
    # 1) Connect to Deluge WebUI (JSON) to get torrent info
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

    # Request torrent info from web.update_ui
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
    # 2) Connect to Daemon RPC
    # ---------------------------------------------------------------------
    try:
        rpc_client = DelugeRPCClient(DELUGE_HOST, DELUGE_PORT, DELUGE_USERNAME, DELUGE_PASSWORD)
        rpc_client.connect()
        logging.info("Connected to Deluge daemon at %s:%d", DELUGE_HOST, DELUGE_PORT)
    except Exception as e:
        logging.error("Daemon RPC connection failed: %s", e)
        return

    # ---------------------------------------------------------------------
    # 3) Remove old completed torrents
    # ---------------------------------------------------------------------
    for torrent_hash, info in torrents_web.items():
        name        = info.get("name", "Unknown")
        progress    = info.get("progress", 0.0)
        time_added  = info.get("time_added", 0)
        age_seconds = current_time - time_added

        logging.info(
            "Checking torrent: %s (Hash: %s, Progress: %.1f%%, Age: %ds)",
            name, torrent_hash, progress, age_seconds
        )

        # Example rule: If progress >= 100% and age >= MIN_AGE_SECONDS => remove
        if progress >= 100.0 and age_seconds >= MIN_AGE_SECONDS:
            logging.info("Removing %s (age >= %d seconds).", name, MIN_AGE_SECONDS)
            try:
                rpc_client.call("core.remove_torrent", torrent_hash, True)
                logging.info("Successfully removed %s via daemon RPC.", name)
            except Exception as err:
                logging.error("Error removing %s: %s", name, err)
        else:
            logging.info("Not removing %s", name)

    logging.info("----- Finished seederr_7 script -----\n")

if __name__ == "__main__":
    main()
