#!/usr/bin/env python3
"""Telegram channel post listener — stores new posts for the digest bot (disabled)."""
import json, os, time, sys, urllib.request, urllib.parse

def load_env():
    env = {}
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env[key.strip()] = value.strip()
    except FileNotFoundError:
        pass
    return env

env = load_env()
BOT_TOKEN = env.get('BOT_TOKEN', '')
DEST_CHAT_ID = env.get('DEST_CHAT_ID', '')
SOURCE_CHANNEL_ID = env.get('SOURCE_CHANNEL_ID', '')
BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
PENDING_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pending_posts.jsonl")
LAST_OFFSET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_offset.txt")

def api_get(path, params=None):
    url = f"{BASE}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "shepel-mers-bot/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

def load_last_offset():
    try:
        with open(LAST_OFFSET_FILE) as f:
            return int(f.read().strip())
    except:
        return 0

def save_last_offset(offset):
    with open(LAST_OFFSET_FILE, "w") as f:
        f.write(str(offset))

def append_post(post):
    with open(PENDING_FILE, "a") as f:
        f.write(json.dumps(post, ensure_ascii=False) + "\n")

def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN not found in .env file")
        sys.exit(1)
    offset = load_last_offset()
    print(f"Listener started. Offset: {offset}")
    while True:
        try:
            data = api_get("getUpdates", {
                "timeout": 25,
                "allowed_updates": "channel_post",
                "offset": offset
            })
            if not data.get("ok"):
                time.sleep(5)
                continue
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                post = update.get("channel_post")
                if post and post.get("chat", {}).get("id") == int(SOURCE_CHANNEL_ID):
                    append_post(post)
                    text = post.get("text", "")[:80]
                    print(f"Got post from {post.get('chat', {}).get('title')}: {text}...")
                save_last_offset(offset)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
