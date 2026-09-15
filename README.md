# AI News Digest Bot — shepel-mers

A Persian-language AI news digest bot that monitors the `shepel_news` Telegram channel for AI/tech news, fetches and analyzes relevant articles, and posts formatted digests to the `Shepel-akhbar` channel via the Telegram Bot Bot API.

## Architecture

```
shepel_news (Telegram channel)
    │
    ▼
scraper.py ──► pending_posts.jsonl ──► Hermes Cron Agent ──► sendRichMessage ──► Shepel-akhbar
    │                                         │
    └── seen_posts.json (dedup)               └── web_extract → filter → Persian analysis
```

## Files

| File | Purpose |
|------|---------|
| `scraper.py` | Web scraper — polls `t.me/s/shepel_news` every 60s, writes new posts to `pending_posts.jsonl` |
| `listener.py` | Bot API listener (disabled — replaced by scraper) |
| `pending_posts.jsonl` | Queue of posts waiting to be processed |
| `seen_posts.json` | Deduplication set — IDs of already-processed posts |
| `last_run.txt` | Summary of most recent cron run |

## Cron Job

The Hermes agent runs every 10 minutes, reads `pending_posts.jsonl`, fetches articles via `web_extract`, filters for real news events, writes original Persian analysis, and sends via `sendRichMessage` (Bot API 10.1+) with rich HTML formatting and RTL support.

## Rules

- **Persian output** — All text in Persian except proper nouns (company/product names)
- **Real filtering** — Discards Show HN, Ask HN, opinions, UI noise, duplicates
- **Rich HTML** — Uses `<details>`, `<summary>`, `<p dir="rtl">`, `<hr/>`, `<footer>`
- **Nested collapsible** — Outer "جزئیات" section wraps all numbered analysis items

## Systemd Services

- `shepel-mers-scraper.service` — Runs `scraper.py` continuously (enabled)
- `shepel-mers-listener.service` — Bot listener (disabled)

## License

MIT
