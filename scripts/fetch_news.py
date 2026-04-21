"""
fetch_news.py
Pulls stories from Durham County RSS feeds and writes news.json.
Runs daily via GitHub Actions.
"""

from __future__ import annotations

import json
import feedparser
import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, date
from typing import Optional

# ── RSS feeds to pull from ────────────────────────────────────────────────────
# durham_only=True  → accept every story (it's a Durham-specific feed)
# durham_only=False → filter stories to Durham-relevant ones only
FEEDS = [
    # ── Official government feeds (Durham-specific) ──
    {
        "url":          "https://www.dconc.gov/Home/ShowRss",
        "source":       "Durham County",
        "default_tag":  "County",
        "durham_only":  True,
    },
    {
        "url":          "https://www.durhamnc.gov/RSSFeed.aspx?ModID=56&CID=All-0",
        "source":       "City of Durham",
        "default_tag":  "City",
        "durham_only":  True,
    },
    {
        "url":          "https://www.dpsnc.net/site/handlers/rss.ashx?DSID=2",
        "source":       "Durham Public Schools",
        "default_tag":  "Schools",
        "durham_only":  True,
    },
    # ── Local news outlets (Triangle-wide → filter for Durham) ──
    {
        "url":          "http://www.wral.com/news/rss/142/",
        "source":       "WRAL News",
        "default_tag":  "Local News",
        "durham_only":  False,
    },
    {
        "url":          "https://indyweek.com/feed/",
        "source":       "Indy Week",
        "default_tag":  "Local News",
        "durham_only":  False,
    },
    {
        "url":          "https://abc11.com/feed/",
        "source":       "ABC11 / WTVD",
        "default_tag":  "Local News",
        "durham_only":  False,
    },
    {
        "url":          "https://ncnewsline.com/feed/",
        "source":       "NC Newsline",
        "default_tag":  "Policy",
        "durham_only":  False,
    },
]

# Keywords that make a story Durham-relevant (for triangle-wide feeds)
DURHAM_KEYWORDS = [
    "durham", "bull city", "dconc", "dpsnc", "gotriangle",
    "duke university", "north carolina central", "nccu",
    "ellerbe creek", "west point on the eno", "american tobacco",
]

# ── Tag keywords ──────────────────────────────────────────────────────────────
TAG_RULES = [
    ("Budget",       ["budget", "fy20", "fiscal year", "tax rate", "appropriation", "spending"]),
    ("Housing",      ["housing", "affordable housing", "bond", "hud", "dhic", "eviction", "rent"]),
    ("Schools",      ["school", "dps", "durham public schools", "education", "superintendent", "classroom"]),
    ("Health",       ["health", "clinic", "vaccine", "mental health", "dhhs", "hospital", "medicaid"]),
    ("Transit",      ["transit", "bus", "gotriangle", "brt", "transportation", "rail", "light rail"]),
    ("Development",  ["rezoning", "zoning", "development", "planning commission", "land use", "construction"]),
    ("Parks",        ["park", "greenway", "recreation", "trail", "eno river"]),
    ("Public Safety",["police", "sheriff", "fire", "crime", "jail", "911", "emergency"]),
    ("Environment",  ["climate", "environment", "water", "stormwater", "flood", "solar", "emissions"]),
    ("Announcement", ["apply", "application", "deadline", "seeking", "vacancy", "hiring", "grant"]),
]

MAX_STORIES  = 25   # more sources → more stories
CUTOFF_DAYS  = 45   # keep up to 45 days

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


def is_durham_relevant(title: str, excerpt: str) -> bool:
    """Return True if any Durham keyword appears in title or excerpt."""
    text = (title + " " + excerpt).lower()
    return any(kw in text for kw in DURHAM_KEYWORDS)


def fetch_all() -> list[dict]:
    stories = []
    today = date.today()

    for feed_cfg in FEEDS:
        print(f"  Fetching: {feed_cfg['source']} …")
        try:
            feed = feedparser.parse(feed_cfg["url"])
        except Exception as e:
            print(f"    Failed: {e}")
            continue

        count_added = 0
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

            # For triangle-wide feeds, skip stories not about Durham
            if not feed_cfg.get("durham_only") and not is_durham_relevant(title, excerpt):
                continue

            # Trim overly long excerpts
            if len(excerpt) > 300:
                excerpt = excerpt[:297].rsplit(" ", 1)[0] + "…"

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
            count_added += 1
        print(f"    → {count_added} Durham stories")

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


def load_existing_news() -> dict:
    import os
    path = "news.json"
    if os.path.exists(path):
        try:
            return json.loads(open(path).read())
        except Exception:
            pass
    return {"updated": "", "count": 0, "stories": []}


def main():
    print("Fetching news feeds…")
    existing = load_existing_news()
    fresh = fetch_all()
    print(f"  Found {len(fresh)} fresh stories")

    if not fresh:
        # Keep existing stories — just refresh og:images on any that are missing them
        print("  No fresh stories from feeds — keeping existing news.json unchanged")
        stories = existing.get("stories", [])
        enriched = False
        for s in stories:
            if not s.get("image"):
                img = fetch_og_image(s["link"])
                if img:
                    s["image"] = img
                    print(f"    ✓ image: {s['title'][:60]}")
                    enriched = True
                time.sleep(0.5)
        if not enriched:
            print("  Nothing to update.")
            return
        payload = {
            "updated": existing.get("updated", date.today().strftime("%Y-%m-%d")),
            "count":   len(stories),
            "stories": stories,
        }
    else:
        # Merge: fresh stories win; keep any existing stories not replaced
        by_link = {s["link"]: s for s in existing.get("stories", [])}
        for s in fresh:
            by_link[s["link"]] = s
        stories = sorted(by_link.values(), key=lambda x: x["date"], reverse=True)[:MAX_STORIES]
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
