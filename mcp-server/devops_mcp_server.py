import anthropic
import subprocess
import json
import requests
import os

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"
TELEALERT_API = "http://localhost:5001"

tools = [
    {
        "name": "kubectl_get_pods",
        "description": "Get the status of all Kubernetes pods in the cluster. Use this to check if pods are running, crashed, or pending.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": "Kubernetes namespace to check. Default is 'default'",
                }
            },
            "required": []
        }
    },
    {
        "name": "kubectl_get_logs",
        "description": "Get logs from a Kubernetes deployment. Use this to diagnose errors in running pods.",
        "input_schema": {
            "type": "object",
            "properties": {
                "deployment": {
                    "type": "string",
                    "description": "Name of the deployment to get logs from"
                },
                "lines": {
                    "type": "integer",
                    "description": "Number of log lines to retrieve. Default is 20"
                }
            },
            "required": ["deployment"]
        }
    },
    {
        "name": "kubectl_scale",
        "description": "Scale a Kubernetes deployment up or down. Use this to handle traffic spikes or reduce load.",
        "input_schema": {
            "type": "object",
            "properties": {
                "deployment": {
                    "type": "string",
                    "description": "Name of the deployment to scale"
                },
                "replicas": {
                    "type": "integer",
                    "description": "Number of replicas to scale to"
                }
            },
            "required": ["deployment", "replicas"]
        }
    },
    {
        "name": "kubectl_rollout_status",
        "description": "Check the rollout status of a Kubernetes deployment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "deployment": {
                    "type": "string",
                    "description": "Name of the deployment to check"
                }
            },
            "required": ["deployment"]
        }
    },
    {
        "name": "get_telealert_status",
        "description": "Get live metrics and status from the TeleAlert telecom network monitoring API. Returns event counts and critical alerts.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_telealert_alerts",
        "description": "Get the most recent critical network alerts from TeleAlert. Use this to understand what network events are happening.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

def run_tool(tool_name, tool_input):
    """Execute the requested tool and return result"""
    print(f"\n🔧 Claude is calling tool: {tool_name}")
    print(f"   Input: {json.dumps(tool_input, indent=2)}")

    if tool_name == "kubectl_get_pods":
        namespace = tool_input.get("namespace", "default")
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace],
            capture_output=True, text=True
        )
        return result.stdout or result.stderr

    elif tool_name == "kubectl_get_logs":
        deployment = tool_input["deployment"]
        lines = tool_input.get("lines", 20)
        result = subprocess.run(
            ["kubectl", "logs", f"deployment/{deployment}", f"--tail={lines}"],
            capture_output=True, text=True
        )
        return result.stdout or result.stderr

    elif tool_name == "kubectl_scale":
        deployment = tool_input["deployment"]
        replicas = tool_input["replicas"]
        result = subprocess.run(
            ["kubectl", "scale", "deployment", deployment,
             f"--replicas={replicas}"],
            capture_output=True, text=True
        )
        return result.stdout or result.stderr

    elif tool_name == "kubectl_rollout_status":
        deployment = tool_input["deployment"]
        result = subprocess.run(
            ["kubectl", "rollout", "status",
             f"deployment/{deployment}"],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout or result.stderr

    elif tool_name == "get_telealert_status":
        try:
            response = requests.get(f"{TELEALERT_API}/status")
            return json.dumps(response.json(), indent=2)
        except Exception as e:
            return f"Error connecting to TeleAlert API: {e}"

    elif tool_name == "get_telealert_alerts":
        try:
            response = requests.get(f"{TELEALERT_API}/alerts")
            return json.dumps(response.json(), indent=2)
        except Exception as e:
            return f"Error connecting to TeleAlert API: {e}"

    return f"Unknown tool: {tool_name}"

def run_agent(user_request):
    """Run Claude as an autonomous DevOps agent"""
    print(f"\n{'='*60}")
    print(f"TELEALERT DEVOPS AGENT")
    print(f"{'='*60}")
    print(f"Request: {user_request}")
    print(f"{'='*60}\n")

    messages = [
        {"role": "user", "content": user_request}
    ]

    system_prompt = """You are an autonomous DevOps agent for TeleAlert — 
a telecom network monitoring system running on Kubernetes at 
Bounteous × Telecom & Media Practice.

You have access to kubectl tools to manage the Kubernetes cluster 
and TeleAlert API tools to check network metrics.

When given a task:
1. Think through what information you need
2. Call the appropriate tools to gather data
3. Analyze the results
4. Take action if needed
5. Report back with a clear summary

Always check the current state before making changes.
Be thorough but concise in your final report."""

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=system_prompt,
            tools=tools,
            messages=messages
        )

        if response.stop_reason == "end_turn":
            print(f"\n{'='*60}")
            print("AGENT FINAL REPORT")
            print(f"{'='*60}")
            for block in response.content:
                if hasattr(block, 'text'):
                    print(block.text)
            print(f"{'='*60}\n")
            break

        if response.stop_reason == "tool_use":
            messages.append({
                "role": "assistant",
                "content": response.content
            })

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = run_tool(block.name, block.input)
                    print(f"   Result: {result[:200]}...")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({
                "role": "user",
                "content": tool_results
            })

if __name__ == "__main__":
    print("\n🚀 TeleAlert DevOps Agent starting...")
    print("📡 Claude will autonomously check and manage your cluster\n")

    run_agent("""
    You are the on-call DevOps agent for TeleAlert.
    Please do the following:
    1. Check the current status of all Kubernetes pods
    2. Get the latest metrics from TeleAlert API
    3. Check recent critical alerts
    4. Get logs from the telealert-worker deployment
    5. Based on what you find, recommend if any scaling is needed
    6. Provide a complete health report of the system
    """)