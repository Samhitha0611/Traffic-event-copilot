"""Tests for Step 2 (wizard) and Step 3 (prediction, signals, pedestrian, operational engine)."""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import operational_engine as OE  # noqa: E402
import pedestrian_model as PM  # noqa: E402
import plan_checker as CHK  # noqa: E402
import prediction_engine as PE  # noqa: E402
import signal_layer as SL  # noqa: E402
import wizard as WIZ  # noqa: E402


def _mock_res():
    return {
        "params": {
            "event_name": "Test Match",
            "attendance": 39000,
            "start_time": "19:30",
            "event_date": "2026-04-15",
            "phase": "ingress",
        },
        "demand": {
            "total_vehicles": 13000,
            "peak_hourly_pcu": 10000.0,
            "peak_bucket": "19:00",
            "metro_riders": 5850.0,
            "pedestrians": 3900.0,
            "persons": {"car": 19500, "2w": 9750, "metro": 5850, "walk": 3900},
        },
        "sum_opt": {"max_vc": 1.6, "congested": 12, "near": 10},
        "sum_naive": {"max_vc": 1.9, "congested": 16, "near": 8},
        "corridor": {"length_m": 1200, "free_min": 1.5, "unprotected_min": 5.2},
        "hotspots": pd.DataFrame([
            {"street": "Street 8", "road_type": "residential", "vc": 1.6, "load_pcu_hr": 2300, "capacity_pcu_hr": 1440},
            {"street": "Habsiguda Rd", "road_type": "primary", "vc": 1.2, "load_pcu_hr": 4000, "capacity_pcu_hr": 3420},
            {"street": "Uppal X Rd", "road_type": "trunk", "vc": 0.9, "load_pcu_hr": 3200, "capacity_pcu_hr": 3600},
        ]),
        "diversions": [
            {"tag": "[D-1]", "name": "Street 8", "vc": 1.6, "feasible": False, "extra_m": 0},
            {"tag": "[D-2]", "name": "Habsiguda Rd", "vc": 1.2, "feasible": True, "extra_m": 450},
        ],
    }


def test_wizard_bilingual_cards_populated():
    assert len(WIZ.WIZARD_VENUES) >= 6
    for v in WIZ.WIZARD_VENUES:
        assert v["en"] and v["te"]
    assert len(WIZ.WIZARD_CROWD_TIERS) == 4


def test_prediction_engine_horizons_and_heatmap(tmp_path):
    res = _mock_res()
    p15 = PE.predict_traffic(res, minutes_ahead=15, weather="clear")
    p30 = PE.predict_traffic(res, minutes_ahead=30, weather="rain")
    p60 = PE.predict_traffic(res, minutes_ahead=60, weather="clear")
    assert p15["status"] == "ASSUMED"
    assert len(p30["rows"]) >= 3
    # Rain + 30 min should predict higher V/C than clear + 15 min
    assert p30["rows"][0]["vc_pred"] > p15["rows"][0]["vc_pred"]
    assert p60["rows"][0]["vc_pred"] < p30["rows"][0]["vc_pred"]

    hm_path = PE.save_heatmap_json(res, venue_key="uppal_stadium", weather="clear", out_dir=tmp_path)
    assert hm_path.exists()
    data = json.loads(hm_path.read_text(encoding="utf-8"))
    assert data["metadata"]["venue_key"] == "uppal_stadium"
    assert len(data["roads"]) >= 3


def test_signal_layer_recommendations():
    res = _mock_res()
    sigs = SL.extract_signals(None, res, venue_key="uppal_stadium")
    assert len(sigs) == 3
    assert sigs[0]["tag"] == "[SIGNAL-1]"
    assert "120s" in sigs[0]["cycle_s"]


def test_pedestrian_model_gates():
    res = _mock_res()
    ped = PM.build_pedestrian_plan(res)
    assert ped["total_pedestrians"] == 9750
    assert len(ped["gates"]) == 4
    assert ped["gates"][0]["tag"] == "[PED-1]"


def test_operational_engine_12_sections():
    res = _mock_res()
    conf = CHK.run_checks(res, venue_key="uppal_stadium")
    ops = OE.compute_operational_decisions(None, res, venue_key="uppal_stadium")
    assert len(ops["closures"]) >= 1
    assert len(ops["barricades"]) >= 4
    assert len(ops["staged_timeline"]) == 6

    rep_en = OE.build_12_section_report("## Base Plan", ops, res, conf, lang="English")
    for tag in ("[CLOSE]", "[B]", "[ES-AMB]", "[ES-FIRE]", "[SIGNAL]", "[PED]"):
        assert tag in rep_en

    rep_te = OE.build_12_section_report("## ప్రాథమిక ప్రణాళిక", ops, res, conf, lang="తెలుగు")
    assert "రోడ్డు మూసివేతలు" in rep_te
    assert "ట్రాఫిక్ సిగ్నల్" in rep_te
