"""
Module to load observed traffic counts from Excel data pack,
filter valid counts, and compare with modelled scenario flows.
"""
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

# Project paths
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_FILE = BASE_DIR / "data" / "uppal_stadium_event_traffic_data_pack.xlsx"
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import event_engine as ee


def load_observed_counts(source: str | Path | pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Load Traffic_Counts sheet and keep only rows where Total_Flow is a valid number.
    If there are none, returns an empty table and prints 'No observed counts yet'.
    Does not fabricate any rows.
    """
    if isinstance(source, pd.DataFrame):
        df = source.copy()
    else:
        path = DATA_FILE if source is None else Path(source)
        if not Path(path).exists():
            print("No observed counts yet")
            return pd.DataFrame()
        try:
            df = pd.read_excel(path, sheet_name="Traffic_Counts")
        except Exception:
            print("No observed counts yet")
            return pd.DataFrame()

    if "Total_Flow" not in df.columns:
        print("No observed counts yet")
        return pd.DataFrame()

    # Keep only rows where Total_Flow is a number
    numeric_flow = pd.to_numeric(df["Total_Flow"], errors="coerce")
    valid_mask = numeric_flow.notna()
    valid_df = df[valid_mask].copy()

    if valid_df.empty:
        print("No observed counts yet")
        return pd.DataFrame()

    valid_df["Total_Flow"] = numeric_flow[valid_mask]
    return valid_df.reset_index(drop=True)


def find_modelled_flow(D, scenario_res: dict, junction_name: str, lat=None, lon=None) -> float:
    """
    Estimate modelled flow (PCU/hr) at a junction or road segment from scenario outputs.
    """
    table_opt = scenario_res.get("table_opt")
    if table_opt is None or table_opt.empty:
        return 0.0

    # 1. Coordinate-based lookup if Latitude & Longitude exist
    if pd.notna(lat) and pd.notna(lon) and D is not None:
        try:
            node = ee.nearest_node(D, float(lat), float(lon))
            # Incoming edges flow to this junction node
            in_edges = table_opt[table_opt["v"] == node]
            if not in_edges.empty:
                return float(in_edges["load_pcu_hr"].sum())
            # Or incident edges
            inc_edges = table_opt[(table_opt["u"] == node) | (table_opt["v"] == node)]
            if not inc_edges.empty:
                return float(inc_edges["load_pcu_hr"].max())
        except Exception:
            pass

    # 2. Key corridor / street name matching
    j_clean = str(junction_name).strip().lower()
    keywords = ["habsiguda", "street 8", "street no 8", "ramanthapur", "uppal", "nagole", "tarnaka", "boduppal"]
    for kw in keywords:
        if kw in j_clean:
            match_term = "street 8" if "street" in kw else kw
            matches = table_opt[table_opt["name"].astype(str).str.lower().str.contains(match_term)]
            if not matches.empty:
                return float(matches["load_pcu_hr"].max())

    # 3. Approach origin matching
    approaches = scenario_res.get("approaches", {})
    for app_name, a in approaches.items():
        if app_name.lower() in j_clean or j_clean in app_name.lower():
            entry_nodes = set(a.get("nodes", []))
            matches = table_opt[table_opt["u"].isin(entry_nodes) | table_opt["v"].isin(entry_nodes)]
            if not matches.empty:
                return float(matches["load_pcu_hr"].sum())

    # 4. Fallback to top hotspot peak load
    hotspots = scenario_res.get("hotspots")
    if hotspots is not None and not hotspots.empty:
        return float(hotspots.iloc[0]["load_pcu_hr"])

    return float(table_opt["load_pcu_hr"].max())


def compare_observed_with_model(
    observed_df: pd.DataFrame,
    D=None,
    scenario_res: dict | None = None,
    pack=None
) -> pd.DataFrame:
    """
    Compare observed flow per junction with modelled flow for the same event and print errors.
    """
    if observed_df is None or observed_df.empty:
        print("No observed counts yet")
        return pd.DataFrame()

    if D is None and scenario_res is None:
        print("Building road network for flow comparison...")
        D, _ = ee.build_network()

    if pack is None and scenario_res is None:
        pack = ee.load_pack()

    if scenario_res is None:
        first_event = observed_df.iloc[0].get("Event_Name", "Uppal Stadium Match")
        first_date = observed_df.iloc[0].get("Date", None)
        params = {
            "attendance": 39000,           # ASSUMED default attendance for event scenario
            "start_time": "19:30",          # ASSUMED default match start time
            "phase": "ingress",             # ASSUMED peak ingress phase
            "duration_h": 3.0,              # ASSUMED match duration
            "event_name": str(first_event),
            "event_date": first_date
        }
        scenario_res = ee.run_scenario(D, params, pack=pack)

    results = []
    print("\n========== OBSERVED VS MODELLED FLOW COMPARISON ==========")

    for idx, row in observed_df.iterrows():
        j_name = str(row.get("Junction_Name", f"Junction #{idx + 1}"))
        obs_flow = float(row["Total_Flow"])
        lat = row.get("Latitude")
        lon = row.get("Longitude")
        event_name = str(row.get("Event_Name", "Event"))

        mod_flow = find_modelled_flow(D, scenario_res, j_name, lat, lon)
        abs_err = abs(obs_flow - mod_flow)
        pct_err = (abs_err / obs_flow * 100.0) if obs_flow > 0 else 0.0

        print(f"\nJunction: {j_name}")
        print(f"  Event: {event_name}")
        print(f"  Observed Flow: {obs_flow:,.1f} vehicles/hr")
        print(f"  Modelled Flow: {mod_flow:,.1f} PCU/hr (model estimate)")
        print(f"  Absolute Error: {abs_err:,.1f}")
        print(f"  Percentage Error: {pct_err:.2f}%")

        results.append({
            "Event_Name": event_name,
            "Junction_Name": j_name,
            "Observed_Flow": round(obs_flow, 1),
            "Modelled_Flow": round(mod_flow, 1),
            "Absolute_Error": round(abs_err, 1),
            "Percentage_Error": round(pct_err, 2)
        })

    comp_df = pd.DataFrame(results)

    if not comp_df.empty:
        mae = comp_df["Absolute_Error"].mean()
        mape = comp_df["Percentage_Error"].mean()
        print("\n-----------------------------------------------------------")
        print(f"Overall Metrics ({len(comp_df)} junction(s)):")
        print(f"  Mean Absolute Error (MAE): {mae:,.1f}")
        print(f"  Mean Absolute Percentage Error (MAPE): {mape:.2f}%")
        print("===========================================================\n")

    return comp_df


if __name__ == "__main__":
    counts = load_observed_counts()
    if not counts.empty:
        compare_observed_with_model(counts)

