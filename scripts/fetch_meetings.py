#!/usr/bin/env python3
from __future__ import annotations
"""
fetch_meetings.py — Durham Civic Hub
Auto-updates meetings.json with fresh meeting data from government sources.

Strategies per body:
  - DPS Board of Education  → BoardDocs JSON API (most reliable)
  - BOCC / City Council     → CivicPlus Agenda Center HTML scraping
  - Planning / BOA          → CivicPlus archive page scraping
  - Mental Health / Housing → Archive page scraping + status refresh

If a source fails, the script keeps existing data for that body and
just refreshes past-meeting statuses based on today's date.

Run by GitHub Actions daily alongside fetch_news.py.
"""

import json
import re
import time
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────────────────
TODAY        = date.today()
TIMEOUT      = 20
KEEP_DAYS    = 180   # drop meetings older than ~6 months
MAX_PER_BODY = 10    # max meetings to keep per body

HEADERS = {
    "User-Agent": (
        "DurhamCivicHub/1.0 (https://nidaallam.github.io/BullCity/; "
        "public civic info aggregator)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.9",
}

OUT_PATH = Path(__file__).parent.parent / "meetings.json"

# ── Helpers ───────────────────────────────────────────────────────────────

def load_existing() -> dict:
    if OUT_PATH.exists():
        return json.loads(OUT_PATH.read_text())
    return {"updated": str(TODAY), "bodies": []}


def safe_get(url: str, **kwargs) -> requests.Response | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, **kwargs)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"      ⚠ GET {url}: {e}")
        return None


def safe_post(url: str, **kwargs) -> requests.Response | None:
    try:
        r = requests.post(url, headers=HEADERS, timeout=TIMEOUT, **kwargs)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"      ⚠ POST {url}: {e}")
        return None


def parse_date(text: str) -> date | None:
    """Parse a date string in several common formats."""
    text = text.strip().rstrip(",").strip()
    # Remove day-of-week prefixes
    text = re.sub(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*",
                  "", text, flags=re.I).strip()

    for fmt in (
        "%B %d, %Y", "%B %d %Y",
        "%b %d, %Y",  "%b %d %Y",
        "%Y-%m-%d",
        "%m/%d/%Y",   "%m/%d/%y",
        "%d %B %Y",   "%d %b %Y",
    ):
        try:
            return date(*time.strptime(text, fmt)[:3])
        except ValueError:
            pass

    # Regex fallback
    m = re.search(
        r"(January|February|March|April|May|June|July|August|"
        r"September|October|November|December|"
        r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"\.?\s+(\d{1,2}),?\s+(\d{4})",
        text, re.I
    )
    if m:
        for fmt in ("%B %d %Y", "%b %d %Y"):
            try:
                return date(*time.strptime(
                    f"{m.group(1)} {m.group(2)} {m.group(3)}", fmt
                )[:3])
            except ValueError:
                pass
    return None


def status_for(d: date) -> str:
    return "upcoming" if d >= TODAY else "minutes"


def iso(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def absolute_url(href: str, base: str) -> str:
    href = href.strip()
    if href.startswith("http"):
        return href
    from urllib.parse import urljoin
    return urljoin(base, href)


def is_doc_link(label: str) -> bool:
    kw = ("agenda", "minutes", "video", "watch", "stream", "recording", "packet")
    return any(k in label.lower() for k in kw)


def mark_primary(links: list[dict]) -> None:
    for priority in ("agenda", "minutes", "video", "watch"):
        for lnk in links:
            if priority in lnk["label"].lower():
                lnk["primary"] = True
                return
    if links:
        links[0]["primary"] = True


# ── Generic CivicPlus scraper ─────────────────────────────────────────────

def scrape_civicplus(page_url: str, archive_url: str,
                     default_type: str = "Regular Meeting",
                     extra_links: list[dict] | None = None) -> list[dict] | None:
    r = safe_get(page_url)
    if not r:
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    found: dict[str, dict] = {}

    # Strategy A: table rows
    for row in soup.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if not cells:
            continue
        d = None
        for cell in cells[:3]:
            d = parse_date(cell.get_text(" ", strip=True))
            if d and 2025 <= d.year <= 2028:
                break
        if not d or not (2025 <= d.year <= 2028):
            continue

        key = iso(d)
        links = []
        for a in row.find_all("a", href=True):
            label = a.get_text(strip=True) or "Details"
            href  = absolute_url(a["href"], page_url)
            if is_doc_link(label):
                links.append({"label": label, "url": href, "primary": False})

        if key not in found:
            found[key] = {
                "date":   key,
                "type":   default_type,
                "status": status_for(d),
                "links":  links or [{"label": "Archive", "url": archive_url, "primary": True}],
            }
        else:
            existing_urls = {l["url"] for l in found[key]["links"]}
            for lnk in links:
                if lnk["url"] not in existing_urls:
                    found[key]["links"].append(lnk)

    # Strategy B: inline date strings
    date_re = re.compile(
        r"\b(January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{1,2},?\s+20(?:2[5-9]|3\d)\b",
        re.I
    )
    for node in soup.find_all(string=date_re):
        text = node.strip()
        d = parse_date(text)
        if not d or not (2025 <= d.year <= 2028):
            continue
        key = iso(d)
        if key in found:
            continue

        container = node.parent
        for _ in range(3):
            if container is None:
                break
            if container.find_all("a", href=True):
                break
            container = container.parent

        links = []
        if container:
            for a in container.find_all("a", href=True):
                label = a.get_text(strip=True) or "Details"
                href  = absolute_url(a["href"], page_url)
                if is_doc_link(label) or not links:
                    links.append({"label": label, "url": href, "primary": False})

        found[key] = {
            "date":   key,
            "type":   default_type,
            "status": status_for(d),
            "links":  links or [{"label": "Archive", "url": archive_url, "primary": True}],
        }

    if not found:
        return None

    for entry in found.values():
        mark_primary(entry["links"])
        if extra_links:
            existing_urls = {l["url"] for l in entry["links"]}
            for lnk in extra_links:
                if lnk["url"] not in existing_urls:
                    entry["links"].append(dict(lnk))

    result = sorted(found.values(), key=lambda x: x["date"], reverse=True)
    return result[:MAX_PER_BODY]


# ── BoardDocs API — DPS ───────────────────────────────────────────────────

def fetch_dps_boarddocs() -> list[dict] | None:
    api_url   = "https://go.boarddocs.com/nc/dpsnc/Board.nsf/BD-getMeetings"
    base_url  = "https://go.boarddocs.com/nc/dpsnc/Board.nsf"
    board_url = "https://www.dpsnc.net/page/board-of-education"

    r = safe_post(
        api_url,
        data="open",
        headers={**HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
    )
    if r and r.status_code == 200:
        try:
            items = r.json()
            meetings = []
            for item in items:
                try:
                    d = date(int(item["year"]), int(item["month"]), int(item["day"]))
                except (KeyError, ValueError, TypeError):
                    continue
                if not (2025 <= d.year <= 2028):
                    continue
                uid   = item.get("unique_key", "")
                label = item.get("name", "Regular Meeting").strip() or "Regular Meeting"
                doc_url = f"{base_url}/Public?open&id={uid}" if uid else board_url
                stat  = status_for(d)
                meetings.append({
                    "date":   iso(d),
                    "type":   label,
                    "status": stat,
                    "links":  [
                        {"label": "Agenda" if stat == "upcoming" else "Minutes",
                         "url": doc_url, "primary": True},
                        {"label": "Watch Online", "url": "https://www.dpsnc.net"},
                    ],
                })
            if meetings:
                meetings.sort(key=lambda x: x["date"], reverse=True)
                print(f"      → BoardDocs API: {len(meetings)} meetings")
                return meetings[:MAX_PER_BODY]
        except Exception as e:
            print(f"      ⚠ BoardDocs JSON parse error: {e}")

    print("      → BoardDocs API failed, falling back to scrape…")
    return scrape_civicplus(board_url, board_url, "Regular Meeting")


# ── Per-body fetch functions ──────────────────────────────────────────────

def fetch_commissioners() -> list[dict] | None:
    archive = "https://www.dconc.gov/Board-of-Commissioners/Meetings-and-Announcements/BOCC-Agendas-and-Video-Library"
    return scrape_civicplus(archive, archive, extra_links=[
        {"label": "Live Stream",    "url": "https://www.youtube.com/user/DCoWebmaster/videos",    "primary": False},
        {"label": "Public Comment", "url": "https://www.dconc.gov/Board-of-Commissioners/Meetings-and-Announcements/Rules-for-Citizens-and-Public-Comment", "primary": False},
    ])


def fetch_city_council() -> list[dict] | None:
    archive  = "https://www.durhamnc.gov/1323/City-Council"
    legistar = "https://durham.legistar.com/Calendar.aspx"
    result = scrape_civicplus(legistar, archive, extra_links=[
        {"label": "Live Stream",    "url": "https://www.youtube.com/user/CityofDurhamNC", "primary": False},
        {"label": "Public Comment", "url": archive, "primary": False},
    ])
    if result:
        return result
    return scrape_civicplus(archive, archive, extra_links=[
        {"label": "Live Stream", "url": "https://www.youtube.com/user/CityofDurhamNC", "primary": False},
    ])


def fetch_dps() -> list[dict] | None:
    return fetch_dps_boarddocs()


def fetch_planning() -> list[dict] | None:
    archive = "https://www.durhamnc.gov/1367/Planning-Commission"
    return scrape_civicplus(archive, archive)


def fetch_board_of_adjustment() -> list[dict] | None:
    archive = "https://www.durhamnc.gov/1372/Board-of-Adjustment-BOA"
    return scrape_civicplus(archive, archive)


def fetch_mental_health() -> list[dict] | None:
    archive = "https://www.dconc.gov/county-departments/departments-a-e/board-of-commissioners/boards-and-commissions"
    return scrape_civicplus(archive, archive)


def fetch_housing_authority() -> list[dict] | None:
    archive = "https://www.durhamhousingauthority.org"
    return scrape_civicplus(archive, archive)


# ── Merge & refresh logic ─────────────────────────────────────────────────

def refresh_statuses(meetings: list[dict]) -> list[dict]:
    cutoff_ord = TODAY.toordinal() - KEEP_DAYS
    result = []
    for m in meetings:
        try:
            d = date.fromisoformat(m["date"])
        except (ValueError, KeyError):
            continue
        if d.toordinal() < cutoff_ord:
            continue
        m["status"] = status_for(d)
        result.append(m)
    return sorted(result, key=lambda x: x["date"], reverse=True)


def merge(existing: list[dict], fresh: list[dict] | None) -> list[dict]:
    if fresh is None:
        return refresh_statuses(existing)
    by_date: dict[str, dict] = {}
    for m in existing:
        by_date[m.get("date", "")] = m
    for m in fresh:
        by_date[m.get("date", "")] = m   # fresh wins
    return refresh_statuses(list(by_date.values()))


# ── Dispatcher ────────────────────────────────────────────────────────────

FETCHERS = {
    "commissioners":       fetch_commissioners,
    "city-council":        fetch_city_council,
    "dps":                 fetch_dps,
    "planning":            fetch_planning,
    "board-of-adjustment": fetch_board_of_adjustment,
    "mental-health":       fetch_mental_health,
    "housing-authority":   fetch_housing_authority,
}

# ── Main ──────────────────────────────────────────────────────────────────

ICS_PATH = Path(__file__).parent.parent / "meetings.ics"


def fmt_ics_dt(date_str: str, time_str: str = "18:00") -> str:
    """Return a DTSTART/DTEND value like 20260422T180000."""
    try:
        d = date.fromisoformat(date_str)
        h, m = (int(x) for x in time_str.split(":"))
        return f"{d.strftime('%Y%m%d')}T{h:02d}{m:02d}00"
    except Exception:
        return ""


def write_ics(data: dict) -> None:
    """Generate a static meetings.ics from the updated meetings.json."""
    vevents: list[str] = []
    for body in data.get("bodies", []):
        body_name = body.get("name", "Durham Meeting")
        for m in body.get("meetings", []):
            if m.get("status") != "upcoming":
                continue
            dt_start = fmt_ics_dt(m["date"], m.get("time", "18:00"))
            dt_end   = fmt_ics_dt(m["date"], m.get("timeEnd", "19:30"))
            if not dt_start:
                continue

            # Primary link or first link as URL
            url = ""
            for lnk in m.get("links", []):
                if lnk.get("primary"):
                    url = lnk.get("url", "")
                    break
            if not url and m.get("links"):
                url = m["links"][0].get("url", "")

            summary = f"{body_name}: {m.get('type', 'Meeting')}"
            location = m.get("location", "Durham, NC")

            lines = [
                "BEGIN:VEVENT",
                f"UID:{m['date']}-{body.get('id','mtg')}@durhamcivichub",
                f"DTSTART;TZID=America/New_York:{dt_start}",
                f"DTEND;TZID=America/New_York:{dt_end}",
                f"SUMMARY:{summary}",
                f"LOCATION:{location}",
            ]
            if url:
                lines.append(f"URL:{url}")
            lines.append("END:VEVENT")
            vevents.append("\r\n".join(lines))

    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Durham Civic Hub//Durham Meetings//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Durham Civic Hub Meetings",
        "X-WR-TIMEZONE:America/New_York",
    ] + vevents + ["END:VCALENDAR"]

    ICS_PATH.write_text("\r\n".join(ics_lines), encoding="utf-8")
    print(f"✓ Wrote {ICS_PATH} ({len(vevents)} upcoming events)")


def main():
    print("Updating meetings.json…")
    data = load_existing()

    for body in data.get("bodies", []):
        body_id = body.get("id", "")
        name    = body.get("name", body_id)
        fetcher = FETCHERS.get(body_id)

        if not fetcher:
            print(f"  '{body_id}': no fetcher, refreshing statuses only")
            body["meetings"] = refresh_statuses(body.get("meetings", []))
            continue

        print(f"  {name}…")
        try:
            fresh = fetcher()
            print(f"      → {len(fresh) if fresh else 0} meetings retrieved")
        except Exception as e:
            print(f"      ⚠ Uncaught error: {e}")
            fresh = None

        body["meetings"] = merge(body.get("meetings", []), fresh)
        time.sleep(1.5)  # be polite to government servers

    data["updated"] = str(TODAY)
    OUT_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"✓ Wrote {OUT_PATH}")

    write_ics(data)


if __name__ == "__main__":
    main()
