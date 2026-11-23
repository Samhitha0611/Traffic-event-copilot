"""
Tests for police_chatbot.py:
Verifies grounded response generation for police queries regarding:
- Hotspots and bottlenecks [H]
- Diversions and closures [D]
- Emergency green corridor [E]
- Police deployment estimates (ASSUMED)
- Parking & transit advice [P]
"""
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import police_chatbot as PC
import event_engine as E

needs_graph = pytest.mark.skipif(not E.GRAPH_PATH.exists(), reason="road graph file not present")


@pytest.fixture(scope="module")
def sample_scenario():
    D, _ = E.build_network()
    return E.run_scenario(D, {"attendance": 35000, "event_name": "Hyderabad Derby"})


def test_chatbot_returns_fallback_when_no_scenario():
    res = PC.generate_police_response("What is the plan?", None)
    assert "No active scenario found" in res


@needs_graph
def test_chatbot_answers_hotspots(sample_scenario):
    ans = PC.generate_police_response("Where are the worst hotspots and congestion bottlenecks?", sample_scenario)
    assert "Congestion Hotspots" in ans
    assert "H-" in ans
    assert "V/C" in ans


@needs_graph
def test_chatbot_answers_diversions(sample_scenario):
    ans = PC.generate_police_response("What diversions should we implement for private traffic?", sample_scenario)
    assert "Diversion Scheme" in ans
    assert "D-" in ans


@needs_graph
def test_chatbot_answers_emergency_corridor(sample_scenario):
    ans = PC.generate_police_response("What is the ambulance emergency corridor route and ETA?", sample_scenario)
    assert "Emergency Green Corridor" in ans
    assert "minutes" in ans
    assert "E-1" in ans


@needs_graph
def test_chatbot_answers_police_deployment(sample_scenario):
    ans = PC.generate_police_response("How many police personnel and officers are needed for deployment?", sample_scenario)
    assert "Tactical Police Deployment" in ans
    assert "Sector Officers" in ans
    assert "Constables" in ans
    assert "ASSUMED" in ans


@needs_graph
def test_chatbot_answers_parking(sample_scenario):
    ans = PC.generate_police_response("Where should spectators park their cars?", sample_scenario)
    assert "Parking & Transit" in ans
    assert "ASSUMED" in ans

