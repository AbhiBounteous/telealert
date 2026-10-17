"""
TeleAlert Multi-Agent Incident Commander
4 Claude agents running in sequence:
  1. DiagnosticAgent   — gathers real cluster data
  2. RemediationAgent  — proposes fixes with risk levels
  3. CommunicationAgent — drafts all stakeholder comms
  4. PostMortemAgent   — writes blameless post-mortem

Run: python3 claude-agents/incident_commander.py
"""

import anthropic
import subprocess
import requests
import json
import os
import time
from datetime import datetime
from dataclasses import dataclass, field

# ══════════════════════════════════════════
# CLIENT SETUP
# ══════════════════════════════════════════

client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
    base_url=os.environ.get(
        "ANTHROPIC_BASE_URL",
        "https://gateway.bounteous.tools"
    )
)

MODEL = "claude-sonnet-4-6"


# ══════════════════════════════════════════
# INCIDENT DATA CLASS
# ══════════════════════════════════════════

@dataclass
class Incident:
    id: str
    title: str
    severity: str        # P1 / P2 / P3
    description: str
    detected_at: str
    diagnosis: dict      = field(default_factory=dict)
    remediation: dict    = field(default_factory=dict)
    communications: dict = field(default_factory=dict)
    postmortem: str      = ""
    resolved_at: str     = ""


# ══════════════════════════════════════════
# HELPERS — GATHER REAL CLUSTER DATA
# ══════════════════════════════════════════

def run_kubectl(args: list) -> str:
    try:
        result = subprocess.run(
            ["kubectl"] + args,
            capture_output=True, text=True, timeout=15
        )
        output = result.stdout
        if result.returncode != 0 and result.stderr:
            output += f"\nSTDERR: {result.stderr[:200]}"
        return output.strip() or "No output."
    except subprocess.TimeoutExpired:
        return "kubectl timed out."
    except FileNotFoundError:
        return "kubectl not found."
    except Exception as e:
        return f"kubectl error: {e}"


def query_prometheus(query: str) -> str:
    try:
        r = requests.get(
            "http://localhost:9090/api/v1/query",
            params={"query": query},
            timeout=5
        )
        data = r.json()
        if data.get("status") == "success" and data["data"]["result"]:
            results = []
            for item in data["data"]["result"][:5]:
                results.append(
                    f"{item.get('metric', {})}: {item['value'][1]}"
                )
            return "\n".join(results)
        return "No data (check Prometheus port-forward)"
    except requests.exceptions.ConnectionError:
        return "Prometheus unreachable on localhost:9090"
    except Exception as e:
        return f"Prometheus error: {e}"


def gather_cluster_context() -> dict:
    """Gather all relevant cluster data for diagnosis"""
    print("  📡 Gathering real cluster data...")

    context = {}

    # Pod status:
    context["pods"] = run_kubectl([
        "get", "pods", "-n", "default",
        "-o", "wide", "--no-headers"
    ])

    # All namespaces pods:
    context["all_pods"] = run_kubectl([
        "get", "pods", "--all-namespaces",
        "--no-headers"
    ])

    # Recent warning events:
    events = run_kubectl([
        "get", "events", "-n", "default",
        "--sort-by=.lastTimestamp",
        "--field-selector=type=Warning"
    ])
    # Take last 10 lines:
    lines = events.strip().split("\n")
    context["events"] = "\n".join(lines[-10:]) if lines else "No events"

    # Node status:
    context["nodes"] = run_kubectl([
        "get", "nodes", "-o", "wide", "--no-headers"
    ])

    # Prometheus metrics:
    context["error_rate"] = query_prometheus(
        "sum(rate(http_requests_total{status=~'5..'}[5m])) "
        "/ sum(rate(http_requests_total[5m])) * 100"
    )
    context["p95_latency"] = query_prometheus(
        "histogram_quantile(0.95, "
        "rate(http_request_duration_seconds_bucket[5m])) * 1000"
    )
    context["pod_restarts"] = query_prometheus(
        "sum(increase("
        "kube_pod_container_status_restarts_total"
        "{namespace='default'}[1h]))"
    )

    return context


# ══════════════════════════════════════════
# AGENT 1: DIAGNOSTIC AGENT
# ══════════════════════════════════════════

def diagnostic_agent(incident: Incident) -> dict:
    """
    Gathers real cluster data and uses Claude
    to identify root cause and affected components.
    """
    print("\n" + "─"*50)
    print("🔍 AGENT 1: DiagnosticAgent running...")
    print("─"*50)

    # Gather real data:
    cluster_data = gather_cluster_context()

    prompt = f"""You are a diagnostic specialist AI for TeleAlert.
Analyze this incident and identify the root cause.

INCIDENT:
  ID:          {incident.id}
  Title:       {incident.title}
  Severity:    {incident.severity}
  Description: {incident.description}
  Detected At: {incident.detected_at}

REAL CLUSTER DATA:
  Pods (default namespace):
{cluster_data.get('pods', 'unavailable')}

  Recent Warning Events:
{cluster_data.get('events', 'unavailable')}

  Node Status:
{cluster_data.get('nodes', 'unavailable')}

  Error Rate: {cluster_data.get('error_rate', 'unavailable')}%
  p95 Latency: {cluster_data.get('p95_latency', 'unavailable')}ms
  Pod Restarts (1h): {cluster_data.get('pod_restarts', 'unavailable')}

Respond ONLY with valid JSON (no markdown, no explanation):
{{
  "root_cause": "specific technical root cause in one sentence",
  "affected_components": ["component1", "component2"],
  "severity_correct": true,
  "revised_severity": "P1",
  "error_rate_percent": 0.0,
  "latency_ms": 0.0,
  "contributing_factors": ["factor1", "factor2"],
  "confidence": 0.85,
  "additional_checks_needed": ["check1"]
}}"""

    print("  🤖 Claude analyzing root cause...")
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = next((b.text for b in response.content if hasattr(b, "text")), "{}").strip()

    # Parse JSON safely:
    try:
        # Remove markdown if present:
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        diagnosis = json.loads(raw.strip())
    except json.JSONDecodeError:
        diagnosis = {
            "root_cause": raw[:200],
            "affected_components": ["unknown"],
            "severity_correct": True,
            "revised_severity": incident.severity,
            "confidence": 0.5
        }

    # Add raw cluster data:
    diagnosis["cluster_data"] = cluster_data

    print(f"  ✅ Root cause: {diagnosis.get('root_cause', 'unknown')}")
    print(f"  ✅ Confidence: {diagnosis.get('confidence', 0):.0%}")
    print(f"  ✅ Affected: {diagnosis.get('affected_components', [])}")

    return diagnosis


# ══════════════════════════════════════════
# AGENT 2: REMEDIATION AGENT
# ══════════════════════════════════════════

def remediation_agent(incident: Incident) -> dict:
    """
    Proposes remediation steps with risk levels.
    LOW risk steps can be auto-executed.
    HIGH risk steps require human approval.
    """
    print("\n" + "─"*50)
    print("🔧 AGENT 2: RemediationAgent running...")
    print("─"*50)

    root_cause = incident.diagnosis.get("root_cause", "unknown")
    affected   = incident.diagnosis.get("affected_components", [])

    prompt = f"""You are a remediation specialist AI for TeleAlert Kubernetes platform.
Propose remediation steps based on the diagnosis.

INCIDENT: {incident.title}
ROOT CAUSE: {root_cause}
AFFECTED COMPONENTS: {affected}
SEVERITY: {incident.severity}

AVAILABLE REMEDIATION ACTIONS:
1. kubectl rollout undo deployment/NAME     → rollback (LOW risk)
2. kubectl scale deployment/NAME --replicas=N → scale (LOW risk)
3. kubectl delete pod NAME                  → restart pod (LOW risk)
4. kubectl patch configmap NAME             → update config (MEDIUM risk)
5. argocd app sync NAME                     → force sync (LOW risk)
6. velero restore create --from-backup NAME → DR restore (HIGH risk)
7. kubectl apply -f manifest.yaml           → apply fix (MEDIUM risk)

Respond ONLY with valid JSON:
{{
  "steps": [
    {{
      "order": 1,
      "action": "exact kubectl command here",
      "rationale": "why this fixes the root cause",
      "risk": "LOW",
      "requires_human_approval": false,
      "estimated_time_minutes": 2
    }}
  ],
  "total_estimated_rtr_minutes": 15,
  "confidence": 0.85,
  "rollback_plan": "what to do if remediation fails"
}}"""

    print("  🤖 Claude proposing remediation steps...")
    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = next((b.text for b in response.content if hasattr(b, "text")), "{}").strip()

    try:
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        remediation = json.loads(raw.strip())
    except json.JSONDecodeError:
        remediation = {
            "steps": [],
            "total_estimated_rtr_minutes": 30,
            "confidence": 0.5,
            "rollback_plan": "Manual investigation required",
            "raw_response": raw[:300]
        }

    steps = remediation.get("steps", [])
    print(f"  ✅ {len(steps)} remediation steps proposed")
    print(f"  ✅ Estimated TTR: {remediation.get('total_estimated_rtr_minutes')} minutes")

    for step in steps:
        risk     = step.get("risk", "HIGH")
        approval = step.get("requires_human_approval", True)
        action   = step.get("action", "")[:60]
        print(f"  Step {step.get('order')}: [{risk}] {action}")
        print(f"    Needs approval: {approval}")

    return remediation


# ══════════════════════════════════════════
# AGENT 3: COMMUNICATION AGENT
# ══════════════════════════════════════════

def communication_agent(incident: Incident) -> dict:
    """
    Drafts all stakeholder communications:
    - Slack message for engineering team
    - Email for management
    - Status page update for users
    """
    print("\n" + "─"*50)
    print("📢 AGENT 3: CommunicationAgent running...")
    print("─"*50)

    root_cause = incident.diagnosis.get("root_cause", "under investigation")
    ttr        = incident.remediation.get("total_estimated_rtr_minutes", "TBD")
    steps      = incident.remediation.get("steps", [])
    first_step = steps[0].get("action", "investigating") if steps else "investigating"

    prompt = f"""You are a communications specialist for TeleAlert SRE team.
Draft incident communications for different audiences.

INCIDENT DETAILS:
  Title:       {incident.title}
  Severity:    {incident.severity}
  Root Cause:  {root_cause}
  First Step:  {first_step}
  Est. TTR:    {ttr} minutes
  Detected:    {incident.detected_at}

DRAFT THREE COMMUNICATIONS:

1. SLACK (engineering team):
   - Technical, immediate, what is happening NOW
   - What broke, exact cause, what we are doing
   - Maximum 3 bullet points
   - Use emoji for quick scanning

2. MANAGEMENT EMAIL:
   - Non-technical, business impact focus
   - Users affected, when resolved, what we are doing
   - No jargon, maximum 2 short paragraphs

3. STATUS PAGE (public):
   - Brief, factual, no blame, no technical details
   - Maximum 2 sentences
   - Calm and professional tone

Respond ONLY with valid JSON:
{{
  "slack_message": "text here with emoji",
  "management_email": {{
    "subject": "email subject here",
    "body": "email body here"
  }},
  "status_page": "short public update here"
}}"""

    print("  🤖 Claude drafting stakeholder communications...")
    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = next((b.text for b in response.content if hasattr(b, "text")), "{}").strip()

    try:
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        communications = json.loads(raw.strip())
    except json.JSONDecodeError:
        communications = {
            "slack_message": raw[:300],
            "management_email": {
                "subject": f"Incident: {incident.title}",
                "body": raw[:300]
            },
            "status_page": "We are investigating an issue."
        }

    print("  ✅ Slack message drafted")
    print("  ✅ Management email drafted")
    print("  ✅ Status page update drafted")
    print(f"\n  📱 Slack preview:\n  {communications.get('slack_message','')[:200]}")

    return communications


# ══════════════════════════════════════════
# AGENT 4: POST-MORTEM AGENT
# ══════════════════════════════════════════

def postmortem_agent(incident: Incident, duration_minutes: int) -> str:
    """
    Generates a complete blameless post-mortem.
    Saves to sre/post-mortems/ folder.
    """
    print("\n" + "─"*50)
    print("📝 AGENT 4: PostMortemAgent running...")
    print("─"*50)

    root_cause   = incident.diagnosis.get("root_cause", "TBD")
    affected     = incident.diagnosis.get("affected_components", [])
    factors      = incident.diagnosis.get("contributing_factors", [])
    error_rate   = incident.diagnosis.get("error_rate_percent", "unknown")
    steps        = incident.remediation.get("steps", [])[:3]
    ttr          = incident.remediation.get("total_estimated_rtr_minutes", duration_minutes)

    prompt = f"""You are a blameless post-mortem writer for TeleAlert SRE team.
Write a complete, production-grade post-mortem document.

INCIDENT DATA:
  ID:           {incident.id}
  Title:        {incident.title}
  Severity:     {incident.severity}
  Duration:     {duration_minutes} minutes
  Detected At:  {incident.detected_at}
  Root Cause:   {root_cause}
  Affected:     {affected}
  Factors:      {factors}
  Error Rate:   {error_rate}%
  Top Steps:    {json.dumps(steps, indent=2)}

BLAMELESS POST-MORTEM RULES:
- NEVER blame individuals
- Systems language: "no circuit breaker existed" NOT "engineer forgot"
- Be specific with numbers: "30s timeout × 8 threads = pool exhausted in 4 min"
- Every action item needs: DRI name, due date, priority

Write a complete post-mortem in Markdown with these sections:
1. Executive Summary (2-3 sentences, non-technical)
2. Impact (quantified: users affected, error budget burned, requests failed)
3. Timeline (6-8 events with relative timestamps like T+0, T+5min)
4. Root Cause Analysis (specific, systemic, no blame)
5. Contributing Factors (numbered list)
6. What Went Well (minimum 3 items)
7. Action Items (markdown table: Priority | Action | DRI | Due Date)
   Include at least one chaos experiment action item.

Make it detailed and production-quality."""

    print("  🤖 Claude writing blameless post-mortem...")
    response = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )

    postmortem = next((b.text for b in response.content if hasattr(b, "text")), "")

    # Save to file:
    pm_dir = "sre/post-mortems"
    os.makedirs(pm_dir, exist_ok=True)

    filename = f"{pm_dir}/{incident.id}-postmortem.md"
    with open(filename, "w") as f:
        f.write(f"# Post-Mortem: {incident.title}\n")
        f.write(f"**Generated by Claude PostMortemAgent**\n")
        f.write(f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n\n")
        f.write(postmortem)

    print(f"  ✅ Post-mortem saved: {filename}")
    print(f"  ✅ {len(postmortem)} characters written")

    return postmortem


# ══════════════════════════════════════════
# INCIDENT COMMANDER — ORCHESTRATOR
# ══════════════════════════════════════════

def incident_commander(incident: Incident) -> Incident:
    """
    Orchestrates all 4 agents in sequence.
    Each agent adds to the incident object.
    """
    start_time = time.time()

    print("\n" + "="*60)
    print("🚨 INCIDENT COMMANDER ACTIVATED")
    print("="*60)
    print(f"  ID:          {incident.id}")
    print(f"  Title:       {incident.title}")
    print(f"  Severity:    {incident.severity}")
    print(f"  Description: {incident.description}")
    print(f"  Detected:    {incident.detected_at}")
    print("="*60)
    print("  4 Claude agents will run in sequence")
    print("  Each agent builds on previous results")
    print("="*60)

    # ── Phase 1: Diagnose ──────────────────────────────────
    print("\n[1/4] Running DiagnosticAgent...")
    incident.diagnosis = diagnostic_agent(incident)

    # ── Phase 2: Remediate ─────────────────────────────────
    print("\n[2/4] Running RemediationAgent...")
    incident.remediation = remediation_agent(incident)

    # ── Phase 3: Communicate ───────────────────────────────
    print("\n[3/4] Running CommunicationAgent...")
    incident.communications = communication_agent(incident)

    # ── Phase 4: Post-mortem ───────────────────────────────
    elapsed = int((time.time() - start_time) / 60) + 1
    print("\n[4/4] Running PostMortemAgent...")
    incident.postmortem = postmortem_agent(incident, elapsed)
    incident.resolved_at = datetime.utcnow().isoformat()

    # ── Final Summary ──────────────────────────────────────
    total_time = int(time.time() - start_time)

    print("\n" + "="*60)
    print("✅ INCIDENT COMMANDER COMPLETE")
    print("="*60)
    print(f"  Total time:    {total_time} seconds")
    print(f"  Agents run:    4")
    print(f"  Root cause:    {incident.diagnosis.get('root_cause','?')[:60]}")
    print(f"  Steps proposed:{len(incident.remediation.get('steps',[]))}")
    print(f"  Est. TTR:      {incident.remediation.get('total_estimated_rtr_minutes','?')} min")
    print(f"  Post-mortem:   sre/post-mortems/{incident.id}-postmortem.md")
    print("="*60)

    return incident


# ══════════════════════════════════════════
# MAIN — RUN A TEST INCIDENT
# ══════════════════════════════════════════

if __name__ == "__main__":

    # Define the incident (simulating PagerDuty firing):
    incident = Incident(
        id="INC-2026-001",
        title="TeleAlert API high error rate — Redis connection timeout",
        severity="P1",
        description=(
            "PagerDuty alert fired: availability burn rate 14.4×. "
            "Alert delivery failing across all channels. "
            "Redis connection timeouts observed in application logs. "
            "Error rate spiking above SLO threshold of 0.1%."
        ),
        detected_at=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    # Run the incident commander:
    resolved_incident = incident_commander(incident)

    # Show the Slack message:
    print("\n" + "─"*60)
    print("📱 SLACK MESSAGE TO POST:")
    print("─"*60)
    print(resolved_incident.communications.get("slack_message", ""))

    # Show email subject:
    email = resolved_incident.communications.get("management_email", {})
    print("\n" + "─"*60)
    print("📧 MANAGEMENT EMAIL:")
    print("─"*60)
    print(f"Subject: {email.get('subject','')}")
    print(f"Body preview: {email.get('body','')[:200]}...")

    # Show status page:
    print("\n" + "─"*60)
    print("🌐 STATUS PAGE UPDATE:")
    print("─"*60)
    print(resolved_incident.communications.get("status_page", ""))

    print("\n✅ All outputs saved.")
    print(f"📄 Post-mortem: sre/post-mortems/{incident.id}-postmortem.md")
    print("\nOpen the post-mortem file to see the full blameless report!")