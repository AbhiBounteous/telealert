FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 #Disables Python output buffering
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY worker.py .
CMD ["python", "worker.py"]


# What Happens When You Run This Container
# Step-by-step:

# Docker starts container
# Worker script runs
# You’ll see:
# TeleAlert worker started


# Worker:

# Connects to DB
# Polls events every 5 seconds
# Processes events continuously