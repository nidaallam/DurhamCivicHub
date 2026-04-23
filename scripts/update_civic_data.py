#!/usr/bin/env python3
"""
Update Durham Civic Hub data files daily at 7 AM ET.
Fetches: polling places, council wards, NC Senate/House districts,
         BOCC meetings (Granicus), City Council / Planning / BOA meetings
         (Durham AgendaCenter), calendar events.
"""
import json, csv, io, re, sys, html as html_module
from datetime import date, datetime, timedelta
from pathlib import Path
import urllib.request

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
MEETINGS_FILE = ROOT / "data" / "meetings.json"
CALENDAR_FILE = ROOT / "data" / "calendar.json"

def fetch(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": "Durham-Civic-Hub/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read() if binary else r.read().decode("utf-8")

def clean_text(raw):
    text = re.sub(r'<[^>]+>', ' ', raw)
    text = html_module.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()

def simplify_ring(ring, precision=4):
    seen, prev = [], None
    for c in ring:
        pt = (round(c[0], precision), round(c[1], precision))
        if pt != prev:
            seen.append(list(pt))
            prev = pt
    if seen and seen[0] != seen[-1]:
        seen.append(seen[0])
    return seen

def simplify_geom(geom):
    if geom["type"] == "Polygon":
        rings = [simplify_ring(r) for r in geom["coordinates"]]
        rings = [r for r in rings if len(r) >= 4]
        return {"type": "Polygon", "coordinates": rings} if rings else None
    elif geom["type"] == "MultiPolygon":
        polys = [[simplify_ring(r) for r in poly] for poly in geom["coordinates"]]
        polys = [[r for r in poly if len(r) >= 4] for poly in polys]
        polys = [p for p in polys if p]
        return {"type": "MultiPolygon", "coordinates": polys} if polys else None
    return geom

# ── Polling Places ─────────────────────────────────────────────────────────────
def update_polling_places():
    print("Fetching polling places from NC SBE...")
    election_dates = [
        f"{date.today().year}_03_03",
        f"{date.today().year}_11_04",
        f"{date.today().year - 1}_11_05",
        f"{date.today().year - 1}_03_05",
    ]
    raw = None
    source_url = None
    for ed in election_dates:
        fn = ed.replace('-', '')
        url = f"https://s3.amazonaws.com/dl.ncsbe.gov/ENRS/{ed}/polling_place_{fn}.csv"
        try:
            raw = fetch(url, binary=True)
            source_url = url
            print(f"  Got data from {url}")
            break
        except Exception as e:
            print(f"  Skipping {url}: {e}")

    if not raw:
        print("ERROR: Could not fetch polling places CSV")
        return

    content = raw.decode("utf-16").replace("\x00", "")
    reader = csv.DictReader(io.StringIO(content), delimiter="\t")
    places = []
    for row in reader:
        if row.get("county_name", "").strip().upper() == "DURHAM":
            places.append({
                "precinct": row.get("precinct_name", "").strip(),
                "name": row.get("polling_place_name", "").strip(),
                "address": row.get("street_address", "").strip(),
                "city": row.get("city", "").strip(),
                "zip": row.get("zip", "").strip(),
            })

    out = {"updated": str(date.today()), "source": source_url, "places": places}
    (DATA_DIR / "polling-places.json").write_text(json.dumps(out, indent=2))
    print(f"  Saved {len(places)} Durham polling places")

# ── Council Wards ──────────────────────────────────────────────────────────────
def update_council_wards():
    print("Fetching Durham council wards from ArcGIS Online...")
    url = (
        "https://services2.arcgis.com/G5vR3cOjh6g2Ed8E/ArcGIS/rest/services/"
        "Electoral/FeatureServer/3/query?where=1%3D1&outFields=Ward&f=geojson&outSR=4326"
    )
    data = json.loads(fetch(url))
    fc = {"type": "FeatureCollection", "features": []}
    for f in data.get("features", []):
        ward_str = f["properties"].get("Ward", "").replace("Ward ", "")
        geom = simplify_geom(f["geometry"])
        if geom and ward_str.isdigit():
            fc["features"].append({
                "type": "Feature",
                "properties": {"ward": int(ward_str)},
                "geometry": geom,
            })
    (DATA_DIR / "council-wards.json").write_text(json.dumps(fc, separators=(",", ":")))
    print(f"  Saved {len(fc['features'])} ward features")

# ── NC State Legislators ───────────────────────────────────────────────────────
def update_legislators():
    for label, layer, outfile in [
        ("Senate", 5, "nc-senate.json"),
        ("House",  4, "nc-house.json"),
    ]:
        print(f"Fetching NC {label} districts...")
        url = (
            f"https://services2.arcgis.com/G5vR3cOjh6g2Ed8E/ArcGIS/rest/services/"
            f"Electoral/FeatureServer/{layer}/query"
            "?where=1%3D1&outFields=DISTRICT,RepName,Party,DistrictURL&f=geojson&outSR=4326"
        )
        data = json.loads(fetch(url))
        fc = {"type": "FeatureCollection", "features": []}
        for f in data.get("features", []):
            p = f["properties"]
            geom = simplify_geom(f["geometry"])
            if geom:
                fc["features"].append({
                    "type": "Feature",
                    "properties": {
                        "district": int(p["DISTRICT"]),
                        "name": p["RepName"],
                        "party": p["Party"],
                        "url": p["DistrictURL"],
                    },
                    "geometry": geom,
                })
        (DATA_DIR / outfile).write_text(json.dumps(fc, separators=(",", ":")))
        print(f"  Saved {len(fc['features'])} {label} districts")

# ── Meetings ───────────────────────────────────────────────────────────────────

def _agenda_center_slug_to_date(slug):
    """'_MMDDYYYY-ID' → 'YYYY-MM-DD'"""
    m = re.match(r'_(\d{2})(\d{2})(\d{4})-(\d+)', slug)
    if m:
        mo, dy, yr, _ = m.groups()
        return f"{yr}-{mo}-{dy}"
    return None

def _scrape_agendacenter(category_id, limit=6):
    """Return list of {date, slug, raw_title} for a Durham AgendaCenter category."""
    html = fetch("https://www.durhamnc.gov/AgendaCenter")
    idx = html.find(f"section{category_id}")
    if idx < 0:
        return []
    section = html[idx: idx + 10000]
    results = []
    seen = set()
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>', section, re.DOTALL):
        if 'ViewFile' not in row:
            continue
        slugs = re.findall(r'ViewFile/Agenda/(_\d{8}-\d+)', row)
        if not slugs or slugs[0] in seen:
            continue
        slug = slugs[0]
        seen.add(slug)
        date_str = _agenda_center_slug_to_date(slug)
        if not date_str:
            continue
        results.append({"date": date_str, "slug": slug, "raw": clean_text(row)})
        if len(results) >= limit:
            break
    return results

def _scrape_bocc_granicus(limit=8):
    """Return list of {date, type, clip_id} for BOCC past meetings."""
    html = fetch("https://durhamcounty.granicus.com/ViewPublisher.php?view_id=2")
    pattern = r'on (\d{4}-\d{2}-\d{2}) \d+:\d+ [AP]M - ([^<"]+?)(?:\s*<|\s*").*?clip_id=(\d+)'
    results = []
    seen = set()
    for date_str, mtype, clip_id in re.findall(pattern, html, re.DOTALL):
        mtype = mtype.strip()
        if 'In Touch' in mtype or clip_id in seen:
            continue
        seen.add(clip_id)
        results.append({"date": date_str, "type": mtype, "clip_id": clip_id})
        if len(results) >= limit:
            break
    return results

def _scrape_city_council_granicus(limit=6):
    """Return list of {date, type, clip_id} for City Council past meetings."""
    html = fetch("https://durham.granicus.com/ViewPublisher.php?view_id=2")
    results = []
    seen = set()
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL):
        clips = re.findall(r'clip_id=(\d+)', row)
        if not clips or clips[0] in seen:
            continue
        clip_id = clips[0]
        seen.add(clip_id)
        name_m = re.search(r'class="listItem clipName"[^>]*>([^<]+)', row)
        date_m = re.search(r'class="listItem clipDate"[^>]*>([^<]+)', row)
        if not name_m or not date_m:
            continue
        mtype = name_m.group(1).strip()
        date_raw = re.sub(r'&[^;]+;', ' ', date_m.group(1)).strip()
        date_raw = re.sub(r'\s+', ' ', date_raw)
        try:
            dt = datetime.strptime(date_raw, '%B %d, %Y')
        except ValueError:
            continue
        results.append({"date": dt.strftime('%Y-%m-%d'), "type": mtype, "clip_id": clip_id})
        if len(results) >= limit:
            break
    return results

def _normalize_bocc_type(raw):
    raw = raw.lower()
    if 'joint' in raw:
        return 'Joint City-County Meeting'
    if 'budget retreat' in raw:
        return 'Budget Retreat'
    if 'budget work' in raw:
        return 'Budget Work Session'
    if 'budget public hearing' in raw or ('budget' in raw and 'hearing' in raw):
        return 'Budget Public Hearing'
    if 'work session' in raw:
        return 'Work Session'
    return 'Regular Meeting'

def _normalize_city_type(raw):
    raw = raw.lower()
    if 'work session' in raw:
        return 'Work Session'
    if 'special' in raw:
        return 'Special Meeting'
    return 'Regular Meeting'

def update_meetings():
    print("Updating meetings.json...")
    with open(MEETINGS_FILE) as f:
        data = json.load(f)

    today_str = date.today().isoformat()
    any_changed = False

    for body in data["bodies"]:
        bid = body.get("id", "")
        try:
            if bid == "commissioners":
                changed = _update_bocc(body, today_str)
            elif bid == "city-council":
                changed = _update_city_council(body, today_str)
            elif bid == "planning":
                changed = _update_agendacenter(body, 15, today_str)
            elif bid == "board-of-adjustment":
                changed = _update_agendacenter(body, 10, today_str)
            else:
                changed = False
        except Exception as e:
            print(f"  Warning: skipped {body['name']}: {e}")
            changed = False
        any_changed = any_changed or changed

    if any_changed:
        data["updated"] = today_str
        with open(MEETINGS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print("  Saved meetings.json")
    else:
        print("  meetings.json already current")
    return data

def _update_bocc(body, today_str):
    print("  Scraping BOCC from Granicus...")
    scraped = _scrape_bocc_granicus()
    if not scraped:
        print("  No BOCC data, skipping")
        return False

    # Preserve upcoming entries (not yet recorded)
    existing_upcoming = [m for m in body.get("meetings", []) if m["date"] > today_str]

    past = []
    for m in scraped:
        if m["date"] > today_str:
            continue
        cid = m["clip_id"]
        past.append({
            "date": m["date"],
            "type": _normalize_bocc_type(m["type"]),
            "status": "past",
            "links": [
                {
                    "label": "Agenda Packet",
                    "url": f"https://durhamcounty.granicus.com/AgendaViewer.php?view_id=2&clip_id={cid}",
                    "primary": True
                },
                {
                    "label": "Video Recording",
                    "url": f"https://durhamcounty.granicus.com/MediaPlayer.php?view_id=2&clip_id={cid}"
                }
            ]
        })
        if len(past) >= 6:
            break

    new_meetings = existing_upcoming + past
    if new_meetings == body.get("meetings"):
        return False
    body["meetings"] = new_meetings
    print(f"  BOCC: {len(existing_upcoming)} upcoming + {len(past)} past")
    return True

def _update_city_council(body, today_str):
    print("  Scraping City Council from AgendaCenter + Granicus...")
    ac = _scrape_agendacenter(4, limit=8)
    if not ac:
        print("  No City Council AgendaCenter data, skipping")
        return False

    # Build a map of date → clip_id from Granicus for video links on past meetings
    try:
        gc = _scrape_city_council_granicus()
        granicus_by_date = {m["date"]: m["clip_id"] for m in gc}
    except Exception:
        granicus_by_date = {}

    new_meetings = []
    for m in ac:
        date_str = m["date"]
        slug = m["slug"]
        mtype = _normalize_city_type(m["raw"])
        status = "upcoming" if date_str >= today_str else "past"
        packet_url = f"https://www.durhamnc.gov/AgendaCenter/ViewFile/Agenda/{slug}?packet=true"

        links = [{"label": "Agenda Packet", "url": packet_url, "primary": True}]
        if status == "past" and date_str in granicus_by_date:
            cid = granicus_by_date[date_str]
            links.append({
                "label": "Video Recording",
                "url": f"https://durham.granicus.com/MediaPlayer.php?view_id=2&clip_id={cid}"
            })
        elif status == "upcoming":
            links.append({"label": "Live Stream", "url": "https://www.youtube.com/@CityofDurhamNC"})
            links.append({"label": "Public Comment", "url": "https://www.durhamnc.gov/1338/City-Council"})

        new_meetings.append({"date": date_str, "type": mtype, "status": status, "links": links})

    if new_meetings == body.get("meetings"):
        return False
    body["meetings"] = new_meetings
    print(f"  City Council: {len(new_meetings)} meetings")
    return True

def _update_agendacenter(body, category_id, today_str):
    name = body['name']
    print(f"  Scraping {name} from AgendaCenter (cat{category_id})...")
    ac = _scrape_agendacenter(category_id, limit=4)
    if not ac:
        print(f"  No data for {name}, skipping")
        return False

    new_meetings = []
    for m in ac:
        date_str = m["date"]
        slug = m["slug"]
        status = "upcoming" if date_str >= today_str else "past"
        agenda_url = f"https://www.durhamnc.gov/AgendaCenter/ViewFile/Agenda/{slug}"
        new_meetings.append({
            "date": date_str,
            "type": "Regular Meeting",
            "status": status,
            "links": [{"label": "Agenda", "url": agenda_url, "primary": True}]
        })

    if new_meetings == body.get("meetings"):
        return False
    body["meetings"] = new_meetings
    print(f"  {name}: {len(new_meetings)} meetings")
    return True

# ── Calendar ───────────────────────────────────────────────────────────────────

_BOCC_LOCATION = "200 E. Main St., Durham, Room 2A"
_CITY_LOCATION = "101 City Hall Plaza, Durham"
_PLANNING_LOCATION = "101 City Hall Plaza, Durham, Room 3G"
_BOA_LOCATION = "101 City Hall Plaza, Durham, Room 3G"

_BOCC_TIMES = {
    "Regular Meeting":        "Monday · 7:00 PM",
    "Work Session":           "Monday · 9:00 AM",
    "Budget Work Session":    "Monday · 9:00 AM",
    "Budget Retreat":         "Thursday · 9:00 AM",
    "Joint City-County Meeting": "Monday · 9:30 AM",
    "Budget Public Hearing":  "Monday · 7:00 PM",
    "Special Session":        "TBD",
}

def update_calendar(meetings=None):
    print("Updating calendar.json...")
    with open(CALENDAR_FILE) as f:
        cal = json.load(f)
    if meetings is None:
        with open(MEETINGS_FILE) as f:
            meetings = json.load(f)

    today_str = date.today().isoformat()
    cutoff = (date.today() - timedelta(days=14)).isoformat()  # keep last 2 weeks of past

    # Split existing events: keep non-government events, rebuild government
    keep_events = []
    for ev in cal.get("events", []):
        cat = ev.get("category", "")
        if cat != "government":
            keep_events.append(ev)
        elif ev.get("date", "") >= cutoff:
            # Keep very recent past government events briefly for context
            keep_events.append(ev)

    # Build fresh government events from meetings.json
    new_gov = []
    for body in meetings["bodies"]:
        bid = body.get("id", "")
        for m in body.get("meetings", []):
            date_str = m["date"]
            if date_str < cutoff:
                continue
            mtype = m.get("type", "Regular Meeting")
            links = m.get("links", [])

            if bid == "commissioners":
                title = f"Board of Commissioners: {mtype}"
                location = _BOCC_LOCATION
                time_str = _BOCC_TIMES.get(mtype, "Monday · 7:00 PM")
            elif bid == "city-council":
                title = f"Durham City Council: {mtype}"
                location = _CITY_LOCATION
                time_str = "Monday · 7:00 PM" if mtype == "Regular Meeting" else "Monday · 9:00 AM"
            elif bid == "planning":
                title = "City-County Planning Commission"
                location = _PLANNING_LOCATION
                time_str = "Monday · 9:00 AM"
            elif bid == "board-of-adjustment":
                title = "Board of Adjustment"
                location = _BOA_LOCATION
                time_str = "Tuesday · 9:00 AM"
            else:
                continue

            new_gov.append({
                "date": date_str,
                "title": title,
                "time": time_str,
                "location": location,
                "category": "government",
                "links": links,
            })

    # Remove duplicates (keep_events may already have some of these dates)
    existing_gov_dates = {
        (ev["date"], ev.get("title", ""))
        for ev in keep_events
        if ev.get("category") == "government"
    }
    new_gov = [
        ev for ev in new_gov
        if (ev["date"], ev["title"]) not in existing_gov_dates
    ]

    all_events = keep_events + new_gov
    all_events.sort(key=lambda e: e["date"])

    # Re-assign stable numeric IDs
    for i, ev in enumerate(all_events, 1):
        ev["id"] = i

    cal["events"] = all_events
    cal["updated"] = date.today().isoformat()

    with open(CALENDAR_FILE, 'w') as f:
        json.dump(cal, f, indent=2)
    print(f"  Saved calendar.json ({len(all_events)} events)")

# ── Elections Calendar ────────────────────────────────────────────────────────

ELECTIONS_FILE = ROOT / "data" / "elections.json"

def update_elections():
    """Fetch upcoming election dates from NCSBE and update elections.json.
    Uses best-effort scraping with graceful fallback to preserve existing data."""
    print("Updating elections from NCSBE...")
    try:
        existing = json.loads(ELECTIONS_FILE.read_text())
    except Exception:
        existing = {"lastUpdated": str(date.today()), "source": "https://www.ncsbe.gov/voting/upcoming-election"}

    try:
        html = fetch("https://www.ncsbe.gov/voting/upcoming-election")
    except Exception as e:
        print(f"  NCSBE fetch failed: {e} — keeping existing elections.json")
        return

    changed = False

    # Look for date patterns like "November 3, 2026" or "2026-11-03"
    # Try to find the next election row in the page
    # NCSBE pages often list elections in a table with date, type, etc.
    date_re = re.compile(
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+'
        r'(\d{1,2}),?\s+(\d{4})',
        re.IGNORECASE,
    )
    months = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12,
    }

    today = date.today()
    found_elections = []
    for m in date_re.finditer(html):
        month_name, day, year = m.group(1), int(m.group(2)), int(m.group(3))
        mn = months[month_name.lower()]
        try:
            d = date(year, mn, int(day))
        except ValueError:
            continue
        if d > today:
            # Get surrounding text for election type
            start = max(0, m.start() - 200)
            end = min(len(html), m.end() + 200)
            context = clean_text(html[start:end])
            found_elections.append({
                "date": d.isoformat(),
                "label": f"{month_name} {day}, {year}",
                "context": context[:120],
            })

    if not found_elections:
        print("  No future election dates found on NCSBE page — keeping existing data")
        return

    # Use the soonest future election
    found_elections.sort(key=lambda e: e["date"])
    next_el = found_elections[0]

    # Determine election type from context
    ctx = next_el["context"].lower()
    if "primary" in ctx:
        el_type = "Primary Election"
    elif "general" in ctx:
        el_type = "General Election"
    elif "municipal" in ctx:
        el_type = "Municipal Election"
    elif "runoff" in ctx:
        el_type = "Runoff Election"
    else:
        el_type = "Election"

    new_next = {
        "date": next_el["date"],
        "label": next_el["label"],
        "type": el_type,
        "color": "orange",
    }

    if existing.get("nextElection", {}).get("date") != new_next["date"]:
        existing["nextElection"] = new_next
        changed = True
        print(f"  Updated nextElection: {new_next['date']} — {el_type}")

    if changed:
        existing["lastUpdated"] = str(today)
        existing["source"] = "https://www.ncsbe.gov/voting/upcoming-election"
        ELECTIONS_FILE.write_text(json.dumps(existing, indent=2))
        print("  Saved elections.json")
    else:
        print("  elections.json already current")


# ── Budget ────────────────────────────────────────────────────────────────────

BUDGET_FILE = ROOT / "data" / "budget-data.json"

def _current_fiscal_year():
    """Return the fiscal year label for the current budget cycle.
    Durham's fiscal year runs July 1 – June 30.
    Budget is adopted in mid-June; we consider the new FY 'current' after June 14.
    FY2026-27 = adopted June 2026, runs July 2026 – June 2027.
    """
    today = date.today()
    if today.month > 6 or (today.month == 6 and today.day >= 15):
        start = today.year
    else:
        start = today.year - 1
    return f"FY{start}-{str(start + 1)[2:]}"

def _scrape_county_budget_doc_url(fy_label):
    """Try to find the adopted budget document URL for the given FY on dconc.gov.
    Returns a URL string or None if not yet posted."""
    try:
        html = fetch("https://www.dconc.gov/Budget-and-Management-Services/Budget-Documents")
        # Look for links containing the FY label (e.g. "FY 2026-27" or "FY2026-27")
        fy_pattern = fy_label.replace("FY", "FY ?").replace("-", "[-–]")
        doc_links = re.findall(
            r'href="(/[^"]+)"[^>]*>[^<]*(?:Adopted|Budget Document)[^<]*', html, re.IGNORECASE
        )
        if not doc_links:
            # Broader search: any internal link near the FY label
            idx = html.find(fy_label.replace("-", " "))
            if idx < 0:
                idx = html.find(fy_label)
            if idx >= 0:
                snippet = html[max(0, idx - 200): idx + 500]
                doc_links = re.findall(r'href="(/[^"]+)"', snippet)

        for path in doc_links:
            if "coming-soon" in path.lower() or "test" in path.lower():
                continue
            return f"https://www.dconc.gov{path}"
    except Exception as e:
        print(f"  Budget doc scrape failed: {e}")
    return None

def _scrape_city_budget_doc_url(fy_label):
    """Try to find the adopted city budget document URL on durhamnc.gov."""
    try:
        html = fetch("https://www.durhamnc.gov/456/Finance")
        idx = html.find(fy_label.replace("-", " "))
        if idx < 0:
            idx = html.find(fy_label)
        if idx >= 0:
            snippet = html[max(0, idx - 200): idx + 500]
            links = re.findall(r'href="(/[^"]+)"', snippet)
            for path in links:
                if any(kw in path.lower() for kw in ["budget", "adopted", "fy"]):
                    return f"https://www.durhamnc.gov{path}"
    except Exception as e:
        print(f"  City budget doc scrape failed: {e}")
    return None

def update_budget():
    """After budget adoption (mid-June):
    1. Scrape dconc.gov and durhamnc.gov for the new adopted budget document URL.
    2. If found, update sourceUrl to the new document.
    3. Add the new fiscal year entry — with the actual doc URL if available,
       or a placeholder flagged for manual dollar-amount update."""
    print("Checking budget fiscal year...")
    with open(BUDGET_FILE) as f:
        data = json.load(f)

    expected_fy = _current_fiscal_year()
    changed = False

    for entity in data["entities"]:
        eid = entity.get("id", "")
        years = entity.get("years", [])
        totals = entity.get("totals", {})

        # Try to fetch the new adopted budget document URL
        if eid == "county":
            doc_url = _scrape_county_budget_doc_url(expected_fy)
        elif eid == "city":
            doc_url = _scrape_city_budget_doc_url(expected_fy)
        else:
            doc_url = None

        if doc_url:
            print(f"  {entity['name']}: found {expected_fy} doc → {doc_url}")
            if entity.get("sourceUrl") != doc_url:
                entity["sourceUrl"] = doc_url
                changed = True

        if expected_fy in years:
            continue

        print(f"  {entity['name']}: adding {expected_fy} entry")
        prior_fy = years[0] if years else None

        if prior_fy and prior_fy in totals:
            prior = dict(totals[prior_fy])
            new_entry = {
                **prior,
                "note": (
                    f"Source: {doc_url}" if doc_url
                    else f"PENDING: Update with adopted {expected_fy} figures from official budget document."
                ),
            }
            if not doc_url:
                new_entry["needs_update"] = True
        else:
            new_entry = {
                "note": (
                    f"Source: {doc_url}" if doc_url
                    else f"PENDING: Update with adopted {expected_fy} figures from official budget document."
                ),
                "needs_update": True,
            }

        totals[expected_fy] = new_entry
        entity["totals"] = totals
        entity["years"] = [expected_fy] + years
        changed = True

    if changed:
        with open(BUDGET_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        fy_entries = [e for ent in data["entities"] for e in [ent.get("totals", {}).get(expected_fy, {})]]
        has_pending = any(e.get("needs_update") for e in fy_entries)
        if has_pending:
            print(f"  Saved budget-data.json — ACTION NEEDED: fill in {expected_fy} dollar amounts")
        else:
            print(f"  Saved budget-data.json with {expected_fy} doc links")
    else:
        print(f"  budget-data.json already current for {expected_fy}")

# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    update_polling_places()
    update_council_wards()
    update_legislators()
    meetings_data = update_meetings()
    update_calendar(meetings_data)
    update_budget()
    update_elections()
    print("\nAll data files updated successfully.")
