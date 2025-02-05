# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create the /data directory for persistent files
RUN mkdir -p /data

# Copy the rest of your application code into the container
COPY . .

# Expose the port that your Flask app runs on (default is 5588)
EXPOSE 5588

# Run the application
CMD ["python", "seederr.py"]
