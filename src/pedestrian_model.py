"""
Pedestrian & Crowd Exit Sequencing Model (Step 3 - Module 3C Q6).
Computes staggered gate opening schedule [PED-1]..[PED-4] and crush-risk flag.
All gate widths and dispersal speeds are labelled ASSUMED.
"""
from __future__ import annotations

from typing import Any


def build_pedestrian_plan(res: dict[str, Any] | None) -> dict[str, Any]:
    """Generate staggered pedestrian exit sequencing and crush risk metrics."""
    if not res:
        return {"total_pedestrians": 0, "gates": [], "crush_risk": False, "flow_pm_m": 0.0}

    dem = res.get("demand", {})
    params = res.get("params", {})
    attendance = int(params.get("attendance", 0) or 0)
    walk_peds = float(dem.get("pedestrians", 0.0))
    metro_riders = float(dem.get("metro_riders", 0.0))
    # All metro + walking + bus passengers exit on foot at venue gates
    total_exit_peds = int(round(walk_peds + metro_riders)) or int(round(attendance * 0.25))

    # ASSUMED 4 exit gates of 4 m effective width each, 40-min egress window
    gate_width_m = 4.0
    egress_min = 40.0
    flow_pm_m = round(total_exit_peds / (4 * gate_width_m * egress_min), 1)
    crush_risk = flow_pm_m > 50.0  # Fruin / crowd safety threshold (ASSUMED)

    gates = [
        {
            "tag": "[PED-1]",
            "time": "T+0 min",
            "gate": "Gate A (North)",
            "direction_en": "Metro Station Exit Corridor",
            "direction_te": "మెట్రో స్టేషన్ మార్గం",
            "share_pct": 35,
            "crowd": int(round(total_exit_peds * 0.35)),
            "marshals": max(2, int(round(total_exit_peds * 0.35 / 500))),
        },
        {
            "tag": "[PED-2]",
            "time": "T+10 min",
            "gate": "Gate B (East)",
            "direction_en": "TGSRTC Special Bus Bays",
            "direction_te": "ఆర్టీసీ ప్రత్యేక బస్సు బేలు",
            "share_pct": 30,
            "crowd": int(round(total_exit_peds * 0.30)),
            "marshals": max(2, int(round(total_exit_peds * 0.30 / 500))),
        },
        {
            "tag": "[PED-3]",
            "time": "T+20 min",
            "gate": "Gate C (South)",
            "direction_en": "Designated Parking Zones [P]",
            "direction_te": "పార్కింగ్ జోన్లు [P]",
            "share_pct": 25,
            "crowd": int(round(total_exit_peds * 0.25)),
            "marshals": max(2, int(round(total_exit_peds * 0.25 / 500))),
        },
        {
            "tag": "[PED-4]",
            "time": "T+30 min",
            "gate": "Gate D (West)",
            "direction_en": "Overspill / Emergency Dispersal",
            "direction_te": "అత్యవసర / అదనపు నిష్క్రమణ",
            "share_pct": 10,
            "crowd": int(round(total_exit_peds * 0.10)),
            "marshals": max(1, int(round(total_exit_peds * 0.10 / 500))),
        },
    ]

    return {
        "total_pedestrians": total_exit_peds,
        "flow_pm_m": flow_pm_m,
        "crush_risk": crush_risk,
        "metro_headway_note_en": "Request 5-min HMRL Metro headway during peak egress window (ASSUMED).",
        "metro_headway_note_te": "గరిష్ట నిష్క్రమణ సమయంలో 5 నిమిషాలకు ఒక మెట్రో రైలు నడపాలని HMRLను కోరండి (అనుకోబడినది / ASSUMED).",
        "gates": gates,
    }
