import os
from datetime import datetime
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_anthropic import ChatAnthropic
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate

KNOWLEDGE_BASE_DOCS = [
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
Two burst events 14 minutes apart on same physical
route. Resolution: Field team dispatched, temporary
bypass activated, permanent repair in 6 hours.
Prevention: Geofencing alerts added for construction
near fiber routes. MTTR: 6 hours."""
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
testing and generator auto-start verification added
to maintenance checklist. MTTR: 45 minutes."""
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
Resolution: BGP config rolled back in 20 minutes.
Prevention: Staging environment validation mandatory
before production network changes. MTTR: 20 minutes."""
    },
    {
        "id": "run001",
        "type": "runbook",
        "title": "Fiber Cut Response Runbook",
        "content": """RUNBOOK: Fiber Cut Response
Trigger: Multiple NODE-BOM critical alerts in burst
Step 1: Check sequential pattern 2 seconds apart
        Sequential means physical fiber cut
        Random means software or config issue
Step 2: Identify affected route
        NODE-BOM-01 to 05 = Southern route
        NODE-BOM-06 to 010 = Northern route
        Both routes = trunk cut at Andheri junction
Step 3: Scale worker immediately
        kubectl scale deployment telealert-worker
        --replicas=3
Step 4: Dispatch field team to Andheri junction
Step 5: Notify NOC lead within 5 minutes
Step 6: Post to Slack #network-alerts channel"""
    },
    {
        "id": "run002",
        "type": "runbook",
        "title": "Kubernetes ImagePullBackOff Runbook",
        "content": """RUNBOOK: ImagePullBackOff Resolution
Trigger: Pod stuck in ImagePullBackOff state
Step 1: kubectl describe pod pod-name
        Look for Failed to pull image error
Step 2: Check image exists in GHCR registry
        github.com/AbhiBounteous packages tab
Step 3: Quick fix rollback deployment
        kubectl rollout undo deployment name
Step 4: Fix root cause
        Bad tag: fix image tag in ci-cd.yaml
        Auth issue: verify CR_PAT secret in GitHub
        Missing image: rebuild via git push
Step 5: kubectl get pods verify all Running"""
    },
    {
        "id": "run003",
        "type": "runbook",
        "title": "High Critical Event Rate Runbook",
        "content": """RUNBOOK: High Critical Event Rate
Trigger: Critical events over 50 percent of total
Step 1: Check pattern same node = genuine incident
        Random nodes = threshold misconfiguration
Step 2: If genuine run python3 ai-ops/incident_bot.py
        Check Grafana dashboard for spike timing
Step 3: Scale worker
        kubectl scale deployment telealert-worker
        --replicas=3
Step 4: If misconfiguration review worker.py severity
Step 5: Monitor until rate drops below 20 percent"""
    },
    {
        "id": "arch001",
        "type": "architecture",
        "title": "TeleAlert Architecture Document",
        "content": """ARCHITECTURE: TeleAlert System v1.2
Service 1: telealert-api Flask port 5000
  POST /event GET /metrics GET /alerts GET /health
Service 2: telealert-worker Python
  Polls PostgreSQL every 5 seconds
  Fires CRITICAL ALERT for severity critical
Service 3: PostgreSQL port 5432
  Table events columns id node_id severity message
Service 4: Prometheus port 9090
  Scrapes telealert-api every 15 seconds
Service 5: Grafana port 3000
  Dashboard TeleAlert Network Operations
Infrastructure: Kind cluster 3 nodes
CI/CD: GitHub Actions 60 seconds
Registry: GHCR ghcr.io/abhibounteous"""
    },
    {
        "id": "kb001",
        "type": "knowledge",
        "title": "Mumbai Network Topology",
        "content": """KNOWLEDGE: Mumbai BOM Network Topology
Southern route: NODE-BOM-01 to NODE-BOM-05
Physical path: Andheri to Bandra via coastal road
Northern route: NODE-BOM-06 to NODE-BOM-010
Physical path: Andheri to Goregaon via highway
High risk: Western Express Highway construction zone
Common failure points:
Andheri junction both routes share this point
WEH construction zone active digging risk
Monsoon flooding June to September
Historical: Burst failures start from NODE-BOM-06
or NODE-BOM-01 never middle nodes."""
    },
    {
        "id": "kb002",
        "type": "knowledge",
        "title": "Escalation Matrix Bounteous NOC",
        "content": """ESCALATION MATRIX: Bounteous Telecom NOC
Level 1: NOC Engineer response time 5 minutes
  Handles low and medium severity events
Level 2: Senior NOC Engineer response 15 minutes
  Handles high severity and repeated incidents
  Escalate when MTTR exceeds 30 minutes
Level 3: NOC Manager response 30 minutes
  Handles critical incidents affecting 5+ nodes
  Escalate when MTTR exceeds 1 hour
Level 4: CTO and Client Notification 1 hour
  Handles major outages affecting entire regions
Slack channels:
  #network-alerts all automated alerts
  #noc-team team communication
  #incidents-critical P1 incidents only"""
    }
]

NOC_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are an expert NOC engineer at
Bounteous x Telecom and Media Practice.

Answer using ONLY the context below.
Reference document titles in your answer.
If answer is not in context say so clearly.
Be specific and technical.

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""
)

def create_documents():
    """Convert knowledge base to LangChain documents"""
    docs = []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    for item in KNOWLEDGE_BASE_DOCS:
        chunks = splitter.create_documents(
            texts=[item["content"]],
            metadatas=[{
                "title": item["title"],
                "type": item["type"],
                "id": item["id"]
            }]
        )
        docs.extend(chunks)
    return docs

class EnterpriseRAG:
    def __init__(self, version):
        self.version = version
        self.vectorstore = None
        self.retriever = None
        self.llm = None

    def format_docs(self, docs):
        return "\n\n".join(
            f"[{d.metadata.get('title','Unknown')}]\n{d.page_content}"
            for d in docs
        )

    def setup_version_a(self):
        """Version A: Claude + mxbai-embed"""
        print("\n" + "="*60)
        print("VERSION A: Claude Sonnet + mxbai-embed-large")
        print("Stack: LangChain + Ollama Embeddings + Claude")
        print("Use case: Enterprise client-facing apps")
        print("="*60)

        print("\n📥 Loading mxbai-embed-large embeddings...")
        embeddings = OllamaEmbeddings(
            model="mxbai-embed-large"
        )

        print("📚 Loading documents into ChromaDB...")
        docs = create_documents()
        self.vectorstore = Chroma.from_documents(
            documents=docs,
            embedding=embeddings,
            collection_name="claude_collection"
        )
        print(f"✅ {len(docs)} chunks loaded")

        print("🤖 Setting up Claude Sonnet LLM...")
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-6",
            anthropic_api_key=os.getenv(
                "ANTHROPIC_API_KEY"
            ),
            timeout=120
        )

        self.retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": 3}
        )
        print("✅ Version A ready!")

    def setup_version_b(self):
        """Version B: Llama3 + mxbai-embed (fully local)"""
        print("\n" + "="*60)
        print("VERSION B: Llama3 + mxbai-embed-large")
        print("Stack: LangChain + Ollama Embeddings + Llama3")
        print("Use case: Air-gapped / data-sensitive deployments")
        print("="*60)

        print("\n📥 Loading mxbai-embed-large embeddings...")
        embeddings = OllamaEmbeddings(
            model="mxbai-embed-large"
        )

        print("📚 Loading documents into ChromaDB...")
        docs = create_documents()
        self.vectorstore = Chroma.from_documents(
            documents=docs,
            embedding=embeddings,
            collection_name="llama_collection"
        )
        print(f"✅ {len(docs)} chunks loaded")

        print("🦙 Setting up Llama3 LLM...")
        self.llm = OllamaLLM(
            model="llama3",
            temperature=0.1
        )

        self.retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": 3}
        )
        print("✅ Version B ready!")

    def ask(self, question):
        """Ask question and get answer with sources"""
        print(f"\n{'─'*50}")
        print(f"🤖 {self.version}")
        print(f"{'─'*50}")
        print(f"🔍 Searching knowledge base...")

        docs = self.retriever.invoke(question)
        context = self.format_docs(docs)

        prompt_text = NOC_PROMPT.format(
            context=context,
            question=question
        )

        print("💡 Generating answer...")

        if "Claude" in self.version:
            response = self.llm.invoke(prompt_text)
            answer = response.content
        else:
            answer = self.llm.invoke(prompt_text)

        print(f"\n{answer}")

        print(f"\n📄 Sources:")
        seen = set()
        for doc in docs:
            title = doc.metadata.get("title", "Unknown")
            if title not in seen:
                seen.add(title)
                print(f"  → {title}")

        return answer

def compare_versions(question, rag_a, rag_b):
    """Compare both versions on same question"""
    print(f"\n{'='*60}")
    print(f"❓ QUESTION: {question}")
    print(f"{'='*60}")

    print("\n🔵 Version A — Claude Sonnet")
    answer_a = rag_a.ask(question)

    print("\n🟢 Version B — Llama3 Local")
    answer_b = rag_b.ask(question)

    print(f"\n{'='*60}")
    print("📊 COMPARISON")
    print(f"{'='*60}")
    print(f"Claude answer:  {len(answer_a)} characters")
    print(f"Llama3 answer:  {len(answer_b)} characters")

def main():
    print("\n" + "="*60)
    print("🏢 TELEALERT ENTERPRISE RAG SYSTEM")
    print("Bounteous x Telecom and Media Practice")
    print("="*60)
    print("\nVersions:")
    print("A: Claude Sonnet + mxbai-embed (client-facing)")
    print("B: Llama3 + mxbai-embed (air-gapped/secure)")
    print("Framework: LangChain")
    print("Vector DB: ChromaDB")
    print("Embeddings: mxbai-embed-large via Ollama")

    rag_a = EnterpriseRAG("Version A: Claude Sonnet")
    rag_b = EnterpriseRAG("Version B: Llama3 Local")

    rag_a.setup_version_a()
    rag_b.setup_version_b()

    print("\n" + "="*60)
    print("✅ BOTH VERSIONS READY")
    print("="*60)
    print("\nOptions:")
    print("1. Ask Version A only (Claude)")
    print("2. Ask Version B only (Llama3)")
    print("3. Compare both versions")
    print("4. List documents")
    print("5. Exit")
    print("="*60)

    while True:
        choice = input("\nChoice (1/2/3/4/5): ").strip()

        if choice == "5":
            print("Goodbye!")
            break

        elif choice == "4":
            print("\n📚 Knowledge base:")
            for doc in KNOWLEDGE_BASE_DOCS:
                print(
                    f"  [{doc['type']}] {doc['title']}"
                )

        elif choice in ["1", "2", "3"]:
            question = input("Question: ").strip()
            if not question:
                continue
            if choice == "1":
                rag_a.ask(question)
            elif choice == "2":
                rag_b.ask(question)
            elif choice == "3":
                compare_versions(
                    question, rag_a, rag_b
                )
        else:
            print("Invalid. Choose 1-5")

if __name__ == "__main__":
    main()