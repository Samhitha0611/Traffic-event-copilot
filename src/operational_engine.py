"""
Operational Decisions Engine (Step 3 - Module 3C).
Produces:
- Road closures [CLOSE]
- Staged diversion timeline (T-90 to T+120)
- Barricades & personnel deployment [B]
- Emergency primary [E-1], backup [E-2], Ambulance [ES-AMB], Fire [ES-FIRE]
- Full 12-section bilingual operational plan markdown
"""
from __future__ import annotations

from typing import Any

import pandas as pd

import prediction_engine as PE
import pedestrian_model as PM
import signal_layer as SL


def compute_operational_decisions(
    D: dict[str, Any] | None,
    res: dict[str, Any],
    venue_key: str = "uppal_stadium",
    weather: str = "clear",
) -> dict[str, Any]:
    """Compute all Module 3A/3B/3C operational intelligence outputs for a scenario."""
    hotspots = res.get("hotspots", pd.DataFrame())
    diversions = res.get("diversions", [])
    corridor = res.get("corridor")
    params = res.get("params", {})
    attendance = int(params.get("attendance", 0) or 0)

    # 1. Road closures [CLOSE]
    closures: list[dict[str, str]] = []
    if isinstance(hotspots, pd.DataFrame) and not hotspots.empty:
        infeasible = {str(d.get("name", "")).lower() for d in diversions if not d.get("feasible")}
        for _, hr in hotspots.head(6).iterrows():
            sname = str(hr.get("street", ""))
            vc = float(hr.get("vc", 0.0))
            rtype = str(hr.get("road_type", "")).lower()
            if vc > 1.5 or sname.lower() in infeasible or "residential" in rtype:
                reason_en = (
                    "V/C > 1.5 with no feasible detour"
                    if vc > 1.5 or sname.lower() in infeasible
                    else "Residential lane near venue — pedestrian-only zone"
                )
                reason_te = (
                    "V/C > 1.5 మరియు ప్రత్యామ్నాయ మళ్లింపు లేదు"
                    if vc > 1.5 or sname.lower() in infeasible
                    else "వేదిక సమీప నివాస రహదారి — పాదచారులకు మాత్రమే"
                )
                closures.append({
                    "tag": f"[CLOSE-{len(closures) + 1}]",
                    "street": sname,
                    "vc": f"{vc:.2f}",
                    "window": "T-60 min to T+120 min",
                    "reason_en": reason_en,
                    "reason_te": reason_te,
                })

    # 2. Barricades & Personnel [B]
    barricades: list[dict[str, Any]] = []
    if isinstance(hotspots, pd.DataFrame) and not hotspots.empty:
        for idx, (_, hr) in enumerate(hotspots.head(4).iterrows()):
            barricades.append({
                "tag": f"[B-{idx + 1}]",
                "location": str(hr.get("street", f"Sector {idx + 1}")),
                "type_en": "Hard barricade + 2 Constables (ASSUMED)",
                "type_te": "గట్టి బారికేడ్ + 2 కానిస్టేబుళ్లు (ASSUMED)",
                "deploy_at": "T-30 min",
            })
    if corridor:
        barricades.append({
            "tag": f"[B-{len(barricades) + 1}]",
            "location": "Emergency Corridor [E-1] Entry Gate",
            "type_en": "Hard barricade — Emergency Vehicles ONLY (1 SI + 2 Constables)",
            "type_te": "అత్యవసర వాహనాలకు మాత్రమే ప్రవేశం (1 SI + 2 కానిస్టేబుళ్లు)",
            "deploy_at": "T-90 min",
        })

    # 3. Staged diversion timeline
    staged_timeline = [
        ("T-90 min", "Activate pre-emptive outer diversions & [B] corridor gates", "ముందస్తు మళ్లింపులు & అత్యవసర గేట్లు ప్రారంభం"),
        ("T-60 min", "Activate primary [D] diversions & extend [SIGNAL] green phases", "ప్రధాన [D] మళ్లింపులు & సిగ్నల్ మార్పులు అమలు"),
        ("T-30 min", "Deploy physical barricades [B] and full [CLOSE] restrictions", "భౌతిక బారికేడ్లు [B] & రోడ్డు మూసివేతలు [CLOSE]"),
        ("T+0 min", "Event starts — full diversion & green corridor active", "ఈవెంట్ ప్రారంభం — పూర్తి బందోబస్తు అమలులో"),
        ("T+90 min", "Gradually release outer diversions; keep [E-1] & [PED] active", "బయటి మళ్లింపులు సడలింపు; [E-1] & [PED] కొనసాగింపు"),
        ("T+120 min", "Lift all diversions and restore normal 90s traffic signals", "అన్ని మళ్లింపులు ఎత్తివేత, సాధారణ ట్రాఫిక్ పునరుద్ధరణ"),
    ]

    # 4. Prediction + Signals + Pedestrian
    pred_30 = PE.predict_traffic(res, minutes_ahead=30, weather=weather)
    signals = SL.extract_signals(D, res, venue_key=venue_key)
    ped = PM.build_pedestrian_plan(res)

    # 5. Deployment totals (ASSUMED ratios)
    total_officers = max(12, int(round(attendance / 500)))

    return {
        "closures": closures,
        "barricades": barricades,
        "staged_timeline": staged_timeline,
        "prediction": pred_30,
        "signals": signals,
        "pedestrian": ped,
        "total_officers": total_officers,
    }


def build_12_section_report(
    base_report: str,
    ops: dict[str, Any],
    res: dict[str, Any],
    conf: dict[str, Any],
    lang: str = "English",
) -> str:
    """
    Append Step 3 operational intelligence sections (Closures, Staged Diversions,
    Barricades, Ambulance/Fire [ES], Signals [SIGNAL], Pedestrian [PED],
    AI Predictions, and Confidence Score) onto the base 8-section plan to form
    the complete 12-section operational plan.
    """
    is_te = lang == "తెలుగు"
    L = [base_report, "\n---"]

    # Road Closures [CLOSE]
    L.append("\n## ⛔ " + ("సూచించిన రోడ్డు మూసివేతలు [CLOSE]" if is_te else "Recommended Road Closures [CLOSE]"))
    if ops["closures"]:
        for cl in ops["closures"]:
            reason = cl["reason_te"] if is_te else cl["reason_en"]
            L.append(f"- **{cl['tag']} {cl['street']}** (V/C `{cl['vc']}`): {cl['window']} — {reason}")
    else:
        L.append("- " + ("పూర్తి రోడ్డు మూసివేతలు అవసరం లేదు; మళ్లింపులు సరిపోతాయి." if is_te else "No full closures needed; diversions are sufficient."))

    # Staged Diversion Timeline
    L.append("\n## 🔀 " + ("దశలవారీ మళ్లింపు సమయపాలన (Staged Diversion Timeline)" if is_te else "Staged Diversion Activation Timeline"))
    for tm, en_txt, te_txt in ops["staged_timeline"]:
        L.append(f"- **{tm}:** {te_txt if is_te else en_txt}")

    # Barricades & Personnel [B]
    L.append("\n## 🚧 " + ("బారికేడ్లు & పోలీసు మోహరింపు [B] (ASSUMED)" if is_te else "Barricade & Personnel Deployment [B] (ASSUMED)"))
    L.append(f"- **{'అంచనా మొత్తం సిబ్బంది' if is_te else 'Estimated total personnel'}:** ~{ops['total_officers']} officers (ASSUMED 1 per 500 crowd)")
    for b in ops["barricades"]:
        btype = b["type_te"] if is_te else b["type_en"]
        L.append(f"- **{b['tag']} {b['location']}** — {btype} ({b['deploy_at']})")

    # Ambulance & Fire Routes [ES-AMB] / [ES-FIRE]
    L.append("\n## 🚑 " + ("అంబులెన్స్ [ES-AMB] & ఫైర్ సర్వీస్ [ES-FIRE] మార్గాలు" if is_te else "Emergency Ambulance [ES-AMB] & Fire Routes [ES-FIRE]"))
    corr = res.get("corridor")
    if corr:
        L.append(
            f"- **[ES-AMB] Primary [E-1]:** {corr['length_m']:,} m · {corr['free_min']} min clear vs {corr['unprotected_min']} min congested."
        )
        L.append(
            f"- **[ES-FIRE] Backup [E-2]:** " + (
                "బారికేడ్లు [B] లేని రింగ్ రోడ్డు / ప్రత్యామ్నాయ మార్గం ద్వారా ఫైర్ ఇంజన్ల రాకపోకలు క్లియర్ ఉంచండి (ASSUMED)."
                if is_te
                else "Keep outer arterial bypass avoiding all [B] hard barricades clear for fire tenders (ASSUMED)."
            )
        )
    else:
        L.append("- " + ("12 కి.మీ పరిధిలో ఆసుపత్రి కారిడార్ లేదు." if is_te else "No hospital corridor in 12 km radius."))

    # Traffic Signals [SIGNAL]
    L.append("\n## 🚦 " + ("ట్రాఫిక్ సిగ్నల్ సిఫార్సులు [SIGNAL] (ASSUMED)" if is_te else "Traffic Signal Timing Recommendations [SIGNAL] (ASSUMED)"))
    for sg in ops["signals"][:5]:
        act = sg["action_te"] if is_te else sg["action_en"]
        L.append(f"- **{sg['tag']} {sg['name']}** (V/C `{sg['vc']}`, {sg['cycle_s']}): {act} *({sg['activate']})*")

    # Pedestrian Exit Plan [PED]
    ped = ops["pedestrian"]
    L.append("\n## 🚶 " + ("పాదచారులు & ప్రేక్షకుల నిష్క్రమణ ప్రణాళిక [PED] (ASSUMED)" if is_te else "Pedestrian & Crowd Exit Sequencing [PED] (ASSUMED)"))
    L.append(
        f"- **{'మొత్తం నిష్క్రమణ పాదచారులు' if is_te else 'Estimated exiting pedestrians'}:** ~{ped['total_pedestrians']:,} | "
        f"Flow: {ped['flow_pm_m']} persons/min/m ({'⚠️ CRUSH RISK >50' if ped['crush_risk'] else '✅ Safe <50'})"
    )
    for g in ped["gates"]:
        d_txt = g["direction_te"] if is_te else g["direction_en"]
        L.append(f"- **{g['tag']} {g['time']} — {g['gate']}:** → {d_txt} (~{g['crowd']:,} people, {g['marshals']} marshals)")

    # AI Prediction Summary
    pred = ops["prediction"]
    L.append("\n## 🤖 " + ("AI ట్రాఫిక్ అంచనా (+30 నిమిషాలు · ASSUMED)" if is_te else "AI Traffic Prediction Summary (+30 min · ASSUMED)"))
    for r in pred["rows"][:5]:
        st_lbl = r["pred_te"] if is_te else r["pred_en"]
        L.append(f"- **{r['tag']} {r['location']}:** Now V/C `{r['vc_now']}` → +30 min V/C `{r['vc_30']}` ({st_lbl})")

    # Confidence Score
    L.append(f"\n## 🛡️ {'విశ్వసనీయత స్కోర్' if is_te else 'Plan Confidence Score'}: **{conf['overall_pct']}%** ({conf['passed']}/{conf['total']} checks · ASSUMED)")
    return "\n".join(L)
