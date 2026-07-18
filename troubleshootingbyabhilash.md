TROUBLESHOOTING THE Issue :-
— Worker logs not visible in real time
Root cause
Python by default buffers its print output — it collects output in memory and only writes it to the console in large chunks, not immediately. This means when the worker called print(...), the text was sitting in a buffer inside the container and never flushed to Docker's log stream in real time.
Two fixes applied
Fix 1 — Added flush=True to every print statement in worker.py
python
# Before — output buffered, never appeared in logs
print(f"Processing event {id}: node={node_id} severity={severity}")

# After — output flushed immediately to Docker logs
print(f"Processing event {id}: node={node_id} severity={severity}", flush=True)
Also added sys.stdout.flush() at the end of the main loop for extra safety.

Fix 2 — Added PYTHONUNBUFFERED=1 to worker/Dockerfile
dockerfile
# Before
FROM python:3.11-slim
WORKDIR /app
...

# After
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1   ← this line was added
WORKDIR /app
...
This environment variable tells Python to completely disable output buffering at the interpreter level — so every print() anywhere in the code writes immediately without needing flush=True.
The golden rule to remember
Any Python app running inside Docker must have PYTHONUNBUFFERED=1 set — otherwise logs are invisible in real time.
This applies to every Python container you ever build — Flask apps, workers, scripts, everything.
# Rebuilt the worker image from scratch with the fix baked in
docker-compose up -d --build worker

# Terminal 1 — live log stream
docker-compose logs worker -f

# Terminal 2 — sent a test event
curl -X POST http://localhost:5000/event ...

=====PLEASE REFER THE BELOW CODE WHERE THE FIX HAS BEEN WORKED OUT SUCCESSFULLY=====

CODE:-
Fix — Add unbuffered output to worker
Open worker/worker.py in VS Code and replace the entire file with this:
import psycopg2, os, time, sys

def get_db():
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
        "WHERE processed=false LIMIT 5"
    )
    events = cur.fetchall()
    for event in events:
        id, node_id, severity, message = event
        print(f"Processing event {id}: node={node_id} severity={severity}", flush=True)
        if severity == 'critical':
            print(f"CRITICAL ALERT: Node {node_id} — {message}", flush=True)
    if events:
        cur.execute(
            "UPDATE events SET processed=true WHERE id = ANY(%s)",
            ([e[0] for e in events],)
        )
    conn.commit()
    conn.close()
    return len(events)

if __name__ == '__main__':
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
        
The key change is flush=True on every print — this forces output to appear immediately.

Also fix the Dockerfile to disable Python buffering
Open worker/Dockerfile in VS Code and replace it with:

FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY worker.py .
CMD ["python", "worker.py"]
The PYTHONUNBUFFERED=1 line is the key fix — it tells Python never to buffer output.

Rebuild and restart
bashdocker-compose up -d --build worker
Wait 5 seconds then follow logs live:
bashdocker-compose logs worker -f
In a second terminal send an event:
bashcurl -X POST http://localhost:5000/event \
  -H "Content-Type: application/json" \
  -d '{"node_id": "NODE-DEL-005", "severity": "critical", "message": "Tower down in Delhi"


=============================================================================================
NEXT TROUBLESHOOTING ISSUE:-

after pasting the command:-curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg i can see that the prompt seems to be stucked please provide the fix
Corporate SSL is blocking it again — same issue as the Helm install. Use the -k flag to bypass it: but it got stucked again,Now try to create an account of bounteous as mail id in github.com
Your corporate network is completely blocking GitHub downloads — not just SSL, but the connection itself times out. The good news is you don't need the GitHub CLI at all. Plain git commands do everything we need.



=========================================================================================
CI/CD Pipeline — Fixes applied:
1. GHCR image tags must be fully lowercase — replaced
   ${{ github.repository_owner }} with hardcoded abhibounteous
2. Dockerfile comments with # caused buildx ENV parsing error —
   removed all comment lines from Dockerfiles
   
=========================================================================================
## Session 1 — Phase 1
- Installed WSL2, Docker, Kind, Claude SDK
- Fixed corporate SSL issue with -k flag
- Cluster running with 3 nodes

## Session 2 — Phase 2A/B
- Built TeleAlert 3-service app
- Pushed to GitHub via SSH over port 443
- CI/CD pipeline green in 63 seconds

## Session 3 — Phase 2C/D
- Deployed to Kubernetes
- Scaled, rolled out, rolled back
- Grafana dashboard live

## Session 4 — Phase 3
- Claude diagnosed fiber cut with 85% confidence
- Autonomous agent made 8 tool calls
- Cluster scaled without human input
This daily log becomes your interview story.
✅ DevOps engineer interviews
✅ Bounteous × Telecom & Media Practice
✅ Claude Architect Certification
✅ AI-powered operations roles
## OPA Gatekeeper on Kind
Problem: Webhook not blocking deployments in default namespace
Root cause: Kind cluster webhook networking limitation
Evidence: constraint_status=enforced in logs but webhook not intercepting
Fix: Use EKS/GKE for production Gatekeeper testing
Workaround: Use dryrun mode to audit violations

## Kibana Readiness Probe Failing on Kind
Problem: Kibana 0/1 ready, readiness probe timeout
Root cause: Memory pressure on 34-day cluster
            running 15+ components simultaneously
Evidence: Event loop blocked 15234ms in logs
Fix: Use dedicated cluster with 8GB+ RAM
     Or reduce other workloads first
     Works correctly on EKS/GKE with proper resources

## Docker restart breaks DNS (July 2026)
Problem: API 500 after Docker Desktop restart
Root cause: Network policies blocking DNS port 53
Fix 1: Delete network policies temporarily
Fix 2: Restart kindnet CNI daemonset
Fix 3: Restart CoreDNS deployment
Fix 4: Delete API pods to get fresh DNS

## protobuf version conflict
Problem: Docker build fails
Error: opentelemetry-proto requires protobuf<5.0
Fix: Use protobuf>=3.19,<5.0 in requirements.txt

## Two clusters consuming 993% CPU
Problem: Docker Desktop overloaded
Root cause: devops-lab + telealert-tf running together
Fix: kind delete cluster --name telealert-tf
