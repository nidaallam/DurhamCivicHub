"""
fetch_news.py
Pulls stories from Durham County RSS feeds and writes news.json.
Runs daily via GitHub Actions.

Guardrails (Part 5.3):
- Auto-merge if fewer than 10 items changed from previous run
- Hold for approval if 10+ items changed (never blocks silently)
- Block and warn if all items disappeared (likely scraper failure)

"What this means for you" lines are generated via Claude API and cached
per story URL so repeat runs don't re-call the API.
"""

from __future__ import annotations

import json
import os
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

MAX_STORIES      = 25    # more sources → more stories
CUTOFF_DAYS      = 45    # keep up to 45 days
GUARDRAIL_HOLD   = 10    # hold for approval if >= this many items changed
ANTHROPIC_MODEL  = "claude-haiku-4-5-20251001"  # cheapest model for one-sentence summaries

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


def generate_meaning(story: dict, api_key: str | None) -> str | None:
    """Call Claude API to produce a one-sentence 'what this means for you' line."""
    if not api_key:
        return None
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": ANTHROPIC_MODEL,
                "max_tokens": 80,
                "messages": [{
                    "role": "user",
                    "content": (
                        f"Headline: {story['title']}\n"
                        f"Summary: {story.get('excerpt', '')}\n\n"
                        "Write one sentence (15-25 words) starting with 'This means' that explains "
                        "what this news story means for Durham County neighbors in plain, warm language. "
                        "No em dashes. No jargon."
                    ),
                }],
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"].strip()
    except Exception as e:
        print(f"    Claude API error: {e}")
        return None


def enrich_with_meanings(stories: list[dict], existing_by_link: dict, api_key: str | None) -> None:
    """Add 'meaning' field to stories that don't already have one."""
    if not api_key:
        return
    for s in stories:
        existing = existing_by_link.get(s["link"], {})
        if existing.get("meaning"):
            s["meaning"] = existing["meaning"]
            continue
        meaning = generate_meaning(s, api_key)
        if meaning:
            s["meaning"] = meaning
            print(f"    Meaning generated: {s['title'][:50]}")
        time.sleep(0.3)


def count_changed(fresh: list[dict], existing: list[dict]) -> int:
    """Count how many stories in fresh are not already in existing (by link)."""
    existing_links = {s["link"] for s in existing}
    return sum(1 for s in fresh if s["link"] not in existing_links)


def load_existing_news() -> dict:
    import os
    path = "data/news.json"
    if os.path.exists(path):
        try:
            return json.loads(open(path).read())
        except Exception:
            pass
    return {"updated": "", "count": 0, "stories": []}


def main():
    import sys
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    print("Fetching news feeds…")
    existing     = load_existing_news()
    existing_stories = existing.get("stories", [])
    existing_by_link = {s["link"]: s for s in existing_stories}
    fresh        = fetch_all()
    print(f"  Found {len(fresh)} fresh stories")

    # ── Guardrail: block if all stories disappeared (scraper failure) ──────────
    if existing_stories and not fresh:
        print("  GUARDRAIL BLOCK: All stories disappeared - likely scraper failure.")
        print("  Keeping existing news.json unchanged.")
        sys.exit(1)

    if not fresh:
        # No existing data and no fresh: refresh og:images on any missing
        print("  No fresh stories from feeds - keeping existing news.json unchanged")
        stories  = existing_stories
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
        by_link = dict(existing_by_link)
        for s in fresh:
            by_link[s["link"]] = s
        stories = sorted(by_link.values(), key=lambda x: x["date"], reverse=True)[:MAX_STORIES]

        # ── Guardrail: hold for approval if many new stories ──────────────────
        n_changed = count_changed(fresh, existing_stories)
        if n_changed >= GUARDRAIL_HOLD:
            print(f"  GUARDRAIL HOLD: {n_changed} new stories (threshold {GUARDRAIL_HOLD}).")
            print("  Writing news.json but marking exit code 2 for workflow review.")
            # Write so content isn't lost, but signal the CI workflow to hold
            payload = {
                "updated":  date.today().strftime("%Y-%m-%d"),
                "count":    len(stories),
                "stories":  stories,
                "_guardrail": f"HOLD: {n_changed} new items - review before merge",
            }
            with open("data/news.json", "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            print("  Wrote news.json (held)")
            sys.exit(2)

        # ── Enrich with Claude "what this means for you" summaries ────────────
        enrich_with_meanings(stories, existing_by_link, api_key)

        payload = {
            "updated": date.today().strftime("%Y-%m-%d"),
            "count":   len(stories),
            "stories": stories,
        }

    with open("data/news.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print("  Wrote news.json")
    write_rss(payload.get("stories", []))


def write_rss(stories: list[dict]) -> None:
    """Generate news.xml (RSS 2.0) from stories list."""
    import xml.etree.ElementTree as ET

    def cdata(text: str) -> str:
        return f"<![CDATA[{text}]]>"

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        '  <channel>',
        '    <title>Durham Civic Hub - Local Government News</title>',
        '    <link>https://civichub.nidaallam.com/news.html</link>',
        '    <description>Local government news for Durham County, NC: budget, schools, housing, transit, public health.</description>',
        '    <language>en-us</language>',
        f'    <lastBuildDate>{date.today().strftime("%a, %d %b %Y 12:00:00 +0000")}</lastBuildDate>',
        '    <atom:link href="https://civichub.nidaallam.com/news.xml" rel="self" type="application/rss+xml" />',
    ]

    for s in stories:
        title   = (s.get("title", "") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        link    = s.get("link", "")
        excerpt = (s.get("excerpt", "") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        source  = (s.get("source", "") or "").replace("&", "&amp;")
        iso_date = s.get("date", "")
        pub_date = ""
        try:
            d = date.fromisoformat(iso_date)
            pub_date = d.strftime("%a, %d %b %Y 12:00:00 +0000")
        except Exception:
            pass

        lines += [
            "    <item>",
            f"      <title>{title}</title>",
            f"      <link>{link}</link>",
            f"      <guid isPermaLink=\"true\">{link}</guid>",
            f"      <description>{excerpt}</description>",
            f"      <source url=\"{link}\">{source}</source>",
        ]
        if pub_date:
            lines.append(f"      <pubDate>{pub_date}</pubDate>")
        lines.append("    </item>")

    lines += ["  </channel>", "</rss>"]

    with open("news.xml", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  Wrote news.xml ({len(stories)} items)")


if __name__ == "__main__":
    main()
