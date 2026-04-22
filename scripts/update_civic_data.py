#!/usr/bin/env python3
"""
Update Durham Civic Hub data files.
Fetches: polling places, council wards, NC Senate/House districts.
Run locally or via GitHub Actions on July 31 and December 31.
"""
import json, csv, io, re, sys
from datetime import date
from pathlib import Path
import urllib.request

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

def fetch(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": "Durham-Civic-Hub/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read() if binary else r.read().decode("utf-8")

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
    # Find the most recent election date from the NC SBE S3 bucket listing
    # Try to detect the latest available CSV
    election_dates = [
        f"{date.today().year}_03_03",
        f"{date.today().year}_11_04",
        f"{date.today().year - 1}_11_05",
        f"{date.today().year - 1}_03_05",
    ]
    raw = None
    source_url = None
    for ed in election_dates:
        url = f"https://s3.amazonaws.com/dl.ncsbe.gov/ENRS/{ed}/polling_place_{ed.replace('-','')}.csv"
        # Normalize: remove extra chars
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
    (DATA_DIR / "council-wards.json").write_text(
        json.dumps(fc, separators=(",", ":"))
    )
    print(f"  Saved {len(fc['features'])} ward features")

# ── NC State Legislators ───────────────────────────────────────────────────────
def update_legislators():
    print("Fetching NC Senate districts...")
    senate_url = (
        "https://services2.arcgis.com/G5vR3cOjh6g2Ed8E/ArcGIS/rest/services/"
        "Electoral/FeatureServer/5/query?where=1%3D1&outFields=DISTRICT,RepName,Party,DistrictURL&f=geojson&outSR=4326"
    )
    senate_data = json.loads(fetch(senate_url))
    senate_fc = {"type": "FeatureCollection", "features": []}
    for f in senate_data.get("features", []):
        p = f["properties"]
        geom = simplify_geom(f["geometry"])
        if geom:
            senate_fc["features"].append({
                "type": "Feature",
                "properties": {
                    "district": int(p["DISTRICT"]),
                    "name": p["RepName"],
                    "party": p["Party"],
                    "url": p["DistrictURL"],
                },
                "geometry": geom,
            })
    (DATA_DIR / "nc-senate.json").write_text(
        json.dumps(senate_fc, separators=(",", ":"))
    )
    print(f"  Saved {len(senate_fc['features'])} Senate districts")

    print("Fetching NC House districts...")
    house_url = (
        "https://services2.arcgis.com/G5vR3cOjh6g2Ed8E/ArcGIS/rest/services/"
        "Electoral/FeatureServer/4/query?where=1%3D1&outFields=DISTRICT,RepName,Party,DistrictURL&f=geojson&outSR=4326"
    )
    house_data = json.loads(fetch(house_url))
    house_fc = {"type": "FeatureCollection", "features": []}
    for f in house_data.get("features", []):
        p = f["properties"]
        geom = simplify_geom(f["geometry"])
        if geom:
            house_fc["features"].append({
                "type": "Feature",
                "properties": {
                    "district": int(p["DISTRICT"]),
                    "name": p["RepName"],
                    "party": p["Party"],
                    "url": p["DistrictURL"],
                },
                "geometry": geom,
            })
    (DATA_DIR / "nc-house.json").write_text(
        json.dumps(house_fc, separators=(",", ":"))
    )
    print(f"  Saved {len(house_fc['features'])} House districts")

if __name__ == "__main__":
    update_polling_places()
    update_council_wards()
    update_legislators()
    print("\nAll data files updated successfully.")
