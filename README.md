# Seederr

Seederr is a Python-based automation tool to manage torrents in Deluge. It automatically removes torrents that have completed seeding after a user-defined period. Seederr connects to the Deluge WebUI and Daemon RPC to provide seamless torrent management with detailed logging.

## Features

- Automatically removes torrents based on seeding time and progress.
- Supports Deluge WebUI and Daemon RPC.
- Detailed logs for monitoring and troubleshooting.
- Configurable settings for connection details and thresholds.
- Works with cron for scheduled execution.

## Requirements

- Python 3.8 or higher
- Deluge 2.0 or higher with WebUI enabled
- Access to Deluge WebUI and Daemon RPC
- Optional: Docker for containerized deployment

## Installation

Docker Pull Command
   
```docker pull f0rm/seederr```

or

1. Clone the repository:
    ```
   git clone https://github.com/f0rmwk/seederr.git
   cd seederr
3. Install dependencies:
   
   `pip install -r requirements.txt`

## Configuration

Edit the script or `.env` file with your Deluge connection details:
```
DELUGE_WEBUI_URL=http://your-deluge-url:8112
DELUGE_WEBUI_PASSWORD=your-webui-password
DELUGE_DAEMON_HOST=your-deluge-daemon-ip
DELUGE_DAEMON_PORT=58846
DELUGE_DAEMON_USERNAME=localclient
DELUGE_DAEMON_PASSWORD=your-daemon-password
MIN_SEED_TIME_SECONDS=1209600  # Two weeks in seconds
LOG_FILE_PATH=/path/to/seederr.log
```

## Usage

### Run the Script Manually

   python3 seederr.py

### Schedule with Cron

1. Open the crontab editor:
   `crontab -e`

2. Add a cron job to run the script daily:
   `0 0 * * * /usr/bin/python3 /path/to/seederr.py >> /path/to/seederr_cron.log 2>&1`

### Run with Docker

1. Build the Docker image:
   `docker build -t seederr .`
   
### Scheduling the Script
By default, the script runs hourly. You can configure the frequency by setting the `SEEDERR_CRON_SCHEDULE` environment variable.

2. Run the container:
   ```
   docker run -d --name seederr \
       -e SEEDERR_CRON_SCHEDULE="*/0 * * * *" \
       -e DELUGE_WEBUI_URL=http://your-deluge-url:8112 \
       -e DELUGE_WEBUI_PASSWORD=your-webui-password \
       -e DELUGE_DAEMON_HOST=your-deluge-daemon-ip \
       -e DELUGE_DAEMON_PORT=58846 \
       -e DELUGE_DAEMON_USERNAME=localclient \
       -e DELUGE_DAEMON_PASSWORD=your-daemon-password \
       -e MIN_SEED_TIME_SECONDS=1209600 \
       -v /path/to/logs:/app/logs \
       seederr
### Docker-Compose.yml
```
version: "3.8"

services:
  seederr:
    image: f0rm/seederr:latest
    container_name: seederr
    restart: unless-stopped
    environment:
      # Set Deluge WebUI configuration
      DELUGE_WEB_URL: "http://localhost:8112"        # Update with your Deluge WebUI URL
      DELUGE_WEB_PASSWORD: "your_web_password"       # Replace with your WebUI password

      # Set Deluge daemon RPC configuration
      DELUGE_HOST: "localhost"                   # Replace with your Deluge daemon IP
      DELUGE_PORT: "58846"                           # Default port for Deluge daemon
      DELUGE_USERNAME: "localclient"                 # Replace if different
      DELUGE_PASSWORD: "your_rpc_password"           # Replace with your daemon password

      # Set the minimum seeding age before removal
      MIN_AGE_SECONDS: "1209600"                     # Default: 14 days (in seconds)

      # Optional: Customize the cron schedule for running seederr
      SEEDERR_CRON_SCHEDULE: "0 * * * *"             # Default: Run every hour

    volumes:
      - ./seederr_data:/app                          # Volume for logs and persistent data
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```
## Logs

Logs are stored in the location specified in the `LOG_FILE_PATH` variable. Ensure the path is writable.

## Contributing

We welcome contributions! Feel free to open issues or submit pull requests.

## License

This project is licensed under the MIT License.
