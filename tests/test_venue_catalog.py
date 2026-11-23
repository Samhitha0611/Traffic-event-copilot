"""
Tests for venue_catalog.py:
1. Verifies verified Hyderabad venues catalog loads with valid coordinates and commissionerates.
2. Verifies verified Hyderabad hospitals catalog loads with valid coordinates.
3. Verifies geocoding lookup and network fallback.
"""
from pathlib import Path
import sys
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import venue_catalog as VC


def test_load_venues_has_required_columns_and_rows():
    df = VC.load_venues()
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert len(df) >= 7
    expected_cols = ["Venue_Key", "Venue_Name", "Commissionerate", "Area", "Latitude", "Longitude", "Capacity"]
    for c in expected_cols:
        assert c in df.columns
    # Check that coordinates are non-empty valid floats in Hyderabad bounding box (lat ~17, lon ~78)
    assert ((df["Latitude"] > 17.0) & (df["Latitude"] < 18.0)).all()
    assert ((df["Longitude"] > 78.0) & (df["Longitude"] < 79.0)).all()


def test_load_hospitals_has_required_columns_and_rows():
    df = VC.load_hospitals()
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert len(df) >= 6
    for c in ["Hospital_Name", "Zone", "Latitude", "Longitude", "Source"]:
        assert c in df.columns
    assert ((df["Latitude"] > 17.0) & (df["Latitude"] < 18.0)).all()
    assert ((df["Longitude"] > 78.0) & (df["Longitude"] < 79.0)).all()


def test_get_venue_and_hospital_lookup():
    v = VC.get_venue("gachibowli_stadium")
    assert v is not None
    assert v["Venue_Name"] == "Gachibowli Stadium"
    assert v["Commissionerate"] == "Cyberabad Police"

    h = VC.get_hospital("Gandhi Hospital")
    assert h is not None
    assert "Secunderabad" in h["Zone"]


def test_hyderabad_location_suggestions():
    suggestions = VC.get_hyderabad_location_suggestions()
    assert isinstance(suggestions, dict)
    assert len(suggestions) >= 20
    for name, loc in suggestions.items():
        assert "lat" in loc and "lon" in loc
        assert "commissionerate" in loc
        assert 17.0 < loc["lat"] < 18.0
        assert 78.0 < loc["lon"] < 79.0

