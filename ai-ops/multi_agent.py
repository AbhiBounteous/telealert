import anthropic
import subprocess
import requests
import json
from datetime import datetime

client = anthropic.Anthropic(timeout=120.0)
MODEL = "claude-sonnet-4-6"
API = "http://localhost:5001"

def call_claude(role, data, agent_num):
    print(f"\n{'='*50}")
    print(f"🤖 AGENT {agent_num}: {role}")
    print(f"{'='*50}")
    msg = client.messages.create(
        model=MODEL,
        max_tokens=400,
        messages=[{"role": "user", "content": data}]
    )
    result = msg.content[0].text
    print(result)
    return result

print("📡 Gathering cluster data...")
pods = subprocess.run(
    ["kubectl", "get", "pods"],
    capture_output=True, text=True
).stdout
status = requests.get(f"{API}/status").json()
alerts = requests.get(f"{API}/alerts").json()

print("✅ Data gathered. Running 4 agents...\n")

findings = call_claude(
    "MONITOR",
    f"""Analyze this cluster data and report
findings in 3 bullet points:
Pods: {pods}
Metrics: {json.dumps(status)}""",
    1
)

diagnosis = call_claude(
    "DIAGNOSIS",
    f"""Based on these findings:
{findings}

Give root cause in 2 sentences.
Confidence percentage.
One recommended fix.""",
    2
)

remediation = call_claude(
    "REMEDIATION",
    f"""Based on diagnosis:
{diagnosis}

What kubectl command would fix this?
Write the exact command.
Expected outcome.""",
    3
)

report = call_claude(
    "REPORTING",
    f"""Create a 5-line incident report:
Monitor: {findings[:200]}
Diagnosis: {diagnosis[:200]}
Fix: {remediation[:200]}
Time: {datetime.now().isoformat()}
Format: professional NOC report""",
    4
)

with open("/tmp/multi_agent_report.txt", "w") as f:
    f.write(f"MULTI-AGENT REPORT\n{datetime.now()}\n\n")
    f.write(f"MONITOR:\n{findings}\n\n")
    f.write(f"DIAGNOSIS:\n{diagnosis}\n\n")
    f.write(f"REMEDIATION:\n{remediation}\n\n")
    f.write(f"REPORT:\n{report}\n")

print("\n✅ PIPELINE COMPLETE")
print("💾 Saved to /tmp/multi_agent_report.txt")