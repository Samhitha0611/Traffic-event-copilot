import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import check_all_venues as C  # noqa: E402
import venue_catalog as VC  # noqa: E402


def test_check_venue_reports_ok_for_a_saved_map_and_no_map_otherwise(monkeypatch):
    v = VC.get_hyderabad_location_suggestions()["Gachibowli Stadium"]
    row = C.check_venue("Gachibowli Stadium", v, {})
    assert row["status"] in ("OK", "CHECK") and row["approaches"] >= 3
    monkeypatch.setattr(C, "map_path_if_available", lambda *a, **k: None)
    assert C.check_venue("X", v, {})["status"] == "NO MAP"
