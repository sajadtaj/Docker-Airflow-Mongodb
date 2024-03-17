# Use the official Airflow image
FROM apache/airflow:2.8.3

# Copy requirements.txt to the container
COPY requirements.txt /requirements.txt

# Install additional Python packages
RUN pip install --no-cache-dir -r /requirements.txt
