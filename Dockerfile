# Use a Python base image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the local files to the container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set the default command to run the script
CMD ["python", "seederr.py"]

# Install cron
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# Copy the crontab file
COPY crontab /etc/cron.d/seederr-cron

# Set permissions for the crontab file
RUN chmod 0644 /etc/cron.d/seederr-cron

# Apply the crontab
RUN crontab /etc/cron.d/seederr-cron

# Start cron in the background
CMD ["cron", "-f"]
