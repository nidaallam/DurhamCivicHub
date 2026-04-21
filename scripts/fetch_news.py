"""
fetch_news.py
Pulls stories from Durham County RSS feeds and writes news.json.
Runs daily via GitHub Actions.
"""

import json
import feedparser
import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, date

# ── RSS feeds to pull from ────────────────────────────────────────────────────
FEEDS = [
    {
        "url": "https://www.dconc.gov/Home/ShowRss",
        "source": "Durham County",
        "default_tag": "County"
    },
    {
        "url": "https://www.durhamnc.gov/RSSFeed.aspx?ModID=56&CID=All-0",
        "source": "City of Durham",
        "default_tag": "City"
    },
    {
        "url": "https://www.dpsnc.net/site/handlers/rss.ashx?DSID=2",
        "source": "Durham Public Schools",
        "default_tag": "Schools"
    },
]

# ── Tag keywords ──────────────────────────────────────────────────────────────
TAG_RULES = [
    ("Budget",       ["budget", "fy20", "fiscal year", "tax rate", "appropriation"]),
    ("Housing",      ["housing", "affordable housing", "bond", "hud", "dhic"]),
    ("Schools",      ["school", "dps", "durham public schools", "education", "superintendent"]),
    ("Health",       ["health", "clinic", "vaccine", "mental health", "dhhs"]),
    ("Transit",      ["transit", "bus", "gotriangle", "brt", "transportation", "rail"]),
    ("Development",  ["rezoning", "zoning", "development", "planning commission", "land use"]),
    ("Parks",        ["park", "greenway", "recreation", "trail"]),
    ("Announcement", ["apply", "application", "deadline", "seeking", "vacancy"]),
]

MAX_STORIES = 15
CUTOFF_DAYS = 30  # ignore stories older than this many days

HEADERS = {
    "User-Agent": (
        "DurhamCivicHub/1.0 (https://nidaallam.github.io/BullCity/; "
        "public civic info aggregator)"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
}


def fetch_og_image(url: str) -> str | None:
    """Try to retrieve the og:image from an article page. Returns None on failure."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for prop in ("og:image", "twitter:image", "og:image:secure_url"):
            tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            if tag and tag.get("content", "").startswith("http"):
                return tag["content"].strip()
    except Exception:
        pass
    return None


def guess_tag(title: str, summary: str) -> str:
    text = (title + " " + summary).lower()
    for tag, keywords in TAG_RULES:
        if any(kw in text for kw in keywords):
            return tag
    return "County"


def strip_html(raw: str) -> str:
    return re.sub(r"<[^>]+>", "", raw or "").strip()


def parse_entry_date(entry) -> date | None:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            return date(*t[:3])
    return None


def fetch_all() -> list[dict]:
    stories = []
    today = date.today()

    for feed_cfg in FEEDS:
        try:
            feed = feedparser.parse(feed_cfg["url"])
        except Exception as e:
            print(f"  Failed to fetch {feed_cfg['url']}: {e}")
            continue

        for entry in feed.entries:
            pub = parse_entry_date(entry)
            if pub is None:
                continue
            if (today - pub).days > CUTOFF_DAYS:
                continue

            title   = strip_html(getattr(entry, "title",   "")).strip()
            excerpt = strip_html(getattr(entry, "summary", "")).strip()
            link    = getattr(entry, "link", "")

            if not title or not link:
                continue

            # Trim overly long excerpts
            if len(excerpt) > 280:
                excerpt = excerpt[:277].rsplit(" ", 1)[0] + "…"

            tag = guess_tag(title, excerpt)

            stories.append({
                "title":       title,
                "excerpt":     excerpt,
                "link":        link,
                "source":      feed_cfg["source"],
                "date":        pub.strftime("%Y-%m-%d"),
                "displayDate": pub.strftime("%B %-d, %Y"),
                "tag":         tag,
            })

    # Sort newest first, deduplicate by link
    seen = set()
    unique = []
    for s in sorted(stories, key=lambda x: x["date"], reverse=True):
        if s["link"] not in seen:
            seen.add(s["link"])
            unique.append(s)

    unique = unique[:MAX_STORIES]

    # Try to enrich each story with a social share image (og:image)
    print("  Fetching social share images…")
    for s in unique:
        img = fetch_og_image(s["link"])
        if img:
            s["image"] = img
            print(f"    ✓ image for: {s['title'][:60]}")
        time.sleep(0.5)  # polite rate-limiting

    return unique


def main():
    print("Fetching news feeds…")
    stories = fetch_all()
    print(f"  Found {len(stories)} stories")

    payload = {
        "updated": date.today().strftime("%Y-%m-%d"),
        "count":   len(stories),
        "stories": stories,
    }

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print("  Wrote news.json")


if __name__ == "__main__":
    main()
