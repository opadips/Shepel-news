#!/usr/bin/env python3
"""Robust scraper that tracks processed state."""
import json, os, time, urllib.request, html as html_module, re

# Load .env file
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
CHANNEL_USERNAME = env.get('SOURCE_CHANNEL_USERNAME', 'shepel_news')
SOURCE_CHANNEL_ID = env.get('SOURCE_CHANNEL_ID', '-1004433759646')
PENDING_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pending_posts.jsonl")
SEEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seen_posts.json")

def fetch_page():
    url = f"https://t.me/s/{CHANNEL_USERNAME}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")

def extract_posts(html):
    posts = []
    ids = re.findall(r'data-post="shepel_news/(\d+)"', html)
    texts = re.findall(r'tgme_widget_message_text[^"]*"[^>]*>([\s\S]*?)</div>\s*<div class="tgme_widget_message_footer', html)
    
    for post_id, text_block in zip(ids, texts):
        urls = re.findall(r'href="(https?://[^"]*)"', text_block)
        article_urls = [u for u in urls if not any(x in u.lower() for x in ['telegram.org', 't.me/', 'twitter.com', 'x.com'])]
        
        txt = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', r'[\2](\1)', text_block)
        text = re.sub(r'<[^>]+>', ' ', txt).strip()
        text = re.sub(r'\s+', ' ', text)
        text = html_module.unescape(text)
        
        if article_urls:
            posts.append({
                "message_id": int(post_id),
                "text": text,
                "urls": article_urls[:10],
                "chat": {"id": SOURCE_CHANNEL_ID, "title": "shepel-news", "type": "channel"},
                "date": int(time.time()),
                "processed": False
            })
    return posts

def load_seen():
    try:
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    except:
        return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(sorted(list(seen))[-500:], f)

def load_pending():
    try:
        with open(PENDING_FILE) as f:
            return [json.loads(line) for line in f if line.strip()]
    except:
        return []

def save_pending(posts):
    with open(PENDING_FILE, "w") as f:
        for p in posts:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

def main():
    print(f"Scraper started for @{CHANNEL_USERNAME}", flush=True)
    seen = load_seen()
    print(f"Loaded {len(seen)} seen posts", flush=True)
    
    while True:
        try:
            html = fetch_page()
            posts = extract_posts(html)
            
            new_posts = [p for p in posts if p["message_id"] not in seen]
            
            if new_posts:
                for p in new_posts:
                    seen.add(p["message_id"])
                
                existing = load_pending()
                existing_ids = {p["message_id"] for p in existing if p.get("processed", False)}
                
                added = 0
                for p in new_posts:
                    if p["message_id"] not in existing_ids:
                        existing.append(p)
                        added += 1
                
                if added > 0:
                    save_pending(existing)
                    ids = [p["message_id"] for p in new_posts]
                    print(f"Added {added} new posts: {ids}", flush=True)
                
                save_seen(seen)
            else:
                save_seen(seen)
            
        except Exception as e:
            print(f"Scraper error: {e}", flush=True)
        
        time.sleep(60)

if __name__ == "__main__":
    main()
