#FROM python:3.11-slim
#ENV PYTHONUNBUFFERED=1 
#WORKDIR /app
#COPY requirements.txt .
#RUN pip install --no-cache-dir -r requirements.txt
#COPY worker.py .
#CMD ["python", "worker.py"]


# What Happens When You Run This Container
# Step-by-step:

# Docker starts container
# Worker script runs
# You’ll see:
# TeleAlert worker started
# Python output buffering ENV PYTHONUNBUFFERED=1 disable

# Worker:

# Connects to DB
# Polls events every 5 seconds
# Processes events continuously
FROM python:3.11-slim

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python3 -c "import psycopg2" || exit 1

ENV PYTHONUNBUFFERED=1

CMD ["python", "worker.py"]