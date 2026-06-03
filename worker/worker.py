import psycopg2, os, time, sys #psycopg2 → Connect to PostgreSQL os → Read environment variables time → Add delay (sleep) random → (not used here, can be removed)

def get_db(): #Connects to PostgreSQL using env variables Uses defaults if env vars are missing 👉 Same logic as your API — reusable connection method
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'postgres'),
        database=os.getenv('DB_NAME', 'telealert'),
        user=os.getenv('DB_USER', 'admin'),
        password=os.getenv('DB_PASSWORD', 'password')
    )

def process_events():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, node_id, severity, message FROM events "
        "WHERE processed=false LIMIT 5" #Retrieves up to 5 unprocessed events ,This avoids reprocessing the same data
    )
    events = cur.fetchall()
    for event in events:
        id, node_id, severity, message = event
        print(f"Processing event {id}: node={node_id} severity={severity}", flush=True) #Print the processoing info

        if severity == 'critical': #if severity is critical then sends alert message ,in real system u can send the alert mail or slack notification

            print(f"CRITICAL ALERT: Node {node_id} — {message}", flush=True)
    if events:
        cur.execute(
            "UPDATE events SET processed=true WHERE id = ANY(%s)", #Prevents reprocessing same event again
            ([e[0] for e in events],)
        )
    conn.commit()
    conn.close()
    return len(events) #Returns number of processed events

if __name__ == '__main__': #This ensures the script runs only when executed directly.
    print("TeleAlert worker started", flush=True)
    while True:
        try:
            count = process_events()
            if count > 0:
                print(f"Processed {count} events", flush=True)
        except Exception as e:
            print(f"Waiting for DB: {e}", flush=True)
        sys.stdout.flush()
        time.sleep(5)

#          How it fits your system:


# API Service (/event)

# Inserts events into DB (processed = false)



# Worker Service (this script)

# Reads unprocessed events
# Processes them
# Marks them processed = true

#  Batch processing (LIMIT 5)
# ✔ Prevents duplicate processing
# ✔ Handles failures gracefully
# ✔ Runs continuously
# ✔ Simple alerting logic

# You use a worker to separate event processing from event ingestion.

# app.py → receives and stores events (fast)
# worker.py → processes events (can be slow/complex)

# 👉 app.py = "Receiver"
# 👉 worker.py = "Processor"
# API → collect events
# Worker → act on events

# ✅ Step-by-step Architecture:
# 1. API (app.py)

# Only does:

# Receive event
# Store in DB
# Return fast response



# ✔ Fast
# ✔ Lightweight
# ✔ Scalable

# 2. Worker (worker.py)

# Runs in background
# Handles:

# Processing logic
# Alerts
# heavy operations



# ✔ Decoupled
# ✔ Reliable
# ✔ Scalable independently