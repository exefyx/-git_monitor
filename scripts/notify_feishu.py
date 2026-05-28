import os
import json
import requests
from datetime import datetime

webhook = os.getenv("FEISHU_WEBHOOK")

if not webhook:
    print("No FEISHU_WEBHOOK found, skip Feishu notification.")
    exit(0)

dashboard_url = "https://exefyx.github.io/-git_monitor/"

text = f"""竞品监控日报已更新

时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

查看 Dashboard：
{dashboard_url}
"""

payload = {
    "msg_type": "text",
    "content": {
        "text": text
    }
}

response = requests.post(
    webhook,
    headers={"Content-Type": "application/json"},
    data=json.dumps(payload),
    timeout=15
)

print(response.status_code)
print(response.text)

if response.status_code != 200:
    raise SystemExit("Feishu notification failed")