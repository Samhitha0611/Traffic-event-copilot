"""
Tests for Bilingual (English / Telugu) Internationalization and Chatbot features.
"""
import pytest
import pandas as pd
from src.translations import t, get_sipoc_df, translate_report_to_telugu, build_telugu_report
import src.police_chatbot as PC


def test_translation_strings():
    """Verify core UI strings exist in both English and Telugu."""
    assert t("event_setup", "English") == "🚦 Event setup"
    assert "ఈవెంట్ సెటప్" in t("event_setup", "తెలుగు")

    assert t("main_title", "English") == "Traffic Event Co-Pilot (Greater Hyderabad)"
    assert "ట్రాఫిక్ ఈవెంట్ కో-పైలట్" in t("main_title", "తెలుగు")

    assert "REAL" in t("real_status", "English")
    assert "వాస్తవ డేటా" in t("real_status", "తెలుగు")


def test_bilingual_sipoc():
    """Verify SIPOC table renders with all 5 dimensions in both languages."""
    df_en = get_sipoc_df("English")
    assert len(df_en) == 6
    assert any("S: Suppliers" in col for col in df_en.columns)
    assert any("C: Customers" in col for col in df_en.columns)

    df_te = get_sipoc_df("తెలుగు")
    assert len(df_te) == 6
    assert any("సరఫరాదారులు" in col for col in df_te.columns)
    assert any("లబ్ధిదారులు" in col for col in df_te.columns)


def test_police_chatbot_telugu_response():
    """Verify police chatbot returns authentic Telugu response when language is Telugu."""
    res = {
        "params": {"event_name": "Mahabharat Show", "attendance": 25000, "phase": "ingress", "start_time": "19:00"},
        "demand": {"total_vehicles": 8000, "peak_hourly_pcu": 3500},
        "sum_opt": {"max_vc": 1.45, "congested": 8, "near": 4},
        "hotspots": pd.DataFrame([{"street": "Road No 36", "vc": 1.45, "load_pcu_hr": 2800, "capacity_pcu_hr": 1900, "fed_by": "North"}]),
        "diversions": [{"tag": "[D-1]", "name": "Road No 36", "vc": 1.45, "feasible": True, "extra_m": 450, "extra_s": 90}],
        "corridor": {"length_m": 3200, "free_min": 5.2, "unprotected_min": 18.5}
    }

    # Query in English with Telugu language selected
    resp_bottlenecks = PC.generate_police_response("What are the bottlenecks?", res, lang="తెలుగు")
    assert "ట్రాఫిక్ రద్దీ హాట్‌స్పాట్లు" in resp_bottlenecks
    assert "Mahabharat Show" in resp_bottlenecks

    # Query in Telugu script
    resp_ambulance = PC.generate_police_response("అంబులెన్స్ ఎమర్జెన్సీ కారిడార్ సమయం ఎంత?", res, lang="తెలుగు")
    assert "అత్యవసర గ్రీన్ కారిడార్" in resp_ambulance
    assert "5.2 నిమిషాలు" in resp_ambulance


def test_translate_report_to_telugu():
    """Verify Telugu operational directives include all required tactical tags."""
    res = {
        "params": {"event_name": "Mahabharat Show", "venue_name": "Shilpakala Vedika", "attendance": 20000, "start_time": "18:30", "phase": "ingress"},
        "demand": {"total_vehicles": 6000, "peak_hourly_pcu": 2800},
        "sum_opt": {"congested": 5},
        "hotspots": pd.DataFrame([{"street": "Hitec City Main Road", "vc": 1.35, "load_pcu_hr": 2400}]),
        "diversions": [{"tag": "[D-1]", "name": "Cyber Towers Junction", "note": "Divert through Mindspace"}],
        "corridor": {"length_m": 2800, "free_min": 4.5, "unprotected_min": 14.0}
    }
    sample_report = "# Original English Report\n- Section 1"
    te_report = translate_report_to_telugu(sample_report, res)

    assert "ట్రాఫిక్ కార్యాచరణ మరియు బందోబస్తు ప్రణాళిక" in te_report
    assert "Mahabharat Show" in te_report
    assert "[E-1]" in te_report
    assert "ASSUMED" in te_report


def test_build_telugu_report_all_sections():
    """Verify build_telugu_report renders all 8 sections in Telugu with zero English section headers."""
    res = {
        "params": {
            "event_name": "SRH IPL Match 2026",
            "attendance": 39000,
            "start_time": "19:30",
            "phase": "ingress"
        },
        "demand": {
            "total_vehicles": 13572,
            "total_pcu": 9106,
            "buses": 117,
            "peak_bucket": "18:45",
            "peak_15min_pcu": 2656,
            "peak_hourly_pcu": 10624,
            "metro_riders": 5850,
            "pedestrians": 9750,
            "persons": {"walk": 3900}
        },
        "sum_naive": {"max_vc": 1.90, "congested": 66},
        "sum_opt": {"max_vc": 1.77, "congested": 64, "near": 61},
        "hotspots": pd.DataFrame([{
            "street": "Habsiguda Main Road",
            "road_type": "primary",
            "lanes": 2,
            "vc": 1.77,
            "load_pcu_hr": 5447,
            "capacity_pcu_hr": 3420,
            "fed_by": "Boduppal, Tarnaka"
        }]),
        "diversions": [{
            "tag": "[D-1]",
            "name": "Street 8",
            "vc": 1.77,
            "feasible": True,
            "extra_m": 450,
            "extra_s": 85,
            "note": "OK"
        }],
        "corridor": {
            "length_m": 800,
            "free_min": 1.2,
            "unprotected_min": 5.4
        },
        "tagged_junctions": [
            {"tag": "[J-1]", "name": "Uppal X Roads", "share": 0.35}
        ],
        "tagged_parking": [
            {"tag": "[P-1]", "xy": (17.405, 78.555)}
        ],
        "advisory": pd.DataFrame([
            {"Movement": "Heavy vehicles", "Diversion_Point": "Nagole", "Diverted_Route": "LB Nagar"}
        ]),
        "hospital_is_placeholder": True
    }

    report = build_telugu_report(res)

    # 1. Title and event details in Telugu
    assert "ట్రాఫిక్ కార్యాచరణ మరియు బందోబస్తు ప్రణాళిక: SRH IPL Match 2026" in report
    assert "రాక (Ingress) దశ" in report
    assert "అనుకోబడినవి / ASSUMED" in report

    # 2. All 8 sections present in Telugu
    assert "## 1. ట్రాఫిక్ ప్రభావ సారాంశం (Impact summary)" in report
    assert "## 2. రద్దీ కేంద్రాలు / బాటిల్‌నెక్స్ (మోడల్ అంచనా - ASSUMED)" in report
    assert "## 3. ట్రాఫిక్ మళ్లింపు వ్యూహం (Diversion scheme)" in report
    assert "## 4. అత్యవసర రక్షణ & గ్రీన్ కారిడార్ (Emergency protection)" in report
    assert "## 5. సెక్టరైజేషన్ & ప్రవేశ చెక్‌పాయింట్లు (`[J]` మరియు `[P]` ట్యాగ్‌లు)" in report
    assert "## 6. పోలీసు బలగాల మోహరింపు మార్గదర్శకాలు (అనుకోబడినవి / ASSUMED Heuristics)" in report
    assert "## 7. ప్రజలకు ట్రాఫిక్ సలహా బులెటిన్ (Public Advisory Bulletin)" in report
    assert "## 8. డేటా స్థితి (Data Status)" in report

    # 3. Tactical tags present
    assert "[H-1]" in report
    assert "[D-1]" in report
    assert "[E-1]" in report
    assert "[J-1]" in report
    assert "[P-1]" in report

    # 4. Zero English section headers leaked
    assert "## 1. Impact summary" not in report
    assert "## 2. Bottlenecks (model estimate)" not in report
    assert "## 3. Diversion scheme" not in report
    assert "## 4. Emergency protection" not in report
    assert "## 5. Sectorization" not in report
    assert "## 6. Police Deployment Guidance" not in report
    assert "## 7. Public Advisory Bulletin" not in report
    assert "## 8. Data status" not in report


def test_police_chatbot_all_categories_in_telugu():
    """Verify chatbot answers all police operational queries in 100% Telugu when Telugu is selected."""
    res = {
        "params": {"event_name": "SRH IPL Match 2026", "attendance": 39000, "phase": "ingress", "start_time": "19:30"},
        "demand": {"total_vehicles": 13572, "peak_hourly_pcu": 10624, "pedestrians": 9750, "metro_riders": 5850, "vehicles": {"car": 4000, "two_wheeler": 9000, "bus": 117}, "mode_share": {"car": 0.25, "two_wheeler": 0.25}},
        "sum_opt": {"max_vc": 1.77, "congested": 64, "near": 61},
        "hotspots": pd.DataFrame([{"street": "Street 8", "vc": 1.77, "load_pcu_hr": 2542, "capacity_pcu_hr": 1440, "fed_by": "Boduppal"}]),
        "diversions": [{"tag": "[D-1]", "name": "Street 8", "vc": 1.77, "feasible": True, "extra_m": 450, "extra_s": 85}],
        "corridor": {"length_m": 800, "free_min": 1.2, "unprotected_min": 5.4},
        "hospital_is_placeholder": True,
        "parking_is_generated": True
    }

    # Bottlenecks
    ans_hot = PC.generate_police_response("hotspots", res, lang="తెలుగు")
    assert "ట్రాఫిక్ రద్దీ హాట్‌స్పాట్లు" in ans_hot
    assert "[H-1]" in ans_hot

    # Diversions
    ans_div = PC.generate_police_response("diversions", res, lang="తెలుగు")
    assert "ట్రాఫిక్ మళ్లింపు వ్యూహం" in ans_div
    assert "[D-1]" in ans_div

    # Emergency corridor
    ans_em = PC.generate_police_response("ambulance ETA", res, lang="తెలుగు")
    assert "రక్షిత అత్యవసర గ్రీన్ కారిడార్" in ans_em
    assert "[E-1]" in ans_em

    # Police deployment
    ans_dep = PC.generate_police_response("police deployment", res, lang="తెలుగు")
    assert "పోలీసు సిబ్బంది మోహరింపు" in ans_dep
    assert "సెక్టార్ అధికారులు" in ans_dep

    # Parking & Transit
    ans_park = PC.generate_police_response("parking and buses", res, lang="తెలుగు")
    assert "పార్కింగ్ మరియు ప్రజా రవాణా నిర్వహణ" in ans_park
    assert "[P-1]" in ans_park

    # Default overview
    ans_def = PC.generate_police_response("hello copilot", res, lang="తెలుగు")
    assert "ట్రాఫిక్ కో-పైలట్ ప్రణాళిక అవలోకనం" in ans_def
