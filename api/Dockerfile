#FROM python:3.11-slim   
#WORKDIR /app
#COPY requirements.txt .
#RUN pip install --no-cache-dir -r requirements.txt
#COPY app.py .
#EXPOSE 5000
#CMD ["python", "app.py"]


#FROM python:3.11-slim

#RUN apt-get update && \
   # apt-get upgrade -y && \
  #  apt-get clean && \
 #   rm -rf /var/lib/apt/lists/*

#WORKDIR /app
#COPY requirements.txt .
#RUN pip install -r requirements.txt
#COPY . .
#CMD ["python", "app.py"]

# Uses an official Python 3.11 lightweight image ,Smaller size → faster downloads ,The python:3.11-slim image on Docker Hub is an official
# Sets /app as the working directory inside the container,All next commands run inside /app
# Copies requirements.txt from your local machine → container, local: requirements.txt → container: /app/requirements.txt
# Prevents storing temporary files → reduces image size for --no-cache-dir
#Copies your Flask app into the container(COPY app.py .) local: app.py → container: /app/app.p
#EXPOSE 5000 tells docker to "This container listens on port 5000"
# Runs your Flask app when container starts CMD ["python", "app.py"]--> python app.py

# Step-by-step:

# Docker pulls Python image
# Creates /app directory
# Copies requirements.txt
# Installs dependencies (Flask, psycopg2, Prometheus)
# Copies app.py
# Starts your API using:


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
  CMD python3 -c "import requests; requests.get('http://localhost:5000/health')" || exit 1

ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]