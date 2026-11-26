"""
Optional FastAPI Prediction Endpoint (Step 3 - Module 3A).
Exposes GET /api/predict?venue=...&crowd=...&start_time=...&minutes_ahead=30
Run standalone: uvicorn src.predict_api:app --reload --port 8000
"""
from __future__ import annotations

from typing import Any

import event_engine as E
import prediction_engine as PE
import venue_catalog as VC

try:
    from fastapi import FastAPI, Query
    app = FastAPI(title="Traffic Event Co-Pilot Prediction API")
except ImportError:  # FastAPI is optional; Streamlit app works without it
    app = None


def compute_api_prediction(
    venue: str = "uppal_stadium",
    crowd: int = 39000,
    start_time: str = "19:30",
    phase: str = "ingress",
    minutes_ahead: int = 30,
    weather: str = "clear",
) -> dict[str, Any]:
    """Pure Python handler reusable by FastAPI or tests."""
    suggestions = VC.get_hyderabad_location_suggestions()
    v_info = next((v for v in suggestions.values() if v.get("key") == venue), None)
    if v_info is None:
        v_info = next(iter(suggestions.values()))
    latlon = (v_info["lat"], v_info["lon"])
    hosp = VC.nearest_hospital(*latlon)
    hosp_latlon = (float(hosp["Latitude"]), float(hosp["Longitude"])) if hosp else None
    net_path = VC.get_road_network_path(v_info.get("key", venue), latlon[0], latlon[1])
    D, _ = E.build_network(net_path)
    pack = E.load_pack()
    res = E.run_scenario(
        D,
        {
            "attendance": crowd,
            "start_time": start_time,
            "phase": phase,
            "venue_latlon": latlon,
            "hospital_latlon": hosp_latlon,
            "event_name": f"API Prediction ({venue})",
        },
        pack,
    )
    pred = PE.predict_traffic(res, minutes_ahead=minutes_ahead, weather=weather)
    hm_path = PE.save_heatmap_json(res, venue_key=venue, weather=weather)
    return {
        "venue": venue,
        "minutes_ahead": minutes_ahead,
        "weather": weather,
        "confidence_pct": pred["confidence_pct"],
        "status": pred["status"],
        "heatmap_file": str(hm_path),
        "roads": pred["rows"],
    }


if app is not None:
    @app.get("/api/predict")
    def api_predict(
        venue: str = Query("uppal_stadium"),
        crowd: int = Query(39000, ge=1000, le=150000),
        start_time: str = Query("19:30"),
        phase: str = Query("ingress"),
        minutes_ahead: int = Query(30),
        weather: str = Query("clear"),
    ):
        return compute_api_prediction(venue, crowd, start_time, phase, minutes_ahead, weather)
