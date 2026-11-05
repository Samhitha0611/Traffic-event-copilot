"""
Tests for observed_counts.py:
1. Real data pack: Total_Flow is missing, so it prints "No observed counts yet" and returns an empty table.
2. Synthetic data test: Uses a tiny synthetic table inside the test file only, clearly named `synthetic`.
"""
import sys
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import observed_counts as OC
import event_engine as E

needs_graph = pytest.mark.skipif(not E.GRAPH_PATH.exists(), reason="road graph file not present")


def test_real_data_pack_has_no_observed_counts(capsys):
    """Real data pack has no published counts, so it must return empty and print 'No observed counts yet'."""
    res = OC.load_observed_counts()
    captured = capsys.readouterr()
    assert "No observed counts yet" in captured.out
    assert isinstance(res, pd.DataFrame)
    assert res.empty


@needs_graph
def test_compare_observed_with_synthetic_table(capsys):
    """
    Test comparison using a tiny synthetic table inside the test file only,
    clearly named synthetic.
    """
    synthetic = pd.DataFrame([
        {
            "Event_Name": "IPL 2026 home match (Day & Night)",
            "Date": "2026-04-05",
            "Junction_Name": "Habsiguda X Roads",
            "Latitude": 17.4155,
            "Longitude": 78.5427,
            "Total_Flow": 4500.0
        },
        {
            "Event_Name": "IPL 2026 home match (Day & Night)",
            "Date": "2026-04-05",
            "Junction_Name": "Street No 8",
            "Latitude": 17.4080,
            "Longitude": 78.5450,
            "Total_Flow": 2800.0
        }
    ])

    # load_observed_counts should keep rows where Total_Flow is a number
    filtered = OC.load_observed_counts(synthetic)
    assert len(filtered) == 2
    assert (filtered["Total_Flow"] == [4500.0, 2800.0]).all()

    # Compare with modelled flows
    comp = OC.compare_observed_with_model(filtered)
    captured = capsys.readouterr()

    # Verify comparison output and metrics printed
    assert "OBSERVED VS MODELLED FLOW COMPARISON" in captured.out
    assert "Observed Flow" in captured.out
    assert "Modelled Flow" in captured.out
    assert "Mean Absolute Error (MAE)" in captured.out

    # Verify returned comparison dataframe structure
    assert isinstance(comp, pd.DataFrame)
    assert len(comp) == 2
    assert "Absolute_Error" in comp.columns
    assert "Percentage_Error" in comp.columns
    assert (comp["Absolute_Error"] >= 0).all()

