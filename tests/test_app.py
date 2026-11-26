"""
AppTest smoke tests for the Gemini-style Agentic AI Traffic Event Co-Pilot UI:
1. Initial onboarding shows "Where should we start?" in English ONLY (no Telugu leaked)
2. Switching language to Telugu switches onboarding to Telugu ONLY
3. Clicking through the 4 wizard steps leads to the Overview + Proceed button
"""
from pathlib import Path
from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parents[1] / "app.py")


def test_apptest_gemini_onboarding_english_only():
    """Verify initial landing screen is English-only and shows venue suggestion chips."""
    at = AppTest.from_file(APP_PATH, default_timeout=120)
    at.run()
    assert not at.exception

    md_all = "\n".join(m.value for m in at.markdown)
    assert "Where should we start?" in md_all
    assert "మనం ఎక్కడి నుండి" not in md_all  # no Telugu when English is selected

    # Venue chip buttons exist
    btn_labels = [b.label for b in at.button]
    assert any("Uppal Stadium" in lbl for lbl in btn_labels)


def test_apptest_gemini_onboarding_telugu_only():
    """Verify switching language to Telugu updates onboarding to Telugu only."""
    at = AppTest.from_file(APP_PATH, default_timeout=120)
    at.run()
    assert not at.exception

    lang_radios = [r for r in at.radio if r.options == ["English", "తెలుగు"]]
    assert len(lang_radios) == 1
    lang_radios[0].set_value("తెలుగు").run()
    assert not at.exception

    md_all = "\n".join(m.value for m in at.markdown)
    assert "మనం ఎక్కడి నుండి ప్రారంభిద్దాం?" in md_all
    assert "Where should we start?" not in md_all


def test_apptest_wizard_click_through_to_overview():
    """Verify clicking chips through steps 1->2->3->4 reaches the Overview screen."""
    at = AppTest.from_file(APP_PATH, default_timeout=120)
    at.run()
    assert not at.exception

    # Step 0 -> pick Uppal Stadium
    uppal_btn = next(b for b in at.button if "Uppal Stadium" in b.label)
    uppal_btn.click().run()
    assert not at.exception

    # Step 1 -> pick Cricket / Sports Match
    cricket_btn = next(b for b in at.button if "Cricket / Sports Match" in b.label)
    cricket_btn.click().run()
    assert not at.exception

    # Step 2 -> pick Large crowd
    large_btn = next(b for b in at.button if "Large" in b.label)
    large_btn.click().run()
    assert not at.exception

    # Step 3 -> pick 19:30 Ingress slot
    slot_btn = next(b for b in at.button if "19:30" in b.label)
    slot_btn.click().run()
    assert not at.exception

    # Step 4 -> Overview + Proceed button visible
    md_all = "\n".join(m.value for m in at.markdown)
    assert "Selected Event Overview" in md_all
    assert any("Proceed & Create Traffic Plan" in b.label for b in at.button)
