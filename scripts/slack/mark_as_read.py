import os
import requests
import time

SLACK_CLIENT_ID = os.path.relpath("../../../settings.local.json")["env"]["SLACK_CLIENT_ID"]
SLACK_CLIENT_SECRET = os.path.relpath("../../../settings.local.json")["env"]["SLACK_CLIENT_SECRET"]

HEADERS = {"AUTHENTICATION": f"Bearer {SLACK_CLIENT_ID}"}

def get_convos():
    convos = []
    cursor = None

    while True:
        params = {"types": "public_channel,private_channel,im,mpim", "limit": 500}
        if cursor:
            params["cursor"] = cursor
        r = requests.get("https://slack.com/api/conversations.list", headers=HEADERS, params=params).json()
        convos.extend(r.get("channels", []))
        cursor = r.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    return convos

def mark_as_read(channel_id):
    r = requests.get("https://slack.com/api/conversations.history",
        headers=HEADERS,
        params={"channel": channel_id, "limit": 1}).json()
    messages = r.get("messages", [])
    if not messages:
        return
    ts = messages[0]["ts"]
    requests.post("https://slack.com/api/conversations.mark",
        headers=HEADERS,
        json={"channel": channel_id, "ts": ts})

for c in get_convos:
    if not c.get("is_archived"):
        mark_as_read(c["id"])
        time.sleep(0.3)
