import anthropic
import chromadb
import json
import os
from datetime import datetime

client = anthropic.Anthropic(timeout=120.0)
MODEL = "claude-sonnet-4-6"

chroma_client = chromadb.Client()
collection = chroma_client.create_collection(
    name="telealert_knowledge"
)

KNOWLEDGE_BASE = [
    {
        "id": "inc001",
        "type": "incident_report",
        "title": "INC-BOM-20260604 Mumbai Fiber Cut",
        "content": """Incident ID: INC-BOM-20260604
Date: 2026-06-04 12:07 UTC
Severity: Critical
Affected: NODE-BOM-01 through NODE-BOM-010
Root cause: Physical fiber duct damage on Western
Express Highway near Andheri. Construction excavation
by contractor cut through underground fiber conduit.
Two burst events 14 minutes apart — both on same
physical route. Resolution: Field team dispatched,
temporary bypass activated, permanent repair in 6h.
Prevention: Added geofencing alerts for construction
near fiber routes."""
    },
    {
        "id": "inc002",
        "type": "incident_report",
        "title": "INC-DEL-20260510 Delhi Tower Outage",
        "content": """Incident ID: INC-DEL-20260510
Date: 2026-05-10 08:30 UTC
Severity: High
Affected: NODE-DEL-001 through NODE-DEL-007
Root cause: Power failure at Delhi data center
due to UPS battery failure during grid maintenance.
Backup generator failed to start automatically.
Resolution: Manual generator start, power restored
in 45 minutes. Prevention: Monthly UPS battery
testing, generator auto-start verification added
to maintenance checklist."""
    },
    {
        "id": "inc003",
        "type": "incident_report",
        "title": "INC-PNE-20260415 Pune Packet Loss",
        "content": """Incident ID: INC-PNE-20260415
Date: 2026-04-15 14:00 UTC
Severity: Medium
Affected: NODE-PNE-001 through NODE-PNE-003
Root cause: BGP routing misconfiguration after
network upgrade. Packet loss 15-30% on uplink.
Resolution: BGP config rolled back, routing
stabilized in 20 minutes. Prevention: Staging
environment validation mandatory before production
network changes."""
    },
    {
        "id": "run001",
        "type": "runbook",
        "title": "Fiber Cut Response Runbook",
        "content": """RUNBOOK: Fiber Cut Response
Trigger: Multiple NODE-BOM critical alerts in burst

Step 1: Identify burst pattern
- Check if alerts are sequential (2s apart)
- Sequential = physical fiber cut
- Random = software or config issue

Step 2: Identify affected route
- NODE-BOM-01 to 05 = Southern route
- NODE-BOM-06 to 010 = Northern route
- Both routes = trunk cut at Andheri junction

Step 3: Immediate actions
- Scale telealert-worker to 3 replicas
- kubectl scale deployment telealert-worker --replicas=3
- Activate backup fiber route if available
- Dispatch field team to Andheri junction

Step 4: Communication
- Notify NOC lead within 5 minutes
- Update status page
- Send Slack alert to #network-alerts

Step 5: Resolution
- Field team confirms physical damage
- Temporary bypass activation
- Permanent repair scheduling
- Update incident ticket"""
    },
    {
        "id": "run002",
        "type": "runbook",
        "title": "Kubernetes ImagePullBackOff Runbook",
        "content": """RUNBOOK: ImagePullBackOff Resolution
Trigger: Pod stuck in ImagePullBackOff state

Step 1: Identify the bad image
kubectl describe pod <pod-name>
Look for: Failed to pull image error message

Step 2: Check if image exists in GHCR
Go to github.com/AbhiBounteous?tab=packages
Verify image tag exists

Step 3: Quick fix — rollback deployment
kubectl rollout undo deployment/<deployment-name>
This restores the previous working image

Step 4: Fix the root cause
- If bad tag: fix the image tag in ci-cd.yaml
- If auth issue: verify CR_PAT secret in GitHub
- If missing image: rebuild and push via git push

Step 5: Verify recovery
kubectl get pods
All pods should show Running status

Prevention: Add image validation step to CI/CD
pipeline before push to GHCR"""
    },
    {
        "id": "run003",
        "type": "runbook",
        "title": "High Critical Event Rate Runbook",
        "content": """RUNBOOK: High Critical Event Rate
Trigger: Critical events > 50% of total events

Step 1: Check if genuine incident
- Query recent alerts: curl localhost:5001/alerts
- Look for pattern: same node or same region
- Pattern = genuine incident
- Random nodes = threshold misconfiguration

Step 2: If genuine incident
- Run incident bot: python3 ai-ops/incident_bot.py
- Check Grafana dashboard for spike timing
- Correlate with recent deployments or changes

Step 3: Scale up worker for processing capacity
kubectl scale deployment telealert-worker --replicas=3

Step 4: If threshold misconfiguration
- Review alert severity logic in worker.py
- Check if severity classification is correct
- Adjust if needed and redeploy

Step 5: Monitor until rate drops below 20%"""
    },
    {
        "id": "arch001",
        "type": "architecture",
        "title": "TeleAlert Architecture Document",
        "content": """ARCHITECTURE: TeleAlert System
Version: 1.2 | Updated: 2026-06-09

Services:
1. telealert-api (Flask, port 5000)
   - Receives network events via POST /event
   - Exposes Prometheus metrics via GET /metrics
   - Returns alerts via GET /alerts
   - Health check via GET /health

2. telealert-worker (Python)
   - Polls PostgreSQL every 5 seconds
   - Processes unprocessed events
   - Fires CRITICAL ALERT for severity=critical
   - Marks events as processed

3. PostgreSQL (port 5432)
   - Table: events
   - Columns: id, node_id, severity, message,
     processed, created_at

4. Prometheus (port 9090)
   - Scrapes telealert-api every 15 seconds
   - Metric: network_events_total{severity}

5. Grafana (port 3000)
   - Dashboard: TeleAlert Network Operations
   - Panels: Total events, Critical alerts,
     Events rate per minute

Kubernetes: Kind cluster, 3 nodes
CI/CD: GitHub Actions, builds in 60 seconds
Registry: GHCR (ghcr.io/abhibounteous)"""
    },
    {
        "id": "kb001",
        "type": "knowledge",
        "title": "Mumbai Network Topology",
        "content": """KNOWLEDGE: Mumbai BOM Network Topology

NODE-BOM-01 to NODE-BOM-05: Southern fiber route
- Physical path: Andheri to Bandra via coastal road
- Shared conduit with NODE-BOM-06 to 010 at Andheri
- junction point

NODE-BOM-06 to NODE-BOM-010: Northern fiber route
- Physical path: Andheri to Goregaon via highway
- High risk: Western Express Highway construction zone

Common failure points:
1. Andheri junction: Both routes share this point
2. WEH construction zone: Active digging risk
3. Monsoon flooding: June-September flash floods

Historical pattern: Burst failures always start
from NODE-BOM-06 or NODE-BOM-01 — never the middle.
This confirms failures start at route endpoints."""
    }
]

def load_knowledge_base():
    """Load all documents into ChromaDB"""
    print("📚 Loading knowledge base into vector store...")

    documents = []
    metadatas = []
    ids = []

    for doc in KNOWLEDGE_BASE:
        documents.append(doc["content"])
        metadatas.append({
            "type": doc["type"],
            "title": doc["title"],
            "id": doc["id"]
        })
        ids.append(doc["id"])

    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

    print(f"✅ Loaded {len(KNOWLEDGE_BASE)} documents")
    print("\nDocument types:")
    types = {}
    for doc in KNOWLEDGE_BASE:
        types[doc["type"]] = types.get(
            doc["type"], 0
        ) + 1
    for t, count in types.items():
        print(f"  {t}: {count} documents")

def search_knowledge(query, n_results=3):
    """Search knowledge base for relevant documents"""
    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, len(KNOWLEDGE_BASE))
    )

    docs = []
    for i in range(len(results["documents"][0])):
        docs.append({
            "content": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i]
        })
    return docs

def ask_with_rag(question):
    """Answer question using RAG"""
    print(f"\n{'='*60}")
    print(f"❓ Question: {question}")
    print(f"{'='*60}")

    print("\n🔍 Searching knowledge base...")
    relevant_docs = search_knowledge(question)

    print(f"Found {len(relevant_docs)} relevant documents:")
    for doc in relevant_docs:
        title = doc["metadata"]["title"]
        distance = doc["distance"]
        print(f"  📄 {title} (relevance: {1-distance:.2f})")

    context = "\n\n".join([
        f"[{doc['metadata']['title']}]\n{doc['content']}"
        for doc in relevant_docs
    ])

    prompt = f"""You are a NOC knowledge assistant for 
TeleAlert at Bounteous × Telecom & Media Practice.

Answer the question using ONLY the provided context.
If the answer is not in the context say so clearly.
Reference specific document titles when relevant.

CONTEXT FROM KNOWLEDGE BASE:
{context}

QUESTION: {question}

Answer clearly and specifically. Reference which
document your answer comes from."""

    print("\n🤖 Claude is generating answer from knowledge base...")

    message = client.messages.create(
        model=MODEL,
        max_tokens=600,
        messages=[{
            "role": "user",
            "content": prompt
        }]
    )

    answer = message.content[0].text
    print(f"\n💡 ANSWER:\n{answer}")
    return answer

def interactive_rag():
    """Interactive Q&A with knowledge base"""
    print("\n" + "="*60)
    print("🧠 TELEALERT RAG KNOWLEDGE BASE")
    print("Ask questions about incidents, runbooks, architecture")
    print("Type 'list' to see all documents")
    print("Type 'exit' to quit")
    print("="*60 + "\n")

    while True:
        question = input("\nYou: ").strip()

        if not question:
            continue

        if question.lower() == "exit":
            print("Goodbye!")
            break

        if question.lower() == "list":
            print("\n📚 Documents in knowledge base:")
            for doc in KNOWLEDGE_BASE:
                print(f"  [{doc['type']}] {doc['title']}")
            continue

        ask_with_rag(question)

if __name__ == "__main__":
    load_knowledge_base()
    interactive_rag()