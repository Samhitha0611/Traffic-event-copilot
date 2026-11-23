"""
Tests for traffic_profiles.py:
Verifies 24-hour diurnal and 7-day-a-week classified baseline traffic flow dataset
synthetic assumed shape (not measured).
"""
from pathlib import Path
import sys
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import traffic_profiles as TP


def test_traffic_profiles_dataset_loaded_and_complete():
    df = TP.load_traffic_profiles()
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert len(df) == 672  # 4 road types x 7 days x 24 hours

    required_cols = [
        "Day_Of_Week", "Hour", "Time_Window", "Road_Category",
        "Total_Vehicles", "Total_PCU", "Two_Wheeler_Count",
        "Car_Count", "Auto_Rickshaw_Count", "Bus_Count", "LCV_Truck_Count",
        "Peak_Status", "Source"
    ]
    for col in required_cols:
        assert col in df.columns

    # Verify all 7 days of the week are present
    expected_days = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
    assert set(df["Day_Of_Week"].unique()) == expected_days

    # Verify 24 hours (0-23)
    assert set(df["Hour"].unique()) == set(range(24))


def test_diurnal_24h_curve_has_24_hours_and_peak_dynamics():
    curve = TP.get_diurnal_24h_curve(day_of_week="Monday", road_category="Primary_Arterial")
    assert len(curve) == 24
    assert list(curve["Hour"]) == list(range(24))

    # Peak hour traffic (e.g. 09:00 or 18:00) must be significantly higher than night traffic (e.g. 02:00)
    night_volume = curve[curve["Hour"] == 2]["Total_Vehicles"].values[0]
    morning_peak = curve[curve["Hour"] == 9]["Total_Vehicles"].values[0]
    evening_peak = curve[curve["Hour"] == 18]["Total_Vehicles"].values[0]

    assert morning_peak > 5 * night_volume
    assert evening_peak > 5 * night_volume


def test_hourly_slice_and_vehicle_classification():
    slice_data = TP.get_hourly_slice(day_of_week="Sunday", hour=19, road_category="Primary_Arterial")
    assert slice_data is not None
    assert slice_data["Day_Of_Week"] == "Sunday"
    assert slice_data["Hour"] == 19
    assert slice_data["Total_Vehicles"] > 0
    assert slice_data["Total_PCU"] > 0

    # Two-wheelers and cars should make up the majority of urban traffic
    assert slice_data["Two_Wheeler_Count"] > slice_data["Bus_Count"]
    assert slice_data["Car_Count"] > slice_data["Bus_Count"]


def test_weekly_comparison_returns_all_seven_days():
    comp = TP.get_weekly_comparison(hour=18, road_category="Primary_Arterial")
    assert len(comp) == 7
    assert "Day_Of_Week" in comp.columns
    assert "Total_Vehicles" in comp.columns

