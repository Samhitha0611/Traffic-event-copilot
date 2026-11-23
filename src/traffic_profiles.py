"""
Traffic Profiles Module for Greater Hyderabad.
Provides a SYNTHETIC (assumed) 24-hour and 7-day typical-day pattern. It is a planning shape, not measured
data. Real published counts live in data/real_count_anchors.csv (see load_real_anchors).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
PROFILES_CSV = DATA_DIR / "hyderabad_hourly_traffic_profiles.csv"
ANCHORS_CSV = DATA_DIR / "real_count_anchors.csv"


def load_traffic_profiles() -> pd.DataFrame:
    """Load the 24-hour x 7-day classified hourly traffic dataset."""
    if PROFILES_CSV.exists():
        return pd.read_csv(PROFILES_CSV)
    # Fallback default empty dataframe if not generated yet
    return pd.DataFrame(columns=[
        "Day_Of_Week", "Hour", "Time_Window", "Road_Category",
        "Total_Vehicles", "Total_PCU", "Two_Wheeler_Count",
        "Car_Count", "Auto_Rickshaw_Count", "Bus_Count", "LCV_Truck_Count",
        "Peak_Status", "Source"
    ])


def get_diurnal_24h_curve(day_of_week: str = "Sunday", road_category: str = "Primary_Arterial") -> pd.DataFrame:
    """Return 24-hour traffic flow curve for a given day and road category."""
    df = load_traffic_profiles()
    if df.empty:
        return pd.DataFrame()
    d_clean = str(day_of_week).capitalize()
    r_clean = str(road_category)
    filtered = df[(df["Day_Of_Week"] == d_clean) & (df["Road_Category"] == r_clean)]
    if filtered.empty:
        filtered = df[df["Day_Of_Week"] == d_clean]
    return filtered.sort_values("Hour").reset_index(drop=True)


def get_hourly_slice(day_of_week: str, hour: int, road_category: str = "Primary_Arterial") -> dict[str, Any] | None:
    """Get the specific traffic composition slice for a specific day and hour (0-23)."""
    df = load_traffic_profiles()
    if df.empty:
        return None
    d_clean = str(day_of_week).capitalize()
    matches = df[(df["Day_Of_Week"] == d_clean) & (df["Hour"] == int(hour)) & (df["Road_Category"] == road_category)]
    if not matches.empty:
        return matches.iloc[0].to_dict()
    # Fallback to any road category matching hour & day
    fallback = df[(df["Day_Of_Week"] == d_clean) & (df["Hour"] == int(hour))]
    if not fallback.empty:
        return fallback.iloc[0].to_dict()
    return None


def get_weekly_comparison(hour: int = 19, road_category: str = "Primary_Arterial") -> pd.DataFrame:
    """Compare traffic volume across all 7 days of the week at a specific hour."""
    df = load_traffic_profiles()
    if df.empty:
        return pd.DataFrame()
    matches = df[(df["Hour"] == int(hour)) & (df["Road_Category"] == road_category)]
    return matches[["Day_Of_Week", "Time_Window", "Total_Vehicles", "Total_PCU", "Two_Wheeler_Count", "Car_Count", "Bus_Count"]].reset_index(drop=True)



def load_real_anchors() -> pd.DataFrame:
    """Real published traffic counts for Hyderabad (older studies, a handful of locations). Never extrapolated."""
    return pd.read_csv(ANCHORS_CSV) if ANCHORS_CSV.exists() else pd.DataFrame()
