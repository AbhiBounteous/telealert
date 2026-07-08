# TeleAlert — AI-Powered Telecom Network Operations

> Built by Abhilash Bhuibhar | Bounteous × Telecom & Media Practice
> DevOps + AI-Powered Operations | Claude Architect Certification Project

---

## Project Overview

TeleAlert is a production-grade telecom network event processing system
built entirely on a local laptop using free and open source tools.
It demonstrates end-to-end DevOps practices combined with AI-powered
autonomous operations using Claude API.

**This project was built as part of:**
- Claude Architect Certification preparation
- Bounteous × Telecom & Media Practice portfolio
- Real-world DevOps hands-on learning

---

## Architecture
Network Nodes (Telecom Towers)
↓
Flask API Service          ← receives network events
↓
PostgreSQL Database        ← stores all events
↓
Event Worker Service       ← processes and alerts
↓
Prometheus + Grafana       ← monitors everything
↓
Claude AI Ops Agent        ← diagnoses and auto-scales

---

## Tech Stack

| Category | Technology |
|---|---|
| Application | Python, Flask, PostgreSQL |
| Containerization | Docker, Docker Compose |
| Orchestration | Kubernetes (Kind — local) |
| CI/CD | GitHub Actions, GHCR |
| Monitoring | Prometheus, Grafana |
| AI/ML | Anthropic Claude API |
| Infrastructure | WSL2, Ubuntu 22.04 |

---

## Project Structure
telealert/
├── api/                    # Flask API service
│   ├── app.py             # 5 endpoints including /metrics
│   ├── requirements.txt
│   └── Dockerfile
├── worker/                 # Event processing worker
│   ├── worker.py
│   ├── requirements.txt
│   └── Dockerfile
├── k8s/                    # Kubernetes manifests
│   ├── api-deployment.yaml
│   ├── worker-deployment.yaml
│   ├── postgres-deployment.yaml
│   ├── prometheus.yaml
│   └── grafana.yaml
├── ai-ops/                 # AI-powered operations
│   └── incident_bot.py    # Claude incident response bot
├── mcp-server/             # MCP autonomous agent
│   └── devops_mcp_server.py
├── .github/
│   └── workflows/
│       └── ci-cd.yaml     # GitHub Actions pipeline
└── docker-compose.yml      # Local development
---

## Phase 1 — Local DevOps Lab

**Tools installed on Windows 11 laptop:**
- WSL2 + Ubuntu 22.04
- Docker Desktop with WSL2 backend
- Kind (Kubernetes in Docker)
- kubectl + Helm
- Claude Python SDK

**Key learning:** Setting up a production-grade DevOps
environment on a corporate Windows laptop including
resolving SSL certificate issues on corporate networks.

---

## Phase 2 — Core DevOps Project

### Microservices App
3-service telecom event processing system:
- API service receives network events from towers
- Worker service processes events and fires alerts
- PostgreSQL stores all events with timestamps

### CI/CD Pipeline
GitHub Actions pipeline with 3 stages:
- Run Tests — syntax check in 6 seconds
- Build and Push — Docker images to GHCR in 30 seconds
- Deploy Notification — AI summary generation
- Total pipeline time: under 60 seconds

### Kubernetes Deployment
- 3-node Kind cluster (1 control plane + 2 workers)
- RollingUpdate strategy with zero downtime
- Scaled from 2 to 4 replicas under load
- Rollback demonstrated in under 10 seconds
- ReadinessProbe and LivenessProbe configured
- Resource requests and limits set

### Observability
- Prometheus scraping metrics every 15 seconds
- Grafana dashboard with 3 live panels:
  - Total network events counter
  - Critical alerts counter
  - Events rate per minute time series

---

## Phase 3 — AI-Powered Operations

### Project 1 — AI Incident Response Bot
```bash
python3 ai-ops/incident_bot.py
```

Claude reads live Prometheus metrics and generates
a complete NOC incident report including:
- Root cause analysis with confidence percentage
- Severity assessment
- Exact kubectl remediation commands
- Prevention recommendations

**Real result:** Claude identified a cascading fiber cut
pattern across 10 Mumbai nodes with 85% confidence,
correctly identifying monsoon season as a contributing
factor and recommending field team dispatch.

### Project 2 — CI/CD Failure Explainer
GitHub Actions pipeline calls Claude when builds fail.
Claude explains errors in plain English and posts
remediation steps directly in pipeline logs.

### Project 3 — Autonomous DevOps Agent
```bash
python3 mcp-server/devops_mcp_server.py
```

Claude acts as an autonomous on-call DevOps engineer:

**Tools available to Claude:**
- kubectl_get_pods — check cluster health
- kubectl_get_logs — read deployment logs
- kubectl_scale — scale deployments up/down
- kubectl_rollout_status — verify rollouts
- get_telealert_status — read live metrics
- get_telealert_alerts — check critical alerts

**Real result:** Claude made 8 autonomous tool calls,
identified two wave patterns of fiber cuts, scaled
telealert-worker from 1 to 3 replicas and telealert-api
from 2 to 3 replicas — all without human intervention.

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| /health | GET | Service health check |
| /event | POST | Receive network event |
| /alerts | GET | Get critical alerts |
| /metrics | GET | Prometheus metrics |
| /status | GET | Live event statistics |

---

## Running Locally

### Prerequisites
- Windows 11 with WSL2
- Docker Desktop
- Kind cluster running
- Anthropic API key

### Quick Start
```bash
# Clone the repo
git clone https://github.com/AbhiBounteous/telealert.git
cd telealert

# Start with Docker Compose
docker-compose up -d

# Create database table
docker-compose exec postgres psql -U admin -d telealert -c \
"CREATE TABLE IF NOT EXISTS events (
  id SERIAL PRIMARY KEY,
  node_id VARCHAR(50),
  severity VARCHAR(20),
  message TEXT,
  processed BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT NOW()
);"

# Test the API
curl http://localhost:5000/health

# Send a test event
curl -X POST http://localhost:5000/event \
  -H "Content-Type: application/json" \
  -d '{"node_id": "NODE-BOM-001", "severity": "critical",
       "message": "Fiber cut on backbone"}'

# Run AI incident bot
export ANTHROPIC_API_KEY="your-key-here"
python3 ai-ops/incident_bot.py

# Run autonomous agent
python3 mcp-server/devops_mcp_server.py
```

---

## Key Achievements

| Achievement | Detail |
|---|---|
| Zero cost | Entire project runs free on local laptop |
| Real K8s cluster | 3-node Kind cluster not minikube |
| CI/CD pipeline | Under 60 seconds end to end |
| Zero downtime | RollingUpdate with readiness probes |
| AI diagnosis | 85% confidence root cause analysis |
| Autonomous scaling | Claude scaled cluster without human input |
| Telecom context | Directly relevant to Bounteous practice |

---

## Bugs Fixed During Development

| Issue | Root Cause | Fix Applied |
|---|---|---|
| Python logs invisible in Docker | Output buffering | PYTHONUNBUFFERED=1 |
| Corporate SSL blocking downloads | Certificate inspection | -k flag + CA cert import |
| GitHub SSH blocked on port 22 | Corporate firewall | SSH over port 443 |
| GHCR image tag rejected | Uppercase not allowed | Hardcoded lowercase tags |
| Dockerfile comment parsing error | Buildx ENV parsing | Removed all comments |
| Prometheus target DOWN | Content-type mismatch | fallback_scrape_protocol |

---

## About

Built by **Abhilash Bhuibhar** as part of the
**Claude Architect Certification** preparation at
**Bounteous × Telecom & Media Practice**.

This project demonstrates that enterprise-grade DevOps
with AI-powered operations can be built entirely on a
local laptop at zero cost using modern open source tools
and the Claude API.

---

*TeleAlert — Where DevOps meets AI-Powered Operations*
=======================
# TeleAlert — AI-Powered Telecom Network Operations

> Production-grade DevOps system built by Abhilash Bhuibhar
> Bounteous × Telecom & Media Practice

---

## Project Overview

TeleAlert is a complete AI-powered network operations
system for telecom NOC teams. It monitors network events,
predicts failures, auto-heals infrastructure, and sends
intelligent alerts — all powered by Claude AI.

---

## Architecture
GitHub → ArgoCD → Kubernetes (3 nodes)
├── telealert-api (Flask)
├── telealert-worker (Python)
├── PostgreSQL
├── Prometheus + Grafana
└── Jaeger (OTel tracing)
---

## Tech Stack

| Layer | Technology |
|---|---|
| GitOps | ArgoCD v3.4.3 |
| Autoscaling | KEDA + HPA + VPA |
| Service Mesh | Istio 1.30.1 |
| Tracing | OpenTelemetry + Jaeger |
| IaC | Terraform v1.7.0 |
| Security | Trivy + Vault + Falco + OPA |
| AI | Claude Sonnet + Llama3 + LangChain |
| RAG | ChromaDB + mxbai-embed-large |
| Framework | LangChain |

---

## Phase 1 — DevOps Foundation

### CI/CD Pipeline
- GitHub Actions pipeline completes in 60 seconds
- Stages: Test → Build → Trivy Scan → Deploy
- Images pushed to GHCR with SHA256 pinning
- Claude AI explains failures automatically

### Kubernetes
- 3-node Kind cluster (1 control + 2 workers)
- Zero downtime rolling deployments
- Rollback in 10 seconds
- Resource limits on all containers

### Monitoring
- Prometheus scraping every 15 seconds
- Grafana dashboard: Total Events, Critical Alerts
- OpenTelemetry traces with 3 spans per request
- Jaeger UI showing DB bottleneck (57% of time)

---

## Phase 2 — GitOps + Advanced K8s

### ArgoCD GitOps
- Git is single source of truth
- Auto-sync on every push
- Self-healing enabled
- App of Apps pattern for 3 environments

### Multi-Environment
dev:     namespace telealert-dev     replicas=1
staging: namespace telealert-staging replicas=2
prod:    namespace telealert-prod    replicas=3
### KEDA Autoscaling
- Worker scales 0→1 in 4 seconds
- Scales back to 0 after processing
- PostgreSQL queue depth as trigger
- Zero cost during idle periods

### Istio Service Mesh
- mTLS STRICT mode enforced
- Plain HTTP rejected
- Canary 90/10 traffic split
- All pods show 2/2 (sidecar injected)

### Kustomize + ApplicationSets
- Base YAML + environment overlays
- ApplicationSet generates 3 apps automatically
- DRY principle — no duplication

### Terraform IaC
- Kind cluster provisioned in 2m36s
- Variables, outputs, state file
- terraform destroy + apply = exact reproduction

---

## Phase 3 — DevSecOps

### Trivy Scanning
- API image: 2 CRITICAL + 13 HIGH CVEs found
- Dockerfile: Running as root fixed
- Added non-root user + HEALTHCHECK
- SBOM generated (254KB CycloneDX 1.7)

### HashiCorp Vault
- Database credentials stored securely
- API keys stored securely
- Read-only policy for app token
- 24h TTL tokens
- Deployed to Kubernetes via Helm

### Falco Runtime Security
- 1 Falco pod per node (3 total)
- Detected shell exec in telealert-api
- Custom rules for TeleAlert
- Alerts include pod name + user + timestamp

### OPA Gatekeeper
- AllowedRegistries policy
- RequireResourceLimits policy
- NoLatestTag policy (warn in prod)

---

## Phase 4 — AI-Powered Operations

### Incident Response Bot
```bash
python3 ai-ops/incident_bot.py
```
Claude diagnoses incidents with 85% confidence.
Identified fiber cut pattern across 10 Mumbai nodes.

### Autonomous DevOps Agent (MCP)
```bash
python3 mcp-server/devops_mcp_server.py
```
8 autonomous tool calls. Scaled deployments
without human intervention.

### Auto-Healing Agent
```bash
python3 ai-ops/auto_healing_agent.py
```
Monitors cluster every 60s.
Auto-restarts crashed pods.
Natural language kubectl interface.

### Predictive Alerts
```bash
python3 ai-ops/predictive_alerts.py
```
91% confidence failure prediction.
99.2% pattern signature match.

### Slack Integration
```bash
python3 ai-ops/slack_alerts.py
```
Claude-generated alerts to #network-alerts.
Smart deduplication prevents spam.

### 4-Agent Pipeline
```bash
python3 ai-ops/multi_agent.py
```
Monitor → Diagnose → Remediate → Report.
Full incident lifecycle automated.

### Enterprise RAG System
```bash
python3 ai-ops/rag_enterprise.py
```
Version A: Claude Sonnet + mxbai-embed (client-facing)
Version B: Llama3 + mxbai-embed (air-gapped)
LangChain framework + ChromaDB vector store.

---

## Real Results

| Achievement | Detail |
|---|---|
| Incident diagnosis | 85% confidence fiber cut |
| Failure prediction | 91% confidence |
| Pattern match | 99.2% signature |
| KEDA scale up | 4 seconds |
| Pipeline speed | 60 seconds |
| Trivy CVEs found | 2 CRITICAL + 17 HIGH |
| SBOM size | 254KB CycloneDX |
| OTel traces | 20 traces, 3 spans each |
| DB bottleneck | 57% of request time |

---

## Bugs Debugged

1. Corporate SSL → `-k` flag + CA cert
2. Python buffering → `PYTHONUNBUFFERED=1`
3. GitHub SSH blocked → port 443 override
4. GHCR lowercase tags → hardcoded name
5. Dockerfile comments → removed all
6. Prometheus content-type → fallback protocol
7. LangChain API changes → new import paths
8. Ollama SSL → `OLLAMA_INSECURE=true`
9. Network Policy + Istio → allow ports 15000-15020
10. KEDA kubectl install → use Helm ownership

---

## Project Stats

| Metric | Value |
|---|---|
| GitHub commits | 30+ |
| AI features | 10 |
| Kubernetes pods | 12 |
| LLM models | 3 |
| Vector documents | 15 |
| Pipeline time | 60 seconds |
| Total cost | ₹0 |

---

## Author

**Abhilash Bhuibhar**
Bounteous × Telecom & Media Practice
