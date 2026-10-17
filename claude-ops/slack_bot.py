"""
TeleAlert Claude Slack Bot
Engineers ask DevOps questions in Slack.
Claude answers with real cluster data.

Commands:
  @ClaudeOps what pods are running?
  @ClaudeOps why is telealert-api crashing?
  @ClaudeOps what is the SLO burn rate?
  @ClaudeOps scale telealert-worker to 3 replicas
  @ClaudeOps run a pod-delete chaos experiment

Run: python3 claude-ops/slack_bot.py
"""

import os
import sys
import subprocess
import requests
import json
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import anthropic
# Fix Mac SSL certificate issue:
#import ssl
#import certifi
#ssl._create_default_https_context = ssl.create_default_context
#import urllib.request
#urllib.request.urlopen.__defaults__ = (None,)

# ══════════════════════════════════════════
# SETUP
# ══════════════════════════════════════════

# Verify tokens:
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.environ.get(
    "ANTHROPIC_BASE_URL",
    "https://gateway.bounteous.tools"
)

if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
    print("❌ Missing Slack tokens!")
    print("   export SLACK_BOT_TOKEN=xoxb-...")
    print("   export SLACK_APP_TOKEN=xapp-...")
    sys.exit(1)

# Initialize Slack app:
app = App(token=SLACK_BOT_TOKEN)

# Initialize Claude client:
claude = anthropic.Anthropic(
    api_key=ANTHROPIC_API_KEY,
    base_url=ANTHROPIC_BASE_URL
)

MODEL = "claude-sonnet-4-6"

# ══════════════════════════════════════════
# DEVOPS TOOLS (same as claude_ops.py)
# ══════════════════════════════════════════

DEVOPS_TOOLS = [
    {
        "name": "kubectl_get_pods",
        "description": (
            "Get all pods in a namespace with status, "
            "restarts, and age."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": "Kubernetes namespace"
                }
            }
        }
    },
    {
        "name": "kubectl_get_all_namespaces",
        "description": (
            "List all namespaces and pods across "
            "the entire cluster."
        ),
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "kubectl_get_logs",
        "description": "Get logs from a pod.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pod_name": {"type": "string"},
                "namespace": {"type": "string"},
                "tail_lines": {"type": "integer"}
            },
            "required": ["pod_name"]
        }
    },
    {
        "name": "kubectl_describe_pod",
        "description": (
            "Get detailed description of a pod "
            "including events."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pod_name": {"type": "string"},
                "namespace": {"type": "string"}
            },
            "required": ["pod_name"]
        }
    },
    {
        "name": "kubectl_get_events",
        "description": "Get recent warning events.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string"}
            }
        }
    },
    {
        "name": "prometheus_query",
        "description": (
            "Run PromQL query for metrics. "
            "Use for error rate, latency, SLO questions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "scale_deployment",
        "description": (
            "Scale a deployment to N replicas. "
            "Shows preview unless confirmed=true."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "deployment": {"type": "string"},
                "replicas": {"type": "integer"},
                "namespace": {"type": "string"},
                "confirmed": {"type": "boolean"}
            },
            "required": ["deployment", "replicas"]
        }
    },
    {
        "name": "get_slo_status",
        "description": (
            "Get TeleAlert SLO status: burn rate, "
            "error budget, latency, error rate."
        ),
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]


# ══════════════════════════════════════════
# TOOL EXECUTION
# ══════════════════════════════════════════

def run_kubectl(args: list) -> str:
    try:
        result = subprocess.run(
            ["kubectl"] + args,
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout
        if result.returncode != 0 and result.stderr:
            output += f"\nError: {result.stderr[:200]}"
        return output.strip() or "No output."
    except subprocess.TimeoutExpired:
        return "kubectl timed out."
    except FileNotFoundError:
        return "kubectl not found."
    except Exception as e:
        return f"Error: {e}"


def query_prometheus(query: str) -> str:
    try:
        r = requests.get(
            "http://localhost:9090/api/v1/query",
            params={"query": query},
            timeout=5
        )
        data = r.json()
        if data.get("status") == "success" \
                and data["data"]["result"]:
            lines = []
            for item in data["data"]["result"][:5]:
                lines.append(
                    f"{item.get('metric', {})}: "
                    f"{item['value'][1]}"
                )
            return "\n".join(lines)
        return "No data (Prometheus port-forward needed?)"
    except requests.exceptions.ConnectionError:
        return "Prometheus unreachable on localhost:9090"
    except Exception as e:
        return f"Prometheus error: {e}"


def execute_tool(name: str, args: dict) -> str:
    if name == "kubectl_get_pods":
        ns = args.get("namespace", "default")
        return run_kubectl(["get", "pods", "-n", ns, "-o", "wide"])

    elif name == "kubectl_get_all_namespaces":
        ns = run_kubectl(["get", "namespaces", "--no-headers"])
        pods = run_kubectl([
            "get", "pods", "--all-namespaces", "-o", "wide"
        ])
        return f"Namespaces:\n{ns}\n\nAll Pods:\n{pods}"

    elif name == "kubectl_get_logs":
        ns   = args.get("namespace", "default")
        pod  = args["pod_name"]
        tail = args.get("tail_lines", 50)
        return run_kubectl([
            "logs", pod, "-n", ns, f"--tail={tail}"
        ])

    elif name == "kubectl_describe_pod":
        ns  = args.get("namespace", "default")
        pod = args["pod_name"]
        return run_kubectl(["describe", "pod", pod, "-n", ns])

    elif name == "kubectl_get_events":
        ns = args.get("namespace", "default")
        result = run_kubectl([
            "get", "events", "-n", ns,
            "--sort-by=.lastTimestamp",
            "--field-selector=type=Warning"
        ])
        lines = result.strip().split("\n")
        return "\n".join(lines[-15:]) if lines else result

    elif name == "prometheus_query":
        return query_prometheus(args["query"])

    elif name == "scale_deployment":
        dep       = args["deployment"]
        replicas  = args["replicas"]
        ns        = args.get("namespace", "default")
        confirmed = args.get("confirmed", False)

        current = run_kubectl([
            "get", "deployment", dep, "-n", ns,
            "-o", "jsonpath={.spec.replicas}",
            "--ignore-not-found"
        ])

        if not confirmed:
            return (
                f"⚠️ SCALE PREVIEW (not applied):\n"
                f"  Deployment: {dep}\n"
                f"  Current: {current or 'unknown'} replicas\n"
                f"  Requested: {replicas} replicas\n\n"
                f"Reply 'yes scale {dep} to {replicas}' to confirm."
            )
        result = run_kubectl([
            "scale", "deployment", dep,
            f"--replicas={replicas}", "-n", ns
        ])
        return f"✅ Scaled {dep} to {replicas} replicas:\n{result}"

    elif name == "get_slo_status":
        queries = {
            "Error Rate (%)": (
                "sum(rate(http_requests_total{status=~'5..'}[5m]))"
                " / sum(rate(http_requests_total[5m])) * 100"
            ),
            "p95 Latency (ms)": (
                "histogram_quantile(0.95, rate("
                "http_request_duration_seconds_bucket[5m])) * 1000"
            ),
            "Burn Rate": (
                "telealert:availability:error_ratio1h / 0.001"
            )
        }
        lines = ["*TeleAlert SLO Status:*"]
        for label, query in queries.items():
            value = query_prometheus(query)
            lines.append(f"  {label}: {value}")
        return "\n".join(lines)

    return f"Unknown tool: {name}"


# ══════════════════════════════════════════
# CLAUDE AGENT WITH TOOL USE
# ══════════════════════════════════════════

SYSTEM_PROMPT = """You are ClaudeOps, a Senior DevOps AI
assistant for TeleAlert running inside Slack.

You answer questions about the Kubernetes cluster by using
the available tools to gather REAL data, then give a clear,
specific answer.

RULES:
1. Always use tools to get real data. Never guess.
2. Be concise — this is Slack, not a report.
3. Use bullet points and emoji for readability.
4. For scale operations: show preview first.
5. End with next recommended action.
6. If cluster appears empty: use kubectl_get_all_namespaces.
7. Format for Slack: use *bold* and bullet points.

TeleAlert context:
- Key services: telealert-api, telealert-worker, postgres, redis
- SLO: 99.9% availability, p95 < 500ms
- ArgoCD manages deployments via GitOps"""


def claude_agent_for_slack(question: str) -> str:
    """
    Run Claude agent with tool use.
    Returns formatted answer for Slack.
    """
    messages = [{"role": "user", "content": question}]
    tool_calls_made = []

    while True:
        response = claude.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=DEVOPS_TOOLS,
            messages=messages
        )

        if response.stop_reason == "tool_use":
            messages.append({
                "role": "assistant",
                "content": response.content
            })

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_calls_made.append(block.name)
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({
                "role": "user",
                "content": tool_results
            })

        elif response.stop_reason == "end_turn":
            answer = next(
                (b.text for b in response.content
                 if hasattr(b, "text")),
                "No response generated."
            )

            if tool_calls_made:
                tools_str = " → ".join(tool_calls_made)
                answer += f"\n\n_🔧 Tools used: {tools_str}_"

            return answer

        else:
            return f"Unexpected response: {response.stop_reason}"


# ══════════════════════════════════════════
# SLACK EVENT HANDLERS
# ══════════════════════════════════════════

@app.event("app_mention")
def handle_mention(event, say, client):
    """
    Respond when @ClaudeOps is mentioned.
    Works in any channel.
    """
    user     = event.get("user", "someone")
    text     = event.get("text", "")
    ts       = event.get("ts")
    channel  = event.get("channel")

    # Remove the bot mention from the question:
    question = text
    for part in text.split():
        if part.startswith("<@"):
            question = text.replace(part, "").strip()
            break

    if not question:
        say(
            text="👋 Hi! Ask me anything about your cluster.\n"
                 "Example: _@ClaudeOps what pods are running?_",
            thread_ts=ts
        )
        return

    # Acknowledge immediately:
    client.reactions_add(
        channel=channel,
        timestamp=ts,
        name="thinking_face"
    )

    print(f"[Slack] {user} asked: {question}")

    # Run Claude agent:
    answer = claude_agent_for_slack(question)

    # Remove thinking reaction:
    try:
        client.reactions_remove(
            channel=channel,
            timestamp=ts,
            name="thinking_face"
        )
    except Exception:
        pass

    # Post answer in thread:
    say(
        text=f"<@{user}> {answer}",
        thread_ts=ts
    )


@app.message("telealert status")
def handle_quick_status(message, say):
    """
    Quick status when anyone types 'telealert status'
    in a channel (no @mention needed).
    """
    say("🔍 Checking TeleAlert status...")
    answer = claude_agent_for_slack(
        "Give me a 3-bullet status summary of TeleAlert: "
        "are pods healthy, what is the SLO burn rate, "
        "any warning events in the last hour?"
    )
    say(answer)


@app.command("/claudeops")
def handle_slash_command(ack, respond, command):
    """
    /claudeops <question> slash command.
    Works from any channel.
    """
    ack()  # Must acknowledge within 3 seconds

    question = command.get("text", "").strip()
    user     = command.get("user_name", "someone")

    if not question:
        respond(
            "Usage: `/claudeops <your question>`\n"
            "Example: `/claudeops what pods are running?`"
        )
        return

    respond(f"🤖 ClaudeOps analyzing: _{question}_")

    print(f"[Slash] {user}: {question}")
    answer = claude_agent_for_slack(question)
    respond(answer)


# ══════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🤖 ClaudeOps Slack Bot Starting...")
    print("="*50)
    print(f"  Model:     {MODEL}")
    print(f"  Tools:     {len(DEVOPS_TOOLS)}")
    print(f"  Base URL:  {ANTHROPIC_BASE_URL}")
    print("="*50)
    print("\nBot is running! Go to Slack and type:")
    print("  @ClaudeOps what pods are running?")
    print("  @ClaudeOps what is the SLO status?")
    print("  telealert status")
    print("\nPress Ctrl+C to stop.\n")

    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()