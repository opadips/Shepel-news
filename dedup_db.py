#!/usr/bin/env python3
"""SQLite-based duplicate story detection for the news digest bot."""
import sqlite3
import os
import json
import sys
import time
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "posted_topics.db")
ARCHIVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "archives")

def init_db():
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posted_topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_key TEXT NOT NULL,
            headline TEXT NOT NULL,
            sources TEXT,
            posted_at REAL NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_posted_at ON posted_topics(posted_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_topic_key ON posted_topics(topic_key)")
    conn.commit()
    return conn

def get_recent_topics(days=3):
    conn = init_db()
    cutoff = time.time() - (days * 86400)
    cursor = conn.execute(
        "SELECT id, topic_key, headline, sources, posted_at FROM posted_topics WHERE posted_at > ? ORDER BY posted_at DESC",
        (cutoff,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "topic_key": r[1], "headline": r[2], "sources": r[3], "posted_at": r[4]}
        for r in rows
    ]

def insert_topic(topic_key, headline, sources):
    conn = init_db()
    if isinstance(sources, list):
        sources = ",".join(sources)
    # Check for duplicate within the last 7 days — reject if same topic_key exists
    cutoff = time.time() - (7 * 86400)
    existing = conn.execute(
        "SELECT id, topic_key, headline, posted_at FROM posted_topics WHERE topic_key = ? AND posted_at > ?",
        (topic_key, cutoff)
    ).fetchall()
    if existing:
        conn.close()
        return False, f"Duplicate rejected: topic_key '{topic_key}' already exists (id {existing[0][0]}, posted {datetime.fromtimestamp(existing[0][3])})"
    conn.execute(
        "INSERT INTO posted_topics (topic_key, headline, sources, posted_at) VALUES (?, ?, ?, ?)",
        (topic_key, headline, sources, time.time())
    )
    conn.commit()
    conn.close()
    return True, f"Inserted: {topic_key}"

def prune_old(days=14):
    conn = init_db()
    cutoff = time.time() - (days * 86400)
    cursor = conn.execute(
        "SELECT topic_key, headline, sources, posted_at FROM posted_topics WHERE posted_at < ?",
        (cutoff,)
    )
    rows = cursor.fetchall()
    if not rows:
        conn.close()
        return 0
    now = datetime.now()
    archive_file = os.path.join(ARCHIVE_DIR, f"archive_{now.strftime('%Y-%m')}.jsonl")
    with open(archive_file, "a") as f:
        for row in rows:
            entry = {"topic_key": row[0], "headline": row[1], "sources": row[2], "posted_at": row[3], "archived_at": time.time()}
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    conn.execute("DELETE FROM posted_topics WHERE posted_at < ?", (cutoff,))
    conn.commit()
    conn.close()
    return len(rows)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: dedup_db.py [recent|insert|prune]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "recent":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        topics = get_recent_topics(days)
        print(json.dumps(topics, ensure_ascii=False, indent=2))
    
    elif cmd == "insert":
        if len(sys.argv) < 4:
            print("Usage: dedup_db.py insert <topic_key> <headline> <sources>")
            sys.exit(1)
        topic_key = sys.argv[2]
        headline = sys.argv[3]
        sources = sys.argv[4] if len(sys.argv) > 4 else ""
        success, message = insert_topic(topic_key, headline, sources)
        print(message)
        if not success:
            sys.exit(1)
    
    elif cmd == "prune":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 14
        pruned = prune_old(days)
        print(f"Pruned {pruned} rows")
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
