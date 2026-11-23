"""
Traffic Event Co-Pilot: SIPOC demo for Uppal Stadium, Hyderabad.
Run:  streamlit run app.py
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))
import event_engine as E  # noqa: E402
from map_view import make_map  # noqa: E402
import venue_catalog as VC  # noqa: E402
import police_chatbot as PC  # noqa: E402
import traffic_profiles as TP  # noqa: E402
import osm_download as OD  # noqa: E402
from translations import t, get_sipoc_df, translate_report_to_telugu, build_telugu_report  # noqa: E402

st.set_page_config(page_title="Traffic Event Co-Pilot", page_icon="🚦", layout="wide")


@st.cache_resource(show_spinner="Loading road network for area...")
def get_network(network_path_str: str | None = None):
    p = Path(network_path_str) if network_path_str else E.GRAPH_PATH
    return E.build_network(p)


@st.cache_data(show_spinner=False)
def get_pack():
    return E.load_pack()


@st.cache_data(show_spinner="Evaluating scenario presets...")
def get_preset_comparison(_D, venue_key, venue_latlon, hospital_latlon, pack=None):
    presets = [
        {
            "Preset": "IPL weeknight 19:30 ingress",
            "params": {"attendance": 39000, "start_time": "19:30", "phase": "ingress", "duration_h": 3.0, "shift_pct": 0.0, "event_name": "IPL Weeknight"}
        },
        {
            "Preset": "IPL weekend 15:30 ingress",
            "params": {"attendance": 39000, "start_time": "15:30", "phase": "ingress", "duration_h": 3.0, "shift_pct": 0.0, "event_name": "IPL Weekend"}
        },
        {
            "Preset": "Same weekend match egress",
            "params": {"attendance": 39000, "start_time": "15:30", "phase": "egress", "duration_h": 3.0, "shift_pct": 0.0, "event_name": "IPL Weekend Egress"}
        },
        {
            "Preset": "20% metro shift",
            "params": {"attendance": 39000, "start_time": "19:30", "phase": "ingress", "duration_h": 3.0, "shift_pct": 20.0, "event_name": "20% Metro Shift"}
        },
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

# ------------------------------------------------------------------ sidebar
# Language Selector (Bilingual: English / తెలుగు) placed on top left corner above Event setup
lang = st.sidebar.radio(
    "🌐 Language / భాష",
    ["English", "తెలుగు"],
    horizontal=True,
    index=0 if st.session_state.get("lang", "English") == "English" else 1,
    key="lang_selector"
)
st.session_state["lang"] = lang
is_te = (lang == "తెలుగు")

st.sidebar.title(t("event_setup", lang))

# Location Auto-Suggest (like Google suggestions)
hyderabad_suggestions = VC.get_hyderabad_location_suggestions()
suggestion_keys = list(hyderabad_suggestions.keys())
location_choices = suggestion_keys + ["+ Custom Address / Coordinates in Hyderabad"]

selected_loc = st.sidebar.selectbox(
    t("location_search", lang),
    location_choices,
    index=0,
    help=t("location_help", lang)
)

venue_coords = None
venue_info = None
if selected_loc == "+ Custom Address / Coordinates in Hyderabad":
    custom_area = st.sidebar.text_input(t("custom_area", lang), "Charminar, Hyderabad")
    c_lat = st.sidebar.number_input(t("latitude", lang), value=17.3616, format="%.6f")
    c_lon = st.sidebar.number_input(t("longitude", lang), value=78.4747, format="%.6f")
    venue_coords = (float(c_lat), float(c_lon))
    st.sidebar.caption("Custom Sector Checkpoint")
    default_capacity = 25000
    selected_loc_name = custom_area
    venue_key = f"custom_{abs(int(c_lat*100))}_{abs(int(c_lon*100))}"
else:
    venue_info = hyderabad_suggestions[selected_loc]
    venue_coords = (venue_info["lat"], venue_info["lon"])
    default_capacity = venue_info["capacity"]
    venue_key = venue_info.get("key", "uppal_stadium")
    jur_lbl = t("jurisdiction", lang)
    area_lbl = t("area", lang)
    st.sidebar.caption(f"{jur_lbl}: **{venue_info['commissionerate']}** | {area_lbl}: {venue_info['area']}")
    selected_loc_name = selected_loc

# Nearest known hospital for the emergency corridor (never an invented one)
_hosp = VC.nearest_hospital(venue_coords[0], venue_coords[1])
hospital_latlon = (float(_hosp["Latitude"]), float(_hosp["Longitude"])) if _hosp else None
if _hosp:
    st.sidebar.caption(f"{t('hosp_corridor_label', lang)}: **{_hosp['Hospital_Name']}** ({_hosp['Distance_km']} km away)")
else:
    st.sidebar.warning(t("no_hosp_warning", lang))

st.sidebar.markdown("---")
st.sidebar.markdown(f"### {t('event_details_hdr', lang)}")
event_name = st.sidebar.text_input(t("event_name_lbl", lang), value="SRH IPL Match 2026")
event_type = st.sidebar.selectbox(
    t("event_cat_lbl", lang),
    ["Cricket / Sports Match", "Concert / Music Show", "Political Rally / Gathering",
     "Exhibition / Trade Fair", "Marathon / Festival", "VIP Movement / Conference"],
    index=0
)
event_date = st.sidebar.date_input(t("event_date_lbl", lang), value=pd.to_datetime("2026-04-15").date())
start_time = st.sidebar.text_input(t("start_time_lbl", lang), "19:30")
attendance_lbl = f"Expected Attendance / Crowd (అంచనా ప్రేక్షకులు - ASSUMED ~{default_capacity:,})" if is_te else f"Expected Attendance / Crowd (ASSUMED capacity ~{default_capacity:,})"
attendance = st.sidebar.number_input(attendance_lbl, 1000, 150000, default_capacity, 1000)
phase_opts = ["ingress", "egress"]
phase_fmt = (lambda x: "రాక (ingress)" if x == "ingress" else "నిష్క్రమణ (egress)") if is_te else (lambda x: x)
phase = st.sidebar.radio(t("phase_lbl", lang), phase_opts, format_func=phase_fmt, horizontal=True,
                         help="ingress = people arriving before the event, egress = leaving after it")
private = st.sidebar.slider(t("private_veh_share", lang), 20, 90, 60)
shift = st.sidebar.slider(t("metro_shift_slider", lang), 0, 40, 0)
with st.sidebar.expander(t("approach_shares_hdr", lang)):
    shares = {k: st.slider(k, 0, 50, int(v * 100)) for k, v in E.DEFAULT_APPROACH_SHARE.items()}
demo_lbl = "Demo mode (డెమో మోడ్)" if is_te else "Demo mode"
demo_mode = st.sidebar.checkbox(demo_lbl, value=False, help=t("demo_mode_help", lang))
run_lbl = "▶ Run Co-Pilot (కో-పైలట్ అమలు చేయండి)" if is_te else "▶ Run Co-Pilot"
run = st.sidebar.button(run_lbl, type="primary")

# Turn-back points missing coordinates (sidebar note)
manual_df = E.load_manual_locations()
if not manual_df.empty and "Type" in manual_df.columns:
    tb_mask = manual_df["Type"].astype(str).str.strip().str.lower() == "turnback"
    tb_rows = manual_df[tb_mask]
    missing_tb = []
    for _, r in tb_rows.iterrows():
        lat = r.get("Latitude")
        lon = r.get("Longitude")
        if pd.isna(lat) or pd.isna(lon) or str(lat).strip() == "" or str(lon).strip() == "":
            missing_tb.append(str(r.get("Location", "")).strip())
    if missing_tb:
        st.sidebar.markdown("---")
        with st.sidebar.expander(f"⚠️ Turn-backs without coordinates ({len(missing_tb)})", expanded=True):
            st.caption("These turn-back points lack coordinates and are skipped on the map until filled:")
            for item in missing_tb:
                st.write(f"• {item}")

_params = {
    "attendance": int(attendance), "start_time": start_time, "phase": phase,
    "mode_share": E.mode_share_with_private_total(private / 100),
    "approach_share": {k: v / 100 for k, v in shares.items()}, "shift_pct": float(shift),
    "event_date": event_date,
    "event_name": event_name,
    "venue_latlon": venue_coords,
    "hospital_latlon": hospital_latlon,
    "venue_name": selected_loc_name,
    "event_type": event_type,
}

# Parameter signature: only recompute when Run Co-Pilot is explicitly clicked or on initial load
_sig = repr((venue_key, tuple(venue_coords), sorted((k, str(v)) for k, v in _params.items())))

_force = st.session_state.pop("force_retry", False)
is_initial = "res" not in st.session_state
should_run = run or is_initial or _force

if should_run:
    try:
        net_path = VC.get_road_network_path(venue_key, venue_coords[0], venue_coords[1], force_retry=_force)
        D, NET = get_network(str(net_path))
        st.session_state["active_D"] = D
        st.session_state["active_NET"] = NET
        st.session_state["active_venue_key"] = venue_key
        st.session_state["active_loc_name"] = selected_loc_name
        st.session_state["active_event_name"] = event_name
        st.session_state["active_event_type"] = event_type
        with st.spinner(f"Computing tactical traffic plan for {selected_loc_name}..."):
            st.session_state["res"] = E.run_scenario(D, _params, PACK)
            st.session_state["active_sig"] = _sig
            # Reset chat history for the new event
            st.session_state["chat_event_name"] = event_name
            st.session_state["chat_lang"] = lang
            st.session_state["chat_history"] = [
                {"role": "assistant", "content": t("chat_greeting", lang, event=event_name)}
            ]
    except OD.NetworkUnavailable as exc:
        st.title("Traffic Event Co-Pilot (Greater Hyderabad)")
        st.error(f"Road map for **{selected_loc_name}** is not available yet, so no plan was made "
                 f"(a plan on the wrong roads would be misleading).\n\n{exc}")
        st.markdown("**How to fix (no API key needed):**\n"
                    "1. Connect to another network (mobile hotspot or VPN) and click **Retry** below.\n"
                    "2. Or run once: `py scripts/prepare_city_data.py` on any working network. It saves road maps for every venue.\n"
                    "3. Find out why: `py scripts/diagnose_network.py`.\n"
                    "4. Browser works but Python does not? Export the area from openstreetmap.org/export and run `py scripts/import_osm_file.py` (instructions at the top of that file).")
        if st.button("🔄 Retry download"):
            st.session_state["force_retry"] = True
            st.rerun()
        st.stop()
    except Exception as exc:
        st.error(f"Could not load the road network for {selected_loc_name}: {exc}")
        st.stop()

res = st.session_state["res"]
D = st.session_state["active_D"]
NET = st.session_state["active_NET"]
active_loc_name = st.session_state.get("active_loc_name", selected_loc_name)
active_event_name = st.session_state.get("active_event_name", event_name)
active_event_type = st.session_state.get("active_event_type", event_type)
dem, so, sn = res["demand"], res["sum_opt"], res["sum_naive"]

inputs_changed = (_sig != st.session_state.get("active_sig"))
if inputs_changed:
    st.sidebar.warning(t("pending_changes_sidebar", lang))

# Top Header with Top-Right AI Chat Popover (as per UI specification)
head_col, ai_col = st.columns([0.76, 0.24])
with head_col:
    st.title(t("main_title", lang))
    st.caption(t("main_caption", lang, area=active_loc_name, event=active_event_name, category=active_event_type))
with ai_col:
    st.write("")
    chat_popover = st.popover(t("ai_chat_btn", lang), use_container_width=True)
    with chat_popover:
        st.markdown(f"### {t('ai_chat_btn', lang)}")
        st.caption(t("chatbot_caption", lang))

        ev_name = res["params"].get("event_name", active_event_name)
        if "chat_history" not in st.session_state or st.session_state.get("chat_event_name") != ev_name or st.session_state.get("chat_lang") != lang:
            st.session_state["chat_event_name"] = ev_name
            st.session_state["chat_lang"] = lang
            st.session_state["chat_history"] = [
                {"role": "assistant", "content": t("chat_greeting", lang, event=ev_name)}
            ]

        # Quick prompt buttons
        q_btn_cols = st.columns(2)
        quick_query_top = None
        if q_btn_cols[0].button(t("btn_bottlenecks", lang), key="q1_top"):
            quick_query_top = "కీలక రద్దీ కేంద్రాలు ఏవి?" if is_te else "What are the critical bottlenecks?"
        if q_btn_cols[1].button(t("btn_diversions", lang), key="q2_top"):
            quick_query_top = "ట్రాఫిక్ మళ్లింపు మార్గాలను వివరించండి" if is_te else "Explain the diversion scheme"
        if q_btn_cols[0].button(t("btn_emergency", lang), key="q3_top"):
            quick_query_top = "అత్యవసర గ్రీన్ కారిడార్ మార్గం మరియు సమయం ఎంత?" if is_te else "What is the emergency corridor route and ETA?"
        if q_btn_cols[1].button(t("btn_deployment", lang), key="q4_top"):
            quick_query_top = "పోలీసు సిబ్బంది మోహరింపు సిఫార్సు ఏమిటి?" if is_te else "What is the recommended police personnel deployment?"

        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        with st.form("top_chat_form", clear_on_submit=True):
            f_cols = st.columns([0.80, 0.20])
            user_text_top = f_cols[0].text_input(t("chat_input_ph", lang), placeholder="Ask about bottlenecks, diversions, ETA...", label_visibility="collapsed")
            send_btn = f_cols[1].form_submit_button("➤")

        active_top_q = quick_query_top or (user_text_top if send_btn and user_text_top.strip() else None)
        if active_top_q:
            st.session_state["chat_history"].append({"role": "user", "content": active_top_q})
            ans_top = PC.generate_police_response(active_top_q, res, lang=lang)
            st.session_state["chat_history"].append({"role": "assistant", "content": ans_top})
            st.rerun()

# Data status strip
st.markdown(f"### {t('data_status_hdr', lang)}")
ds1, ds2, ds3 = st.columns(3)
ds1.success(t("real_status", lang))
ds2.warning(t("assumed_status", lang))
ds3.error(t("missing_status", lang))

if inputs_changed:
    st.info(t("pending_changes_banner", lang, location=selected_loc_name, event=event_name))

# Warning badges until real rows exist in data/manual_locations.csv
badges = []
if res.get("hospital_is_placeholder", True):
    badges.append("Hospital is a placeholder (ఆసుపత్రి లొకేషన్ ప్లేస్‌హోల్డర్)" if is_te else "Hospital is a placeholder")
if res.get("parking_is_generated", True):
    badges.append("Parking zones are generated (పార్కింగ్ కేంద్రాలు అల్గారిథమిక్)" if is_te else "Parking zones are generated")

if badges:
    badge_cols = st.columns(len(badges))
    for col, badge_text in zip(badge_cols, badges):
        col.warning(f"⚠️ {badge_text}")

tab_titles = [
    t("tab1_title", lang),
    t("tab2_title", lang),
    t("tab3_title", lang),
    t("tab4_title", lang),
    t("tab5_title", lang),
    t("tab6_title", lang),
]
t1, t2, t3, t4, t5, t6 = st.tabs(tab_titles)

# ------------------------------------------------------------------ 1. SIPOC
with t1:
    if demo_mode:
        st.caption(t("tab1_demo", lang))
    st.subheader(t("tab1_subhdr", lang))
    sipoc = get_sipoc_df(lang=lang)
    st.dataframe(sipoc, hide_index=True)
    c1, c2, c3 = st.columns(3)
    if is_te:
        c1.success("**వాస్తవ డేటా (Real Data)**\n\nOSM రోడ్డు నెట్‌వర్క్\n\nపోలీసు సలహాలు, డైవర్షన్లు\n\nఈవెంట్ తేదీలు, మెట్రో & ఆర్టీసీ బస్సు సర్వీసులు")
        c2.warning("**అనుకోబడినవి (ASSUMED)**\n\nమోడ్ స్ప్లిట్, ఆక్యుపెన్సీ, PCU గుణకాలు\n\nరోడ్డు సామర్థ్యం & వేగం\n\nఅప్రోచ్ షేర్లు, బ్యాక్‌గ్రౌండ్ ట్రాఫిక్, పార్కింగ్ జోన్లు")
        c3.error("**లభించనివి (Missing Data)**\n\nఈవెంట్ రోజుల్లో క్లాసిఫైడ్ వాహనాల కౌంట్లు\n\nలైవ్ వేగం & క్యూ పొడవులు\n\nవాస్తవ ఆసుపత్రి & పార్కింగ్ ఖచ్చిత కోఆర్డినేట్లు")
    else:
        c1.success("**Real data used**\n\nOSM road network\n\nPolice advisories and diversions\n\nEvent dates, metro and bus provisions")
        c2.warning("**Assumed (labelled in the app)**\n\nMode split, occupancy, PCU factors\n\nRoad capacity and speeds\n\nApproach shares, background traffic, parking zones")
        c3.error("**Missing (needs police data)**\n\nClassified vehicle counts on event days\n\nSpeeds and queue lengths\n\nReal hospital and parking coordinates")

# ------------------------------------------------------------------ 2. Suppliers -> Inputs
with t2:
    if demo_mode:
        st.caption(t("tab2_demo", lang))
    st.subheader(t("tab2_subhdr", lang))
    a, b = st.columns(2)
    with a:
        st.markdown("**ఎంచుకున్న ఈవెంట్ (Event selected)**" if is_te else "**Event selected**")
        st.write({"Event": res["params"]["event_name"], "Date": str(res["params"]["event_date"] or "custom"),
                  "Start": res["params"]["start_time"], "Phase": res["params"]["phase"],
                  "Attendance": f"{res['params']['attendance']:,}"})
        st.caption(f"Category: {event_type} | Operational Phase: {phase.title()}")
        st.markdown("**డేటా ప్యాక్ (Excel Data Pack)**" if is_te else "**Data pack (Excel)**")
        st.write({k: f"{len(v)} rows" for k, v in PACK.items()} if PACK else ("డేటా ప్యాక్ కనుగొనబడలేదు" if is_te else "Data pack not found"))
    with b:
        st.markdown("**రోడ్డు నెట్‌వర్క్ నాణ్యత (Road network quality)**" if is_te else "**Road network quality**")
        st.write({"Routable junctions": NET["nodes"], "Road segments": NET["edges"],
                  "Lanes missing in OSM (defaulted)": f"{NET['pct_lanes_defaulted']}%",
                  "Speeds missing in OSM (defaulted)": f"{NET['pct_speed_defaulted']}%",
                  "Real event-day vehicle counts": "0 (not public)"})
        st.caption("OSM రోడ్డు డేటాలో చాలా రోడ్లకు లేన్లు లేదా వేగం ట్యాగ్ లేదు, కాబట్టి సామర్థ్యాలు అంచనాలు మాత్రమే (ASSUMED)." if is_te else
                   "Almost all roads have no lane or speed tag in OSM, so capacities are estimates. This is why we show model estimates, not measurements.")
    st.markdown("**ఈ తేదీకి పోలీసు అడ్వైజరీ మళ్లింపులు (Police Advisory Diversions)**" if is_te else "**Police advisory diversions for this date**")
    adv = res["advisory"]
    if adv is not None and not adv.empty:
        st.dataframe(adv[["Movement", "Vehicle_Class", "Diversion_Point", "Diverted_Route", "Window_Start", "Window_End"]]
                     .drop_duplicates(), hide_index=True)
    else:
        st.info("ఈ తేదీకి డేటా ప్యాక్‌లో పోలీసు సలహాలు లేవు." if is_te else "No advisory rows for this date in the data pack.")
    st.markdown("**ప్రయాణ సాధనాల విభజన (Mode Split - శాతం)**" if is_te else "**Mode split used (share of people)**")
    ms = pd.DataFrame({"mode": list(dem["mode_share"]), "share_%": [round(v * 100, 1) for v in dem["mode_share"].values()]})
    st.bar_chart(ms.set_index("mode"))

    st.markdown("---")
    st.markdown("### 📊 సాధారణ రోజు ట్రాఫిక్ సరళి (అనుకోబడినది / ASSUMED - కొలవనిది)" if is_te else "### 📊 Typical-day traffic pattern (ASSUMED shape, synthetic, NOT measured counts)")
    st.caption("ఈ ట్రాఫిక్ కర్వ్‌లు ప్రణాళిక కోసం రూపొందించబడిన అనుకోబడిన (ASSUMED) మోడల్. హైదరాబాద్ రోడ్లకు పబ్లిక్ లైవ్ కౌంట్లు అందుబాటులో లేవు. పోలీసు ITMS కౌంట్లు లభించినప్పుడు వీటిని భర్తీ చేయవచ్చు." if is_te else
               "These curves are a hand-made planning shape. Real hourly counts per road are not public for Hyderabad. Real published counts (older studies) are listed below. Replace with police/ITMS counts when you get them.")

    day_name = pd.to_datetime(event_date).day_name()
    ev_hour = int(start_time.split(":")[0]) if ":" in start_time else 19
    c_day1, c_day2 = st.columns(2)
    with c_day1:
        st.markdown(f"**24 గంటల ట్రాఫిక్ కర్వ్ ({day_name})**" if is_te else f"**24-Hour Diurnal Traffic Curve ({day_name})**")
        curve_df = TP.get_diurnal_24h_curve(day_of_week=day_name, road_category="Primary_Arterial")
        if not curve_df.empty:
            st.line_chart(curve_df.set_index("Time_Window")[["Total_Vehicles", "Total_PCU"]])
    with c_day2:
        st.markdown(f"**ఈవెంట్ సమయం వద్ద వాహనాల మిశ్రమం ({start_time[:2]}:00)**" if is_te else f"**Classified Vehicle Mix during Event Hour ({start_time[:2]}:00)**")
        slice_data = TP.get_hourly_slice(day_of_week=day_name, hour=ev_hour, road_category="Primary_Arterial")
        if slice_data:
            mix_df = pd.DataFrame({
                "Vehicle Class": ["2-Wheelers", "Cars", "Autos", "Buses", "Trucks/LCVs"],
                "Count": [slice_data["Two_Wheeler_Count"], slice_data["Car_Count"], slice_data["Auto_Rickshaw_Count"], slice_data["Bus_Count"], slice_data["LCV_Truck_Count"]]
            })
            st.bar_chart(mix_df.set_index("Vehicle Class"))

    st.markdown(f"**{start_time[:2]}:00 వద్ద 7 రోజుల ట్రాఫిక్ పరిమాణ పోలిక (కారిడార్ గుండా వెళ్లే వాహనాలు)**" if is_te else f"**7-Day Traffic Volume Comparison at {start_time[:2]}:00 (Vehicles passing through corridor)**")
    week_df = TP.get_weekly_comparison(hour=ev_hour, road_category="Primary_Arterial")
    if not week_df.empty:
        st.dataframe(week_df, hide_index=True)
    _anch = TP.load_real_anchors()
    if not _anch.empty:
        st.markdown("**గతంలో ప్రచురించబడిన వాస్తవ కౌంట్లు (పాత అధ్యయనాలు - Real published counts)**" if is_te else "**Real published counts (older studies, a few locations only)**")
        st.dataframe(_anch[["Location", "Count", "Unit", "Year", "Source"]], hide_index=True)

# ------------------------------------------------------------------ 3. Process
with t3:
    if demo_mode:
        st.caption(t("tab3_demo", lang))
    st.subheader(t("tab3_subhdr", lang))
    st.markdown("**దశ 1-2. డేటా మరియు రోడ్డు గ్రాఫ్ (Road Graph)**" if is_te else "**Step 1-2. Data and road graph**")
    st.write(f"{NET['nodes']:,} కూడళ్లు (Junctions), {NET['edges']:,} రోడ్డు విభాగాలు (Segments), రోడ్డు రకాలు: {NET['road_types']}" if is_te else
             f"{NET['nodes']:,} junctions, {NET['edges']:,} road segments, road types: {NET['road_types']}")
    st.markdown("**దశ 3. రోడ్డు కూడళ్లకు అనుసంధానించబడిన ప్రవేశ కేంద్రాలు (Approach Entry Points)**" if is_te else "**Step 3. Locations snapped to road junctions (approach entry points)**")
    rows = [{"Approach": n, "Share of traffic": f"{a['share']*100:.0f}%", "Entry junctions": len(a["nodes"]),
             "Lat/Lon": f"{a['latlon'][0]:.4f}, {a['latlon'][1]:.4f}"} for n, a in res["approaches"].items()]
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.caption("లొకేషన్ కోఆర్డినేట్లు వాస్తవ/వెరిఫైడ్ రికార్డులను ఉపయోగిస్తాయి." if is_te else "Location coordinates use verified records where available.")
    st.markdown("**దశ 4. మోడ్ వారీగా ట్రాఫిక్ డిమాండ్ (ప్రజలు → వాహనాలు → PCU)**" if is_te else "**Step 4. Demand per mode (people → vehicles → PCU)**")
    dtab = pd.DataFrame({"mode": list(E.MODES),
                         "people": [round(dem["persons"][m]) for m in E.MODES],
                         "vehicles": [dem["vehicles"].get(m, 0) for m in E.MODES],
                         "PCU": [round(dem["pcu"].get(m, 0)) for m in E.MODES]})
    st.dataframe(dtab, hide_index=True)
    st.write(f"మొత్తం {dem['total_vehicles']:,} వాహనాలు = {dem['total_pcu']:,.0f} PCU. గరిష్ట రద్దీ ప్రారంభం "
             f"**{dem['peak_bucket']}**: {dem['peak_15min_pcu']:,.0f} PCU = {dem['peak_hourly_pcu']:,.0f} PCU/గంట." if is_te else
             f"Total {dem['total_vehicles']:,} vehicles = {dem['total_pcu']:,.0f} PCU. Busiest 15 minutes start at "
             f"**{dem['peak_bucket']}**: {dem['peak_15min_pcu']:,.0f} PCU = {dem['peak_hourly_pcu']:,.0f} PCU/hour.")
    st.line_chart(dem["curve"].set_index("Time")["PCU"])
    st.markdown("**దశ 5. రోడ్లపై ట్రాఫిక్ భారం: సాధారణం (Naive) vs ఆప్టిమైజ్డ్ (Optimised)**" if is_te else "**Step 5. Load the roads: naive vs optimised**")
    st.write("సాధారణం (Naive) = ప్రతి ఒక్కరూ షార్ట్‌కట్ ఖాళీ రోడ్డును ఎంచుకుంటారు. ఆప్టిమైజ్డ్ = రోడ్లు రద్దీ అయ్యే కొద్దీ ట్రాఫిక్ పునఃపంపిణీ (Successive Averaging)." if is_te else
             "Naive = everyone takes the shortest empty-road path (what a plain route finder does). Optimised = repeated re-routing as roads fill up (method of successive averages).")
    st.line_chart(pd.DataFrame({"max V/C": res["history"]}, index=[f"iter {i}" for i in range(len(res["history"]))]))
    st.markdown("**దశ 6-7. రద్దీ కేంద్రాలు (Hotspots), మళ్లింపులు (Diversions), ఎమర్జెన్సీ కారిడార్** వివరాలు ఫలితాల (Outputs) ట్యాబ్‌లో చూపబడ్డాయి." if is_te else
                "**Step 6-7. Hotspots, diversions, emergency corridor** are shown in the Outputs tab.")

# ------------------------------------------------------------------ 4. Outputs
with t4:
    if demo_mode:
        st.caption(t("tab4_demo", lang))
    st.subheader(t("tab4_subhdr", lang))
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(t("metric_vehicles", lang), f"{dem['total_vehicles']:,}")
    m2.metric(t("metric_peak_pcu", lang), f"{dem['peak_hourly_pcu']:,.0f}")
    m3.metric(t("metric_max_vc", lang), f"{so['max_vc']:.2f}", f"{so['max_vc'] - sn['max_vc']:+.2f} vs naive", delta_color="inverse")
    m4.metric(t("metric_roads_over_cap", lang), so["congested"], f"{so['congested'] - sn['congested']:+d} vs naive", delta_color="inverse")
    view_opts = ["Co-Pilot (optimised)", "Naive shortest path"]
    view_fmt = (lambda x: "కో-పైలట్ ఆప్టిమైజ్డ్ రూట్" if "optimised" in x else "సాధారణ షార్ట్‌కట్ రూట్") if is_te else (lambda x: x)
    view = st.radio(t("map_view_label", lang), view_opts, format_func=view_fmt, horizontal=True)
    try:
        from streamlit_folium import st_folium
        st_folium(make_map(D, res, use_naive=view.startswith("Naive")), height=560, width=1200,
                  returned_objects=[])
    except Exception as exc:
        st.warning(f"Map could not be drawn: {exc}")
    st.markdown(f"**{t('hotspots_hdr', lang)}**")
    hs = res["hotspots"]
    if len(hs):
        st.dataframe(hs[["street", "road_type", "lanes", "segments", "load_pcu_hr", "capacity_pcu_hr", "vc", "fed_by"]]
                     .rename(columns={"vc": "V/C"}).head(10), hide_index=True)
    st.markdown(f"**{t('diversions_hdr', lang)}**")
    dv = pd.DataFrame([{"Hotspot": d["name"], "V/C": d["vc"], "Feasible": d["feasible"],
                        "Extra metres": d.get("extra_m"), "Extra seconds": d.get("extra_s"), "Note": d["note"]}
                       for d in res["diversions"]])
    if len(dv):
        st.dataframe(dv, hide_index=True)
    c = res["corridor"]
    if c:
        hosp_note = "ఆసుపత్రి లొకేషన్ ప్లేస్‌హోల్డర్ (ASSUMED)." if (is_te and res.get("hospital_is_placeholder", True)) else ("Hospital point is a placeholder." if res.get("hospital_is_placeholder", True) else ("ఆసుపత్రి లొకేషన్ రికార్డుల నుండి వెరిఫై చేయబడింది." if is_te else "Hospital point from manual_locations.csv."))
        st.info(f"రక్షిత అత్యవసర గ్రీన్ కారిడార్: {c['length_m']:,} మీటర్లు. క్లియర్‌గా ఉంచితే సమయం {c['free_min']} నిమిషాలు, సాధారణ ట్రాఫిక్‌లో సుమారు {c['unprotected_min']} నిమిషాలు. {hosp_note}" if is_te else
                f"Protected emergency corridor: {c['length_m']:,} m. ETA {c['free_min']} min if kept clear, about {c['unprotected_min']} min if open to event traffic. {hosp_note}")
    st.markdown("**What-if: shifting riders to metro**" if not is_te else "**వాట్-ఇఫ్: మెట్రో ప్రయాణికుల మళ్లింపు దృశ్యం**")
    if st.button("Run what-if comparison (0, 10, 20, 30%)" if not is_te else "మెట్రో పోలికను అమలు చేయండి (0, 10, 20, 30%)"):
        rows = []
        for sh in (0, 10, 20, 30):
            r2 = E.run_scenario(D, {**res["params"], "shift_pct": float(sh)}, PACK)
            rows.append({"Shift to metro %": sh, "Vehicles": r2["demand"]["total_vehicles"],
                         "Peak PCU/h": round(r2["demand"]["peak_hourly_pcu"]), "Max V/C": r2["sum_opt"]["max_vc"],
                         "Roads over capacity": r2["sum_opt"]["congested"]})
        st.dataframe(pd.DataFrame(rows), hide_index=True)

    st.markdown(f"**{t('preset_hdr', lang)}**")
    st.caption("Side-by-side comparison across 4 standard event presets (attendance ASSUMED: 39,000)." if not is_te else "4 ప్రామాణిక ఈవెంట్ దృశ్యాల పోలిక (హాజరు అనుకోబడినది: 39,000 / ASSUMED).")
    comp_df = get_preset_comparison(D, venue_key, tuple(venue_coords), hospital_latlon, PACK)
    st.dataframe(comp_df, hide_index=True)

# ------------------------------------------------------------------ 5. Operational Plan & Customers
with t5:
    if demo_mode:
        st.caption(t("tab5_demo", lang))

    st.markdown(f"### {t('tab5_plan_hdr', lang, event=res['params']['event_name'])}")
    st.caption(t("tab5_authority_cap", lang, area=selected_loc_name, phase=res['params']['phase'].title()))

    report_to_show = build_telugu_report(res) if is_te else res["report"]
    report_txt = report_to_show.replace("#", "").replace("**", "")

    # Quick Download Buttons at the top
    d1, d2, d3 = st.columns(3)
    d1.download_button(t("dl_md", lang), report_to_show, f"traffic_plan_{res['params']['event_name']}.md", key="dl_md_top")
    d2.download_button(t("dl_txt", lang), report_txt, f"traffic_plan_{res['params']['event_name']}.txt", key="dl_txt_top")
    d3.download_button(t("dl_csv", lang), res["table_opt"].to_csv(index=False), "hotspots.csv", key="dl_csv_top")

    # Key Tactical Numbers Banner
    km1, km2, km3, km4 = st.columns(4)
    km1.metric(t("exp_crowd", lang), f"{res['params']['attendance']:,}")
    km2.metric(t("metric_vehicles", lang), f"{dem['total_vehicles']:,}")
    km3.metric(t("metric_peak_pcu", lang), f"{dem['peak_hourly_pcu']:,.0f} PCU/h")
    c_eta = f"{res['corridor']['free_min']} min" if res['corridor'] else "N/A"
    km4.metric(t("green_corridor_eta", lang), c_eta)

    st.markdown("---")
    # Complete text-based detailed plan for the police to read
    st.markdown(report_to_show)

    st.markdown("---")
    st.subheader("Stakeholder Deliverables (Customers)" if not is_te else "భాగస్వాముల కార్యాచరణ అంశాలు (Stakeholder Deliverables)")
    hs_plan = res.get("hotspots", pd.DataFrame())
    top = hs_plan.head(3)["street"].tolist() if len(hs_plan) else []
    cols = st.columns(2)
    with cols[0]:
        st.markdown("##### " + ("ట్రాఫిక్ పోలీసు ప్లానర్లు" if is_te else "Traffic police planners"))
        st.write("హాట్‌స్పాట్లు, మళ్లింపులు మరియు గ్రీన్ కారిడార్‌తో పూర్తి కార్యాచరణ ప్రణాళిక (పై పత్రం డౌన్‌లోడ్ చేసుకోండి)." if is_te else "Full plan with hotspots, diversions and emergency corridor (above, downloadable).")
        st.markdown("##### " + ("ఈవెంట్ నిర్వాహకులు" if is_te else "Event organiser"))
        st.write(f"సుమారు {dem['buses']} ప్రత్యేక బస్సులు మరియు {dem['metro_riders']:,.0f} మెట్రో ప్రయాణికుల కోసం ఏర్పాట్లు చేయండి. "
                 f"{dem['pedestrians']:,.0f} మంది నడిచి వస్తారు, కాబట్టి ప్రవేశ గేట్ల వద్ద క్రౌడ్ కంట్రోల్ అవసరం." if is_te else
                 f"Plan for about {dem['buses']} event buses and {dem['metro_riders']:,.0f} metro riders. "
                 f"{dem['pedestrians']:,.0f} people arrive on foot, so gate queues and metro exits need crowd control.")
    with cols[1]:
        st.markdown("##### " + ("అత్యవసర రవాణా సేవలు (108 అంబులెన్స్)" if is_te else "Emergency services"))
        c = res["corridor"]
        st.write(f"పర్పుల్ గ్రీన్ కారిడార్‌ను నిరంతరం క్లియర్‌గా ఉంచండి ({c['length_m']:,} మీటర్లు, {c['free_min']} నిమిషాలు)." if is_te and c else
                 (f"Keep the purple corridor clear ({c['length_m']:,} m, {c['free_min']} min)." if c else "No corridor computed."))
        st.markdown("##### " + ("నిత్య ప్రయాణికులకు ముందస్తు హెచ్చరిక (Public Advisory)" if is_te else "Commuters (draft public message)"))
        msg = (f"{selected_loc_name} పరిసరాల్లో {res['params']['start_time']} నుండి భారీ ట్రాఫిక్ ఉండే అవకాశం ఉంది. {', '.join(top) if top else 'వేదిక రోడ్లను'} నివారించండి. "
               "మెట్రో లేదా ఆర్టీసీ ప్రత్యేక బస్సులను ఉపయోగించండి." if is_te else
               f"Heavy traffic expected around {selected_loc_name} from {res['params']['start_time']}. Avoid {', '.join(top) if top else 'the venue roads'}. "
               "Use Metro or TGSRTC special buses.")
        st.code(msg, language=None)

# ------------------------------------------------------------------ 6. Police Copilot Chatbot
with t6:
    st.subheader(t("chatbot_subhdr", lang))
    st.caption(t("chatbot_caption", lang))

    ev_name = res["params"].get("event_name", active_event_name)
    if "chat_history" not in st.session_state or st.session_state.get("chat_event_name") != ev_name or st.session_state.get("chat_lang") != lang:
        st.session_state["chat_event_name"] = ev_name
        st.session_state["chat_lang"] = lang
        st.session_state["chat_history"] = [
            {"role": "assistant", "content": t("chat_greeting", lang, event=ev_name)}
        ]

    # Quick prompt buttons
    st.markdown(f"**{t('quick_inquiries', lang)}**")
    qc1, qc2, qc3, qc4 = st.columns(4)
    quick_q = None
    if qc1.button(t("btn_bottlenecks", lang)):
        quick_q = "కీలక రద్దీ కేంద్రాలు ఏవి?" if is_te else "What are the critical bottlenecks?"
    if qc2.button(t("btn_diversions", lang)):
        quick_q = "ట్రాఫిక్ మళ్లింపు మార్గాలను వివరించండి" if is_te else "Explain the diversion scheme"
    if qc3.button(t("btn_emergency", lang)):
        quick_q = "అత్యవసర గ్రీన్ కారిడార్ మార్గం మరియు సమయం ఎంత?" if is_te else "What is the emergency corridor route and ETA?"
    if qc4.button(t("btn_deployment", lang)):
        quick_q = "పోలీసు సిబ్బంది మోహరింపు సిఫార్సు ఏమిటి?" if is_te else "What is the recommended police personnel deployment?"

    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_query = st.chat_input(t("chat_input_ph", lang)) or quick_q
    if user_query:
        st.session_state["chat_history"].append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        ans = PC.generate_police_response(user_query, res, lang=lang)
        st.session_state["chat_history"].append({"role": "assistant", "content": ans})
        with st.chat_message("assistant"):
            st.markdown(ans)
