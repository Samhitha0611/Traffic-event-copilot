"""
Traffic Signal Layer (Step 3 - Module 3B).
Extracts traffic_signals nodes from the loaded OSM road graph (or cached JSON
in data/traffic_signals_{venue}.json) and computes signal timing recommendations
(ASSUMED cycle heuristics) for police ACP/Inspector action.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"


def _recommend_action(vc: float, on_corridor: bool, on_diversion: bool) -> dict[str, str]:
    if on_corridor:
        return {
            "action_en": "GREEN WAVE / MANUAL OVERRIDE — Clear for emergency corridor [E-1]",
            "action_te": "గ్రీన్ వేవ్ / మాన్యువల్ ఓవర్‌రైడ్ — అత్యవసర కారిడార్ [E-1] కోసం క్లియర్ ఉంచండి",
            "cycle_s": "Override (Priority)",
            "activate": "T-120 min",
        }
    if vc > 1.0:
        return {
            "action_en": "EXTEND GREEN to 120s on main event approach; SHORTEN cross-road to 45s",
            "action_te": "ప్రధాన మార్గంలో గ్రీన్ సిగ్నల్ 120 సెకన్లకు పెంచండి; క్రాస్-రోడ్డును 45 సెకన్లకు తగ్గించండి",
            "cycle_s": "120s / 45s (ASSUMED)",
            "activate": "T-60 min",
        }
    if on_diversion:
        return {
            "action_en": "EXTEND GREEN to 110s along diversion corridor to pull alternate flow",
            "action_te": "మళ్లింపు మార్గంలో గ్రీన్ సిగ్నల్ 110 సెకన్లకు పెంచండి",
            "cycle_s": "110s (ASSUMED)",
            "activate": "T-60 min",
        }
    if vc >= 0.6:
        return {
            "action_en": "MONITOR — Keep standard 90s cycle with manual officer standby",
            "action_te": "పర్యవేక్షించండి — సాధారణ 90 సెకన్ల సైకిల్ కొనసాగించండి",
            "cycle_s": "90s (ASSUMED)",
            "activate": "T-30 min",
        }
    return {
        "action_en": "NO CHANGE — Normal 90s cycle (free-flow)",
        "action_te": "మార్పు అవసరం లేదు — సాధారణ 90 సెకన్ల సైకిల్",
        "cycle_s": "90s",
        "activate": "Normal",
    }


def extract_signals(
    D: dict[str, Any] | None,
    res: dict[str, Any] | None,
    venue_key: str = "uppal_stadium",
) -> list[dict[str, Any]]:
    """
    Identify traffic signals within the venue road network and pair each with
    an operational signal-timing recommendation.
    """
    if not res:
        return []

    signals: list[dict[str, Any]] = []
    hotspots = res.get("hotspots", pd.DataFrame())
    corridor = res.get("corridor") or {}
    corridor_nodes = set(corridor.get("nodes", [])) if isinstance(corridor, dict) else set()
    diversion_names = {str(d.get("name", "")).lower() for d in res.get("diversions", [])}

    # 1. Check OSM graph nodes tagged highway=traffic_signals
    if D and "G" in D:
        G = D["G"]
        edge_vc_map: dict[Any, float] = {}
        edge_name_map: dict[Any, str] = {}
        if isinstance(hotspots, pd.DataFrame) and not hotspots.empty:
            for _, hr in hotspots.iterrows():
                sname = str(hr.get("street", ""))
                vc = float(hr.get("vc", 0.0))
                edge_name_map[sname.lower()] = vc
                edge_vc_map[sname.lower()] = vc

        for nid, ndata in G.nodes(data=True):
            hw = str(ndata.get("highway", "")).lower()
            if "traffic_signals" in hw:
                lat = float(ndata.get("y", 0.0))
                lon = float(ndata.get("x", 0.0))
                # Inspect incident edges for street name
                street_name = "Junction Signal"
                max_vc = 0.75
                for _, _, edata in G.edges(nid, data=True):
                    nm = edata.get("name")
                    if isinstance(nm, list):
                        nm = nm[0]
                    if nm:
                        street_name = str(nm)
                        max_vc = max(max_vc, float(edge_vc_map.get(street_name.lower(), 0.75)))
                on_corr = nid in corridor_nodes
                on_div = street_name.lower() in diversion_names
                rec = _recommend_action(max_vc, on_corr, on_div)
                signals.append({
                    "tag": f"[SIGNAL-{len(signals) + 1}]",
                    "name": street_name,
                    "lat": round(lat, 6),
                    "lon": round(lon, 6),
                    "vc": round(max_vc, 2),
                    "source": "OSM traffic_signals",
                    **rec,
                })

    # 2. If OSM graph had no explicit traffic_signals tags, derive signal checkpoints from top hotspots
    if not signals and isinstance(hotspots, pd.DataFrame) and not hotspots.empty:
        for idx, (_, hr) in enumerate(hotspots.head(5).iterrows()):
            sname = str(hr.get("street", f"Junction {idx + 1}"))
            vc = float(hr.get("vc", 0.0))
            rec = _recommend_action(vc, False, sname.lower() in diversion_names)
            signals.append({
                "tag": f"[SIGNAL-{idx + 1}]",
                "name": f"{sname} Junction",
                "lat": None,
                "lon": None,
                "vc": round(vc, 2),
                "source": "Hotspot junction (ASSUMED signal)",
                **rec,
            })

    # Save cache JSON if coordinates exist
    try:
        cache_path = DATA_DIR / f"traffic_signals_{venue_key}.json"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(signals, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    return signals
