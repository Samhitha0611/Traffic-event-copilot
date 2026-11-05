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
    at = AppTest.from_file(APP_PATH, default_timeout=60)
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
    at = AppTest.from_file(APP_PATH, default_timeout=60)
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
    at = AppTest.from_file(APP_PATH, default_timeout=60)
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

