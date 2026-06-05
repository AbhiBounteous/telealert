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