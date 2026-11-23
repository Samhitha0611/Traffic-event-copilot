"""
AppTest smoke tests for app.py UI features:
1. Demo mode checkbox and SIPOC tab captions (S, I, P, O, C)
2. Preset scenario comparison table in Outputs tab
3. Data status strip at the top
"""
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parents[1] / "app.py")


def test_apptest_data_status_strip():
    """Verify that the Data Status strip is rendered at the top of the app."""
    at = AppTest.from_file(APP_PATH, default_timeout=300)
    at.run()
    assert not at.exception

    # Check that REAL, ASSUMED, and MISSING status indicators are present
    success_texts = [s.value for s in at.success]
    assert any("REAL" in text and "(OSM, advisories)" in text for text in success_texts)

    warning_texts = [w.value for w in at.warning]
    assert any("ASSUMED" in text and "(parameters)" in text for text in warning_texts)

    error_texts = [e.value for e in at.error]
    assert any("MISSING" in text and "(event-day counts)" in text for text in error_texts)


def test_apptest_demo_mode_toggle_and_sipoc_captions():
    """Verify Demo mode checkbox in sidebar toggles SIPOC guidance captions under each tab."""
    at = AppTest.from_file(APP_PATH, default_timeout=300)
    at.run()
    assert not at.exception

    # Find the Demo mode checkbox in the sidebar
    demo_checkboxes = [c for c in at.sidebar.checkbox if c.label == "Demo mode"]
    assert len(demo_checkboxes) == 1
    demo_box = demo_checkboxes[0]
    assert demo_box.value is False

    # Captions when Demo mode is OFF should not contain tab-specific SIPOC guidance
    captions_off = [c.value for c in at.caption]
    assert not any("(S, I, P, O, C)" in c for c in captions_off)
    assert not any("S & I (Suppliers & Inputs)" in c for c in captions_off)

    # Turn Demo mode ON and re-run
    demo_box.check().run()
    assert not at.exception

    captions_on = [c.value for c in at.caption]
    # Check that each SIPOC letter is present with guidance
    assert any("SIPOC Overview (S, I, P, O, C)" in c for c in captions_on)
    assert any("S & I (Suppliers & Inputs)" in c for c in captions_on)
    assert any("P (Process)" in c for c in captions_on)
    assert any("O (Outputs)" in c for c in captions_on)
    assert any("C (Customers)" in c for c in captions_on)


def test_apptest_preset_scenario_comparison_table():
    """Verify the scenario comparison table in the Outputs tab displays the 4 presets side-by-side."""
    at = AppTest.from_file(APP_PATH, default_timeout=300)
    at.run()
    assert not at.exception

    # Locate the comparison table dataframe
    target_df = None
    for df_element in at.dataframe:
        df = df_element.value
        if "Scenario Preset" in df.columns:
            target_df = df
            break

    assert target_df is not None, "Scenario preset comparison table dataframe not found"

    # Verify expected side-by-side metric columns
    expected_cols = ["Scenario Preset", "Vehicles", "Peak PCU/hour", "Max V/C", "Roads over capacity"]
    for col in expected_cols:
        assert col in target_df.columns

    # Verify all 4 required presets are present
    presets_found = list(target_df["Scenario Preset"])
    assert "IPL weeknight 19:30 ingress" in presets_found
    assert "IPL weekend 15:30 ingress" in presets_found
    assert "Same weekend match egress" in presets_found
    assert "20% metro shift" in presets_found


def test_apptest_run_copilot_button_gate():
    """Verify simulation only runs on initial load and after clicking 'Run Co-Pilot', not automatically on input change."""
    at = AppTest.from_file(APP_PATH, default_timeout=300)
    at.run()
    assert not at.exception

    # Change attendance in sidebar
    att_inputs = [num for num in at.sidebar.number_input if "Expected Attendance" in num.label]
    assert len(att_inputs) == 1
    att_inputs[0].set_value(50000).run()
    assert not at.exception

    # Should show pending input changes warning, and NOT recompute until Run Co-Pilot is clicked
    sidebar_warnings = [w.value for w in at.sidebar.warning]
    assert any("Pending input changes" in w for w in sidebar_warnings)

    # Click '▶ Run Co-Pilot' button
    run_buttons = [b for b in at.sidebar.button if "Run Co-Pilot" in b.label]
    assert len(run_buttons) == 1
    run_buttons[0].click().run()
    assert not at.exception

    # Warning should be gone after clicking run
    sidebar_warnings_after = [w.value for w in at.sidebar.warning]
    assert not any("Pending input changes" in w for w in sidebar_warnings_after)


def test_apptest_chatbot_event_name_sync():
    """Verify chatbot greeting and plan sync to new event name when Run Co-Pilot is clicked."""
    at = AppTest.from_file(APP_PATH, default_timeout=300)
    at.run()
    assert not at.exception

    # Initially chatbot has SRH IPL Match 2026
    chat_hist = at.session_state.get("chat_history", [])
    assert any("SRH IPL Match 2026" in msg.get("content", "") for msg in chat_hist)

    # Change event name to 'mahabhrat show' and click Run Co-Pilot
    name_inputs = [t for t in at.sidebar.text_input if "Event Name" in t.label or "ఈవెంట్ పేరు" in t.label]
    assert len(name_inputs) == 1
    name_inputs[0].set_value("mahabhrat show")

    run_buttons = [b for b in at.sidebar.button if "Run Co-Pilot" in b.label]
    assert len(run_buttons) == 1
    run_buttons[0].click().run()
    assert not at.exception

    # Chatbot history should now greet with mahabhrat show
    chat_hist_after = at.session_state.get("chat_history", [])
    assert any("mahabhrat show" in msg.get("content", "") for msg in chat_hist_after)
    assert not any("SRH IPL Match 2026" in msg.get("content", "") for msg in chat_hist_after)


def test_apptest_language_switch_to_telugu():
    """Verify bilingual language switch from English to Telugu updates titles and controls."""
    at = AppTest.from_file(APP_PATH, default_timeout=300)
    at.run()
    assert not at.exception

    # Locate language radio button on top left corner
    lang_radios = [r for r in at.sidebar.radio if "Language" in r.label or "భాష" in r.label]
    assert len(lang_radios) == 1
    lang_radio = lang_radios[0]
    assert lang_radio.value == "English"

    # Switch to Telugu and re-run
    lang_radio.set_value("తెలుగు").run()
    assert not at.exception

    # Check title is in Telugu
    titles = [t.value for t in at.title]
    assert any("ట్రాఫిక్ ఈవెంట్ కో-పైలట్" in t for t in titles)

    # Check report in Tab 5 is in Telugu and has no raw English section headers
    markdown_texts = [m.value for m in at.markdown]
    assert any("ట్రాఫిక్ కార్యాచరణ మరియు బందోబస్తు ప్రణాళిక" in m for m in markdown_texts)
    assert not any("## 1. Impact summary" in m for m in markdown_texts)

    # Check chatbot greeting in session state switched to Telugu
    chat_hist = at.session_state.get("chat_history", [])
    assert any("నమస్కారం, ఆఫీసర్" in msg.get("content", "") for msg in chat_hist)


