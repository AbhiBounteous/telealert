# telealert/claude-ops/claude_ops.py
# Project created by Abhilash
# ClaudeOps — Senior DevOps AI Agent
# A CLI tool that uses Claude with tool_use to answer
# DevOps questions using real cluster data

import anthropic
import subprocess
import json
import sys
import requests
from typing import Any

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

# ══════════════════════════════════════════
# DEFINE TOOLS CLAUDE CAN USE
# ══════════════════════════════════════════

DEVOPS_TOOLS = [
    {
        "name": "kubectl_get_pods",
        "description": "Get all pods in a namespace with their status, restarts, and age. Use when asked about pod health, crashes, or restarts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": "Kubernetes namespace (default: 'default')"
                },
                "label_selector": {
                    "type": "string",
                    "description": "Optional label selector e.g. 'app=telealert'"
                }
            },
            "required": []
        }
    },
    {
        "name": "kubectl_describe_pod",
        "description": "Get detailed description of a specific pod including events. Use when a pod is crashing or in error state.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pod_name": {"type": "string", "description": "Name of the pod"},
                "namespace": {"type": "string", "description": "Namespace (default: 'default')"}
            },
            "required": ["pod_name"]
        }
    },
    {
        "name": "kubectl_get_logs",
        "description": "Get logs from a pod. Use when diagnosing application errors.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pod_name": {"type": "string"},
                "namespace": {"type": "string"},
                "tail_lines": {"type": "integer", "description": "Number of recent lines (default: 50)"},
                "previous": {"type": "boolean", "description": "Get logs from crashed previous container"}
            },
            "required": ["pod_name"]
        }
    },
    {
        "name": "prometheus_query",
        "description": "Run a PromQL query to get current metrics. Use for CPU, memory, error rate, latency questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "PromQL expression e.g. 'rate(http_requests_total[5m])'"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "argocd_app_status",
        "description": "Get ArgoCD application sync and health status. Use when asked about deployment state.",
        "input_schema": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "ArgoCD application name"}
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "kubectl_get_events",
        "description": "Get recent Kubernetes events sorted by time. Use when diagnosing scheduling or resource issues.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string", "description": "Namespace (default: 'default')"},
                "field_selector": {"type": "string", "description": "e.g. 'type=Warning'"}
            },
            "required": []
        }
    },
    {
        "name": "kubectl_get_all_namespaces",
        "description": "List all namespaces and pods across the entire cluster. Use when workloads are not found in default namespace.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "kubectl_apply",
        "description": "Apply a Kubernetes manifest. ONLY use when explicitly asked to fix or apply something AND user has confirmed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "manifest_yaml": {
                    "type": "string",
                    "description": "YAML manifest to apply"
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, validate only (default: true for safety!)"
                }
            },
            "required": ["manifest_yaml"]
        }
    }
]

# ══════════════════════════════════════════
# TOOL EXECUTION ENGINE
# ══════════════════════════════════════════

def run_kubectl(args: list) -> str:
    """Run kubectl command and return combined stdout + stderr"""
    try:
        result = subprocess.run(
            ["kubectl"] + args,
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout
        if result.stderr and result.returncode != 0:
            output += f"\nSTDERR: {result.stderr}"
        return output if output.strip() else "No output returned."
    except subprocess.TimeoutExpired:
        return "Error: kubectl command timed out after 30 seconds."
    except FileNotFoundError:
        return "Error: kubectl not found. Is it installed and in PATH?"
    except Exception as e:
        return f"Error running kubectl: {str(e)}"


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a DevOps tool and return the result as a string"""

    # ── kubectl_get_pods ───────────────────────────────────
    if tool_name == "kubectl_get_pods":
        ns = tool_input.get("namespace", "default")
        cmd = ["get", "pods", "-n", ns, "-o", "wide"]
        if label := tool_input.get("label_selector"):
            cmd += ["-l", label]
        pods = run_kubectl(cmd)

        # Also try to get resource usage (may fail if metrics-server not installed)
        try:
            top = run_kubectl(["top", "pods", "-n", ns, "--no-headers"])
            return f"=== Pods in '{ns}' ===\n{pods}\n=== Resource Usage ===\n{top}"
        except Exception:
            return f"=== Pods in '{ns}' ===\n{pods}"

    # ── kubectl_get_all_namespaces ─────────────────────────
    elif tool_name == "kubectl_get_all_namespaces":
        namespaces = run_kubectl(["get", "namespaces", "--no-headers",
                                  "-o", "custom-columns=NAME:.metadata.name"])
        pods_all = run_kubectl(["get", "pods", "--all-namespaces", "-o", "wide"])
        return f"=== All Namespaces ===\n{namespaces}\n\n=== All Pods ===\n{pods_all}"

    # ── kubectl_describe_pod ───────────────────────────────
    elif tool_name == "kubectl_describe_pod":
        ns = tool_input.get("namespace", "default")
        pod = tool_input["pod_name"]
        return run_kubectl(["describe", "pod", pod, "-n", ns])

    # ── kubectl_get_logs ───────────────────────────────────
    elif tool_name == "kubectl_get_logs":
        ns = tool_input.get("namespace", "default")
        pod = tool_input["pod_name"]
        tail = tool_input.get("tail_lines", 50)
        cmd = ["logs", pod, "-n", ns, f"--tail={tail}"]
        if tool_input.get("previous"):
            cmd.append("--previous")
        return run_kubectl(cmd)

    # ── prometheus_query ───────────────────────────────────
    elif tool_name == "prometheus_query":
        query = tool_input["query"]
        try:
            r = requests.get(
                "http://localhost:9090/api/v1/query",
                params={"query": query},
                timeout=10
            )
            data = r.json()
            if data.get("status") == "success" and data["data"]["result"]:
                results = []
                for item in data["data"]["result"][:10]:
                    labels = item.get("metric", {})
                    value = item["value"][1]
                    results.append(f"{labels}: {value}")
                return "\n".join(results)
            return (
                f"No data returned for query: {query}\n"
                "Hint: Is Prometheus port-forwarded? "
                "Run: kubectl port-forward svc/prometheus-server 9090:80 -n monitoring"
            )
        except requests.exceptions.ConnectionError:
            return (
                "Cannot connect to Prometheus on localhost:9090.\n"
                "Start port-forward: kubectl port-forward svc/prometheus-server 9090:80 -n monitoring &"
            )
        except Exception as e:
            return f"Prometheus error: {e}"

    # ── argocd_app_status ──────────────────────────────────
    elif tool_name == "argocd_app_status":
        app = tool_input["app_name"]

        # Try argocd namespace first, then argocd-system
        for ns in ["argocd", "argocd-system"]:
            result = run_kubectl([
                "get", "application", app,
                "-n", ns,
                "-o", "jsonpath={.status.sync.status}|{.status.health.status}|{.status.operationState.phase}",
                "--ignore-not-found"
            ])
            # A real app always yields "sync|health|phase", so require the separator
            # and reject run_kubectl's placeholder/error strings.
            if "|" in result and "STDERR:" not in result and not result.startswith("Error"):
                parts = result.strip().split("|")
                sync    = parts[0] if len(parts) > 0 else "Unknown"
                health  = parts[1] if len(parts) > 1 else "Unknown"
                phase   = parts[2] if len(parts) > 2 else "Unknown"
                return (
                    f"ArgoCD App: {app}\n"
                    f"  Sync:   {sync}\n"
                    f"  Health: {health}\n"
                    f"  Phase:  {phase}"
                )

        # ArgoCD CLI fallback
        try:
            cli = subprocess.run(
                ["argocd", "app", "get", app, "--output", "json"],
                capture_output=True, text=True, timeout=15
            )
            if cli.returncode == 0 and cli.stdout:
                data = json.loads(cli.stdout)
                sync   = data.get("status", {}).get("sync", {}).get("status", "Unknown")
                health = data.get("status", {}).get("health", {}).get("status", "Unknown")
                return f"ArgoCD App: {app}\n  Sync: {sync}\n  Health: {health}"
        except Exception:
            pass

        return (
            f"ArgoCD app '{app}' not found.\n"
            "Possible reasons:\n"
            "  1. ArgoCD is not installed on this cluster\n"
            "  2. The app name is different — run: kubectl get applications -A\n"
            "  3. Your kubectl context points to a different cluster"
        )

    # ── kubectl_get_events ─────────────────────────────────
    elif tool_name == "kubectl_get_events":
        ns = tool_input.get("namespace", "default")
        # BUG FIX: removed --tail flag (not supported by kubectl get events)
        cmd = ["get", "events", "-n", ns, "--sort-by=.lastTimestamp"]
        if fs := tool_input.get("field_selector"):
            cmd += ["--field-selector", fs]
        result = run_kubectl(cmd)

        # Return last 20 lines only to keep output manageable
        lines = result.strip().split("\n")
        if len(lines) > 21:  # header + 20 events
            result = "\n".join(lines[:1] + lines[-20:])  # keep header + last 20
        return result

    # ── kubectl_apply ──────────────────────────────────────
    elif tool_name == "kubectl_apply":
        manifest = tool_input["manifest_yaml"]
        dry_run  = tool_input.get("dry_run", True)  # SAFE DEFAULT: always dry-run!

        import tempfile, os
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(manifest)
            tmp_path = f.name

        cmd = ["apply", "-f", tmp_path]
        if dry_run:
            cmd += ["--dry-run=client"]

        result = run_kubectl(cmd)
        os.unlink(tmp_path)

        if dry_run:
            return (
                f"DRY RUN RESULT (nothing applied yet):\n{result}\n\n"
                "To actually apply, run again with dry_run=false after confirming."
            )
        return f"APPLIED:\n{result}"

    return f"Unknown tool: {tool_name}"


# ══════════════════════════════════════════
# AGENTIC LOOP
# Handles multi-tool use automatically
# ══════════════════════════════════════════

MAX_AGENT_ITERATIONS = 15


def claude_ops_agent(user_question: str, verbose: bool = False) -> str:
    """
    Claude DevOps agent with tool use.
    Automatically calls kubectl, Prometheus, ArgoCD as needed.
    Loops until Claude stops using tools and gives a final answer.
    """

    system_prompt = """You are ClaudeOps, a Senior DevOps AI engineer for TeleAlert.

Your job: answer questions about the Kubernetes cluster by using the available
tools to gather REAL data, then provide specific, actionable analysis.

RULES:
1. Always use tools to get real data. Never guess or make up values.
2. For debugging: start broad (kubectl_get_all_namespaces or kubectl_get_pods),
   then narrow (describe specific pod, get logs).
3. For apply/fix operations: ALWAYS use dry_run=true first, show the result,
   then ask user to confirm before real apply.
4. Be specific: quote actual values from tool output.
5. If pods are not in 'default', use kubectl_get_all_namespaces to find them.
6. If Prometheus is unavailable, say so clearly and suggest the port-forward command.
7. If ArgoCD is not found, say so and suggest kubectl get applications -A.
8. End every response with: next recommended action.

TeleAlert context:
- Key deployments: telealert-api, telealert-worker, postgres, redis
- Prometheus port: 9090 (needs port-forward if remote cluster)
- ArgoCD namespace: argocd or argocd-system
- SLOs: availability 99.9%, p95 latency < 500ms
- If cluster appears empty, ALWAYS try kubectl_get_all_namespaces first."""

    messages = [{"role": "user", "content": user_question}]
    tool_calls_made = []

    # Agentic loop — continues until Claude stops using tools, up to MAX_AGENT_ITERATIONS
    for _ in range(MAX_AGENT_ITERATIONS):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system_prompt,
            tools=DEVOPS_TOOLS,
            messages=messages
        )

        if verbose:
            print(f"\n[Claude stop_reason: {response.stop_reason}]")

        # ── Claude wants to use tools ──────────────────────
        if response.stop_reason == "tool_use":
            messages.append({
                "role": "assistant",
                "content": response.content
            })

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_name  = block.name
                    tool_input = block.input
                    tool_calls_made.append(tool_name)

                    print(f"\n🔧 Claude is using: {tool_name}")
                    if verbose:
                        print(f"   Input: {json.dumps(tool_input, indent=2)}")

                    is_error = False
                    try:
                        result = execute_tool(tool_name, tool_input)
                    except Exception as e:
                        is_error = True
                        result = f"Tool '{tool_name}' failed: {type(e).__name__}: {e}"

                    if verbose:
                        preview = result[:300] if len(result) > 300 else result
                        print(f"   Result preview: {preview}")

                    tool_result = {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    }
                    if is_error:
                        tool_result["is_error"] = True
                    tool_results.append(tool_result)

            messages.append({
                "role": "user",
                "content": tool_results
            })

        # ── Claude finished — return final answer ──────────
        elif response.stop_reason == "end_turn":
            final_answer = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_answer += block.text

            if tool_calls_made:
                print(f"\n✅ Tools used: {' → '.join(tool_calls_made)}")
            else:
                print("\n✅ Tools used: none (answered from context)")

            return final_answer

        else:
            return f"Unexpected stop_reason: {response.stop_reason}"

    return (
        f"Stopped after {MAX_AGENT_ITERATIONS} model calls without a final answer. "
        f"Tools used so far: {' → '.join(tool_calls_made)}. "
        "Try a narrower question."
    )


# ══════════════════════════════════════════
# STREAMING VERSION
# Shows Claude's answer in real time
# ══════════════════════════════════════════

def claude_ops_stream(user_question: str):
    """Streaming version — answer appears word by word (no tool use)"""
    print(f"\n🤖 ClaudeOps (stream): {user_question}\n{'='*60}")

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system="You are ClaudeOps, a Senior DevOps AI. Be concise and specific.",
        messages=[{"role": "user", "content": user_question}]
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
    print("\n")


# ══════════════════════════════════════════
# CLI INTERFACE
# ══════════════════════════════════════════

def print_banner():
    print("\n" + "="*60)
    print("🤖  ClaudeOps — Senior DevOps AI Agent")
    print("="*60)
    print("Commands:")
    print("  Type any DevOps question → Claude answers with real data")
    print("  Add --stream  → streaming answer (no tool use)")
    print("  Add --verbose → show tool inputs and result previews")
    print("  exit          → quit")
    print("="*60)
    print("\nExample questions:")
    print("  What pods are running?")
    print("  Why is telealert-api crashing?")
    print("  What is the current error rate?")
    print("  Is ArgoCD synced?")
    print("  Show me all namespaces and pods")
    print("="*60 + "\n")


if __name__ == "__main__":
    print_banner()

    while True:
        try:
            question = input("📋 Your question: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye! 👋")
            sys.exit(0)

        if not question:
            continue

        if question.lower() in ("exit", "quit", "q"):
            print("Goodbye! 👋")
            sys.exit(0)

        verbose = "--verbose" in question
        stream  = "--stream"  in question

        # Strip flags from the actual question
        clean_question = (
            question
            .replace("--verbose", "")
            .replace("--stream", "")
            .strip()
        )

        if not clean_question:
            print("Please enter a question.")
            continue

        print("")  # blank line before Claude's response

        if stream:
            claude_ops_stream(clean_question)
        else:
            answer = claude_ops_agent(clean_question, verbose=verbose)
            print(f"\n{'='*60}")
            print(answer)
            print(f"{'='*60}\n")
