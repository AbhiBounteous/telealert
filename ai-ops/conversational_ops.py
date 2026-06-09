import anthropic
import subprocess
import json
import requests
import os
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
        "description": "Get status of all Kubernetes pods.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": "Kubernetes namespace"
                }
            },
            "required": []
        }
    },
    {
        "name": "kubectl_get_logs",
        "description": "Get logs from a deployment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "deployment": {
                    "type": "string",
                    "description": "Deployment name"
                },
                "lines": {
                    "type": "integer",
                    "description": "Number of lines"
                }
            },
            "required": ["deployment"]
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
                    "description": "Deployment name"
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
        "name": "kubectl_rollout_restart",
        "description": "Restart a deployment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "deployment": {
                    "type": "string",
                    "description": "Deployment name"
                }
            },
            "required": ["deployment"]
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
    },
    {
        "name": "get_telealert_alerts",
        "description": "Get recent critical alerts from TeleAlert.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "save_report",
        "description": "Save a report to a file on disk.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Name of the file to save"
                },
                "content": {
                    "type": "string",
                    "description": "Content to save"
                }
            },
            "required": ["filename", "content"]
        }
    }
]

def run_tool(tool_name, tool_input):
    """Execute the requested tool"""
    print(f"  🔧 {tool_name}")

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
            ["kubectl", "logs",
             f"deployment/{deployment}",
             f"--tail={lines}"],
            capture_output=True, text=True
        )
        return result.stdout or result.stderr

    elif tool_name == "kubectl_scale":
        deployment = tool_input["deployment"]
        replicas = tool_input["replicas"]
        result = subprocess.run(
            ["kubectl", "scale", "deployment",
             deployment, f"--replicas={replicas}"],
            capture_output=True, text=True
        )
        return result.stdout or result.stderr

    elif tool_name == "kubectl_rollout_restart":
        deployment = tool_input["deployment"]
        result = subprocess.run(
            ["kubectl", "rollout", "restart",
             f"deployment/{deployment}"],
            capture_output=True, text=True
        )
        return result.stdout or result.stderr

    elif tool_name == "get_telealert_status":
        try:
            response = requests.get(f"{TELEALERT_API}/status")
            return json.dumps(response.json(), indent=2)
        except Exception as e:
            return f"API error: {e}"

    elif tool_name == "get_telealert_alerts":
        try:
            response = requests.get(f"{TELEALERT_API}/alerts")
            return json.dumps(response.json(), indent=2)
        except Exception as e:
            return f"API error: {e}"

    elif tool_name == "save_report":
        filename = tool_input["filename"]
        content = tool_input["content"]
        filepath = f"/tmp/{filename}"
        with open(filepath, "w") as f:
            f.write(content)
        return f"Report saved to {filepath}"

    return f"Unknown tool: {tool_name}"

def process_turn(messages, user_input, system_prompt):
    """Process one conversation turn"""
    messages.append({
        "role": "user",
        "content": user_input
    })

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=system_prompt,
            tools=tools,
            messages=messages
        )

        if response.stop_reason == "end_turn":
            final_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    final_text = block.text
            messages.append({
                "role": "assistant",
                "content": response.content
            })
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

def show_conversation_history(messages):
    """Show summary of conversation so far"""
    turns = sum(1 for m in messages
                if m["role"] == "user"
                and isinstance(m["content"], str))
    print(f"\n  📝 Conversation turns: {turns}")

def main():
    """Main conversational ops loop"""
    print("\n" + "="*60)
    print("🤖 TELEALERT CONVERSATIONAL OPS")
    print("Powered by Claude AI — Bounteous NOC")
    print("="*60)
    print("Chat with Claude about your cluster.")
    print("Claude remembers the full conversation.")
    print("Type 'history' to see turn count.")
    print("Type 'reset' to start fresh.")
    print("Type 'exit' to quit.")
    print("="*60 + "\n")

    system_prompt = f"""You are an expert DevOps engineer and NOC analyst 
for TeleAlert at Bounteous × Telecom & Media Practice.

You have access to kubectl tools and the TeleAlert API.
You maintain full context across the entire conversation.

Key behaviors:
- Remember everything discussed in this conversation
- Reference previous findings when relevant
- Take actions proactively when asked
- Build on previous analysis rather than starting fresh
- When asked for a report — include everything discussed
- When asked to save — use the save_report tool

Current session started: {datetime.now().isoformat()}
You are the on-call NOC engineer for this shift."""

    messages = []
    session_start = datetime.now()

    while True:
        try:
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            if user_input.lower() == 'exit':
                duration = datetime.now() - session_start
                print(f"\n👋 Session ended.")
                print(f"Duration: {duration}")
                print(f"Total turns: {len([m for m in messages if m['role'] == 'user' and isinstance(m['content'], str)])}")
                break

            if user_input.lower() == 'reset':
                messages = []
                session_start = datetime.now()
                print("🔄 Conversation reset. Starting fresh.")
                continue

            if user_input.lower() == 'history':
                show_conversation_history(messages)
                continue

            print("\nClaude: ", end="", flush=True)
            response = process_turn(
                messages,
                user_input,
                system_prompt
            )
            print(response)
            print("\n" + "-"*40)

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n⚠️ Error: {e}")
            print("Retrying...")

if __name__ == "__main__":
    main()