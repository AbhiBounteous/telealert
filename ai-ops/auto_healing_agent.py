import anthropic
import subprocess
import json
import requests
import os
import time
from datetime import datetime

client = anthropic.Anthropic(
    timeout=60.0,
    max_retries=3
)
MODEL = "claude-sonnet-4-6"
TELEALERT_API = "http://localhost:5001"

tools = [
    {
        "name": "kubectl_get_pods",
        "description": "Get status of all Kubernetes pods. Use to detect crashed or unhealthy pods.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": "Kubernetes namespace. Default is default"
                }
            },
            "required": []
        }
    },
    {
        "name": "kubectl_restart_deployment",
        "description": "Restart a Kubernetes deployment to heal crashed pods.",
        "input_schema": {
            "type": "object",
            "properties": {
                "deployment": {
                    "type": "string",
                    "description": "Name of deployment to restart"
                }
            },
            "required": ["deployment"]
        }
    },
    {
        "name": "kubectl_get_logs",
        "description": "Get logs from a deployment to understand why it crashed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "deployment": {
                    "type": "string",
                    "description": "Name of deployment"
                },
                "lines": {
                    "type": "integer",
                    "description": "Number of lines to retrieve"
                }
            },
            "required": ["deployment"]
        }
    },
    {
        "name": "kubectl_describe_pod",
        "description": "Get detailed information about a specific pod including events and errors.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pod_name": {
                    "type": "string",
                    "description": "Full name of the pod"
                }
            },
            "required": ["pod_name"]
        }
    },
    {
        "name": "kubectl_scale",
        "description": "Scale a deployment up or down.",
        "input_schema": {
            "type": "object",
            "properties": {
                "deployment": {
                    "type": "string",
                    "description": "Name of deployment"
                },
                "replicas": {
                    "type": "integer",
                    "description": "Number of replicas"
                }
            },
            "required": ["deployment", "replicas"]
        }
    },
    {
        "name": "get_telealert_status",
        "description": "Get live metrics from TeleAlert API.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

def run_tool(tool_name, tool_input):
    """Execute kubectl or API tool"""
    print(f"  🔧 Tool: {tool_name} | Input: {tool_input}")

    if tool_name == "kubectl_get_pods":
        namespace = tool_input.get("namespace", "default")
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace],
            capture_output=True, text=True
        )
        return result.stdout or result.stderr

    elif tool_name == "kubectl_restart_deployment":
        deployment = tool_input["deployment"]
        result = subprocess.run(
            ["kubectl", "rollout", "restart",
             f"deployment/{deployment}"],
            capture_output=True, text=True
        )
        return result.stdout or result.stderr

    elif tool_name == "kubectl_get_logs":
        deployment = tool_input["deployment"]
        lines = tool_input.get("lines", 20)
        result = subprocess.run(
            ["kubectl", "logs",
             f"deployment/{deployment}",
             f"--tail={lines}"],
            capture_output=True, text=True
        )
        return result.stdout or result.stderr

    elif tool_name == "kubectl_describe_pod":
        pod_name = tool_input["pod_name"]
        result = subprocess.run(
            ["kubectl", "describe", "pod", pod_name],
            capture_output=True, text=True
        )
        return result.stdout[:2000] or result.stderr

    elif tool_name == "kubectl_scale":
        deployment = tool_input["deployment"]
        replicas = tool_input["replicas"]
        result = subprocess.run(
            ["kubectl", "scale", "deployment",
             deployment, f"--replicas={replicas}"],
            capture_output=True, text=True
        )
        return result.stdout or result.stderr

    elif tool_name == "get_telealert_status":
        try:
            response = requests.get(f"{TELEALERT_API}/status")
            return json.dumps(response.json(), indent=2)
        except Exception as e:
            return f"API error: {e}"

    return f"Unknown tool: {tool_name}"

def run_agent(user_request, silent=False):
    """Run Claude as autonomous agent"""
    if not silent:
        print(f"\n{'='*60}")
        print(f"REQUEST: {user_request}")
        print(f"{'='*60}")

    messages = [{"role": "user", "content": user_request}]

    system_prompt = """You are an autonomous DevOps healing agent 
for TeleAlert at Bounteous × Telecom & Media Practice.

Your job is to:
1. Monitor Kubernetes cluster health
2. Detect crashed or unhealthy pods
3. Automatically restart failing deployments
4. Scale up if needed
5. Report what you did and why

Always check pod status first. If you find crashed pods:
- Get logs to understand why
- Restart the deployment
- Verify it recovered
- Report the healing action taken

Be decisive and act quickly."""

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=system_prompt,
            tools=tools,
            messages=messages
        )

        if response.stop_reason == "end_turn":
            final_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    final_text = block.text
            return final_text

        if response.stop_reason == "tool_use":
            messages.append({
                "role": "assistant",
                "content": response.content
            })

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({
                "role": "user",
                "content": tool_results
            })

def auto_heal_loop():
    """Continuously monitor and auto-heal every 60 seconds"""
    print("\n🚀 TeleAlert Auto-Healing Agent started")
    print("📡 Monitoring cluster every 60 seconds")
    print("Press Ctrl+C to stop\n")

    check_count = 0
    healed_count = 0

    while True:
        try:
            check_count += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{timestamp}] Health check #{check_count}")

            result = run_agent("""
            Check all Kubernetes pods right now.
            If any pods are in CrashLoopBackOff, Error,
            or ImagePullBackOff state:
            1. Get logs to understand why
            2. Restart that deployment
            3. Confirm it recovered
            If everything is healthy just say HEALTHY.
            Be brief.
            """, silent=True)

            if "HEALTHY" in result.upper():
                print(f"  ✅ All pods healthy")
            else:
                healed_count += 1
                print(f"\n🚨 ISSUE DETECTED AND HEALED:")
                print(result)
                log_healing_action(timestamp, result)

            print(f"  📊 Checks: {check_count} | "
                  f"Heals: {healed_count}")
            time.sleep(60)

        except KeyboardInterrupt:
            print(f"\n\n Agent stopped.")
            print(f"Total checks: {check_count}")
            print(f"Total heals:  {healed_count}")
            break
        except Exception as e:
            print(f"  ⚠️ Error: {e}")
            time.sleep(60)

def log_healing_action(timestamp, action):
    """Log healing actions to file"""
    log_file = "/tmp/telealert_healing_log.txt"
    with open(log_file, "a") as f:
        f.write(f"\n[{timestamp}]\n{action}\n{'='*40}\n")
    print(f"  💾 Logged to {log_file}")

def natural_language_cli():
    """Chat with Claude about your cluster"""
    print("\n🤖 TeleAlert Natural Language CLI")
    print("Ask anything about your cluster in plain English")
    print("Type 'exit' to quit\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() == 'exit':
            print("Goodbye!")
            break

        if not user_input:
            continue

        print("\nClaude: thinking...\n")
        result = run_agent(user_input)
        print(f"\nClaude: {result}\n")
        print("-" * 40)

if __name__ == "__main__":
    print("\n🚀 TeleAlert Auto-Healing + NL Agent")
    print("=" * 40)
    print("1. Start auto-healing monitor")
    print("2. Natural language CLI")
    print("3. Single health check")
    print("=" * 40)

    choice = input("Choose (1/2/3): ").strip()

    if choice == "1":
        auto_heal_loop()
    elif choice == "2":
        natural_language_cli()
    elif choice == "3":
        print("\nRunning single health check...\n")
        result = run_agent("""
        Check all pods and TeleAlert metrics.
        Give me a complete health summary in
        plain English. Be concise.
        """)
        print(result)
    else:
        print("Invalid choice")