"""Tests for the SIPOC demo engine. Run from the project root:  pytest -q"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import event_engine as E  # noqa: E402

needs_graph = pytest.mark.skipif(not E.GRAPH_PATH.exists(), reason="road graph file not present")


def test_demand_hand_calc_39000():
    d = E.compute_demand(39000)
    # people: 2W 9750, car 9750, auto 1950, cab 1950, bus 5850, metro 5850, walk 3900
    assert d["vehicles"] == {"two_wheeler": 7800, "car": 3900, "auto_rickshaw": 780, "cab": 975, "bus": 117}
    assert d["total_vehicles"] == 13572
    assert d["total_pcu"] == pytest.approx(3120 + 3900 + 702 + 975 + 409.5)
    assert d["pedestrians"] == pytest.approx(9750)


def test_peak_hourly_is_4x_peak_15min_and_share_is_7_over_24():
    d = E.compute_demand(39000)
    assert d["peak_share"] == pytest.approx(7 / 24)
    assert d["peak_hourly_pcu"] == pytest.approx(4 * d["peak_15min_pcu"])


def test_people_conserved_and_shares_sum_to_one():
    d = E.compute_demand(48317, E.mode_share_with_private_total(0.7))
    assert sum(d["persons"].values()) == pytest.approx(48317)
    assert sum(d["mode_share"].values()) == pytest.approx(1.0)
    assert sum(d["mode_share"][m] for m in E.PRIVATE_MODES) == pytest.approx(0.7)


def test_shift_to_metro_lowers_pcu_and_raises_pedestrians():
    base, shifted = E.compute_demand(39000), E.compute_demand(39000, shift_to_metro_pct=20)
    assert shifted["total_pcu"] < base["total_pcu"]
    assert shifted["metro_riders"] > base["metro_riders"]


def test_arrival_curve_sums_to_total_and_peak_label():
    d = E.compute_demand(39000, start_time="19:30")
    assert d["curve"]["PCU"].sum() == pytest.approx(d["total_pcu"], abs=1)
    assert d["curve"]["Time"].iloc[0] == "18:00"
    assert d["peak_bucket"] == "18:45"


def test_egress_curve_starts_after_event_end():
    d = E.compute_demand(39000, start_time="19:30", phase="egress", duration_h=3)
    assert d["curve"]["Time"].iloc[0] == "22:30"


@pytest.fixture(scope="module")
def network():
    return E.build_network()


@needs_graph
def test_network_every_edge_has_capacity_and_time(network):
    D, stats = network
    assert stats["nodes"] > 1000
    assert all(d["cap"] > 0 and d["t0"] > 0 for _, _, d in D.edges(data=True))


@needs_graph
def test_run_is_deterministic_and_optimised_not_worse(network):
    D, _ = network
    p = {"attendance": 39000, "start_time": "19:30", "phase": "ingress"}
    a, b = E.run_scenario(D, p), E.run_scenario(D, p)
    assert a["sum_opt"] == b["sum_opt"]
    assert a["sum_opt"]["max_vc"] <= a["sum_naive"]["max_vc"] + 1e-9


@needs_graph
def test_more_attendance_never_lowers_max_vc(network):
    D, _ = network
    lo = E.run_scenario(D, {"attendance": 10000})["sum_opt"]["max_vc"]
    hi = E.run_scenario(D, {"attendance": 39000})["sum_opt"]["max_vc"]
    assert hi >= lo


@needs_graph
def test_alternate_route_never_uses_removed_or_protected_edge(network):
    D, _ = network
    r = E.run_scenario(D, {"attendance": 39000})
    protected = set(r["corridor"]["edges"])
    for d in r["diversions"]:
        if d["path"]:
            u, v = (int(x) for x in d["edge"].split("-"))
            edges = set(zip(d["path"][:-1], d["path"][1:]))
            assert (u, v) not in edges and not (edges & protected)


@needs_graph
def test_emergency_corridor_is_connected_path_ending_at_stadium(network):
    D, _ = network
    r = E.run_scenario(D, {"attendance": 39000})
    c = r["corridor"]
    assert all(D.has_edge(a, b) for a, b in c["edges"])
    assert c["unprotected_min"] >= c["free_min"]


@needs_graph
def test_report_contains_only_computed_numbers_header_and_sections(network):
    D, _ = network
    rep = E.run_scenario(D, {"attendance": 39000, "event_name": "Test"})["report"]
    for h in ("Impact summary", "Bottlenecks", "Diversion scheme", "Emergency protection", "Data status"):
        assert h in rep


@needs_graph
def test_manual_locations_fallback_when_no_rows_exist(network, tmp_path, monkeypatch):
    D, _ = network
    empty_csv = tmp_path / "manual_locations.csv"
    empty_csv.write_text("Location,Latitude,Longitude,Source,Verified\nUppal Metro Station,17.3987948,78.5538439,Wikipedia,True\n")
    monkeypatch.setattr(E, "MANUAL_LOCATION_CSV", empty_csv)

    r = E.run_scenario(D, {"attendance": 10000})
    assert r["hospital_is_placeholder"] is True
    assert r["parking_is_generated"] is True
    assert r["params"]["hospital_latlon"] == E.FALLBACK_LOCATIONS["Habsiguda"]


@needs_graph
def test_manual_locations_used_when_hospital_and_parking_rows_exist(network, tmp_path, monkeypatch):
    D, _ = network
    custom_csv = tmp_path / "manual_locations.csv"
    custom_csv.write_text(
        "Location,Latitude,Longitude,Source,Verified,Type\n"
        "TX Hospitals Uppal,17.4005,78.5570,TX Hospitals,True,hospital\n"
        "Little Flower Junior College,17.4044,78.5577,OSM,True,parking\n"
    )
    monkeypatch.setattr(E, "MANUAL_LOCATION_CSV", custom_csv)

    r = E.run_scenario(D, {"attendance": 10000})
    assert r["hospital_is_placeholder"] is False
    assert r["parking_is_generated"] is False
    assert r["params"]["hospital_latlon"] == (17.4005, 78.5570)
    expected_hospital_node = E.nearest_node(D, 17.4005, 78.5570)
    assert r["corridor"]["path"][0] == expected_hospital_node
    expected_parking_node = E.nearest_node(D, 17.4044, 78.5577)
    assert r["parking"] == [expected_parking_node]


def test_turnback_rows_have_no_coordinates_and_unverified():
    df = E.load_manual_locations()
    assert not df.empty
    assert "Type" in df.columns
    tb = df[df["Type"].astype(str).str.strip().str.lower() == "turnback"]
    assert len(tb) >= 4  # contains Nagole, Habsiguda, HMDA, Street No 8, etc.
    # Coordinates must be empty
    assert tb["Latitude"].isna().all()
    assert tb["Longitude"].isna().all()
    # Verified must be NO
    assert (tb["Verified"].astype(str).str.strip().str.upper() == "NO").all()


@needs_graph
def test_map_view_draws_turnback_markers_when_coords_present_and_skips_when_empty(network, tmp_path, monkeypatch):
    import map_view as M
    D, _ = network
    # Create test csv with one turnback having coordinates and one without
    test_csv = tmp_path / "manual_locations.csv"
    test_csv.write_text(
        "Location,Latitude,Longitude,Source,Verified,Type\n"
        "Nagole Metro Station U-turn,17.3900,78.5600,Diversions sheet,NO,turnback\n"
        "Habsiguda X Roads,,,Diversions sheet,NO,turnback\n"
    )
    monkeypatch.setattr(E, "MANUAL_LOCATION_CSV", test_csv)

    scenario_res = E.run_scenario(D, {"attendance": 10000})
    folium_map = M.make_map(D, scenario_res)
    # Convert map to HTML string to inspect elements
    html = folium_map.get_root().render()
    # Turn-back with coordinates (17.39, 78.56) should be rendered in HTML
    assert "Nagole Metro Station U-turn" in html
    assert "Police turn-back points" in html
