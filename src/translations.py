"""
Bilingual (English / Telugu) Internationalization Module for Traffic Event Co-Pilot.
Provides authentic Telugu translations used by Telangana / Hyderabad Traffic Police.
Labels all assumptions strictly as 'అనుకోబడినవి (ASSUMED)'.
"""
from __future__ import annotations

import pandas as pd
from typing import Any

STRINGS: dict[str, dict[str, str]] = {
    # Sidebar
    "lang_label": {
        "English": "🌐 Language / భాష",
        "తెలుగు": "🌐 Language / భాష",
    },
    "event_setup": {
        "English": "🚦 Event setup",
        "తెలుగు": "🚦 ఈవెంట్ సెటప్ (Event Setup)",
    },
    "location_search": {
        "English": "Location / Venue in Hyderabad (type to search)",
        "తెలుగు": "హైదరాబాద్‌లో వేదిక / ప్రాంతం (శోధించండి)",
    },
    "location_help": {
        "English": "Type to search locations across Greater Hyderabad (stadiums, junctions, IT corridors, and areas)",
        "తెలుగు": "గ్రేటర్ హైదరాబాద్ పరిధిలోని స్టేడియంలు, కూడళ్లు, ఐటీ కారిడార్లు మరియు ప్రాంతాలను ఎంచుకోండి",
    },
    "custom_area": {
        "English": "Area or Landmark name",
        "తెలుగు": "ప్రాంతం లేదా మైలురాయి పేరు",
    },
    "latitude": {
        "English": "Latitude",
        "తెలుగు": "అక్షాంశం (Latitude)",
    },
    "longitude": {
        "English": "Longitude",
        "తెలుగు": "రేఖాంశం (Longitude)",
    },
    "jurisdiction": {
        "English": "Jurisdiction",
        "తెలుగు": "పోలీస్ కమిషనరేట్ పరిధి",
    },
    "area": {
        "English": "Area",
        "తెలుగు": "ప్రాంతం",
    },
    "hosp_corridor_label": {
        "English": "Emergency corridor hospital",
        "తెలుగు": "అత్యవసర గ్రీన్ కారిడార్ ఆసుపత్రి",
    },
    "no_hosp_warning": {
        "English": "No hospital within 12 km in data/hyderabad_hospitals.csv, so the emergency corridor is skipped.",
        "తెలుగు": "డేటాలో 12 కి.మీ పరిధిలో ఆసుపత్రి కనుగొనబడలేదు, కాబట్టి ఎమర్జెన్సీ కారిడార్ మినహాయించబడింది.",
    },
    "event_details_hdr": {
        "English": "📋 Event Details",
        "తెలుగు": "📋 ఈవెంట్ వివరాలు (Event Details)",
    },
    "event_name_lbl": {
        "English": "Event Name / Description",
        "తెలుగు": "ఈవెంట్ పేరు / వివరణ",
    },
    "event_cat_lbl": {
        "English": "Event Category",
        "తెలుగు": "ఈవెంట్ వర్గం (Category)",
    },
    "event_date_lbl": {
        "English": "Event Date",
        "తెలుగు": "ఈవెంట్ తేదీ (Date)",
    },
    "start_time_lbl": {
        "English": "Start time (HH:MM)",
        "తెలుగు": "ప్రారంభ సమయం (HH:MM)",
    },
    "crowd_lbl": {
        "English": "Expected Attendance / Crowd (ASSUMED capacity ~{capacity:,})",
        "తెలుగు": "అంచనా ప్రేక్షకుల సంఖ్య (సామర్థ్యం ~{capacity:,} - అనుకోబడినది / ASSUMED)",
    },
    "phase_lbl": {
        "English": "Phase",
        "తెలుగు": "కార్యాచరణ దశ (Phase)",
    },
    "ingress": {
        "English": "ingress",
        "తెలుగు": "రాక (Ingress)",
    },
    "egress": {
        "English": "egress",
        "తెలుగు": "నిష్క్రమణ (Egress)",
    },
    "private_veh_share": {
        "English": "Share arriving by own/hired vehicle (%)",
        "తెలుగు": "స్వంత/అద్దె వాహనాల్లో వచ్చే వారి శాతం (%)",
    },
    "metro_shift_slider": {
        "English": "What-if: move this % of 2-wheeler and car riders to metro",
        "తెలుగు": "వాట్-ఇఫ్: మెట్రోకు మళ్లించే వాహనదారుల శాతం (%)",
    },
    "approach_shares_hdr": {
        "English": "Approach shares (ASSUMED)",
        "తెలుగు": "ట్రాఫిక్ వచ్చే దిశల వాటా (అనుకోబడినవి / ASSUMED)",
    },
    "demo_mode_lbl": {
        "English": "Demo mode",
        "తెలుగు": "డెమో మోడ్ (Demo mode)",
    },
    "demo_mode_help": {
        "English": "Show SIPOC letter and guidance caption under each tab",
        "తెలుగు": "ప్రతి ట్యాబ్ కింద SIPOC మార్గదర్శకాలను ప్రదర్శించండి",
    },
    "run_copilot_btn": {
        "English": "▶ Run Co-Pilot",
        "తెలుగు": "▶ కో-పైలట్ అమలు చేయండి (Run Co-Pilot)",
    },
    "pending_changes_sidebar": {
        "English": "⚠️ **Pending input changes.**\nClick **▶ Run Co-Pilot** above to apply.",
        "తెలుగు": "⚠️ **ఇన్‌పుట్ మార్పులు పెండింగ్‌లో ఉన్నాయి.**\nవర్తింపజేయడానికి పైన **▶ Run Co-Pilot** క్లిక్ చేయండి.",
    },
    "pending_changes_banner": {
        "English": "💡 **Pending input changes:** You selected **{location}** ({event}). The results below display the active plan. Click **'▶ Run Co-Pilot'** in the sidebar to compute and apply the new plan.",
        "తెలుగు": "💡 **మార్పులు పెండింగ్‌లో ఉన్నాయి:** మీరు **{location}** ({event}) ఎంచుకున్నారు. దిగువ ఫలితాలు ప్రస్తుతం అమలులో ఉన్న ప్లాన్‌ను చూపుతున్నాయి. కొత్త ప్లాన్ రూపొందించడానికి సైడ్‌బార్‌లో **'▶ Run Co-Pilot'** క్లిక్ చేయండి.",
    },

    # Main Header
    "main_title": {
        "English": "Traffic Event Co-Pilot (Greater Hyderabad)",
        "తెలుగు": "ట్రాఫిక్ ఈవెంట్ కో-పైలట్ (గ్రేటర్ హైదరాబాద్)",
    },
    "main_caption": {
        "English": "Area: **{area}** | Event: **{event}** ({category}) | Plans traffic before the event happens.",
        "తెలుగు": "ప్రాంతం: **{area}** | ఈవెంట్: **{event}** ({category}) | ఈవెంట్ ప్రారంభానికి ముందే శాస్త్రీయ ట్రాఫిక్ ప్రణాళిక.",
    },
    "ai_chat_btn": {
        "English": "✨ AI Chat",
        "తెలుగు": "✨ ఏఐ చాట్ (AI Chat)",
    },

    # Data Status Strip
    "data_status_hdr": {
        "English": "Data status",
        "తెలుగు": "డేటా స్థితి (Data Status)",
    },
    "real_status": {
        "English": "**REAL** (OSM, advisories)",
        "తెలుగు": "**వాస్తవ డేటా (REAL)** (OSM నెట్‌వర్క్, పోలీసు సలహాలు)",
    },
    "assumed_status": {
        "English": "**ASSUMED** (parameters)",
        "తెలుగు": "**అనుకోబడినవి (ASSUMED)** (మోడల్ పారామితులు)",
    },
    "missing_status": {
        "English": "**MISSING** (event-day counts)",
        "తెలుగు": "**లభించనివి (MISSING)** (ఈవెంట్ రోజున లైవ్ కౌంట్లు)",
    },

    # Tabs
    "tab1_title": {
        "English": "1 · SIPOC overview",
        "తెలుగు": "1 · SIPOC అవలోకనం (Overview)",
    },
    "tab2_title": {
        "English": "2 · Suppliers → Inputs",
        "తెలుగు": "2 · వనరులు → ఇన్‌పుట్‌లు (Inputs)",
    },
    "tab3_title": {
        "English": "3 · Process",
        "తెలుగు": "3 · విశ్లేషణ ప్రక్రియ (Process)",
    },
    "tab4_title": {
        "English": "4 · Outputs",
        "తెలుగు": "4 · ఫలితాలు & మ్యాప్ (Outputs & Map)",
    },
    "tab5_title": {
        "English": "5 · 📋 Operational Plan & Customers",
        "తెలుగు": "5 · 📋 కార్యాచరణ ప్రణాళిక (Operational Plan)",
    },
    "tab6_title": {
        "English": "6 · 💬 Police Copilot Chatbot",
        "తెలుగు": "6 · 💬 పోలీసు కో-పైలట్ చాట్‌బాట్ (Police Chatbot)",
    },

    # Tab 1 Guidance
    "tab1_demo": {
        "English": "ℹ️ **SIPOC Overview (S, I, P, O, C):** Look at the complete system map and how real OSM network and police advisories balance with assumed parameters.",
        "తెలుగు": "ℹ️ **SIPOC అవలోకనం (S, I, P, O, C):** పూర్తి సిస్టమ్ మ్యాప్ మరియు వాస్తవ OSM రోడ్లు, పోలీసు అడ్వైజరీలతో పాటు అనుకోబడిన (ASSUMED) పారామితుల సమతుల్యతను పరిశీలించండి.",
    },
    "tab1_subhdr": {
        "English": "SIPOC of the Traffic Event Co-Pilot",
        "తెలుగు": "ట్రాఫిక్ ఈవెంట్ కో-పైలట్ - SIPOC ఫ్రేమ్‌వర్క్",
    },

    # Tab 2 Guidance
    "tab2_demo": {
        "English": "ℹ️ **S & I (Suppliers & Inputs):** Look at the selected event details, OSM network data quality, and the travel mode split.",
        "తెలుగు": "ℹ️ **S & I (వనరులు & ఇన్‌పుట్‌లు):** ఎంచుకున్న ఈవెంట్ వివరాలు, OSM రోడ్డు డేటా నాణ్యత మరియు ప్రయాణ సాధనాల విభజన (Mode Split) వివరాలను చూడండి.",
    },
    "tab2_subhdr": {
        "English": "Suppliers → Inputs",
        "తెలుగు": "వనరులు → ఇన్‌పుట్‌లు (Suppliers → Inputs)",
    },

    # Tab 3 Guidance
    "tab3_demo": {
        "English": "ℹ️ **P (Process):** Look at the 15-minute arrival PCU profile and how successive averaging reallocates traffic across roads.",
        "తెలుగు": "ℹ️ **P (ప్రక్రియ):** 15 నిమిషాల పీక్ అరైవల్ ప్రొఫైల్ మరియు ట్రాఫిక్ పునఃపంపిణీ అల్గారిథమ్ (Successive Averaging) విధానాన్ని పరిశీలించండి.",
    },
    "tab3_subhdr": {
        "English": "Process: what the Co-Pilot does, step by step",
        "తెలుగు": "విశ్లేషణ ప్రక్రియ: కో-పైలట్ ఎలా పనిచేస్తుంది (దశలవారీగా)",
    },

    # Tab 4 Guidance
    "tab4_demo": {
        "English": "ℹ️ **O (Outputs):** Look at critical congestion bottlenecks, diversion paths with detour penalties, and preset scenario comparisons.",
        "తెలుగు": "ℹ️ **O (ఫలితాలు):** కీలక రద్దీ కేంద్రాలు (Bottlenecks), డైవర్షన్ మార్గాలు, గ్రీన్ కారిడార్ మరియు వివిధ దృశ్యాల పోలికను పరిశీలించండి.",
    },
    "tab4_subhdr": {
        "English": "Outputs",
        "తెలుగు": "ఫలితాలు & ట్రాఫిక్ మ్యాప్ (Outputs & Map)",
    },
    "metric_vehicles": {
        "English": "Vehicles",
        "తెలుగు": "మొత్తం వాహనాలు (Vehicles)",
    },
    "metric_peak_pcu": {
        "English": "Peak PCU / hour",
        "తెలుగు": "గరిష్ట పీక్ PCU / గంట",
    },
    "metric_max_vc": {
        "English": "Max V/C (Co-Pilot)",
        "తెలుగు": "గరిష్ట V/C నిష్పత్తి",
    },
    "metric_roads_over_cap": {
        "English": "Roads over capacity",
        "తెలుగు": "సామర్థ్యానికి మించిన రోడ్లు",
    },
    "map_view_label": {
        "English": "Map shows",
        "తెలుగు": "మ్యాప్ ప్రదర్శన",
    },
    "map_opt": {
        "English": "Co-Pilot (optimised)",
        "తెలుగు": "కో-పైలట్ ఆప్టిమైజ్డ్ రూట్ (Optimised)",
    },
    "map_naive": {
        "English": "Naive shortest path",
        "తెలుగు": "సాధారణ షార్ట్‌కట్ రూట్ (Naive)",
    },
    "hotspots_hdr": {
        "English": "Congestion hotspots (streets)",
        "తెలుగు": "తీవ్ర ట్రాఫిక్ రద్దీ కేంద్రాలు (హాట్‌స్పాట్ రోడ్లు)",
    },
    "diversions_hdr": {
        "English": "Recommended diversions for the worst hotspots",
        "తెలుగు": "ప్రధాన రద్దీ కేంద్రాల కోసం సిఫార్సు చేయబడిన మళ్లింపులు (Diversions)",
    },
    "preset_hdr": {
        "English": "Scenario Preset Comparison",
        "తెలుగు": "వివిధ ఈవెంట్ దృశ్యాల పోలిక (Preset Comparison)",
    },

    # Tab 5 Guidance
    "tab5_demo": {
        "English": "ℹ️ **C (Customers):** Look at tailored deliverables for traffic police, event organizers, ambulances, and commuter advisories.",
        "తెలుగు": "ℹ️ **C (లబ్ధిదారులు):** ట్రాఫిక్ పోలీసులు, నిర్వాహకులు, అంబులెన్స్ సేవలు మరియు నిత్య ప్రయాణికులకు అందించే సూచనలను పరిశీలించండి.",
    },
    "tab5_plan_hdr": {
        "English": "📋 Special Traffic Operation Plan: {event}",
        "తెలుగు": "📋 ప్రత్యేక ట్రాఫిక్ బందోబస్తు ప్రణాళిక: {event}",
    },
    "tab5_authority_cap": {
        "English": "Authority: Hyderabad Traffic Police | Sector: {area} | Operational Phase: {phase}",
        "తెలుగు": "అధికార పరిధి: హైదరాబాద్ ట్రాఫిక్ పోలీస్ | సెక్టార్: {area} | కార్యాచరణ దశ: {phase}",
    },
    "dl_md": {
        "English": "📥 Download Plan (.MD)",
        "తెలుగు": "📥 ప్లాన్ డౌన్‌లోడ్ (.MD)",
    },
    "dl_txt": {
        "English": "📥 Download Plan (.TXT)",
        "తెలుగు": "📥 ప్లాన్ డౌన్‌లోడ్ (.TXT)",
    },
    "dl_csv": {
        "English": "📥 Download Hotspots (.CSV)",
        "తెలుగు": "📥 హాట్‌స్పాట్లు డౌన్‌లోడ్ (.CSV)",
    },
    "exp_crowd": {
        "English": "Expected Crowd",
        "తెలుగు": "అంచనా ప్రేక్షకులు",
    },
    "green_corridor_eta": {
        "English": "Green Corridor ETA [E-1]",
        "తెలుగు": "గ్రీన్ కారిడార్ సమయం [E-1]",
    },

    # Tab 6 Chatbot
    "chatbot_subhdr": {
        "English": "💬 Police Copilot Chatbot",
        "తెలుగు": "💬 పోలీసు కో-పైలట్ చాట్‌బాట్ (Police Copilot Chatbot)",
    },
    "chatbot_caption": {
        "English": "Ask operational questions regarding the traffic plan, bottlenecks [H], diversions [D], green corridors [E], and personnel deployment.",
        "తెలుగు": "ట్రాఫిక్ ప్రణాళిక, రద్దీ ప్రాంతాలు [H], మళ్లింపులు [D], ఎమర్జెన్సీ కారిడార్లు [E] మరియు సిబ్బంది మోహరింపుపై ప్రశ్నలు అడగండి.",
    },
    "quick_inquiries": {
        "English": "Quick Inquiries:",
        "తెలుగు": "సత్వర ప్రశ్నలు (Quick Inquiries):",
    },
    "btn_bottlenecks": {
        "English": "🚨 Critical Bottlenecks",
        "తెలుగు": "🚨 ప్రధాన రద్దీ ప్రాంతాలు",
    },
    "btn_diversions": {
        "English": "🔀 Diversion Directives",
        "తెలుగు": "🔀 ట్రాఫిక్ మళ్లింపు ఆదేశాలు",
    },
    "btn_emergency": {
        "English": "🚑 Emergency Corridor",
        "తెలుగు": "🚑 అత్యవసర గ్రీన్ కారిడార్",
    },
    "btn_deployment": {
        "English": "👮 Police Deployment",
        "తెలుగు": "👮 పోలీసు సిబ్బంది మోహరింపు",
    },
    "chat_input_ph": {
        "English": "Ask a question about this traffic plan...",
        "తెలుగు": "ఈ ట్రాఫిక్ ప్రణాళిక గురించి ఏదైనా అడగండి...",
    },
    "chat_greeting": {
        "English": "Hello, Officer. I have prepared the traffic operation plan for **{event}**. How can I help you understand the plan, manage bottlenecks, or position your personnel?",
        "తెలుగు": "నమస్కారం, ఆఫీసర్. **{event}** ఈవెంట్ కొరకు ట్రాఫిక్ కార్యాచరణ ప్రణాళికను సిద్ధం చేసాను. రద్దీ ప్రాంతాలు, ట్రాఫిక్ మళ్లింపులు లేదా పోలీసు సిబ్బంది మోహరింపును అర్థం చేసుకోవడంలో మీకు ఎలా సహాయపడగలను?",
    },
}


def t(key: str, lang: str = "English", **kwargs) -> str:
    """Retrieve translated string with optional formatting."""
    lang_key = "తెలుగు" if str(lang).strip() == "తెలుగు" else "English"
    entry = STRINGS.get(key, {})
    val = entry.get(lang_key, entry.get("English", key))
    if kwargs:
        try:
            return val.format(**kwargs)
        except Exception:
            return val
    return val


def get_sipoc_df(lang: str = "English") -> pd.DataFrame:
    """Generate bilingual SIPOC matrix dataframe."""
    if str(lang).strip() == "తెలుగు":
        return pd.DataFrame({
            "S: సరఫరాదారులు (Suppliers)": [
                "ఓపెన్‌స్ట్రీట్‌మ్యాప్ (రోడ్డు నెట్‌వర్క్)",
                "ట్రాఫిక్ పోలీసు అడ్వైజరీలు (రాచకొండ / హైదరాబాద్ / సైబరాబాద్)",
                "HMRL మెట్రో & TGSRTC బస్సు సర్వీసులు",
                "వార్తలు & ఈవెంట్ షెడ్యూల్స్ (తేదీలు, వేళలు)",
                "ఈవెంట్ నిర్వాహకులు (హాజరు సంఖ్య): ఇంకా కనెక్ట్ కాలేదు",
                "RTA వాహన డేటా (ఫ్లీట్ మిశ్రమం): ప్లాన్ చేయబడింది"
            ],
            "I: ఇన్‌పుట్‌లు (Inputs)": [
                "ఈవెంట్ పేరు, తేదీ, సమయం, అంచనా ప్రేక్షకులు",
                "వేదిక చుట్టూ 3 కి.మీ రోడ్డు నెట్‌వర్క్ గ్రాఫ్",
                "ప్రయాణ మోడ్ విభజన & ఆక్యుపెన్సీ (అనుకోబడినవి/ASSUMED)",
                "డైవర్షన్ పాయింట్లు మరియు సమయ వ్యవధులు",
                "ఈవెంట్ రోజున మెట్రో మరియు బస్సు మద్దతు",
                "వివిధ మార్గాల నుంచి వచ్చే ట్రాఫిక్ వాటా (Approach Shares)"
            ],
            "P: ప్రక్రియ (Process)": [
                "1 డేటా సేకరణ మరియు ప్రాసెసింగ్",
                "2 రోడ్డు గ్రాఫ్ నిర్మాణం, రోడ్డు సామర్థ్యం అంచనా",
                "3 రోడ్లకు కూడళ్లను అనుసంధానించడం (Snapping)",
                "4 PCU లో మోడ్ వారీగా ట్రాఫిక్ డిమాండ్ (15 నిమిషాల పీక్)",
                "5 రోడ్లపై ట్రాఫిక్ అసైన్‌మెంట్: నైవ్ vs ఆప్టిమైజ్డ్",
                "6 హాట్‌స్పాట్లు, మళ్లింపులు, గ్రీన్ కారిడార్, ప్లాన్ టెక్స్ట్"
            ],
            "O: ఫలితాలు (Outputs)": [
                "V/C నిష్పత్తితో తీవ్ర రద్దీ కేంద్రాలు (Hotspots)",
                "రంగుల కోడింగ్‌తో కూడిన ట్రాఫిక్ మ్యాప్",
                "అదనపు దూరంతో డైవర్షన్ మార్గాలు",
                "రక్షిత ఎమర్జెన్సీ గ్రీన్ కారిడార్ మరియు ప్రయాణ సమయం (ETA)",
                "వాట్-ఇఫ్ మెట్రో మళ్లింపు పోలిక",
                "పోలీసు కార్యాచరణ ప్రణాళిక (డౌన్‌లోడ్ ఫైల్)"
            ],
            "C: లబ్ధిదారులు (Customers)": [
                "ట్రాఫిక్ పోలీసు ప్రణాళికా అధికారులు",
                "ఈవెంట్ నిర్వాహక బృందం",
                "అత్యవసర విభాగాలు (108 అంబులెన్స్, అగ్నిమాపక)",
                "నిత్య ప్రయాణికులు మరియు ప్రేక్షకులు",
                "మెట్రో మరియు బస్సు రవాణా ఆపరేటర్లు",
                "ప్రాజెక్ట్ మూల్యాంకన కమిటీ / మెంటార్"
            ]
        })
    return pd.DataFrame({
        "S: Suppliers": [
            "OpenStreetMap (road network)", "Traffic police advisories (Rachakonda / Malkajgiri)",
            "HMRL metro and TGSRTC bus provisions", "News and event schedules (dates, start times)",
            "Event organiser (attendance): not yet connected", "RTA vehicle data (fleet mix): planned"
        ],
        "I: Inputs": [
            "Event name, date, start time, attendance", "3 km road graph around the stadium",
            "Mode split and occupancy (assumed)", "Diversion points and time windows",
            "Metro and bus support on match days", "Approach shares (where traffic comes from)"
        ],
        "P: Process": [
            "1 Collect and clean data", "2 Build road graph, estimate capacity", "3 Snap locations to roads",
            "4 Demand per mode in PCU, 15-min peak", "5 Load roads: naive vs optimised, V/C and delay",
            "6 Hotspots, diversions, emergency corridor, plan text"
        ],
        "O: Outputs": [
            "Congestion hotspots with V/C", "Colour-coded congestion map",
            "Diversion routes with extra distance", "Protected emergency corridor and ETA",
            "What-if comparison", "Event traffic plan (downloadable)"
        ],
        "C: Customers": [
            "Traffic police planners", "Event organiser", "Emergency services (ambulance, fire)",
            "Commuters and attendees", "Metro and bus operators", "Project mentor / evaluator"
        ]
    })


def build_telugu_report(res: dict[str, Any]) -> str:
    """
    Generate 100% authentic Telugu Traffic Operation Plan report mirroring build_report.
    Strictly labels all assumptions as 'అనుకోబడినవి (ASSUMED)'.
    Does NOT output any raw English report sections.
    """
    P = res.get("params", {})
    dem = res.get("demand", {})
    so = res.get("sum_opt", {})
    sn = res.get("sum_naive", {})
    hotspots = res.get("hotspots", pd.DataFrame())
    diversions = res.get("diversions", [])
    corridor = res.get("corridor")
    advisory = res.get("advisory", pd.DataFrame())

    event_name = P.get("event_name", "ఈవెంట్")
    phase = P.get("phase", "ingress")
    phase_te = "రాక (Ingress)" if phase == "ingress" else "నిష్క్రమణ (Egress)"
    start_time = P.get("start_time", "19:30")
    attendance = P.get("attendance", 0)

    L = []
    L.append(f"# 📋 ట్రాఫిక్ కార్యాచరణ మరియు బందోబస్తు ప్రణాళిక: {event_name}")
    L.append(f"*{phase_te} దశ, ఈవెంట్ ప్రారంభ సమయం {start_time}, అంచనా ప్రేక్షకులు {attendance:,} మంది (అనుకోబడినవి / ASSUMED).*\n")

    # 1. Impact summary
    L.append("## 1. ట్రాఫిక్ ప్రభావ సారాంశం (Impact summary)")
    L.append(f"- రోడ్డు వాహనాల డిమాండ్: **{dem.get('total_vehicles', 0):,} వాహనాలు = {dem.get('total_pcu', 0):,.0f} PCU** (బస్సులు: {dem.get('buses', 0)}).")
    L.append(f"- 15 నిమిషాల గరిష్ట రద్దీ ప్రారంభ సమయం: **{dem.get('peak_bucket', '18:45')}** వద్ద: {dem.get('peak_15min_pcu', 0):,.0f} PCU, ఇది గంటకు **{dem.get('peak_hourly_pcu', 0):,.0f} PCU/గంట** కు సమానం.")
    walk_count = dem.get("persons", {}).get("walk", 0) if isinstance(dem.get("persons"), dict) else 0
    L.append(f"- ప్రజా రవాణా & కాలినడకన: మెట్రో ద్వారా **{dem.get('metro_riders', 0):,.0f}** మంది మరియు కాలినడకన **{walk_count:,.0f}** మంది (మొత్తం పాదచారులు: {dem.get('pedestrians', 0):,.0f} మంది).")

    # 2. Bottlenecks
    L.append("\n## 2. రద్దీ కేంద్రాలు / బాటిల్‌నెక్స్ (మోడల్ అంచనా - ASSUMED)")
    L.append(f"- అనియంత్రిత సాధారణ రూటింగ్ (Naive unmanaged): గరిష్ట V/C **{sn.get('max_vc', 0):.2f}**, సామర్థ్యానికి మించిన రోడ్డు విభాగాలు {sn.get('congested', 0)}.")
    L.append(f"- కో-పైలట్ నియంత్రిత పంపిణీ (Co-Pilot managed): గరిష్ట V/C **{so.get('max_vc', 0):.2f}**, సామర్థ్యానికి మించిన రోడ్డు విభాగాలు {so.get('congested', 0)}, రద్దీ సమీపంలో ఉన్న రోడ్డు విభాగాలు (0.8–1.0) {so.get('near', 0)}.")
    L.append("\n**వ్యూహాత్మక రద్దీ కేంద్రాల మోహరింపు (`[H]` ట్యాగ్‌లు):**")

    road_type_map = {
        "primary": "ప్రధాన రహదారి (Primary)",
        "secondary": "ద్వితీయ రహదారి (Secondary)",
        "tertiary": "తృతీయ రహదారి (Tertiary)",
        "trunk": "ట్రంక్ రహదారి (Trunk)",
        "residential": "నివాస రోడ్డు (Residential)",
        "service": "సర్వీస్ రోడ్డు (Service)",
        "unclassified": "ఇతర రోడ్డు (Unclassified)"
    }

    if not hotspots.empty:
        for idx, (_, row) in enumerate(hotspots.head(6).iterrows()):
            tag = f"[H-{idx+1}]"
            rt = road_type_map.get(str(row.get("road_type", "")).lower(), str(row.get("road_type", "రహదారి")))
            st = row.get("street", "Unnamed road")
            lanes = row.get("lanes", 1)
            load = row.get("load_pcu_hr", 0)
            cap = row.get("capacity_pcu_hr", 0)
            vc = row.get("vc", 0.0)
            fed = row.get("fed_by", "అన్ని మార్గాలు")
            L.append(f"- **{tag} {st}** ({rt}, {lanes} లేన్): పీక్ లోడ్ {load:,.0f} vs సామర్థ్యం {cap:,.0f} PCU/గం (V/C **{vc:.2f}**); వచ్చే ట్రాఫిక్ ప్రవాహం: *{fed}*.")

    # 3. Diversions
    L.append("\n## 3. ట్రాఫిక్ మళ్లింపు వ్యూహం (Diversion scheme)")
    L.append("**వ్యూహాత్మక మళ్లింపు ఆదేశాలు (`[D]` ట్యాగ్‌లు):**")
    for idx, d in enumerate(diversions):
        tag = d.get("tag", f"[D-{idx+1}]")
        d_name = d.get("name", "రద్దీ కేంద్రం")
        d_vc = d.get("vc", 0.0)
        if d.get("feasible"):
            extra_m = d.get("extra_m", 0)
            extra_s = d.get("extra_s", 0)
            L.append(f"- **{tag} {d_name}** (రద్దీ ఉపశమనం V/C {d_vc:.2f}): ప్రత్యామ్నాయ దారి అదనంగా **+{extra_m:,} మీటర్లు** మరియు **+{extra_s} సెకన్లు**. పాస్ లేని సాధారణ ప్రైవేట్ వాహనాలను ఇక్కడికి మళ్లించండి.")
        else:
            d_note = d.get("note", "సురక్షిత ప్రత్యామ్నాయం లేదు")
            L.append(f"- **{tag} {d_name}** (రద్దీ ఉపశమనం V/C {d_vc:.2f}): **సురక్షిత ప్రత్యామ్నాయ దారి అందుబాటులో లేదు** ({d_note}). యూ-టర్న్ / వెనక్కి తిప్పేలా కఠినంగా అమలు చేయండి.")

    if advisory is not None and not advisory.empty:
        L.append("\n- **ఈ తేదీకి అధికారిక పోలీసు అడ్వైజరీ మళ్లింపులు:**")
        for _, a in advisory.drop_duplicates(["Movement", "Diversion_Point"]).iterrows():
            L.append(f"  - *{a.get('Movement')}*: **{a.get('Diversion_Point')}** వద్ద మళ్లింపు -> {a.get('Diverted_Route')}")

    # 4. Emergency protection
    L.append("\n## 4. అత్యవసర రక్షణ & గ్రీన్ కారిడార్ (Emergency protection)")
    if corridor:
        hosp_note = (
            "ఆసుపత్రి లొకేషన్ ప్లేస్‌హోల్డర్ (అనుకోబడినది / ASSUMED)"
            if res.get("hospital_is_placeholder", True)
            else "ఆసుపత్రి లొకేషన్ వెరిఫై చేయబడింది"
        )
        c_len = corridor.get("length_m", 0)
        c_free = corridor.get("free_min", 0)
        c_unprot = corridor.get("unprotected_min", 0)
        time_saved = max(0, c_unprot - c_free)
        L.append(f"- రక్షిత అత్యవసర గ్రీన్ కారిడార్ **`[E-1]`**: **{c_len:,} మీటర్లు**.")
        L.append(f"  - రక్షిత క్లియర్ లేన్ ప్రయాణ సమయం (ETA): **{c_free} నిమిషాలు** (ఈవెంట్ ట్రాఫిక్ లేకుండా క్లియర్‌గా ఉంచినప్పుడు).")
        L.append(f"  - రద్దీలో ప్రయాణ సమయం (అన్‌ప్రొటెక్టెడ్ ETA): **{c_unprot} నిమిషాలు** ({hosp_note}).")
        L.append(f"  - ట్రామా రోగుల తరలింపులో ఆదా అయ్యే కీలక సమయం: **{time_saved:.1f} నిమిషాలు**.")

    # 5. Sectorization & Checkpoints
    L.append("\n## 5. సెక్టరైజేషన్ & ప్రవేశ చెక్‌పాయింట్లు (`[J]` మరియు `[P]` ట్యాగ్‌లు)")
    L.append("**ప్రవేశ చెక్‌పాయింట్ కూడళ్లు (`[J]` ట్యాగ్‌లు):**")
    for j in res.get("tagged_junctions", []):
        L.append(f"- **{j['tag']} {j['name']}**: ప్రేక్షకుల ట్రాఫిక్‌లో **{j['share']*100:.0f}%** నిర్వహించే ప్రవేశ చెక్‌పాయింట్.")
    L.append("\n**ప్రేక్షకుల పార్కింగ్ జోన్లు (`[P]` ట్యాగ్‌లు):**")
    for p in res.get("tagged_parking", []):
        L.append(f"- **{p['tag']}**: నిర్దేశిత ప్రేక్షకుల పార్కింగ్ / హోల్డింగ్ జోన్ (కోఆర్డినేట్లు: {p['xy'][0]:.4f}, {p['xy'][1]:.4f} - అనుకోబడినవి / ASSUMED).")

    # 6. Police Deployment Guidance
    L.append("\n## 6. పోలీసు బలగాల మోహరింపు మార్గదర్శకాలు (అనుకోబడినవి / ASSUMED Heuristics)")
    tot_veh = dem.get("total_vehicles", 0)
    hs_count = len(hotspots)
    traffic_si = max(2, round(hs_count * 0.8))
    traffic_constables = max(10, round(tot_veh / 800) + hs_count * 4)
    marshals = max(6, round(dem.get("pedestrians", 0) / 2500))
    L.append(f"- **సెక్టార్ అధికారులు (ఎస్సైలు/ఇన్‌స్పెక్టర్లు):** సెక్టార్లలో పర్యవేక్షణ కోసం సుమారు ~{traffic_si} మంది అధికారులు.")
    L.append(f"- **ట్రాఫిక్ కానిస్టేబుళ్లు / సిబ్బంది:** చెక్‌పాయింట్లు `[J-1]`–`[J-4]` మరియు డైవర్షన్లు `[D-1]`–`[D-3]` వద్ద సుమారు ~{traffic_constables} మంది సిబ్బంది.")
    L.append(f"- **క్రౌడ్ కంట్రోలర్లు / మార్షల్స్:** మెట్రో స్టేషన్లు, ఎంట్రీ గేట్ల వద్ద క్రౌడ్ కంట్రోల్ కోసం సుమారు ~{marshals} మంది సిబ్బంది.")

    # 7. Public Advisory Bulletin
    L.append("\n## 7. ప్రజలకు ట్రాఫిక్ సలహా బులెటిన్ (Public Advisory Bulletin)")
    top_str = ", ".join(hotspots.head(3)["street"].tolist()) if len(hotspots) else "వేదిక పరిసర ప్రాంతాలు"
    L.append(f"> వేదిక పరిసరాల్లో {start_time} నుండి భారీ ట్రాఫిక్ రద్దీ ఉండే అవకాశం ఉంది. {top_str} రహదారులను నివారించండి. "
             f"నిత్య ప్రయాణికులు మరియు ప్రేక్షకులు మెట్రో లేదా TGSRTC ప్రత్యేక షటిల్ బస్సులను ఉపయోగించాలని కోరడమైనది.")

    # 8. Data status
    L.append("\n## 8. డేటా స్థితి (Data Status)")
    L.append("- రోడ్డు నెట్‌వర్క్: ఓపెన్‌స్ట్రీట్‌మ్యాప్ (వాస్తవ డేటా - REAL). ఈవెంట్ తేదీలు, అడ్వైజరీలు, మళ్లింపులు: అధికారిక పోలీసు సలహాలు (వాస్తవ డేటా - REAL).")
    L.append("- ఈవెంట్ రోజుల్లో లైవ్ వాహనాల కౌంట్లు, వేగాలు, క్యూలు: **లభించలేదు (MISSING)**; ఇక్కడ పేర్కొన్న అన్ని ట్రాఫిక్ లోడ్లు మోడల్ అంచనాలు మాత్రమే (అనుకోబడిన పారామితులు / ASSUMED parameters).")

    return "\n".join(L)


def translate_report_to_telugu(report_md: str, res: dict[str, Any]) -> str:
    """Provide complete authentic Telugu operational plan for the police report."""
    return build_telugu_report(res)
