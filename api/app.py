from flask import Flask, request, jsonify
from prometheus_client import Counter, generate_latest
import psycopg2
import os

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.sdk.resources import Resource

resource = Resource.create({
    "service.name": "telealert-api",
    "service.version": "1.2",
    "deployment.environment": os.getenv("ENVIRONMENT", "production")
})

provider = TracerProvider(resource=resource)

otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "http://jaeger:4318/v1/traces"
    )
)

processor = BatchSpanProcessor(otlp_exporter)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("telealert.api")

app = Flask(__name__)

FlaskInstrumentor().instrument_app(app)
Psycopg2Instrumentor().instrument()

EVENTS = Counter(
    'network_events_total',
    'Total network events',
    ['severity']
)

def get_db():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'postgres'),
        database=os.getenv('DB_NAME', 'telealert'),
        user=os.getenv('DB_USER', 'admin'),
        password=os.getenv('DB_PASSWORD', 'password')
    )

@app.route('/health')
def health():
    return jsonify({
        "status": "ok",
        "service": "telealert-api",
        "version": "1.2",
        "tracing": "enabled"
    })

@app.route('/event', methods=['POST'])
def receive_event():
    with tracer.start_as_current_span("receive_event") as span:
        data = request.json
        severity = data.get('severity', 'low')
        node_id = data.get('node_id', 'unknown')

        span.set_attribute("event.severity", severity)
        span.set_attribute("event.node_id", node_id)
        span.set_attribute("event.message",
                          data.get('message', ''))

        EVENTS.labels(severity=severity).inc()

        with tracer.start_as_current_span("db_insert"):
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO events "
                "(node_id, severity, message) "
                "VALUES (%s, %s, %s)",
                (node_id, severity,
                 data.get('message', ''))
            )
            conn.commit()
            conn.close()

        return jsonify({
            "status": "received",
            "severity": severity,
            "traced": True
        })

@app.route('/metrics')
def metrics():
    return generate_latest()

@app.route('/alerts')
def get_alerts():
    with tracer.start_as_current_span("get_alerts"):
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM events "
            "WHERE severity='critical' "
            "ORDER BY created_at DESC LIMIT 10"
        )
        rows = cur.fetchall()
        conn.close()
        return jsonify({"alerts": rows})

@app.route('/status')
def status():
    with tracer.start_as_current_span("get_status"):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM events")
        total = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM events "
            "WHERE severity='critical'"
        )
        critical = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM events "
            "WHERE processed=true"
        )
        processed = cur.fetchone()[0]
        conn.close()
        return jsonify({
            "service": "telealert-api",
            "version": "1.2",
            "stats": {
                "total_events": total,
                "critical_events": critical,
                "processed_events": processed
            }
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)