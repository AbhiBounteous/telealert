from flask import Flask, request, jsonify
from prometheus_client import Counter, generate_latest
import psycopg2, os

app = Flask(__name__) # app initialisation Creates a Flask application instance 
EVENTS = Counter('network_events_total', 'Total network events', ['severity']) #prometheus matrics,A counter metric named network_events_total ,Tracks total events based on severity labels

def get_db(): #database connection function ,Creates a connection to PostgreSQL
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'postgres'),
        database=os.getenv('DB_NAME', 'telealert'),
        user=os.getenv('DB_USER', 'admin'),
        password=os.getenv('DB_PASSWORD', 'password')
    )

@app.route('/health') #Endpoint: GET /health,Load balancers,Kubernetes readiness/liveness probes
def health():
    return jsonify({"status": "ok", "service": "telealert-api"})

@app.route('/event', methods=['POST']) #receive event api
def receive_event():
    data = request.json #Read incoming JSON
    severity = data.get('severity', 'low') #Extract severity
    EVENTS.labels(severity=severity).inc() #Increments metric count for given severity
    conn = get_db()#Inserts event into events table 
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO events (node_id, severity, message) VALUES (%s, %s, %s)",#Uses parameterized query
        (data['node_id'], severity, data['message'])
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "received", "severity": severity}) #Send response

@app.route('/metrics') #Endpoint: GET /metrics,Returns Prometheus metrics
def metrics():
    return generate_latest()

@app.route('/alerts') 
def get_alerts(): #Fetches last 10 critical events
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, node_id, severity, message, created_at::text FROM events "
        "WHERE severity='critical' ORDER BY created_at DESC LIMIT 10" #used for Dashboard,alert monitoring system

    )
    rows = cur.fetchall()
    conn.close()
    return jsonify({"alerts": rows})


#We have added  this below new endpoint just for the sake of another example to see how pipeline works

@app.route('/status')
def status():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM events")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM events WHERE severity='critical'")
    critical = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM events WHERE processed=true")
    processed = cur.fetchone()[0]
    conn.close()
    return jsonify({
        "service": "telealert-api",
        "version": "1.1",
        "stats": {
            "total_events": total,
            "critical_events": critical,
            "processed_events": processed
        }
    })

#We have added  this above new endpoint just for the sake of another example to see how pipeline works

if __name__ == '__main__':             #Host: all interfaces (0.0.0.0),Port: 5000
    app.run(host='0.0.0.0', port=5000)

    #This service acts like a mini observability + alerting backend:
#     🔄 Flow:

# Client sends event → /event
# Event:

# Stored in DB
# Counted in Prometheus


# Prometheus scrapes → /metrics
# Alerts dashboard fetches → /alerts
# Health check via → /health

#KEY FEATURES
# REST API using Flask
# ✔ PostgreSQL data storage
# ✔ Prometheus monitoring integration
# ✔ Alert querying support
# ✔ Environment-based configuration
