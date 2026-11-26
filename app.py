"""
Traffic Event Co-Pilot — Gemini-style Agentic AI Interface (Greater Hyderabad Police).
Run: streamlit run app.py
"""
import importlib
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))
import event_engine as E  # noqa: E402
from map_view import make_map  # noqa: E402
import venue_catalog as VC  # noqa: E402
import groq_chatbot as GC  # noqa: E402
import ui_theme as UI  # noqa: E402
importlib.reload(UI)
import plan_checker as CHK  # noqa: E402
import wizard as WIZ  # noqa: E402
importlib.reload(WIZ)
import prediction_engine as PE  # noqa: E402
import operational_engine as OE  # noqa: E402
import traffic_profiles as TP  # noqa: E402
import osm_download as OD  # noqa: E402
from translations import t, get_sipoc_df, build_telugu_report  # noqa: E402

st.set_page_config(
    page_title="Traffic Event Co-Pilot",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="collapsed",
)
UI.inject_css()


@st.cache_resource(show_spinner="Loading road network...")
def get_network(network_path_str: str | None = None):
    p = Path(network_path_str) if network_path_str else E.GRAPH_PATH
    return E.build_network(p)


@st.cache_data(show_spinner=False)
def get_pack():
    return E.load_pack()


@st.cache_data(show_spinner="Evaluating scenario presets...")
def get_preset_comparison(_D, venue_key, venue_latlon, hospital_latlon, pack=None):
    presets = [
        {"Preset": "IPL weeknight 19:30 ingress", "params": {"attendance": 39000, "start_time": "19:30", "phase": "ingress", "duration_h": 3.0, "shift_pct": 0.0, "event_name": "IPL Weeknight"}},
        {"Preset": "IPL weekend 15:30 ingress", "params": {"attendance": 39000, "start_time": "15:30", "phase": "ingress", "duration_h": 3.0, "shift_pct": 0.0, "event_name": "IPL Weekend"}},
        {"Preset": "Same weekend match egress", "params": {"attendance": 39000, "start_time": "15:30", "phase": "egress", "duration_h": 3.0, "shift_pct": 0.0, "event_name": "IPL Weekend Egress"}},
        {"Preset": "20% metro shift", "params": {"attendance": 39000, "start_time": "19:30", "phase": "ingress", "duration_h": 3.0, "shift_pct": 20.0, "event_name": "20% Metro Shift"}},
    ]
    rows = []
    for p in presets:
        res_p = E.run_scenario(_D, {**p["params"], "venue_latlon": venue_latlon, "hospital_latlon": hospital_latlon}, pack)
        rows.append({
            "Scenario Preset": p["Preset"],
            "Vehicles": f"{res_p['demand']['total_vehicles']:,}",
            "Peak PCU/hour": f"{round(res_p['demand']['peak_hourly_pcu']):,}",
            "Max V/C": f"{res_p['sum_opt']['max_vc']:.2f}",
            "Roads over capacity": res_p["sum_opt"]["congested"],
        })
    return pd.DataFrame(rows)


PACK = get_pack()
EVENTS = E.event_options(PACK)

# ------------------------------------------------------------------ Top Gemini-style Navigation Bar
nav_l, nav_lang, nav_new, nav_tune = st.columns([0.52, 0.20, 0.14, 0.14])
with nav_lang:
    lang = st.radio(
        "Language",
        ["English", "తెలుగు"],
        horizontal=True,
        index=0 if st.session_state.get("lang", "English") == "English" else 1,
        label_visibility="collapsed",
        key="lang_selector",
    )
    st.session_state["lang"] = lang
is_te = lang == "తెలుగు"

with nav_l:
    brand = "🚦 ట్రాఫిక్ ఈవెంట్ కో-పైలట్" if is_te else "🚦 Traffic Event Co-Pilot"
    st.markdown(f"<div style='font-size:1.15rem;font-weight:700;padding-top:0.3rem;'>{brand}</div>", unsafe_allow_html=True)

with nav_new:
    if st.session_state.get("plan_ready"):
        new_lbl = "✨ కొత్త ఈవెంట్" if is_te else "✨ New Event"
        if st.button(new_lbl, use_container_width=True, key="nav_new_event"):
            st.session_state["plan_ready"] = False
            st.session_state["wizard_step"] = 0
            st.rerun()

with nav_tune:
    tune_lbl = "⚙️ సెట్టింగ్స్" if is_te else "⚙️ Tuning"
    with st.popover(tune_lbl, use_container_width=True):
        private_pct = st.slider(
            "స్వంత/అద్దె వాహనాల శాతం (%)" if is_te else "Private/hired vehicle share (%)",
            20, 90, st.session_state.get("private_pct", 60), key="tune_private"
        )
        shift_pct = st.slider(
            "మెట్రోకు మళ్లింపు (%)" if is_te else "What-if metro shift (%)",
            0, 40, st.session_state.get("shift_pct", 0), key="tune_shift"
        )
        st.session_state["private_pct"] = private_pct
        st.session_state["shift_pct"] = shift_pct
        demo_mode = st.checkbox("డెమో మోడ్" if is_te else "Demo mode", value=False, key="tune_demo")
        if st.session_state.get("plan_ready") and st.button("🔁 Re-run Plan" if not is_te else "🔁 మళ్ళీ లెక్కించండి", type="primary", use_container_width=True):
            st.session_state["force_retry"] = True
            st.rerun()

# ------------------------------------------------------------------ PHASE 1: Gemini-style Guided Onboarding
if not st.session_state.get("plan_ready", False):
    wiz_out = WIZ.render_wizard(EVENTS, lang=lang)
    if isinstance(wiz_out, dict):
        st.session_state["wizard_override"] = wiz_out
        st.session_state["plan_ready"] = True
        st.session_state["force_retry"] = True
        st.rerun()
    st.stop()

# ------------------------------------------------------------------ PHASE 2: Compute & Display Active Plan
wiz = st.session_state.get("wizard_override", {})
suggestions = VC.get_hyderabad_location_suggestions()
selected_loc_name = wiz.get("venue_name", "Rajiv Gandhi International Cricket Stadium, Uppal")
venue_info = suggestions.get(selected_loc_name, next(iter(suggestions.values())))
venue_coords = (venue_info["lat"], venue_info["lon"])
venue_key = venue_info.get("key", "uppal_stadium")
event_name = wiz.get("event_name", "SRH IPL Match 2026")
event_type = wiz.get("event_type", "Cricket / Sports Match")
event_date = wiz.get("event_date", pd.to_datetime("2026-04-15").date())
start_time = wiz.get("start_time", "19:30")
attendance = int(wiz.get("attendance", venue_info.get("capacity", 39000)))
phase = wiz.get("phase", "ingress")

_hosp = VC.nearest_hospital(venue_coords[0], venue_coords[1])
hospital_latlon = (float(_hosp["Latitude"]), float(_hosp["Longitude"])) if _hosp else None

_params = {
    "attendance": attendance,
    "start_time": start_time,
    "phase": phase,
    "mode_share": E.mode_share_with_private_total(st.session_state.get("private_pct", 60) / 100),
    "approach_share": dict(E.DEFAULT_APPROACH_SHARE),
    "shift_pct": float(st.session_state.get("shift_pct", 0)),
    "event_date": event_date,
    "event_name": event_name,
    "venue_latlon": venue_coords,
    "hospital_latlon": hospital_latlon,
    "venue_name": selected_loc_name,
    "event_type": event_type,
}

_force = st.session_state.pop("force_retry", False)
if _force or "res" not in st.session_state:
    try:
        net_path = VC.get_road_network_path(venue_key, venue_coords[0], venue_coords[1], force_retry=_force)
        D, NET = get_network(str(net_path))
        st.session_state["active_D"] = D
        st.session_state["active_NET"] = NET
        st.session_state["active_venue_key"] = venue_key
        with st.spinner("Generating AI traffic plan..." if not is_te else "ట్రాఫిక్ ప్రణాళిక రూపొందించబడుతోంది..."):
            st.session_state["res"] = E.run_scenario(D, _params, PACK)
            st.session_state["chat_event_name"] = event_name
            st.session_state["chat_lang"] = lang
            st.session_state["chat_history"] = [{"role": "assistant", "content": GC.greeting(event_name, lang)}]
    except OD.NetworkUnavailable as exc:
        st.error(f"Road network unavailable for **{selected_loc_name}**: {exc}")
        if st.button("🔄 Retry"):
            st.session_state["force_retry"] = True
            st.rerun()
        st.stop()

res = st.session_state["res"]
D = st.session_state["active_D"]
NET = st.session_state["active_NET"]
dem, so, sn = res["demand"], res["sum_opt"], res["sum_naive"]
conf = CHK.run_checks(res, venue_key=venue_key)
ops = OE.compute_operational_decisions(D, res, venue_key=venue_key)

# Event summary header
st.caption(
    f"📍 **{selected_loc_name}** · 🎪 **{event_name}** ({event_type}) · 👥 **{attendance:,}** · 📅 {event_date} {start_time} ({phase})"
)

# Data status + Confidence Score row
ds1, ds2, ds3, ds4 = st.columns(4)
ds1.success(t("real_status", lang))
ds2.warning(t("assumed_status", lang))
ds3.error(t("missing_status", lang))
ds4.info(
    f"🛡️ **{'విశ్వసనీయత' if is_te else 'Reliability'}:** {conf['overall_pct']}% ({conf['passed']}/{conf['total']} · ASSUMED)"
)

# ------------------------------------------------------------------ 40% AI CHAT | 60% MAP & PLAN
chat_col, work_col = st.columns([0.40, 0.60], gap="large")

with chat_col:
    st.markdown("### " + ("💬 ఏఐ కో-పైలట్ చాట్" if is_te else "💬 AI Co-Pilot Chat"))
    if st.session_state.get("chat_event_name") != event_name or st.session_state.get("chat_lang") != lang:
        st.session_state["chat_event_name"] = event_name
        st.session_state["chat_lang"] = lang
        st.session_state["chat_history"] = [{"role": "assistant", "content": GC.greeting(event_name, lang)}]

    qc1, qc2 = st.columns(2)
    quick_q = None
    if qc1.button(t("btn_bottlenecks", lang), key="q_btn_1", use_container_width=True):
        quick_q = "కీలక రద్దీ కేంద్రాలు ఏవి?" if is_te else "What are the critical bottlenecks?"
    if qc2.button(t("btn_diversions", lang), key="q_btn_2", use_container_width=True):
        quick_q = "ట్రాఫిక్ మళ్లింపు మార్గాలను వివరించండి" if is_te else "Explain the diversion scheme"
    if qc1.button(t("btn_emergency", lang), key="q_btn_3", use_container_width=True):
        quick_q = "అత్యవసర గ్రీన్ కారిడార్ మార్గం మరియు సమయం ఎంత?" if is_te else "What is the emergency corridor route and ETA?"
    if qc2.button(t("btn_deployment", lang), key="q_btn_4", use_container_width=True):
        quick_q = "పోలీసు సిబ్బంది మోహరింపు సిఫార్సు ఏమిటి?" if is_te else "What is the recommended police personnel deployment?"

    chat_box = st.container(height=450)
    with chat_box:
        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and msg.get("source"):
                    st.caption(GC.source_badge(msg["source"], lang))

    with st.form("workspace_chat_form", clear_on_submit=True):
        fc1, fc2 = st.columns([0.82, 0.18])
        user_q = fc1.text_input(
            "Ask",
            placeholder="ఏదైనా అడగండి..." if is_te else "Ask anything about this plan...",
            label_visibility="collapsed",
        )
        sent = fc2.form_submit_button("➤", use_container_width=True)

    active_q = quick_q or (user_q.strip() if sent and user_q.strip() else None)
    if active_q:
        st.session_state["chat_history"].append({"role": "user", "content": active_q})
        ans, src = GC.generate_response(active_q, res, lang=lang, chat_history=st.session_state["chat_history"])
        st.session_state["chat_history"].append({"role": "assistant", "content": ans, "source": src})
        st.rerun()

with work_col:
    ev_dt = res["params"].get("event_date")
    show_post = ev_dt is not None and date.today() > ev_dt
    tab_names = [
        "🗺️ మ్యాప్ & అంచనాలు" if is_te else "🗺️ Map & Predictions",
        "📋 12-విభాగాల ప్రణాళిక" if is_te else "📋 12-Section Plan",
        "🔍 SIPOC & డేటా" if is_te else "🔍 SIPOC & Inputs",
    ]
    if show_post:
        tab_names.append("📝 సమీక్ష" if is_te else "📝 Post-Event Review")
        wt1, wt2, wt3, wt4 = st.tabs(tab_names)
    else:
        wt1, wt2, wt3 = st.tabs(tab_names)
        wt4 = None

    with wt1:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(t("metric_vehicles", lang), f"{dem['total_vehicles']:,}")
        m2.metric(t("metric_peak_pcu", lang), f"{dem['peak_hourly_pcu']:,.0f}")
        m3.metric(t("metric_max_vc", lang), f"{so['max_vc']:.2f}", f"{so['max_vc'] - sn['max_vc']:+.2f}", delta_color="inverse")
        m4.metric(t("metric_roads_over_cap", lang), so["congested"], f"{so['congested'] - sn['congested']:+d}", delta_color="inverse")

        mc1, mc2 = st.columns([0.65, 0.35])
        view = mc1.radio(
            t("map_view_label", lang),
            ["Co-Pilot (optimised)", "Naive shortest path"],
            horizontal=True,
        )
        show_signals = mc2.checkbox("🚦 Signals [SIGNAL]" if not is_te else "🚦 సిగ్నల్స్ [SIGNAL]", value=True)
        try:
            from streamlit_folium import st_folium
            st_folium(
                make_map(D, res, use_naive=view.startswith("Naive"), signals=ops["signals"] if show_signals else None),
                height=420,
                use_container_width=True,
                returned_objects=[],
            )
        except Exception as exc:
            st.warning(f"Map could not be drawn: {exc}")

        st.markdown("#### " + ("🤖 AI ట్రాఫిక్ అంచనా (+15/30/60 నిమి · ASSUMED)" if is_te else "🤖 AI Traffic Prediction (+15/30/60 min · ASSUMED)"))
        pc1, pc2, pc3 = st.columns([0.42, 0.28, 0.30])
        horizon_min = pc1.radio("Horizon" if not is_te else "సమయం", [15, 30, 60], index=1, format_func=lambda x: f"+{x}m", horizontal=True)
        weather_sel = pc2.selectbox("Weather" if not is_te else "వాతావరణం", ["clear", "rain", "fog"], index=0)
        pred_out = PE.predict_traffic(res, minutes_ahead=horizon_min, weather=weather_sel)
        if pc3.button("💾 Save Heatmap" if not is_te else "💾 హీట్‌మ్యాప్ సేవ్", use_container_width=True):
            hm_p = PE.save_heatmap_json(res, venue_key=venue_key, weather=weather_sel)
            st.success(f"Saved `{hm_p.name}`")
        if pred_out["rows"]:
            st.dataframe(pd.DataFrame([
                {
                    "Tag": r["tag"],
                    "Location": r["location"],
                    "Now": r["now_te"] if is_te else r["now_en"],
                    f"+{horizon_min}m": r["pred_te"] if is_te else r["pred_en"],
                    "V/C Now": r["vc_now"],
                    f"V/C +{horizon_min}m": r["vc_pred"],
                }
                for r in pred_out["rows"]
            ]), hide_index=True, use_container_width=True)

    with wt2:
        base_rep = build_telugu_report(res) if is_te else res["report"]
        full_rep = OE.build_12_section_report(base_rep, ops, res, conf, lang=lang)
        d1, d2, d3 = st.columns(3)
        d1.download_button(t("dl_md", lang), full_rep, f"traffic_plan_{event_name}.md", use_container_width=True)
        d2.download_button(t("dl_txt", lang), full_rep.replace("#", "").replace("**", ""), f"traffic_plan_{event_name}.txt", use_container_width=True)
        d3.download_button(t("dl_csv", lang), res["table_opt"].to_csv(index=False), "hotspots.csv", use_container_width=True)
        st.markdown(full_rep)

    with wt3:
        st.dataframe(get_sipoc_df(lang=lang), hide_index=True, use_container_width=True)
        with st.expander("🛡️ " + ("6 అంతర్గత విశ్వసనీయత తనిఖీలు" if is_te else "6 Internal Reliability Checks")):
            for chk in conf["checks"]:
                st.write(f"{'✅' if chk['passed'] else '❌'} **{chk['name_te'] if is_te else chk['name_en']}** — `{chk['detail']}`")
        comp_df = get_preset_comparison(D, venue_key, tuple(venue_coords), hospital_latlon, PACK)
        st.dataframe(comp_df, hide_index=True, use_container_width=True)

    if wt4 is not None:
        with wt4:
            with st.form("post_event_review_form"):
                q1 = st.radio("1. Were predicted hotspots congested?" if not is_te else "1. అంచనా వేసిన రద్దీ రోడ్లు నిజంగానే రద్దీగా ఉన్నాయా?", ["Yes", "No"], horizontal=True)
                q2 = st.radio("2. Were diversions implementable?" if not is_te else "2. మళ్లింపులు అమలు చేయగలిగారా?", ["Yes", "No"], horizontal=True)
                q3 = st.radio("3. Did emergency corridor stay clear?" if not is_te else "3. అత్యవసర కారిడార్ క్లియర్‌గా ఉందా?", ["Yes", "No"], horizontal=True)
                rec_off = max(10, int(round(attendance / 500)))
                q4 = st.slider("4. Officers deployed" if not is_te else "4. మోహరించిన సిబ్బంది", 5, 500, min(500, rec_off))
                q5 = st.text_area("5. Any missed incident?" if not is_te else "5. ఇతర సంఘటనలు?")
                if st.form_submit_button("💾 Save Review" if not is_te else "💾 సమీక్ష సేవ్ చేయండి", type="primary"):
                    CHK.save_post_event_feedback({
                        "venue_key": venue_key, "venue_name": selected_loc_name,
                        "event_name": event_name, "event_date": str(ev_dt),
                        "hotspots_accurate": q1 == "Yes", "diversions_feasible": q2 == "Yes",
                        "corridor_clear": q3 == "Yes", "officers_deployed": q4,
                        "officers_recommended": rec_off, "missed_incidents": q5,
                    })
                    st.success("✅ Saved!" if not is_te else "✅ సేవ్ చేయబడింది!")
