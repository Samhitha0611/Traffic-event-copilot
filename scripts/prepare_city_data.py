"""
Prepare road maps (and hospitals) for every venue, once, so the app works fast and offline.

  py scripts/prepare_city_data.py --check        test which OpenStreetMap servers your network can reach
  py scripts/prepare_city_data.py                download road maps for every venue that has none yet
  py scripts/prepare_city_data.py --hospitals    also add hospitals near each venue (from OpenStreetMap)
  py scripts/prepare_city_data.py --radius 4000  use a 4 km map instead of 3 km

No API key is needed. If every server times out, your network blocks it: use a mobile hotspot or VPN.
Commit the saved files in data/networks/ so teammates never need to download again.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "src"))
import osm_download as OD  # noqa: E402
import venue_catalog as VC  # noqa: E402


def add_hospitals(lat: float, lon: float, radius_m: int = 6000, session=None) -> int:
    """Add hospitals near a point to data/hyderabad_hospitals.csv using Nominatim (the OpenStreetMap search
    service, which works when Overpass is slow). Returns how many new hospitals were added."""
    import math
    import time

    import pandas as pd
    import requests
    session = session or requests
    dlat = radius_m / 111320.0
    dlon = radius_m / (111320.0 * math.cos(math.radians(lat)))
    params = {"q": "hospital", "format": "jsonv2", "limit": 40, "bounded": 1,
              "viewbox": f"{lon - dlon},{lat + dlat},{lon + dlon},{lat - dlat}"}   # left, top, right, bottom
    r = session.get("https://nominatim.openstreetmap.org/search", params=params,
                    headers={"User-Agent": "traffic_event_copilot_student_project"}, timeout=(10, 30))
    time.sleep(1.1)                                    # Nominatim rule: at most 1 request per second
    r.raise_for_status()
    cur = VC.load_hospitals()
    known = set(cur["Hospital_Name"].astype(str).str.lower()) if not cur.empty else set()
    rows = []
    for it in r.json():
        name = str(it.get("name") or it.get("display_name", "").split(",")[0]).strip()
        if not name or name.lower() in known:
            continue
        if it.get("type") != "hospital" and "hospital" not in name.lower():
            continue                                    # skip clinics, pharmacies, etc.
        rows.append({"Hospital_Name": name, "Zone": "OpenStreetMap", "Latitude": round(float(it["lat"]), 6),
                     "Longitude": round(float(it["lon"]), 6), "Source": "OpenStreetMap Nominatim"})
        known.add(name.lower())
    if rows:
        pd.concat([cur, pd.DataFrame(rows)], ignore_index=True).to_csv(VC.HOSPITALS_CSV, index=False)
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--hospitals", action="store_true")
    ap.add_argument("--radius", type=int, default=3000)
    a = ap.parse_args()

    print("Testing OpenStreetMap servers (up to 30 s each; slow does not mean blocked)...")
    for url in OD.endpoints():
        ok, note = OD.probe_detail(url)
        print(f"  {'OK  ' if ok else 'SLOW/FAIL'}  {url}  ({note})")
    if a.check:
        return
    print("\nIf Overpass is slow, the main OpenStreetMap API is used automatically (tile by tile, about 1-3 min per venue).\n")

    venues = VC.get_hyderabad_location_suggestions()
    done = failed = 0
    todo = [(l, v) for l, v in venues.items() if v.get("key")]
    for n, (label, v) in enumerate(todo, 1):
        key = v.get("key")
        print(f"[{n}/{len(todo)}] {label} ...", flush=True)
        try:
            path = OD.get_graph_for_venue(key, v["lat"], v["lon"], a.radius, force_retry=True)
            print(f"  ready  {label}  ->  {Path(path).name}", flush=True)
            done += 1
            if a.hospitals:
                try:
                    print(f"         hospitals added: {add_hospitals(v['lat'], v['lon'])}", flush=True)
                except Exception as exc:               # never let hospitals block the road maps
                    print(f"         hospitals skipped ({type(exc).__name__}); run again later", flush=True)
        except Exception as exc:
            print(f"  FAILED {label}: {exc}")
            failed += 1
    print(f"\nFinished: {done} ready, {failed} failed. Re-run to retry the failed ones.")


if __name__ == "__main__":
    main()
