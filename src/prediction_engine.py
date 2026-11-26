"""
AI Traffic Prediction Engine (Step 3 - Module 3A).
Computes 15 / 30 / 60 minute future traffic V/C forecasts per hotspot road
using a transparent time-decay + weather multiplier model (labelled ASSUMED).
Saves event heatmap JSONs to data/heatmaps/{venue}_{event_date}.json.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
HEATMAP_DIR = ROOT_DIR / "data" / "heatmaps"

WEATHER_CAP_FACTOR: dict[str, float] = {
    "clear": 1.00,
    "rain": 0.85,
    "fog": 0.75,
}

TIME_HORIZON_FACTOR: dict[str, dict[int, float]] = {
    "ingress": {15: 1.08, 30: 1.22, 60: 0.92},
    "egress": {15: 1.12, 30: 1.18, 60: 0.85},
}


def classify_vc(vc: float) -> tuple[str, str, str]:
    """Return (emoji, English label, Telugu label) for a V/C ratio."""
    if vc < 0.60:
        return "🟢", "Free", "సాధారణం"
    if vc < 0.85:
        return "🟢", "Low", "తక్కువ"
    if vc < 1.10:
        return "🟡", "Moderate", "మధ్యస్థం"
    if vc < 1.50:
        return "🔴", "Heavy", "భారీ"
    return "🔴", "Very Heavy", "అత్యంత భారీ"


def predict_traffic(
    res: dict[str, Any] | None,
    minutes_ahead: int = 30,
    weather: str = "clear",
) -> dict[str, Any]:
    """
    Predict traffic status for the next 15, 30, or 60 minutes based on
    computed scenario V/C, phase (ingress/egress), and weather (ASSUMED model).
    """
    if not res:
        return {"rows": [], "confidence_pct": 0, "status": "ASSUMED", "minutes_ahead": minutes_ahead}

    params = res.get("params", {})
    phase = str(params.get("phase", "ingress")).lower()
    if phase not in TIME_HORIZON_FACTOR:
        phase = "ingress"
    horizon = minutes_ahead if minutes_ahead in (15, 30, 60) else 30
    w_key = weather.lower() if weather.lower() in WEATHER_CAP_FACTOR else "clear"

    t_factor = TIME_HORIZON_FACTOR[phase][horizon]
    cap_factor = WEATHER_CAP_FACTOR[w_key]

    hotspots = res.get("hotspots", pd.DataFrame())
    rows: list[dict[str, Any]] = []

    if isinstance(hotspots, pd.DataFrame) and not hotspots.empty:
        for idx, (_, r) in enumerate(hotspots.head(6).iterrows()):
            vc_now = float(r.get("vc", 0.0))
            vc_pred = round((vc_now * t_factor) / cap_factor, 2)
            e_now, l_now_en, l_now_te = classify_vc(vc_now)
            e_pred, l_pred_en, l_pred_te = classify_vc(vc_pred)
            trend = "↑" if vc_pred > vc_now + 0.05 else ("↓" if vc_pred < vc_now - 0.05 else "→")
            rows.append({
                "tag": f"[H-{idx + 1}]",
                "location": str(r.get("street", "Unknown Road")),
                "vc_now": round(vc_now, 2),
                "vc_15": round((vc_now * TIME_HORIZON_FACTOR[phase][15]) / cap_factor, 2),
                "vc_30": round((vc_now * TIME_HORIZON_FACTOR[phase][30]) / cap_factor, 2),
                "vc_60": round((vc_now * TIME_HORIZON_FACTOR[phase][60]) / cap_factor, 2),
                "vc_pred": vc_pred,
                "now_en": f"{e_now} {l_now_en}",
                "now_te": f"{e_now} {l_now_te}",
                "pred_en": f"{e_pred} {l_pred_en} {trend}",
                "pred_te": f"{e_pred} {l_pred_te} {trend}",
                "trend": trend,
            })

    corridor = res.get("corridor")
    if corridor:
        rows.append({
            "tag": "[E-1]",
            "location": "Emergency Green Corridor",
            "vc_now": 0.25,
            "vc_15": 0.25,
            "vc_30": 0.25,
            "vc_60": 0.25,
            "vc_pred": 0.25,
            "now_en": "🟢 Clear",
            "now_te": "🟢 క్లియర్",
            "pred_en": "🟢 Clear ✅",
            "pred_te": "🟢 క్లియర్ ✅",
            "trend": "→",
        })

    return {
        "rows": rows,
        "minutes_ahead": horizon,
        "weather": w_key,
        "confidence_pct": 73,  # ASSUMED baseline without live ITMS sensors
        "status": "ASSUMED",
    }


def save_heatmap_json(
    res: dict[str, Any],
    venue_key: str = "uppal_stadium",
    weather: str = "clear",
    out_dir: Path | None = None,
) -> Path:
    """Save 15/30/60 min predicted congestion heatmap JSON for an event."""
    target_dir = out_dir or HEATMAP_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    params = res.get("params", {})
    ev_date = str(params.get("event_date") or "custom").replace("/", "-")
    fname = f"{venue_key}_{ev_date}.json"
    out_path = target_dir / fname

    pred = predict_traffic(res, minutes_ahead=30, weather=weather)
    payload = {
        "metadata": {
            "event": params.get("event_name", "Unknown"),
            "venue_key": venue_key,
            "crowd": int(params.get("attendance", 0) or 0),
            "phase": params.get("phase", "ingress"),
            "weather": weather,
            "model_status": "ASSUMED (time-decay heuristic; real sensor data missing)",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        },
        "roads": [
            {
                "tag": r["tag"],
                "name": r["location"],
                "vc_now": r["vc_now"],
                "vc_15min": r["vc_15"],
                "vc_30min": r["vc_30"],
                "vc_60min": r["vc_60"],
            }
            for r in pred["rows"]
        ],
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path
