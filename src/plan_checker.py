"""
Plan Confidence Score & Post-Event Feedback module for Traffic Event Co-Pilot.
Runs 6 internal sanity checks on every generated traffic plan and stores/reads
post-event officer feedback in data/post_event_feedback.csv.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
FEEDBACK_CSV = ROOT_DIR / "data" / "post_event_feedback.csv"


def _hhmm_to_minutes(hhmm: str) -> int | None:
    try:
        parts = str(hhmm).strip().split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return None


def load_post_event_feedback(csv_path: Path | None = None) -> pd.DataFrame:
    path = csv_path or FEEDBACK_CSV
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def save_post_event_feedback(record: dict[str, Any], csv_path: Path | None = None) -> Path:
    path = csv_path or FEEDBACK_CSV
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "submitted_at": datetime.now().isoformat(timespec="seconds"),
        "venue_key": str(record.get("venue_key", "")),
        "venue_name": str(record.get("venue_name", "")),
        "event_name": str(record.get("event_name", "")),
        "event_date": str(record.get("event_date", "")),
        "hotspots_accurate": bool(record.get("hotspots_accurate", True)),
        "diversions_feasible": bool(record.get("diversions_feasible", True)),
        "corridor_clear": bool(record.get("corridor_clear", True)),
        "officers_deployed": int(record.get("officers_deployed", 0)),
        "officers_recommended": int(record.get("officers_recommended", 0)),
        "missed_incidents": str(record.get("missed_incidents", "")).strip(),
    }
    df_new = pd.DataFrame([row])
    if path.exists():
        try:
            df_old = pd.read_csv(path)
            df_all = pd.concat([df_old, df_new], ignore_index=True)
        except Exception:
            df_all = df_new
    else:
        df_all = df_new
    df_all.to_csv(path, index=False)
    return path


def run_checks(
    res: dict[str, Any] | None,
    venue_key: str | None = None,
    feedback_path: Path | None = None,
) -> dict[str, Any]:
    """
    Run 6 internal consistency & sanity checks on a computed scenario result.
    All reliability scores are labelled ASSUMED until calibrated with real ITMS counts.
    """
    if not res:
        return {
            "checks": [],
            "passed": 0,
            "total": 6,
            "score_pct": 0,
            "calibration_pct": None,
            "calibration_events": 0,
            "overall_pct": 0,
            "status_label": "ASSUMED",
        }

    params = res.get("params", {})
    dem = res.get("demand", {})
    so = res.get("sum_opt", {})
    sn = res.get("sum_naive", {})
    corridor = res.get("corridor")
    hotspots = res.get("hotspots", pd.DataFrame())
    diversions = res.get("diversions", [])

    checks: list[dict[str, Any]] = []

    # 1. Optimised V/C <= Naive V/C
    opt_vc = float(so.get("max_vc", 0.0))
    naive_vc = float(sn.get("max_vc", 0.0))
    c1_pass = opt_vc <= naive_vc + 1e-6
    checks.append({
        "id": 1,
        "name_en": "Optimised routing improves or matches naive V/C",
        "name_te": "ఆప్టిమైజ్డ్ రూటింగ్ సాధారణ రూటింగ్ కంటే మెరుగ్గా ఉంది",
        "passed": c1_pass,
        "detail": f"Opt {opt_vc:.2f} vs Naive {naive_vc:.2f}",
    })

    # 2. Demand balance: sum of mode persons within 5% of attendance
    attendance = int(params.get("attendance", 0) or 0)
    persons_sum = sum(float(v) for v in dem.get("persons", {}).values())
    tol = max(1.0, attendance * 0.05)
    c2_pass = attendance > 0 and abs(persons_sum - attendance) <= tol
    checks.append({
        "id": 2,
        "name_en": "Demand balance matches expected attendance (±5%)",
        "name_te": "మొత్తం ప్రయాణికుల సంఖ్య అంచనా హాజరుతో సరిపోలింది (±5%)",
        "passed": c2_pass,
        "detail": f"{persons_sum:,.0f} vs {attendance:,}",
    })

    # 3. Emergency corridor: Free-flow ETA < Unprotected ETA
    if corridor:
        free_m = float(corridor.get("free_min", 0.0))
        unprot_m = float(corridor.get("unprotected_min", 0.0))
        c3_pass = free_m < unprot_m
        c3_detail = f"Clear {free_m} min vs Congested {unprot_m} min"
    else:
        c3_pass = True
        c3_detail = "No hospital corridor in 12 km radius (skipped)"
    checks.append({
        "id": 3,
        "name_en": "Green corridor saves time vs congested traffic",
        "name_te": "గ్రీన్ కారిడార్ సాధారణ ట్రాఫిక్ కంటే వేగంగా ఉంది",
        "passed": c3_pass,
        "detail": c3_detail,
    })

    # 4. Hotspot detection: at least 1 hotspot per 10,000 crowd (when crowd >= 10,000)
    expected_hs = max(1, attendance // 10000)
    found_hs = len(hotspots) if isinstance(hotspots, pd.DataFrame) else 0
    c4_pass = found_hs >= min(expected_hs, 5)
    checks.append({
        "id": 4,
        "name_en": "Hotspot detection covers crowd scale",
        "name_te": "జనసమూహ స్థాయికి తగిన రద్దీ కేంద్రాలు గుర్తించబడ్డాయి",
        "passed": c4_pass,
        "detail": f"{found_hs} hotspots found (target ≥ {min(expected_hs, 5)})",
    })

    # 5. Diversion feasibility: >= 50% feasible (or no congested roads needing diversion)
    if diversions:
        feasible_cnt = sum(1 for d in diversions if d.get("feasible"))
        feas_pct = feasible_cnt / len(diversions) * 100.0
        c5_pass = feas_pct >= 50.0
        c5_detail = f"{feasible_cnt}/{len(diversions)} feasible ({feas_pct:.0f}%)"
    else:
        c5_pass = int(so.get("congested", 0)) == 0
        c5_detail = "No diversions needed" if c5_pass else "No diversions found"
    checks.append({
        "id": 5,
        "name_en": "At least 50% of diversions are physically feasible",
        "name_te": "కనీసం 50% మళ్లింపు మార్గాలు ఆచరణాత్మకంగా ఉన్నాయి",
        "passed": c5_pass,
        "detail": c5_detail,
    })

    # 6. Peak traffic bucket timing sanity
    start_m = _hhmm_to_minutes(params.get("start_time", "19:30"))
    peak_m = _hhmm_to_minutes(dem.get("peak_bucket", ""))
    phase = str(params.get("phase", "ingress")).lower()
    if start_m is not None and peak_m is not None:
        diff = peak_m - start_m
        if phase == "ingress":
            c6_pass = -60 <= diff <= 30
        else:
            c6_pass = -30 <= diff <= 240
        c6_detail = f"Peak {dem.get('peak_bucket')} vs Start {params.get('start_time')} ({phase})"
    else:
        c6_pass = False
        c6_detail = "Missing peak/start time"
    checks.append({
        "id": 6,
        "name_en": "Peak 15-min bucket aligns with event timing",
        "name_te": "గరిష్ట రద్దీ సమయం ఈవెంట్ సమయంతో సరిపోలింది",
        "passed": c6_pass,
        "detail": c6_detail,
    })

    passed = sum(1 for c in checks if c["passed"])
    score_pct = round(passed / 6 * 100)

    # Venue calibration from post_event_feedback.csv if available
    cal_pct: float | None = None
    cal_events = 0
    fb_df = load_post_event_feedback(feedback_path)
    if not fb_df.empty and venue_key and "venue_key" in fb_df.columns:
        v_df = fb_df[fb_df["venue_key"].astype(str) == str(venue_key)]
        if not v_df.empty:
            cal_events = len(v_df)
            scores = []
            for _, row in v_df.iterrows():
                pts = (
                    int(bool(row.get("hotspots_accurate", False)))
                    + int(bool(row.get("diversions_feasible", False)))
                    + int(bool(row.get("corridor_clear", False)))
                )
                scores.append(pts / 3.0 * 100.0)
            cal_pct = round(sum(scores) / len(scores))

    overall_pct = round(score_pct * 0.7 + cal_pct * 0.3) if cal_pct is not None else score_pct

    return {
        "checks": checks,
        "passed": passed,
        "total": 6,
        "score_pct": score_pct,
        "calibration_pct": cal_pct,
        "calibration_events": cal_events,
        "overall_pct": overall_pct,
        "status_label": "ASSUMED",
    }
