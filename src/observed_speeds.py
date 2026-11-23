"""
Real observed speeds (from a traffic API such as TomTom) stored as a table, and helpers to use them.

This is REAL data about how congested roads are by hour and day, collected by you over time.
It is speed data, not vehicle counts. Vehicle counts per road are not available from any free source.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
SPEEDS_CSV = BASE_DIR / "data" / "observed_speeds.csv"
COLUMNS = ["timestamp", "day_of_week", "hour", "location", "lat", "lon", "current_speed_kmh",
           "free_flow_speed_kmh", "confidence", "road_closure", "source"]

BPR_ALPHA = 0.15   # same standard BPR coefficient used in the engine


def bpr_inverse_vc(free_flow_kmh: float, current_kmh: float) -> float:
    """Estimate load/capacity from the slow-down: t/t0 = 1 + 0.15 (V/C)^4  =>  V/C = ((t/t0 - 1)/0.15)^0.25.
    Returns 0 when traffic moves at free-flow speed. Capped at 3 (same cap as the engine)."""
    if current_kmh <= 0 or free_flow_kmh <= 0:
        return 3.0
    ratio = free_flow_kmh / current_kmh
    if ratio <= 1:
        return 0.0
    return min(((ratio - 1.0) / BPR_ALPHA) ** 0.25, 3.0)


def load_speeds(path: Path = SPEEDS_CSV) -> pd.DataFrame:
    if Path(path).exists():
        return pd.read_csv(path)
    return pd.DataFrame(columns=COLUMNS)


def typical_by_hour(df: pd.DataFrame | None = None, location: str | None = None) -> pd.DataFrame:
    """Average congestion by day of week and hour. Empty table if nothing has been collected yet."""
    df = load_speeds() if df is None else df
    if df.empty:
        return pd.DataFrame(columns=["day_of_week", "hour", "samples", "avg_speed_kmh", "avg_free_flow_kmh",
                                     "speed_ratio", "est_vc"])
    if location:
        df = df[df["location"] == location]
    g = (df.groupby(["day_of_week", "hour"])
           .agg(samples=("current_speed_kmh", "count"), avg_speed_kmh=("current_speed_kmh", "mean"),
                avg_free_flow_kmh=("free_flow_speed_kmh", "mean")).reset_index())
    g["speed_ratio"] = (g["avg_speed_kmh"] / g["avg_free_flow_kmh"]).round(2)
    g["est_vc"] = [round(bpr_inverse_vc(f, c), 2) for f, c in zip(g["avg_free_flow_kmh"], g["avg_speed_kmh"])]
    return g.round(1)
