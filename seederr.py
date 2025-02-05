#!/usr/bin/env python3
import os
import time
import json
import logging
from threading import Thread
from flask import Flask, request, redirect, url_for, flash
from deluge_client import DelugeRPCClient
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.secret_key = "change-this-secret-key"  # Replace with a secure secret key for production

# Path to the persistent configuration file.
CONFIG_FILE = "/data/seederr_config.json"

# Default configuration (removal criteria stored internally in seconds)
config = {
    "DELUGE_HOST": os.environ.get("DELUGE_HOST", "0.0.0.0"),
    "DELUGE_PORT": int(os.environ.get("DELUGE_PORT", 58846)),
    "DELUGE_USERNAME": os.environ.get("DELUGE_USERNAME", "localclient"),
    "DELUGE_PASSWORD": os.environ.get("DELUGE_PASSWORD", "YourDelugeRPCPassword"),
    # Removal criteria (stored in seconds)
    "SEEDING_TIME_LIMIT": int(os.environ.get("SEEDING_TIME_LIMIT", 80 * 3600)),  # 80 hours default
    "MIN_AGE_SECONDS": int(os.environ.get("MIN_AGE_SECONDS", 14 * 24 * 3600)),   # 14 days default
    "TARGET_TRACKERS": [
        "trnt.tracker.com"
    ],
    "LOGFILE": os.environ.get("SEEDERR_LOGFILE", "/data/seederr.log"),
    # Scheduling: stored in seconds, but UI shows in minutes; 0 means disabled.
    "SCHEDULE_INTERVAL": int(os.environ.get("SCHEDULE_INTERVAL", 0))
}

# Setup logging.
logging.basicConfig(
    filename=config["LOGFILE"],
    filemode="a",
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.DEBUG  # DEBUG level to capture detailed messages.
)

# Global variable to store the summary output of the most recent removal run.
last_run_summary = "No run output yet."

# Create and start the background scheduler.
scheduler = BackgroundScheduler()
scheduler.start()


def update_scheduler():
    """
    Update the scheduler according to the current configuration.
    If SCHEDULE_INTERVAL (in seconds) is greater than 0, schedule (or reschedule) the removal job.
    If it is 0, remove any existing job.
    """
    schedule_interval = config.get("SCHEDULE_INTERVAL", 0)
    try:
        if schedule_interval > 0:
            # Convert seconds to minutes for APScheduler's 'interval' trigger.
            minutes = schedule_interval // 60
            job = scheduler.get_job("removal_job")
            if job:
                scheduler.reschedule_job("removal_job", trigger='interval', minutes=minutes)
                logging.info("Rescheduled removal job to run every %d minutes", minutes)
            else:
                scheduler.add_job(run_removal_job, 'interval', minutes=minutes, id="removal_job")
                logging.info("Scheduled removal job to run every %d minutes", minutes)
        else:
            # If scheduling is disabled, remove the job if it exists.
            job = scheduler.get_job("removal_job")
            if job:
                scheduler.remove_job("removal_job")
                logging.info("Removed scheduled removal job (interval set to 0)")
    except Exception as e:
        logging.error("Error updating scheduler: %s", e)


def load_config():
    """Load configuration from a JSON file if it exists."""
    global config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                loaded = json.load(f)
            config.update(loaded)
            logging.info("Configuration loaded from %s", CONFIG_FILE)
        except Exception as e:
            logging.error("Failed to load config file: %s", e)
    else:
        logging.info("No configuration file found. Using default settings.")


def save_config():
    """Save the current configuration to a JSON file."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        logging.info("Configuration saved to %s", CONFIG_FILE)
    except Exception as e:
        logging.error("Failed to save config file: %s", e)


def decode_bytes(value):
    """Helper to decode a bytes value to a string if needed."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def connect_to_deluge_rpc(host, port, username, password, fields):
    """
    Connect to the Deluge daemon RPC and retrieve torrent info.
    Returns a tuple (client, torrents) where torrents is a dict mapping a lowercase torrent hash to its info.
    """
    try:
        logging.info("Connecting to %s:%d", host, port)
        client = DelugeRPCClient(host, port, username, password)
        client.connect()
        logging.info("Connected to Deluge daemon at %s:%d", host, port)
        torrents = client.call("core.get_torrents_status", {}, fields)
        normalized_torrents = {}
        for raw_hash, info in torrents.items():
            torrent_hash = raw_hash.hex() if isinstance(raw_hash, bytes) else raw_hash
            normalized_torrents[torrent_hash.lower()] = info
        return client, normalized_torrents
    except Exception as e:
        logging.exception("Daemon RPC connection or retrieval failed: %s", e)
        return None, {}


def process_torrents_rpc(rpc_torrents, rpc_client, seeding_time_limit, min_age_seconds, target_trackers):
    """
    Evaluate each torrent (from the RPC list) against two removal rules:
      - Rule A (tracker rule): Remove if seeding time > seeding_time_limit and a target tracker is found.
      - Rule B (age rule): Remove if torrent is 100% complete and older than min_age_seconds.
    Returns two lists: removed and not_removed.
    Logs detailed information for each torrent.
    """
    current_time = int(time.time())
    removed = []
    not_removed = []
    for torrent_hash, info in rpc_torrents.items():
        name = decode_bytes(info.get(b"name", b"Unknown"))
        progress = info.get(b"progress", 0.0)
        time_added = info.get(b"time_added", 0)
        age_seconds = current_time - time_added
        seeding_time = info.get(b"seeding_time", 0)
        trackers_list = info.get(b"trackers", [])
        tracker_urls = [decode_bytes(tracker.get(b"url", b"")) for tracker in trackers_list]

        logging.info("Torrent: '%s' | Hash: %s", name, torrent_hash)
        logging.info("Progress: %.1f%% | Age: %ds (min: %ds) | Seeding time: %ds (min: %ds)",
                     progress, age_seconds, min_age_seconds, seeding_time, seeding_time_limit)
        logging.info("Tracker URLs: %s", tracker_urls)

        has_target_tracker = any(
            any(target in url for target in target_trackers)
            for url in tracker_urls
        )
        logging.info("Target tracker match: %s", has_target_tracker)

        remove_by_tracker = seeding_time > seeding_time_limit and has_target_tracker
        remove_by_age = progress >= 100.0 and age_seconds >= min_age_seconds
        logging.info("Removal criteria: Tracker rule: %s, Age rule: %s",
                     remove_by_tracker, remove_by_age)

        if remove_by_tracker or remove_by_age:
            try:
                rpc_client.call("core.remove_torrent", torrent_hash, True)
                removed.append(name)
                logging.info("Removed torrent: '%s'", name)
            except Exception as err:
                logging.exception("Error removing torrent '%s': %s", name, err)
                not_removed.append(name)
        else:
            not_removed.append(name)
            logging.info("Not removing torrent: '%s'", name)
    return removed, not_removed


def run_removal_job():
    """Run the full removal job using only RPC and update the global summary."""
    global last_run_summary
    logging.info("----- Starting removal job -----")
    rpc_fields = ["name", "hash", "progress", "time_added", "seeding_time", "trackers"]
    rpc_client, rpc_torrents = connect_to_deluge_rpc(
        config["DELUGE_HOST"],
        config["DELUGE_PORT"],
        config["DELUGE_USERNAME"],
        config["DELUGE_PASSWORD"],
        rpc_fields
    )
    if rpc_client is None:
        logging.error("Failed to connect to RPC or retrieve torrents.")
        last_run_summary = "RPC retrieval failed."
        return "RPC retrieval failed."
    removed, not_removed = process_torrents_rpc(
        rpc_torrents,
        rpc_client,
        config["SEEDING_TIME_LIMIT"],
        config["MIN_AGE_SECONDS"],
        config["TARGET_TRACKERS"]
    )
    summary = ""
    if removed:
        summary += "Removed torrents:\n" + "\n".join(removed) + "\n"
    else:
        summary += "No torrents removed.\n"
    if not_removed:
        summary += "Torrents not removed:\n" + "\n".join(not_removed)
    else:
        summary += "All torrents were removed."
    logging.info("----- Finished removal job -----")
    last_run_summary = summary
    return summary


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Update configuration from the form.
        config["DELUGE_HOST"] = request.form.get("DELUGE_HOST", config["DELUGE_HOST"])
        config["DELUGE_PORT"] = int(request.form.get("DELUGE_PORT", config["DELUGE_PORT"]))
        config["DELUGE_USERNAME"] = request.form.get("DELUGE_USERNAME", config["DELUGE_USERNAME"])
        config["DELUGE_PASSWORD"] = request.form.get("DELUGE_PASSWORD", config["DELUGE_PASSWORD"])
        try:
            # The form provides values in hours and days.
            seeding_hours = int(request.form.get("SEEDING_TIME_LIMIT", config["SEEDING_TIME_LIMIT"] // 3600))
            min_age_days = int(request.form.get("MIN_AGE_DAYS", config["MIN_AGE_SECONDS"] // 86400))
            # Schedule interval in minutes; 0 means disabled.
            schedule_minutes = int(request.form.get("SCHEDULE_INTERVAL", config["SCHEDULE_INTERVAL"] // 60))
        except ValueError:
            flash("Please enter valid integer values for hours/days/schedule.", "danger")
            return redirect(url_for("index"))
        config["SEEDING_TIME_LIMIT"] = seeding_hours * 3600
        config["MIN_AGE_SECONDS"] = min_age_days * 86400
        config["SCHEDULE_INTERVAL"] = schedule_minutes * 60
        trackers = request.form.get("TARGET_TRACKERS", ",".join(config["TARGET_TRACKERS"]))
        config["TARGET_TRACKERS"] = [t.strip() for t in trackers.split(",") if t.strip()]

        action = request.form.get("action", "Update")
        flash("Configuration updated in memory.", "success")
        if action == "Save Configuration":
            save_config()
            flash("Configuration saved to file.", "success")
        # Update the scheduler with the new schedule.
        update_scheduler()
        return redirect(url_for("index"))
    else:
        load_config()

    seeding_hours = config["SEEDING_TIME_LIMIT"] // 3600
    min_age_days = config["MIN_AGE_SECONDS"] // 86400
    schedule_minutes = config["SCHEDULE_INTERVAL"] // 60

    # Use the global removal summary.
    summary = last_run_summary

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Seederr RPC Configuration</title>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
      <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
      <style>
        body {{
          padding-top: 70px;
        }}
        .output-box {{
          height: 300px;
          overflow-y: scroll;
          background-color: #f8f9fa;
          border: 1px solid #dee2e6;
          padding: 10px;
          font-family: monospace;
          font-size: 0.9em;
        }}
      </style>
    </head>
    <body>
      <nav class="navbar navbar-expand-lg navbar-dark bg-dark fixed-top">
        <a class="navbar-brand" href="/">Seederr RPC Configuration</a>
      </nav>
      <div class="container">
        <div class="row">
          <div class="col-md-6">
            <div class="card mb-4">
              <div class="card-header">
                Configuration
              </div>
              <div class="card-body">
                <form method="POST">
                  <div class="form-group">
                    <label>Deluge Host:</label>
                    <input type="text" name="DELUGE_HOST" class="form-control" value="{config['DELUGE_HOST']}">
                  </div>
                  <div class="form-group">
                    <label>Deluge Port:</label>
                    <input type="number" name="DELUGE_PORT" class="form-control" value="{config['DELUGE_PORT']}">
                  </div>
                  <div class="form-group">
                    <label>Deluge Username:</label>
                    <input type="text" name="DELUGE_USERNAME" class="form-control" value="{config['DELUGE_USERNAME']}">
                  </div>
                  <div class="form-group">
                    <label>Deluge Password:</label>
                    <input type="password" name="DELUGE_PASSWORD" class="form-control" value="{config['DELUGE_PASSWORD']}">
                  </div>
                  <div class="form-group">
                    <label>Seeding Time Limit (hours):</label>
                    <input type="number" name="SEEDING_TIME_LIMIT" class="form-control" value="{seeding_hours}">
                  </div>
                  <div class="form-group">
                    <label>Minimum Age for Completed Torrents (days):</label>
                    <input type="number" name="MIN_AGE_DAYS" class="form-control" value="{min_age_days}">
                  </div>
                  <div class="form-group">
                    <label>Target Trackers (comma separated):</label>
                    <input type="text" name="TARGET_TRACKERS" class="form-control" value="{','.join(config['TARGET_TRACKERS'])}">
                  </div>
                  <div class="form-group">
                    <label>Schedule Interval (minutes, 0 to disable):</label>
                    <input type="number" name="SCHEDULE_INTERVAL" class="form-control" value="{schedule_minutes}">
                  </div>
                  <div class="form-group">
                    <button type="submit" name="action" value="Update" class="btn btn-primary">Update</button>
                    <button type="submit" name="action" value="Save Configuration" class="btn btn-success">Save Configuration</button>
                  </div>
                </form>
                <form action="/run" method="POST">
                  <button type="submit" class="btn btn-danger">Run Removal Job</button>
                </form>
              </div>
            </div>
          </div>
          <div class="col-md-6">
            <div class="card">
              <div class="card-header">
                Recent Removal Summary
                <button onclick="location.reload()" class="btn btn-sm btn-secondary float-right">Refresh</button>
              </div>
              <div class="card-body output-box">
                <pre>{summary}</pre>
              </div>
            </div>
          </div>
        </div>
        <div class="row mt-4">
          <div class="col">
            <div class="card">
              <div class="card-header">
                Current Configuration (Internal Values)
              </div>
              <div class="card-body">
                <pre>{json.dumps(config, indent=4)}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>
      <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/popper.js@1.16.1/dist/umd/popper.min.js"></script>
      <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"></script>
    </body>
    </html>
    """


@app.route("/run", methods=["POST"])
def run_job():
    # Run the removal job in a separate thread and wait for it to complete.
    thread = Thread(target=run_removal_job)
    thread.start()
    thread.join()  # Wait for the thread to finish so that the summary is updated.
    flash("Removal job finished!", "info")
    return redirect(url_for("index"))


if __name__ == "__main__":
    load_config()  # Load persistent configuration if available.
    update_scheduler()  # Set up the scheduler based on the current config.
    app.run(host="0.0.0.0", port=5588)
