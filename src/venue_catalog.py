"""
Venue and Hospital Catalog for Greater Hyderabad.
Manages verified locations, coordinates, hospital corridors, and road network retrieval.
Includes extensive auto-suggest locations across Hyderabad (stadiums, junctions, IT hubs, and areas).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
NETWORKS_DIR = DATA_DIR / "networks"
VENUES_CSV = DATA_DIR / "hyderabad_venues.csv"
HOSPITALS_CSV = DATA_DIR / "hyderabad_hospitals.csv"
UPPAL_GRAPHML = DATA_DIR / "uppal_road_network.graphml"

# Verified prominent Hyderabad hubs, stadiums, junctions and areas for auto-suggest
HYDERABAD_SUGGESTIONS = {
    "Rajiv Gandhi International Cricket Stadium, Uppal": {
        "key": "uppal_stadium",
        "lat": 17.406500,
        "lon": 78.550500,
        "commissionerate": "Rachakonda Police",
        "area": "Uppal",
        "capacity": 39000,
        "default_hospital": "Gandhi Hospital"
    },
    "Gachibowli Stadium": {
        "key": "gachibowli_stadium",
        "lat": 17.449409,
        "lon": 78.348468,
        "commissionerate": "Cyberabad Police",
        "area": "Gachibowli",
        "capacity": 30000,
        "default_hospital": "Continental Hospitals Gachibowli"
    },
    "Lal Bahadur Shastri Stadium (LB Stadium), Basheerbagh": {
        "key": "lb_stadium",
        "lat": 17.399565,
        "lon": 78.472999,
        "commissionerate": "Hyderabad City Police",
        "area": "Basheerbagh",
        "capacity": 25000,
        "default_hospital": "Osmania General Hospital"
    },
    "HITEX Exhibition Centre, Madhapur": {
        "key": "hitex_centre",
        "lat": 17.470811,
        "lon": 78.374915,
        "commissionerate": "Cyberabad Police",
        "area": "Madhapur/Kondapur",
        "capacity": 20000,
        "default_hospital": "Continental Hospitals Gachibowli"
    },
    "Shilpakala Vedika, Madhapur": {
        "key": "shilpakala_vedika",
        "lat": 17.451408,
        "lon": 78.379375,
        "commissionerate": "Cyberabad Police",
        "area": "Madhapur",
        "capacity": 5000,
        "default_hospital": "Continental Hospitals Gachibowli"
    },
    "Parade Ground, Secunderabad": {
        "key": "parade_ground",
        "lat": 17.445061,
        "lon": 78.493566,
        "commissionerate": "Hyderabad City Police",
        "area": "Secunderabad",
        "capacity": 60000,
        "default_hospital": "Gandhi Hospital"
    },
    "NTR Marg / Tank Bund / People's Plaza": {
        "key": "tank_bund",
        "lat": 17.415412,
        "lon": 78.479628,
        "commissionerate": "Hyderabad City Police",
        "area": "Khairatabad/Tank Bund",
        "capacity": 50000,
        "default_hospital": "Osmania General Hospital"
    },
    "Charminar, Old City": {
        "key": "charminar",
        "lat": 17.361564,
        "lon": 78.474665,
        "commissionerate": "Hyderabad City Police",
        "area": "Old City",
        "capacity": 20000,
        "default_hospital": "Osmania General Hospital"
    },
    "Cyber Towers / Hitec City": {
        "key": "hitec_city",
        "lat": 17.450410,
        "lon": 78.380840,
        "commissionerate": "Cyberabad Police",
        "area": "Hitec City",
        "capacity": 25000,
        "default_hospital": "Continental Hospitals Gachibowli"
    },
    "Banjara Hills (Road No 1 & 12)": {
        "key": "banjara_hills",
        "lat": 17.415582,
        "lon": 78.448255,
        "commissionerate": "Hyderabad City Police",
        "area": "Banjara Hills",
        "capacity": 15000,
        "default_hospital": "Care Hospital Banjara Hills"
    },
    "Jubilee Hills Checkpost": {
        "key": "jubilee_hills",
        "lat": 17.430030,
        "lon": 78.409380,
        "commissionerate": "Hyderabad City Police",
        "area": "Jubilee Hills",
        "capacity": 15000,
        "default_hospital": "Apollo Hospitals Jubilee Hills"
    },
    "Financial District / Nanakramguda": {
        "key": "financial_district",
        "lat": 17.417200,
        "lon": 78.341100,
        "commissionerate": "Cyberabad Police",
        "area": "Gachibowli/Nanakramguda",
        "capacity": 20000,
        "default_hospital": "Continental Hospitals Gachibowli"
    },
    "Secunderabad Railway Station / Station Road": {
        "key": "secunderabad_station",
        "lat": 17.434390,
        "lon": 78.501570,
        "commissionerate": "Hyderabad City Police",
        "area": "Secunderabad",
        "capacity": 30000,
        "default_hospital": "Gandhi Hospital"
    },
    "Mehdipatnam X Roads": {
        "key": "mehdipatnam",
        "lat": 17.391620,
        "lon": 78.438530,
        "commissionerate": "Hyderabad City Police",
        "area": "Mehdipatnam",
        "capacity": 20000,
        "default_hospital": "Care Hospital Banjara Hills"
    },
    "Kukatpally / KPHB Colony": {
        "key": "kukatpally",
        "lat": 17.493250,
        "lon": 78.399430,
        "commissionerate": "Cyberabad Police",
        "area": "Kukatpally",
        "capacity": 25000,
        "default_hospital": "Apollo Hospitals Jubilee Hills"
    },
    "Dilsukhnagar Bus Depot / X Roads": {
        "key": "dilsukhnagar",
        "lat": 17.368810,
        "lon": 78.524730,
        "commissionerate": "Rachakonda Police",
        "area": "Dilsukhnagar",
        "capacity": 25000,
        "default_hospital": "Yashoda Hospitals Malakpet"
    },
    "LB Nagar Ring Road / Junction": {
        "key": "lb_nagar",
        "lat": 17.345720,
        "lon": 78.552230,
        "commissionerate": "Rachakonda Police",
        "area": "LB Nagar",
        "capacity": 30000,
        "default_hospital": "Yashoda Hospitals Malakpet"
    },
    "Panjagutta X Roads": {
        "key": "panjagutta",
        "lat": 17.426210,
        "lon": 78.452650,
        "commissionerate": "Hyderabad City Police",
        "area": "Panjagutta",
        "capacity": 20000,
        "default_hospital": "Care Hospital Banjara Hills"
    },
    "Ameerpet X Roads": {
        "key": "ameerpet",
        "lat": 17.437460,
        "lon": 78.448290,
        "commissionerate": "Hyderabad City Police",
        "area": "Ameerpet",
        "capacity": 20000,
        "default_hospital": "Care Hospital Banjara Hills"
    },
    "Habsiguda X Roads": {
        "key": "habsiguda",
        "lat": 17.415476,
        "lon": 78.542692,
        "commissionerate": "Rachakonda Police",
        "area": "Habsiguda",
        "capacity": 20000,
        "default_hospital": "Gandhi Hospital"
    },
    "Tarnaka X Roads": {
        "key": "tarnaka",
        "lat": 17.428548,
        "lon": 78.537943,
        "commissionerate": "Hyderabad City Police",
        "area": "Tarnaka",
        "capacity": 20000,
        "default_hospital": "Gandhi Hospital"
    },
    "Uppal X Roads": {
        "key": "uppal",
        "lat": 17.400772,
        "lon": 78.560495,
        "commissionerate": "Rachakonda Police",
        "area": "Uppal",
        "capacity": 25000,
        "default_hospital": "Gandhi Hospital"
    }
}


def get_hyderabad_location_suggestions() -> dict[str, dict[str, Any]]:
    """Return verified prominent Hyderabad locations for auto-suggestions."""
    return dict(HYDERABAD_SUGGESTIONS)


def load_venues() -> pd.DataFrame:
    """Load verified Hyderabad venues catalog."""
    if VENUES_CSV.exists():
        return pd.read_csv(VENUES_CSV)
    return pd.DataFrame(columns=[
        "Venue_Key", "Venue_Name", "Commissionerate", "Area",
        "Latitude", "Longitude", "Capacity", "Default_Hospital", "Source"
    ])


def load_hospitals() -> pd.DataFrame:
    """Load verified Hyderabad emergency referral hospitals."""
    if HOSPITALS_CSV.exists():
        return pd.read_csv(HOSPITALS_CSV)
    return pd.DataFrame(columns=[
        "Hospital_Name", "Zone", "Latitude", "Longitude", "Source"
    ])


def get_venue(venue_key: str) -> dict[str, Any] | None:
    """Get venue record by key."""
    # Check in suggestions dict first
    for name, data in HYDERABAD_SUGGESTIONS.items():
        if data.get("key") == venue_key:
            return {
                "Venue_Key": venue_key,
                "Venue_Name": name,
                "Commissionerate": data["commissionerate"],
                "Area": data["area"],
                "Latitude": data["lat"],
                "Longitude": data["lon"],
                "Capacity": data["capacity"],
                "Default_Hospital": data["default_hospital"]
            }

    df = load_venues()
    if df.empty:
        return None
    matches = df[df["Venue_Key"] == venue_key]
    if not matches.empty:
        return matches.iloc[0].to_dict()
    return None


def get_hospital(hospital_name: str) -> dict[str, Any] | None:
    """Get hospital record by name."""
    df = load_hospitals()
    if df.empty:
        return None
    h_clean = str(hospital_name).strip().lower()
    matches = df[df["Hospital_Name"].astype(str).str.strip().str.lower() == h_clean]
    if not matches.empty:
        return matches.iloc[0].to_dict()
    return None


def geocode_custom_location(query: str) -> tuple[float, float, str] | None:
    """
    Safely look up coordinates for a user-specified location in Hyderabad via OpenStreetMap Nominatim.
    Returns (lat, lon, display_name) or None if not found or unreachable.
    Never invents coordinates.
    """
    if not query or not query.strip():
        return None
    try:
        import requests
        headers = {"User-Agent": "traffic_copilot_location_lookup"}
        q = f"{query.strip()}, Hyderabad, India"
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": q, "format": "json", "limit": 1},
            headers=headers,
            timeout=5
        )
        if resp.status_code == 200:
            results = resp.json()
            if results and len(results) > 0:
                lat = float(results[0]["lat"])
                lon = float(results[0]["lon"])
                addr = str(results[0].get("display_name", query))
                return lat, lon, addr
    except Exception:
        pass
    return None


def get_road_network_path(venue_key: str, lat: float | None = None, lon: float | None = None, dist_m: int = 3000,
                          force_retry: bool = False) -> Path:
    """
    Path to the road graph for this venue (cached, or downloaded once with several Overpass mirrors).
    Raises osm_download.NetworkUnavailable if the roads for THIS location cannot be obtained.
    It never falls back to the Uppal network: a plan on the wrong roads is worse than no plan.
    """
    import osm_download
    return osm_download.get_graph_for_venue(venue_key, lat, lon, dist_m, force_retry)


def nearest_hospital(lat: float, lon: float, max_km: float = 12.0) -> dict[str, Any] | None:
    """Closest hospital in data/hyderabad_hospitals.csv within max_km, else None (never invents one)."""
    import math
    df = load_hospitals()
    if df.empty:
        return None
    best, best_d = None, None
    for _, r in df.iterrows():
        try:
            la, lo = float(r["Latitude"]), float(r["Longitude"])
        except (TypeError, ValueError):
            continue
        d = math.hypot((la - lat) * 111.0, (lo - lon) * 111.0 * math.cos(math.radians(lat)))
        if best_d is None or d < best_d:
            best, best_d = r.to_dict(), d
    if best is None or best_d > max_km:
        return None
    best["Distance_km"] = round(best_d, 1)
    return best
