"""
Collect REAL traffic speeds for the roads that matter, every hour, and save them.

After 1-2 weeks you have real "typical speed by hour and day of week" for each point.
This is speed/congestion data (current speed vs free-flow speed), NOT vehicle counts.

Setup (free): create a TomTom developer account, copy your API key, then in PowerShell:
    $env:TOMTOM_API_KEY = "your_key_here"
Run once now:            py scripts/collect_tomtom_speeds.py
Run every hour (Windows): schedule it with Task Scheduler, or leave this running:
                         py scripts/collect_tomtom_speeds.py --loop
Points to watch: data/watch_points.csv  (columns: location,lat,lon). If missing, the venue
approach roads from data/hyderabad_venues.csv are used (venue centre only).
Free-plan limits change; check TomTom's current terms before collecting many points.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "src"))
import observed_speeds as OS  # noqa: E402

URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"


def fetch_point(key: str, lat: float, lon: float, session=requests) -> dict | None:
    r = session.get(URL, params={"key": key, "point": f"{lat},{lon}"}, timeout=15)
    if r.status_code != 200:
        print("  API error", r.status_code, r.text[:120])
        return None
    d = r.json().get("flowSegmentData", {})
    if "currentSpeed" not in d:
        return None
    return {"current_speed_kmh": d["currentSpeed"], "free_flow_speed_kmh": d["freeFlowSpeed"],
            "confidence": d.get("confidence"), "road_closure": d.get("roadClosure", False)}


def watch_points() -> pd.DataFrame:
    p = BASE / "data" / "watch_points.csv"
    if p.exists():
        return pd.read_csv(p)
    v = pd.read_csv(BASE / "data" / "hyderabad_venues.csv")
    return v.rename(columns={"Venue_Name": "location", "Latitude": "lat", "Longitude": "lon"})[["location", "lat", "lon"]]


def collect_once(key: str, session=requests) -> int:
    rows, now = [], datetime.now()
    for _, p in watch_points().iterrows():
        res = fetch_point(key, float(p["lat"]), float(p["lon"]), session)
        if res:
            rows.append({"timestamp": now.isoformat(timespec="minutes"), "day_of_week": now.strftime("%A"),
                         "hour": now.hour, "location": p["location"], "lat": p["lat"], "lon": p["lon"],
                         "source": "TomTom Traffic Flow API", **res})
    if rows:
        df = pd.DataFrame(rows)[OS.COLUMNS]
        OS.SPEEDS_CSV.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(OS.SPEEDS_CSV, mode="a", header=not OS.SPEEDS_CSV.exists(), index=False)
    print(f"{now:%Y-%m-%d %H:%M}  saved {len(rows)} readings -> {OS.SPEEDS_CSV}")
    return len(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", action="store_true", help="collect every hour until stopped (Ctrl+C)")
    a = ap.parse_args()
    key = os.environ.get("TOMTOM_API_KEY", "").strip()
    if not key:
        sys.exit("Set TOMTOM_API_KEY first (see the top of this file). No key = no data; nothing is invented.")
    while True:
        collect_once(key)
        if not a.loop:
            break
        time.sleep(3600)
