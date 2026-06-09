import anthropic
import requests
import json
import os
from datetime import datetime

client = anthropic.Anthropic(
    timeout=60.0,
    max_retries=3
)
MODEL = "claude-sonnet-4-6"
TELEALERT_API = "http://localhost:5001"
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "")

def send_slack_message(message, color="#ff0000"):
    """Send formatted message to Slack"""
    if not SLACK_WEBHOOK:
        print("⚠️  No Slack webhook configured")
        print("Message that would be sent:")
        print(message)
        return False

    payload = {
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": message
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"🤖 TeleAlert AI Bot | "
                                        f"Bounteous × Telecom & Media | "
                                        f"{datetime.now().strftime('%H:%M:%S')}"
                            }
                        ]
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(
            SLACK_WEBHOOK,
            json=payload,
            timeout=10
        )
        if response.status_code == 200:
            print("✅ Slack notification sent!")
            return True
        else:
            print(f"❌ Slack error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Slack error: {e}")
        return False

def get_metrics():
    """Fetch TeleAlert metrics"""
    try:
        status = requests.get(
            f"{TELEALERT_API}/status"
        ).json()
        alerts = requests.get(
            f"{TELEALERT_API}/alerts"
        ).json()
        return status, alerts
    except Exception as e:
        return None, None

def diagnose_with_claude(status, alerts):
    """Get Claude's diagnosis"""
    prompt = f"""You are a NOC engineer at Bounteous.
Analyze this TeleAlert data and write a SHORT Slack alert message.

Data:
{json.dumps(status, indent=2)}

Recent alerts:
{json.dumps(alerts, indent=2)}

Write a Slack message with:
- 🚨 Severity level
- What happened in 1 sentence
- Affected nodes
- Recommended immediate action
- Use Slack markdown (*bold*, _italic_)

Keep it under 150 words. Be direct."""

    message = client.messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": prompt
        }]
    )
    return message.content[0].text

def determine_color(critical_count, total_count):
    """Determine alert color based on severity"""
    if total_count == 0:
        return "#36a64f"
    ratio = critical_count / total_count
    if ratio > 0.5:
        return "#ff0000"
    elif ratio > 0.25:
        return "#ff9900"
    else:
        return "#36a64f"

def run_slack_alert():
    """Main function to send Slack alert"""
    print("🚀 TeleAlert Slack Alert System")
    print("=" * 40)
    print("📡 Fetching network data...")

    status, alerts = get_metrics()

    if not status:
        print("❌ Cannot reach TeleAlert API")
        return

    critical = status.get("stats", {}).get(
        "critical_events", 0
    )
    total = status.get("stats", {}).get(
        "total_events", 0
    )

    print(f"📊 Events: {total} total, {critical} critical")
    print("🤖 Claude is generating alert message...")

    diagnosis = diagnose_with_claude(status, alerts)

    color = determine_color(critical, total)

    print("\n📨 Sending to Slack...")
    print("-" * 40)
    print(diagnosis)
    print("-" * 40)

    send_slack_message(diagnosis, color)

def monitor_and_alert(threshold=10, interval=120):
    """Monitor continuously and alert when threshold exceeded"""
    import time
    print(f"\n🔄 Continuous monitor started")
    print(f"   Alert threshold: {threshold} critical events")
    print(f"   Check interval: {interval} seconds")
    print("   Press Ctrl+C to stop\n")

    last_critical_count = 0

    while True:
        try:
            status, alerts = get_metrics()

            if status:
                critical = status.get(
                    "stats", {}
                ).get("critical_events", 0)
                timestamp = datetime.now().strftime(
                    "%H:%M:%S"
                )

                print(
                    f"[{timestamp}] Critical events: "
                    f"{critical}"
                )

                if (critical > threshold and
                        critical != last_critical_count):
                    print(
                        f"  🚨 Threshold exceeded! "
                        f"Sending Slack alert..."
                    )
                    diagnosis = diagnose_with_claude(
                        status, alerts
                    )
                    color = determine_color(
                        critical,
                        status.get("stats", {}).get(
                            "total_events", 0
                        )
                    )
                    send_slack_message(diagnosis, color)
                    last_critical_count = critical
                else:
                    print(f"  ✅ Below threshold")

            time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n Monitor stopped.")
            break
        except Exception as e:
            print(f"  ⚠️ Error: {e}")
            import time
            time.sleep(interval)

if __name__ == "__main__":
    print("\n🔔 TeleAlert Slack Integration")
    print("=" * 40)
    print("1. Send single alert now")
    print("2. Start continuous monitor")
    print("=" * 40)

    choice = input("Choose (1/2): ").strip()

    if choice == "1":
        run_slack_alert()
    elif choice == "2":
        threshold = input(
            "Alert threshold (critical events): "
        ).strip()
        monitor_and_alert(
            threshold=int(threshold) if threshold else 10
        )
    else:
        print("Invalid choice")