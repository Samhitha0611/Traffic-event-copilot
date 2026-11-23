"""Tests for: no silent Uppal fallback, other-venue approaches, hospital choice, honest data labels."""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import event_engine as E  # noqa: E402
import observed_speeds as OS  # noqa: E402
import osm_download as OD  # noqa: E402
import traffic_profiles as TP  # noqa: E402
import venue_catalog as VC  # noqa: E402

GACH = (17.449409, 78.348468)


def test_failed_download_raises_and_never_returns_uppal(monkeypatch, tmp_path):
    monkeypatch.setattr(OD, "NETWORKS_DIR", tmp_path)
    monkeypatch.setattr(OD, "find_covering_graph", lambda *a, **k: None)
    monkeypatch.setattr(OD, "pick_endpoint", lambda force=False: (_ for _ in ()).throw(OD.NetworkUnavailable("blocked")))
    monkeypatch.setattr(OD, "download_graph_via_api", lambda *a, **k: (_ for _ in ()).throw(OD.NetworkUnavailable("api blocked")))
    OD._FAILED.clear()
    with pytest.raises(OD.NetworkUnavailable):
        OD.get_graph_for_venue("somewhere_new", 17.45, 78.38)
    with pytest.raises(OD.NetworkUnavailable):
        VC.get_road_network_path("somewhere_new", 17.45, 78.38)


def test_failure_is_remembered_so_the_app_does_not_retry_every_click(monkeypatch, tmp_path):
    monkeypatch.setattr(OD, "NETWORKS_DIR", tmp_path)
    monkeypatch.setattr(OD, "find_covering_graph", lambda *a, **k: None)
    calls = []
    def boom(*a, **k):
        calls.append(1); raise OD.NetworkUnavailable("blocked")
    monkeypatch.setattr(OD, "download_graph", boom)
    OD._FAILED.clear()
    for _ in range(3):
        with pytest.raises(OD.NetworkUnavailable):
            OD.get_graph_for_venue("venue_x", 17.45, 78.38)
    assert len(calls) == 1
    with pytest.raises(OD.NetworkUnavailable):
        OD.get_graph_for_venue("venue_x", 17.45, 78.38, force_retry=True)
    assert len(calls) == 2


def test_cached_venue_and_uppal_still_load():
    assert VC.get_road_network_path("gachibowli_stadium", *GACH).name == "gachibowli_stadium.graphml"
    assert VC.get_road_network_path("uppal_stadium", 17.4065, 78.5505).name == "uppal_road_network.graphml"


def test_probe_returns_false_on_network_error(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: (_ for _ in ()).throw(requests.ConnectTimeout()))
    assert OD.probe("https://example.invalid/api") is False


def test_overpass_urls_can_be_set_by_environment(monkeypatch):
    monkeypatch.setenv("OVERPASS_URLS", "https://a.test/api/, https://b.test/api")
    assert OD.endpoints() == ["https://a.test/api", "https://b.test/api"]


@pytest.fixture(scope="module")
def gach():
    return E.build_network(ROOT / "data" / "networks" / "gachibowli_stadium.graphml")


def test_auto_approaches_come_from_real_roads_and_shares_sum_to_one(gach):
    D, _ = gach
    ap = E.auto_approaches(D, GACH)
    assert len(ap) >= 4
    assert sum(a["share"] for a in ap.values()) == pytest.approx(1.0)
    assert not any("Habsiguda" in k for k in ap)          # no Uppal names for a Gachibowli plan


def test_other_venue_plan_has_no_uppal_hospital_or_approaches(gach):
    D, _ = gach
    r = E.run_scenario(D, {"attendance": 30000, "venue_latlon": GACH})
    assert r["corridor"] is None                           # no hospital given: skipped, not invented at Habsiguda
    assert not any("Habsiguda" in k for k in r["approaches"])


def test_nearest_hospital_and_corridor_start_near_the_venue(gach):
    D, _ = gach
    h = VC.nearest_hospital(*GACH)
    assert h is not None and h["Distance_km"] < 12
    r = E.run_scenario(D, {"attendance": 30000, "venue_latlon": GACH, "hospital_latlon": (h["Latitude"], h["Longitude"])})
    assert r["corridor"] is not None
    start = E.node_xy(D, r["corridor"]["path"][0])
    assert E.haversine(start, GACH) < 6000


def test_nearest_hospital_returns_none_when_too_far():
    assert VC.nearest_hospital(12.97, 77.59) is None       # Bengaluru: do not invent a Hyderabad hospital


def test_manual_rows_only_apply_near_the_venue():
    df = pd.DataFrame({"Location": ["A"], "Latitude": [17.4235], "Longitude": [78.5035], "Type": ["hospital"]})
    assert E.get_manual_hospital_and_parking(df, near_latlon=GACH)[0] is None
    assert E.get_manual_hospital_and_parking(df, near_latlon=(17.42, 78.50))[0] is not None


def test_synthetic_profile_is_labelled_not_attributed_to_hmda():
    df = TP.load_traffic_profiles()
    assert set(df["Source"]) == {"SYNTHETIC-ASSUMED (not measured)"}
    assert not any("HMDA" in str(x) for x in df["Source"].unique())


def test_real_anchors_have_source_links():
    a = TP.load_real_anchors()
    assert len(a) >= 3 and a["Source_URL"].str.startswith("http").all()


def test_bpr_inverse_roundtrip_and_empty_table():
    assert OS.bpr_inverse_vc(40, 40) == 0.0
    vc = OS.bpr_inverse_vc(40, 20)                         # half speed -> ratio 2
    assert vc == pytest.approx(((2 - 1) / 0.15) ** 0.25)
    assert OS.typical_by_hour(pd.DataFrame(columns=OS.COLUMNS)).empty


def test_typical_by_hour_averages_samples():
    df = pd.DataFrame({"day_of_week": ["Monday"] * 2, "hour": [9, 9], "location": ["X"] * 2,
                       "current_speed_kmh": [20, 30], "free_flow_speed_kmh": [40, 40]})
    out = OS.typical_by_hour(df)
    assert out.iloc[0]["samples"] == 2 and out.iloc[0]["avg_speed_kmh"] == 25.0


def test_collector_parses_tomtom_response_and_saves(monkeypatch, tmp_path):
    sys.path.insert(0, str(ROOT / "scripts"))
    import collect_tomtom_speeds as C

    class R:
        status_code = 200
        text = ""
        def json(self): return {"flowSegmentData": {"currentSpeed": 22, "freeFlowSpeed": 41, "confidence": 0.9, "roadClosure": False}}
    class S:
        def get(self, *a, **k): return R()
    monkeypatch.setattr(OS, "SPEEDS_CSV", tmp_path / "s.csv")
    monkeypatch.setattr(C, "watch_points", lambda: pd.DataFrame({"location": ["P"], "lat": [17.4], "lon": [78.5]}))
    assert C.collect_once("KEY", S()) == 1
    saved = pd.read_csv(tmp_path / "s.csv")
    assert saved.loc[0, "current_speed_kmh"] == 22 and saved.loc[0, "location"] == "P"
