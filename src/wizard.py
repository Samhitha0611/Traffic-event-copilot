"""
Gemini-style Conversational 5-Step Guided Onboarding for Traffic Event Co-Pilot.
- Strictly single-language (English ONLY when English selected; Telugu ONLY when తెలుగు selected).
- Pure click-through suggestion chips inside the chat dialogue (no left sidebar).
- Typing is only an optional "Other" escape hatch.
- Shows a complete Overview card before "Proceed & Create Traffic Plan".
"""
from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

import venue_catalog as VC

WIZARD_VENUES: list[dict[str, Any]] = [
    {"catalog_key": "Rajiv Gandhi International Cricket Stadium, Uppal", "icon": "🏟️", "en": "Uppal Stadium", "te": "ఉప్పల్ స్టేడియం", "sub_en": "Rachakonda · ~39,000", "sub_te": "రాచకొండ · ~39,000"},
    {"catalog_key": "Gachibowli Stadium", "icon": "🏟️", "en": "Gachibowli Stadium", "te": "గచ్చిబౌలి స్టేడియం", "sub_en": "Cyberabad · ~30,000", "sub_te": "సైబరాబాద్ · ~30,000"},
    {"catalog_key": "Lal Bahadur Shastri Stadium (LB Stadium), Basheerbagh", "icon": "🏟️", "en": "LB Stadium", "te": "ఎల్బీ స్టేడియం", "sub_en": "Hyd City · ~25,000", "sub_te": "హైదరాబాద్ సిటీ · ~25,000"},
    {"catalog_key": "Shilpakala Vedika, Madhapur", "icon": "🎭", "en": "Shilpakala Vedika", "te": "శిల్పకళా వేదిక", "sub_en": "Cyberabad · ~5,000", "sub_te": "సైబరాబాద్ · ~5,000"},
    {"catalog_key": "HITEX Exhibition Centre, Madhapur", "icon": "🏛️", "en": "HITEX Centre", "te": "హైటెక్స్ సెంటర్", "sub_en": "Cyberabad · ~20,000", "sub_te": "సైబరాబాద్ · ~20,000"},
    {"catalog_key": "Parade Ground, Secunderabad", "icon": "🎖️", "en": "Parade Ground", "te": "పరేడ్ గ్రౌండ్", "sub_en": "Hyd City · ~60,000", "sub_te": "హైదరాబాద్ సిటీ · ~60,000"},
]

WIZARD_EVENT_TYPES: list[dict[str, str]] = [
    {"icon": "🏏", "en": "Cricket / Sports Match", "te": "క్రికెట్ / క్రీడా మ్యాచ్", "name_en": "IPL / Cricket Match", "name_te": "ఐపీఎల్ / క్రికెట్ మ్యాచ్"},
    {"icon": "🎵", "en": "Concert / Music Show", "te": "సంగీత కచేరీ / షో", "name_en": "Live Music Concert", "name_te": "సంగీత కచేరీ"},
    {"icon": "🕌", "en": "Religious / Procession", "te": "మతపరమైన వేడుక / ఊరేగింపు", "name_en": "Religious Gathering", "name_te": "మతపరమైన వేడుక"},
    {"icon": "🏛️", "en": "Political Rally / Gathering", "te": "రాజకీయ సభ / ర్యాలీ", "name_en": "Public Rally", "name_te": "రాజకీయ సభ"},
    {"icon": "🏃", "en": "Marathon / Festival", "te": "మారథాన్ / ఉత్సవం", "name_en": "City Marathon / Festival", "name_te": "మారథాన్ / ఉత్సవం"},
    {"icon": "🎪", "en": "Exhibition / Trade Fair", "te": "ప్రదర్శన / జాతర", "name_en": "Exhibition / Trade Fair", "name_te": "ప్రదర్శన / జాతర"},
    {"icon": "⚽", "en": "Football / Athletics", "te": "ఫుట్‌బాల్ / అథ్లెటిక్స్", "name_en": "Football Match", "name_te": "ఫుట్‌బాల్ మ్యాచ్"},
    {"icon": "🎓", "en": "VIP Movement / Conference", "te": "వీఐపీ పర్యటన / సదస్సు", "name_en": "VIP Conference", "name_te": "వీఐపీ సదస్సు"},
]

WIZARD_CROWD_TIERS: list[dict[str, Any]] = [
    {"icon": "🟢", "en": "Small · Under 10,000", "te": "చిన్నది · 10,000 కన్నా తక్కువ", "val": 7500},
    {"icon": "🟡", "en": "Medium · 10,000 – 30,000", "te": "మధ్యస్థం · 10,000 – 30,000", "val": 20000},
    {"icon": "🟠", "en": "Large · 30,000 – 60,000", "te": "పెద్దది · 30,000 – 60,000", "val": 39000},
    {"icon": "🔴", "en": "Massive · 60,000+ (ASSUMED)", "te": "అతిపెద్దది · 60,000+ (ASSUMED)", "val": 75000},
]


def _init_wizard_state() -> None:
    if "wizard_step" not in st.session_state:
        st.session_state["wizard_step"] = 0
    if "wizard_data" not in st.session_state:
        st.session_state["wizard_data"] = {
            "venue_name": "Rajiv Gandhi International Cricket Stadium, Uppal",
            "venue_label_en": "Uppal Stadium",
            "venue_label_te": "ఉప్పల్ స్టేడియం",
            "event_type": "Cricket / Sports Match",
            "event_type_te": "క్రికెట్ / క్రీడా మ్యాచ్",
            "event_name": "SRH IPL Match 2026",
            "attendance": 39000,
            "event_date": date(2026, 4, 15),
            "start_time": "19:30",
            "phase": "ingress",
        }


def _lbl(en: str, te: str, is_te: bool) -> str:
    return te if is_te else en


def render_wizard(events_df: pd.DataFrame | None = None, lang: str = "English") -> dict[str, Any] | None:
    """
    Render the Gemini-style conversational onboarding wizard.
    Strictly displays ONLY the selected language (`English` or `తెలుగు`).
    Returns the confirmed parameters dict when officer clicks Proceed, else None.
    """
    _init_wizard_state()
    is_te = lang == "తెలుగు"
    step = int(st.session_state["wizard_step"])
    data = st.session_state["wizard_data"]

    # Centered Gemini Hero
    badge = _lbl("GREATER HYDERABAD TRAFFIC POLICE · AI CO-PILOT", "గ్రేటర్ హైదరాబాద్ ట్రాఫిక్ పోలీస్ · ఏఐ కో-పైలట్", is_te)
    hero_q = _lbl("Where should we start?", "మనం ఎక్కడి నుండి ప్రారంభిద్దాం?", is_te)
    hero_sub = _lbl(
        "Tap a suggestion below to configure your event plan — no typing required.",
        "ఈవెంట్ ప్రణాళిక కోసం దిగువ సూచనలను క్లిక్ చేయండి — టైప్ చేయాల్సిన అవసరం లేదు.",
        is_te,
    )
    st.markdown(
        f"""
        <div class="gemini-hero">
            <div class="gemini-hero-badge"><span class="live-dot"></span> {badge}</div>
            <h1>{hero_q}</h1>
            <p>{hero_sub}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 4-Step Visual Progress Stepper
    step_labels = (
        ["① వేదిక", "② ఈవెంట్", "③ జనసమూహం", "④ సమయం", "⑤ సమీక్ష"]
        if is_te
        else ["① Venue", "② Event", "③ Crowd", "④ Schedule", "⑤ Overview"]
    )
    pills_html = []
    for i, slbl in enumerate(step_labels):
        cls = "step-pill done" if i < step else ("step-pill active" if i == step else "step-pill")
        pills_html.append(f"<span class='{cls}'>{slbl}</span>")
    st.markdown(f"<div class='stepper-row'>{''.join(pills_html)}</div>", unsafe_allow_html=True)

    _, center_col, _ = st.columns([0.1, 0.8, 0.1])
    with center_col:
        # Conversational trail of completed steps
        if step >= 1:
            with st.chat_message("assistant"):
                st.markdown(_lbl("Which venue or area in Hyderabad is the event at?", "హైదరాబాద్‌లో ఈవెంట్ ఏ వేదిక లేదా ప్రాంతంలో జరుగుతుంది?", is_te))
            with st.chat_message("user"):
                v_disp = data.get("venue_label_te" if is_te else "venue_label_en", data["venue_name"])
                st.markdown(f"📍 **{v_disp}**")

        if step >= 2:
            with st.chat_message("assistant"):
                st.markdown(_lbl("What type of event are we planning for?", "మనం ఏ రకమైన ఈవెంట్ కోసం ప్లాన్ చేస్తున్నాము?", is_te))
            with st.chat_message("user"):
                et_disp = data.get("event_type_te", data["event_type"]) if is_te else data["event_type"]
                st.markdown(f"🎪 **{data['event_name']}** ({et_disp})")

        if step >= 3:
            with st.chat_message("assistant"):
                st.markdown(_lbl("What is the expected crowd size? *(ASSUMED planning estimate)*", "అంచనా ప్రేక్షకుల సంఖ్య ఎంత? *(ASSUMED ప్రణాళిక అంచనా)*", is_te))
            with st.chat_message("user"):
                st.markdown(f"👥 **{data['attendance']:,}**")

        if step >= 4:
            with st.chat_message("assistant"):
                st.markdown(_lbl("When does the event start, and which phase should we plan?", "ఈవెంట్ ఎప్పుడు ప్రారంభమవుతుంది మరియు ఏ దశను ప్లాన్ చేయాలి?", is_te))
            with st.chat_message("user"):
                ph_txt = _lbl("Ingress (arriving)" if data["phase"] == "ingress" else "Egress (leaving)", "రాక (Ingress)" if data["phase"] == "ingress" else "నిష్క్రమణ (Egress)", is_te)
                st.markdown(f"📅 **{data['event_date']} · {data['start_time']} · {ph_txt}**")

        # ------------------------------------------------------------------ ACTIVE STEP PROMPT + CHIPS
        if step == 0:
            with st.chat_message("assistant"):
                st.markdown(_lbl(
                    "**Step 1 of 4:** Select the event venue or area in Greater Hyderabad:",
                    "**దశ 1 / 4:** గ్రేటర్ హైదరాబాద్‌లో ఈవెంట్ వేదిక లేదా ప్రాంతాన్ని ఎంచుకోండి:",
                    is_te,
                ))
            suggestions = VC.get_hyderabad_location_suggestions()
            cols = st.columns(3)
            for idx, v in enumerate(WIZARD_VENUES):
                with cols[idx % 3]:
                    name = v["te"] if is_te else v["en"]
                    sub = v["sub_te"] if is_te else v["sub_en"]
                    if st.button(f"{v['icon']} {name}\n\n`{sub}`", key=f"wiz_v_{idx}", use_container_width=True):
                        data["venue_name"] = v["catalog_key"]
                        data["venue_label_en"] = v["en"]
                        data["venue_label_te"] = v["te"]
                        cat_info = suggestions.get(v["catalog_key"], {})
                        if cat_info.get("capacity"):
                            data["attendance"] = int(cat_info["capacity"])
                        st.session_state["wizard_step"] = 1
                        st.rerun()

            with st.expander(_lbl("🔍 Other Hyderabad location (optional)", "🔍 ఇతర ప్రాంతాన్ని ఎంచుకోండి (ఐచ్ఛికం)", is_te)):
                all_locs = list(suggestions.keys())
                picked = st.selectbox(_lbl("Choose any location", "ప్రాంతాన్ని ఎంచుకోండి", is_te), all_locs, key="wiz_other_loc")
                if st.button(_lbl("Select & Continue →", "ఎంచుకొని కొనసాగండి →", is_te), key="wiz_other_loc_go", type="primary"):
                    data["venue_name"] = picked
                    data["venue_label_en"] = picked
                    data["venue_label_te"] = picked
                    st.session_state["wizard_step"] = 1
                    st.rerun()
            return None

        if step == 1:
            with st.chat_message("assistant"):
                st.markdown(_lbl(
                    "**Step 2 of 4:** What kind of event is this?",
                    "**దశ 2 / 4:** ఇది ఏ రకమైన ఈవెంట్?",
                    is_te,
                ))
            cols = st.columns(4)
            for idx, et in enumerate(WIZARD_EVENT_TYPES):
                with cols[idx % 4]:
                    lbl = et["te"] if is_te else et["en"]
                    if st.button(f"{et['icon']} {lbl}", key=f"wiz_et_{idx}", use_container_width=True):
                        data["event_type"] = et["en"]
                        data["event_type_te"] = et["te"]
                        data["event_name"] = et["name_te"] if is_te else et["name_en"]
                        st.session_state["wizard_step"] = 2
                        st.rerun()

            with st.expander(_lbl("✏️ Other / Custom event name", "✏️ ఇతర ఈవెంట్ పేరు టైప్ చేయండి", is_te)):
                custom_ev = st.text_input(_lbl("Event Name", "ఈవెంట్ పేరు", is_te), value=data.get("event_name", ""), key="wiz_custom_ev")
                if st.button(_lbl("Continue →", "కొనసాగండి →", is_te), key="wiz_custom_ev_go", type="primary"):
                    if custom_ev.strip():
                        data["event_name"] = custom_ev.strip()
                    st.session_state["wizard_step"] = 2
                    st.rerun()
            return None

        if step == 2:
            with st.chat_message("assistant"):
                st.markdown(_lbl(
                    "**Step 3 of 4:** Tap the expected crowd tier *(ASSUMED estimate)*:",
                    "**దశ 3 / 4:** అంచనా జనసమూహ స్థాయిని ఎంచుకోండి *(ASSUMED అంచనా)*:",
                    is_te,
                ))
            cols = st.columns(2)
            for idx, tier in enumerate(WIZARD_CROWD_TIERS):
                with cols[idx % 2]:
                    lbl = tier["te"] if is_te else tier["en"]
                    if st.button(f"{tier['icon']} {lbl}", key=f"wiz_cr_{idx}", use_container_width=True):
                        data["attendance"] = int(tier["val"])
                        st.session_state["wizard_step"] = 3
                        st.rerun()

            with st.expander(_lbl("✏️ Enter exact crowd number", "✏️ ఖచ్చితమైన సంఖ్యను నమోదు చేయండి", is_te)):
                exact_n = st.number_input(_lbl("Expected Attendance", "అంచనా హాజరు", is_te), 1000, 150000, int(data.get("attendance", 39000)), 1000, key="wiz_exact_crowd")
                if st.button(_lbl("Continue →", "కొనసాగండి →", is_te), key="wiz_exact_crowd_go", type="primary"):
                    data["attendance"] = int(exact_n)
                    st.session_state["wizard_step"] = 3
                    st.rerun()
            return None

        if step == 3:
            with st.chat_message("assistant"):
                st.markdown(_lbl(
                    "**Step 4 of 4:** Pick a quick schedule slot or advisory date:",
                    "**దశ 4 / 4:** సమయం మరియు తేదీని ఎంచుకోండి:",
                    is_te,
                ))

            quick_slots = [
                ("🌙 19:30 · Ingress", "🌙 19:30 · రాక (Ingress)", "19:30", "ingress"),
                ("☀️ 15:30 · Ingress", "☀️ 15:30 · రాక (Ingress)", "15:30", "ingress"),
                ("🚦 22:30 · Egress", "🚦 22:30 · నిష్క్రమణ (Egress)", "22:30", "egress"),
                ("🌅 06:30 · Morning", "🌅 06:30 · ఉదయం (Ingress)", "06:30", "ingress"),
            ]
            qcols = st.columns(4)
            for idx, (en_q, te_q, tm_q, ph_q) in enumerate(quick_slots):
                with qcols[idx]:
                    if st.button(te_q if is_te else en_q, key=f"wiz_slot_{idx}", use_container_width=True):
                        data["start_time"] = tm_q
                        data["phase"] = ph_q
                        st.session_state["wizard_step"] = 4
                        st.rerun()

            ev_rows: list[dict[str, Any]] = []
            if isinstance(events_df, list):
                ev_rows = [
                    {
                        "Date": r.get("date", "2026-04-15"),
                        "Start_Time": r.get("start", "19:30"),
                        "Event_Name": r.get("name", "Scheduled Event"),
                    }
                    for r in events_df[:3]
                    if isinstance(r, dict)
                ]
            elif isinstance(events_df, pd.DataFrame) and not events_df.empty and "Date" in events_df.columns:
                ev_rows = events_df.head(3).to_dict("records")

            if ev_rows:
                st.caption(_lbl("Or tap an upcoming Police Advisory date:", "లేదా పోలీసు అడ్వైజరీ తేదీని ఎంచుకోండి:", is_te))
                scols = st.columns(len(ev_rows))
                for idx, r in enumerate(ev_rows):
                    dt_str = str(r.get("Date", "2026-04-15"))[:10]
                    tm_str = str(r.get("Start_Time", "19:30"))[:5]
                    lbl_ev = str(r.get("Event_Name", "Scheduled Event"))
                    with scols[idx]:
                        if st.button(f"📅 {dt_str} · {tm_str}\n\n{lbl_ev[:22]}", key=f"wiz_dt_{idx}", use_container_width=True):
                            try:
                                data["event_date"] = pd.to_datetime(dt_str).date()
                            except Exception:
                                pass
                            data["start_time"] = tm_str
                            data["event_name"] = lbl_ev
                            st.session_state["wizard_step"] = 4
                            st.rerun()

            with st.expander(_lbl("📅 Custom date / time", "📅 వేరే తేదీ / సమయం", is_te)):
                c1, c2, c3 = st.columns(3)
                picked_dt = c1.date_input(_lbl("Date", "తేదీ", is_te), value=data.get("event_date", date(2026, 4, 15)), key="wiz_date_in")
                picked_tm = c2.text_input(_lbl("Time (HH:MM)", "సమయం (HH:MM)", is_te), value=data.get("start_time", "19:30"), key="wiz_time_in")
                picked_ph = c3.radio(
                    _lbl("Phase", "దశ", is_te),
                    ["ingress", "egress"],
                    format_func=lambda x: _lbl("Ingress" if x == "ingress" else "Egress", "రాక (Ingress)" if x == "ingress" else "నిష్క్రమణ (Egress)", is_te),
                    key="wiz_phase_in",
                )
                if st.button(_lbl("Continue to Overview →", "సమీక్షకు వెళ్లండి →", is_te), type="primary", key="wiz_dt_next"):
                    data["event_date"] = picked_dt
                    data["start_time"] = picked_tm.strip() or "19:30"
                    data["phase"] = picked_ph
                    st.session_state["wizard_step"] = 4
                    st.rerun()
            return None

        # ------------------------------------------------------------------ STEP 4: OVERVIEW & PROCEED
        with st.chat_message("assistant"):
            v_disp = data.get("venue_label_te" if is_te else "venue_label_en", data["venue_name"])
            et_disp = data.get("event_type_te", data["event_type"]) if is_te else data["event_type"]
            ph_disp = _lbl("Ingress (arriving)" if data["phase"] == "ingress" else "Egress (leaving)", "రాక (Ingress)" if data["phase"] == "ingress" else "నిష్క్రమణ (Egress)", is_te)

            if is_te:
                st.markdown(
                    f"""
                    ### 📋 ఎంచుకున్న వివరాల సమీక్ష (Overview)
                    - **📍 వేదిక:** {v_disp}
                    - **🎪 ఈవెంట్:** {data['event_name']} ({et_disp})
                    - **👥 అంచనా హాజరు:** ~{data['attendance']:,} *(ASSUMED)*
                    - **📅 తేదీ & సమయం:** {data['event_date']} · {data['start_time']} · {ph_disp}

                    అన్నీ సరిగ్గా ఉన్నాయా? ప్రణాళిక రూపొందించడానికి **కొనసాగండి** క్లిక్ చేయండి.
                    """
                )
            else:
                st.markdown(
                    f"""
                    ### 📋 Selected Event Overview
                    - **📍 Venue:** {v_disp}
                    - **🎪 Event:** {data['event_name']} ({et_disp})
                    - **👥 Expected Crowd:** ~{data['attendance']:,} *(ASSUMED)*
                    - **📅 Schedule:** {data['event_date']} at {data['start_time']} · {ph_disp}

                    Everything looks ready. Click **Proceed & Create Traffic Plan** to run the AI Co-Pilot.
                    """
                )

        b1, b2 = st.columns([0.65, 0.35])
        if b1.button(_lbl("▶ Proceed & Create Traffic Plan", "▶ కొనసాగండి & ట్రాఫిక్ ప్రణాళిక రూపొందించండి", is_te), type="primary", use_container_width=True, key="wiz_proceed"):
            return dict(data)
        if b2.button(_lbl("🔄 Change Selections", "🔄 మార్పులు చేయండి", is_te), use_container_width=True, key="wiz_restart"):
            st.session_state["wizard_step"] = 0
            st.rerun()
    return None
