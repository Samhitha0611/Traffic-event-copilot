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
