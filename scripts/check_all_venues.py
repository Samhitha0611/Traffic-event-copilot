"""
Check every venue in the dropdown: does it have a road map, and does the plan look sane?

    py scripts/check_all_venues.py

Prints one line per venue and saves outputs/venue_check.csv. It never downloads anything.
A venue is flagged if: no map, the venue is not on the map, fewer than 3 approaches, no road gets loaded,
no hospital within 12 km, or max V/C is extreme (above 4), which usually means a map or capacity problem.
"""
import sys
import time
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "src"))
import event_engine as E  # noqa: E402
import osm_download as OD  # noqa: E402
import venue_catalog as VC  # noqa: E402


def map_path_if_available(key: str, lat: float, lon: float):
    """Saved map for this venue, or None. Never downloads."""
    if key.startswith("uppal") and OD.UPPAL_GRAPHML.exists():
        return OD.UPPAL_GRAPHML
    f = OD.NETWORKS_DIR / f"{key}.graphml"
    if f.exists():
        return f
    return OD.find_covering_graph(lat, lon)


def check_venue(label: str, v: dict, nets: dict) -> dict:
    row = {"venue": label, "status": "OK", "notes": ""}
    notes = []
    path = map_path_if_available(v.get("key", ""), v["lat"], v["lon"])
    if path is None:
        return {**row, "status": "NO MAP", "notes": "run scripts/prepare_city_data.py"}
    if path not in nets:
        nets[path] = E.build_network(path)
    D, st = nets[path]
    venue = (v["lat"], v["lon"])
    off = E.haversine(venue, E.node_xy(D, E.nearest_node(D, *venue)))
    hosp = VC.nearest_hospital(*venue)
    t = time.time()
    r = E.run_scenario(D, {"attendance": int(v.get("capacity", 25000)), "venue_latlon": venue, "venue_name": label,
                           "hospital_latlon": (float(hosp["Latitude"]), float(hosp["Longitude"])) if hosp else None})
    row.update({"map": path.name, "junctions": st["nodes"], "approaches": len(r["approaches"]),
                "max_vc_naive": r["sum_naive"]["max_vc"], "max_vc_copilot": r["sum_opt"]["max_vc"],
                "roads_over_capacity": r["sum_opt"]["congested"], "hotspots": len(r["hotspots"]),
                "hospital_km": hosp["Distance_km"] if hosp else None, "seconds": round(time.time() - t, 1)})
    if off > 300:
        notes.append(f"venue is {off:.0f} m from the nearest road on the map")
    if len(r["approaches"]) < 3:
        notes.append("fewer than 3 approaches")
    if r["sum_opt"]["loaded_edges"] == 0:
        notes.append("no road was loaded")
    if hosp is None:
        notes.append("no hospital within 12 km")
    if r["sum_opt"]["max_vc"] > 4:
        notes.append("extreme V/C: check map and capacity")
    if notes:
        row.update({"status": "CHECK", "notes": "; ".join(notes)})
    return row


def main():
    nets, rows = {}, []
    for label, v in VC.get_hyderabad_location_suggestions().items():
        if not v.get("key"):
            continue
        try:
            rows.append(check_venue(label, v, nets))
        except Exception as exc:
            rows.append({"venue": label, "status": "ERROR", "notes": f"{type(exc).__name__}: {exc}"})
        print(f"{rows[-1]['status']:7} {label}  {rows[-1].get('notes', '')}", flush=True)
    df = pd.DataFrame(rows)
    out = BASE / "outputs" / "venue_check.csv"
    out.parent.mkdir(exist_ok=True)
    df.to_csv(out, index=False)
    print(f"\n{(df.status == 'OK').sum()} OK, {(df.status == 'CHECK').sum()} to check, "
          f"{(df.status.isin(['NO MAP', 'ERROR'])).sum()} missing/error. Saved {out}")


if __name__ == "__main__":
    main()
