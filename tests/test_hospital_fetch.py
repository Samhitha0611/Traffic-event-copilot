import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import prepare_city_data as P  # noqa: E402
import venue_catalog as VC  # noqa: E402


class R:
    status_code = 200
    def __init__(self, data): self._d = data
    def raise_for_status(self): pass
    def json(self): return self._d


def test_hospitals_from_nominatim_are_filtered_deduped_and_saved(monkeypatch, tmp_path):
    csv = tmp_path / "h.csv"
    pd.DataFrame({"Hospital_Name": ["Gandhi Hospital"], "Zone": ["x"], "Latitude": [17.4], "Longitude": [78.5], "Source": ["s"]}).to_csv(csv, index=False)
    monkeypatch.setattr(VC, "HOSPITALS_CSV", csv)
    monkeypatch.setattr("time.sleep", lambda s: None)
    data = [
        {"name": "Gandhi Hospital", "type": "hospital", "lat": "17.4", "lon": "78.5"},            # already known
        {"name": "Sunshine Hospitals", "type": "hospital", "lat": "17.43", "lon": "78.46"},       # new
        {"name": "City Pharmacy", "type": "pharmacy", "lat": "17.41", "lon": "78.47"},            # not a hospital
        {"name": "Sunshine Hospitals", "type": "hospital", "lat": "17.43", "lon": "78.46"},       # duplicate
    ]
    class S:
        def get(self, url, params=None, **k):
            assert "viewbox" in params and params["bounded"] == 1
            return R(data)
    assert P.add_hospitals(17.42, 78.47, session=S()) == 1
    out = pd.read_csv(csv)
    assert list(out["Hospital_Name"]) == ["Gandhi Hospital", "Sunshine Hospitals"]
