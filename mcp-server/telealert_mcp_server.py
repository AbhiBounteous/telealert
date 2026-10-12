"""
TeleAlert MCP Server — FastMCP version
Works with MCP SDK 1.x
"""

import subprocess
import requests
import time
from mcp.server.fastmcp import FastMCP

# ══════════════════════════════════════════
# CREATE SERVER
# ══════════════════════════════════════════

mcp = FastMCP("telealert-devops")

# ══════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════

def run_kubectl(args: list) -> str:
    try:
        result = subprocess.run(
            ["kubectl"] + args,
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout
        if result.returncode != 0 and result.stderr:
            output += f"\nError: {result.stderr}"
        return output.strip() or "No output returned."
    except subprocess.TimeoutExpired:
        return "Error: kubectl timed out."
    except FileNotFoundError:
        return "Error: kubectl not found."
    except Exception as e:
        return f"Error: {str(e)}"


def query_prometheus(query: str) -> str:
    try:
        r = requests.get(
            "http://localhost:9090/api/v1/query",
            params={"query": query},
            timeout=10
        )
        data = r.json()
        if data.get("status") == "success" and data["data"]["result"]:
            lines = []
            for item in data["data"]["result"][:10]:
                metric = item.get("metric", {})
                value = item["value"][1]
                lines.append(f"{metric}: {value}")
            return "\n".join(lines)
        return (
            "No data. Start port-forward: "
            "kubectl port-forward svc/prometheus-server 9090:80 -n monitoring &"
        )
    except requests.exceptions.ConnectionError:
        return (
            "Cannot connect to Prometheus on localhost:9090.\n"
            "Run: kubectl port-forward svc/prometheus-server 9090:80 -n monitoring &"
        )
    except Exception as e:
        return f"Prometheus error: {str(e)}"


# ══════════════════════════════════════════
# TOOLS
# ══════════════════════════════════════════

@mcp.tool()
def get_pod_status(namespace: str = "default") -> str:
    """
    Get status of all pods in a namespace.
    Shows health, restarts, age, and resource usage.
    Use when asked about pod health or crashes.
    """
    pods = run_kubectl(["get", "pods", "-n", namespace, "-o", "wide"])
    top = run_kubectl(["top", "pods", "-n", namespace, "--no-headers"])
    return f"=== Pods in '{namespace}' ===\n{pods}\n\n=== CPU/Memory ===\n{top}"


@mcp.tool()
def get_all_namespaces() -> str:
    """
    List all namespaces and pods across the entire cluster.
    Use when workloads are not found in the default namespace.
    """
    ns_list = run_kubectl(["get", "namespaces", "--no-headers"])
    all_pods = run_kubectl(["get", "pods", "--all-namespaces", "-o", "wide"])
    return f"=== Namespaces ===\n{ns_list}\n\n=== All Pods ===\n{all_pods}"


@mcp.tool()
def get_pod_logs(
    pod_name: str,
    namespace: str = "default",
    tail_lines: int = 50,
    previous: bool = False
) -> str:
    """
    Get logs from a specific pod.
    Use when diagnosing application errors or crashes.
    Set previous=True to get logs from a crashed container.
    """
    cmd = ["logs", pod_name, "-n", namespace, f"--tail={tail_lines}"]
    if previous:
        cmd.append("--previous")
    return run_kubectl(cmd)


@mcp.tool()
def describe_pod(pod_name: str, namespace: str = "default") -> str:
    """
    Get detailed description of a pod including events.
    Use when a pod is stuck, crashing, or pending.
    """
    return run_kubectl(["describe", "pod", pod_name, "-n", namespace])


@mcp.tool()
def get_cluster_events(namespace: str = "default") -> str:
    """
    Get recent Kubernetes warning events sorted by time.
    Use when diagnosing scheduling, OOM, or resource issues.
    """
    result = run_kubectl([
        "get", "events", "-n", namespace,
        "--sort-by=.lastTimestamp",
        "--field-selector=type=Warning"
    ])
    lines = result.strip().split("\n")
    if len(lines) > 21:
        result = "\n".join(lines[:1] + lines[-20:])
    return result


@mcp.tool()
def run_prometheus_query(query: str) -> str:
    """
    Run a PromQL query to get current metrics.
    Use for CPU, memory, error rate, latency, SLO questions.
    Requires Prometheus port-forwarded to localhost:9090.
    Example queries:
      rate(http_requests_total[5m])
      histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
    """
    return query_prometheus(query)


@mcp.tool()
def get_slo_status() -> str:
    """
    Get current TeleAlert SLO status.
    Shows availability burn rate, error budget, p95 latency, error rate.
    Use when asked about reliability or SLO health.
    """
    queries = {
        "Error Rate (%)": (
            "sum(rate(http_requests_total{status=~'5..'}[5m])) "
            "/ sum(rate(http_requests_total[5m])) * 100"
        ),
        "p95 Latency (ms)": (
            "histogram_quantile(0.95, rate("
            "http_request_duration_seconds_bucket{job='telealert'}[5m])) * 1000"
        ),
        "Availability Burn Rate": (
            "telealert:availability:error_ratio1h / 0.001"
        ),
        "Error Budget Consumed": (
            "telealert:availability:error_budget_consumed"
        )
    }
    lines = ["=== TeleAlert SLO Status ==="]
    for label, query in queries.items():
        value = query_prometheus(query)
        lines.append(f"{label}:\n  {value}")
    return "\n".join(lines)


@mcp.tool()
def scale_deployment(
    deployment: str,
    replicas: int,
    namespace: str = "default",
    confirmed: bool = False
) -> str:
    """
    Scale a deployment to N replicas.
    SAFETY: shows preview first unless confirmed=True.
    Always call without confirmed=True first to see what will happen.
    Only set confirmed=True after reviewing the preview.
    """
    current = run_kubectl([
        "get", "deployment", deployment,
        "-n", namespace,
        "-o", "jsonpath={.spec.replicas}",
        "--ignore-not-found"
    ])

    if not confirmed:
        return (
            f"SCALE PREVIEW (nothing applied yet):\n"
            f"  Deployment: {deployment}\n"
            f"  Namespace:  {namespace}\n"
            f"  Current replicas: {current or 'unknown'}\n"
            f"  Requested replicas: {replicas}\n\n"
            f"Call again with confirmed=True to apply."
        )

    result = run_kubectl([
        "scale", "deployment", deployment,
        f"--replicas={replicas}",
        "-n", namespace
    ])
    return f"Scaled {deployment} to {replicas} replicas:\n{result}"


@mcp.tool()
def rollback_deployment(
    deployment: str,
    namespace: str = "default",
    confirmed: bool = False
) -> str:
    """
    Rollback a deployment to the previous revision.
    SAFETY: shows rollout history first unless confirmed=True.
    Always call without confirmed=True first to review history.
    """
    history = run_kubectl([
        "rollout", "history",
        f"deployment/{deployment}",
        "-n", namespace
    ])

    if not confirmed:
        return (
            f"ROLLBACK PREVIEW:\n{history}\n\n"
            f"Call again with confirmed=True to rollback."
        )

    result = run_kubectl([
        "rollout", "undo",
        f"deployment/{deployment}",
        "-n", namespace
    ])
    return f"Rollback result:\n{result}"


@mcp.tool()
def get_argocd_status(app_name: str = "telealert") -> str:
    """
    Get ArgoCD application sync and health status.
    Use when asked about deployment or GitOps state.
    """
    for ns in ["argocd", "argocd-system"]:
        result = run_kubectl([
            "get", "application", app_name,
            "-n", ns,
            "-o",
            "jsonpath={.status.sync.status}|"
            "{.status.health.status}|"
            "{.status.operationState.phase}",
            "--ignore-not-found"
        ])
        if result and result.strip():
            parts  = result.strip().split("|")
            sync   = parts[0] if len(parts) > 0 else "Unknown"
            health = parts[1] if len(parts) > 1 else "Unknown"
            phase  = parts[2] if len(parts) > 2 else "Unknown"
            return (
                f"ArgoCD App: {app_name}\n"
                f"  Sync:   {sync}\n"
                f"  Health: {health}\n"
                f"  Phase:  {phase}"
            )
    return (
        f"ArgoCD app '{app_name}' not found.\n"
        "Check: kubectl get applications -A"
    )


@mcp.tool()
def trigger_velero_backup(backup_name: str = "") -> str:
    """
    Trigger an immediate Velero backup of TeleAlert namespaces.
    Use before any risky operation or when asked to create a backup.
    """
    name = backup_name or f"mcp-backup-{int(time.time())}"
    try:
        result = subprocess.run(
            [
                "velero", "backup", "create", name,
                "--include-namespaces",
                "default,monitoring,litmus",
                "--wait"
            ],
            capture_output=True, text=True, timeout=300
        )
        return f"Backup '{name}':\n{result.stdout}\n{result.stderr}"
    except FileNotFoundError:
        return "Velero not installed or not in PATH."
    except Exception as e:
        return f"Backup error: {str(e)}"


# ══════════════════════════════════════════
# RUN
# ══════════════════════════════════════════

if __name__ == "__main__":
    print("TeleAlert MCP Server starting...")
    print("10 DevOps tools registered")
    print("Waiting for Claude Desktop connection...")
    mcp.run()