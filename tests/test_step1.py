"""Tests for Step 1 modules: groq_chatbot and plan_checker."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import groq_chatbot as GC  # noqa: E402
import plan_checker as CHK  # noqa: E402


def _mock_res():
    return {
        "params": {
            "event_name": "Test Match",
            "attendance": 30000,
            "start_time": "19:30",
            "phase": "ingress",
        },
        "demand": {
            "total_vehicles": 9000,
            "peak_hourly_pcu": 8000.0,
            "peak_bucket": "19:00",
            "metro_riders": 4500.0,
            "pedestrians": 3000.0,
            "persons": {"car": 15000, "2w": 7500, "metro": 4500, "walk": 3000},
        },
        "sum_opt": {"max_vc": 1.4, "congested": 10, "near": 12},
        "sum_naive": {"max_vc": 1.8, "congested": 15, "near": 10},
        "corridor": {"length_m": 1200, "free_min": 1.5, "unprotected_min": 5.2},
        "hotspots": pd.DataFrame([
            {"street": "Street 8", "vc": 1.4, "load_pcu_hr": 2000, "capacity_pcu_hr": 1440},
            {"street": "Habsiguda Rd", "vc": 1.2, "load_pcu_hr": 4000, "capacity_pcu_hr": 3420},
            {"street": "Uppal X Rd", "vc": 1.1, "load_pcu_hr": 3900, "capacity_pcu_hr": 3600},
        ]),
        "diversions": [
            {"tag": "[D-1]", "name": "Street 8", "vc": 1.4, "feasible": True, "extra_m": 300},
            {"tag": "[D-2]", "name": "Habsiguda Rd", "vc": 1.2, "feasible": True, "extra_m": 450},
        ],
    }


def test_groq_chatbot_rule_first():
    res = _mock_res()
    ans, src = GC.generate_response("What are the critical bottlenecks?", res, lang="English")
    assert src == "rule"
    assert "Street 8" in ans


def test_groq_chatbot_greeting_bilingual():
    en = GC.greeting("IPL 2026", "English")
    te = GC.greeting("IPL 2026", "తెలుగు")
    assert "IPL 2026" in en
    assert "నమస్కారం, ఆఫీసర్" in te
    assert "IPL 2026" in te


def test_plan_checker_all_6_pass(tmp_path):
    res = _mock_res()
    out = CHK.run_checks(res, venue_key="uppal_stadium", feedback_path=tmp_path / "none.csv")
    assert out["total"] == 6
    assert out["passed"] == 6
    assert out["score_pct"] == 100
    assert out["status_label"] == "ASSUMED"


def test_post_event_feedback_roundtrip(tmp_path):
    csv_p = tmp_path / "fb.csv"
    CHK.save_post_event_feedback(
        {
            "venue_key": "uppal_stadium",
            "venue_name": "Uppal Stadium",
            "event_name": "Test Match",
            "event_date": "2026-04-15",
            "hotspots_accurate": True,
            "diversions_feasible": True,
            "corridor_clear": False,
            "officers_deployed": 60,
            "officers_recommended": 60,
            "missed_incidents": "Minor delay at Gate 2",
        },
        csv_path=csv_p,
    )
    df = CHK.load_post_event_feedback(csv_path=csv_p)
    assert len(df) == 1
    out = CHK.run_checks(_mock_res(), venue_key="uppal_stadium", feedback_path=csv_p)
    assert out["calibration_events"] == 1
    assert out["calibration_pct"] == 67
