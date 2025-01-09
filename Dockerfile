# Use a Python base image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the local files to the container
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install cron
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# Set up an environment variable for the cron schedule
ENV SEEDERR_CRON_SCHEDULE="0 * * * *"

# Dynamically create the crontab file from the environment variable
RUN echo "$SEEDERR_CRON_SCHEDULE python3 /app/seederr.py >> /app/seederr.log 2>&1" > /etc/cron.d/seederr-cron

# Set permissions for the crontab file
RUN chmod 0644 /etc/cron.d/seederr-cron

# Apply the crontab
RUN crontab /etc/cron.d/seederr-cron

# Expose a volume for logs (optional, so logs persist outside the container)
VOLUME /app/seederr.log

# Start cron in the foreground
CMD ["cron", "-f"]
