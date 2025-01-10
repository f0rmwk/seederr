# Seederr

Seederr is a Python-based automation tool to manage torrents in Deluge. It automatically removes torrents that have completed seeding after a user-defined period. Seederr connects to the Deluge WebUI and Daemon RPC to provide seamless torrent management with detailed logging.

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Table of Contents
1. [Features](#features)
2. [Requirements](#requirements)
4. [Configuration](#configuration)
5. [Usage](#usage)
    - [Run the Script Manually](#run-the-script-manually)
    - [Run with Docker](#run-with-docker)
6. [How It Works](#how-it-works)
7. [Contributing](#contributing)
8. [License](#license)

## Features

- Automatically removes torrents based on seeding time and progress.
- Supports Deluge WebUI and Daemon RPC.
- Configurable settings for connection details and thresholds.

## Requirements

- Python 3.8 or higher
- Deluge 2.0 or higher with WebUI enabled
- Access to Deluge WebUI and Daemon RPC
- Optional: Docker for containerized deployment

## Configuration

Seederr is configured using environment variables. Below is a list of variables you can set:

| Variable               | Default Value           | Description                                      |
|------------------------|-------------------------|--------------------------------------------------|
| `DELUGE_WEB_URL`       | `http://127.0.0.1:8112` | URL of the Deluge WebUI.                        |
| `DELUGE_WEB_PASSWORD`  | `your_deluge_web_password`| Password for the Deluge WebUI.                 |
| `DELUGE_DAEMON_HOST`   | `127.0.0.1`            | Hostname or IP address of the Deluge daemon.    |
| `DELUGE_DAEMON_PORT`   | `58846`                | Port number for the Deluge daemon.             |
| `DELUGE_DAEMON_USERNAME` | `localclient`        | Username for the Deluge daemon.                |
| `DELUGE_DAEMON_PASSWORD` | `your_daemon_password` | Password for the Deluge daemon.                |
| `MIN_AGE_SECONDS`      | `1209600`              | Minimum seeding time (in seconds) before removal. |
| `TASK_INTERVAL_SECONDS` | `300`                | Interval (in seconds) at which the script runs. |

Edit the script or create a `.env` file with your configuration.

## Usage

### Run the Script Manually

Run the script directly:
```bash
python3 seederr.py
```

### Run with Docker

1. Pull the Docker image:
   ```bash
   docker pull f0rm/seederr:latest
   ```

2. Run the container:
   ```bash
   docker run -d --name seederr \
       -e DELUGE_WEB_URL=http://your-deluge-url:8112 \
       -e DELUGE_WEB_PASSWORD=your-webui-password \
       -e DELUGE_DAEMON_HOST=your-deluge-daemon-ip \
       -e DELUGE_DAEMON_PORT=58846 \
       -e DELUGE_DAEMON_USERNAME=localclient \
       -e DELUGE_DAEMON_PASSWORD=your-daemon-password \
       -e MIN_AGE_SECONDS=604800 \
       -e TASK_INTERVAL_SECONDS=300 \
       seederr
   ```

   By default, the script runs every 5 minutes. Customize the interval using the `TASK_INTERVAL_SECONDS` environment variable.

### Use with Docker Compose

To simplify deployment and configuration, you can use Docker Compose. Below is an example `docker-compose.yml` file:

```yaml
version: "3.8"

services:
  seederr:
    build:
    image: f0rm/seederr:latest
    container_name: seederr
    environment:
      - DELUGE_WEB_URL=http://0.0.0.0:8112
      - DELUGE_WEB_PASSWORD=your_deluge_web_password
      - DELUGE_HOST=0.0.0.0
      - DELUGE_PORT=58846
      - DELUGE_USERNAME=localclient
      - DELUGE_PASSWORD=your_daemon_password
      - MIN_AGE_SECONDS=604800
      - TASK_INTERVAL_SECONDS=300
    restart: unless-stopped
```

## How It Works

1. Seederr connects to the Deluge WebUI and Daemon using the provided credentials.
2. It fetches the list of torrents and checks their progress and age.
3. Torrents meeting the configured criteria (e.g., completed seeding for more than 2 weeks) are automatically removed.
4. Logs are generated to provide detailed information about script activity.

## Contributing

Feel free to open issues or submit pull requests.

## License

This project is licensed under the MIT License.
