# Seederr

Seederr is a Python-based automation tool to manage torrents in Deluge. It automatically removes torrents that have completed seeding after a user-defined period. Seederr connects to the Deluge Daemon RPC.

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Table of Contents
1. [Features](#features)
2. [Requirements](#requirements)
4. [Configuration](#installation)
5. [How It Works](#how-it-works)
6. [Contributing](#contributing)
7. [License](#license)

## Features

- **Web UI** – Configure everything from your browser  
- **Automated Cleanup** – Remove torrents after they exceed seeding limits  
- **Tracker-Based Rules** – Set specific trackers for early removal  
- **Scheduling** – Auto-run cleanup (e.g., hourly)  
- **Logs & Summaries** – View recent removals in the web interface  

## Requirements

- Python 3.8 or higher
- Deluge 2.0 or higher
- Access to Deluge Daemon RPC
- Optional: Docker for containerized deployment

## Installation  
### **Run with Docker**  

```sh
docker run -d -p 5588:5588 -v /path/to/config:/data --name seederr f0rm/seederr:latest
```

- Access the web UI at **[http://localhost:5588](http://localhost:5588)**  
- Configure **Deluge RPC**, **seeding limits**, and **scheduling** in the settings  
- Logs and settings are stored in `/data/` (persistent across restarts)

### Run with Docker

1. **Pull the Docker image:**

   ```sh
   docker pull f0rm/seederr:latest
   ```

2. **Run the container:**

   ```sh
docker run -d \
  --name seederr \
  -p 5588:5588 \
  -v /path/to/config:/data \
  --restart unless-stopped \
  f0rm/seederr:latest
   ```

---

### Use with Docker Compose

To simplify deployment and configuration, you can use **Docker Compose**. Below is an example `docker-compose.yml` file:

```yaml
version: "3.8"

services:
  seederr:
    image: f0rm/seederr:latest
    container_name: seederr
    restart: unless-stopped
    ports:
      - "5588:5588"
    volumes:
      - /path/to/config:/data
```
## How It Works

1. Connects to **Deluge RPC** and retrieves torrents  
2. Removes torrents that exceed **seeding time limits** (default: **14 days**)  
3. Deletes torrents from **specific trackers** after a shorter time (default: **80 hours**)  
4. Runs **on-demand** or on a **schedule** 

## Contributing

Feel free to open issues or submit pull requests.

## License

This project is licensed under the MIT License.
