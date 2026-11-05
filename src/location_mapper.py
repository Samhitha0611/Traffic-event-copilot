import os
import time
import math
import osmnx as ox
import pandas as pd

# Project paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GRAPH_PATH = os.path.join(
    BASE_DIR, "data", "uppal_road_network.graphml"
)
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
OUTPUT_PATH = os.path.join(
    OUTPUT_DIR, "location_mapping.csv"
)
MANUAL_LOCATIONS_PATH = os.path.join(
    BASE_DIR, "data", "manual_locations.csv"
)

SEARCH_RADIUS = 3000       # 3 km
MAX_SNAP_DISTANCE = 250    # Maximum acceptable distance to a road


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate straight-line distance between two coordinates."""

    R = 6371000

    lat1, lon1, lat2, lon2 = map(
        math.radians, [lat1, lon1, lat2, lon2]
    )

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    return 2 * R * math.asin(math.sqrt(a))


def find_manual_location(place, manual_df):
    """Check if place exists in manual locations."""
    if manual_df is None or manual_df.empty:
        return None
    place_clean = place.strip().lower()
    place_short = place_clean.split(",")[0].strip()
    for _, row in manual_df.iterrows():
        lat_val = row.get("Latitude")
        lon_val = row.get("Longitude")
        if pd.isna(lat_val) or pd.isna(lon_val) or str(lat_val).strip() == "" or str(lon_val).strip() == "":
            continue
        man_loc = str(row["Location"]).strip().lower()
        man_short = man_loc.split(",")[0].strip()
        if man_loc == place_clean or man_short == place_short or place_clean.startswith(man_short):
            return row
    return None


def map_locations():

    print("\n========== HYDERABAD LOCATION MAPPING ==========")

    # Load existing road network
    if not os.path.exists(GRAPH_PATH):
        print("Road network file not found!")
        return

    G = ox.load_graphml(GRAPH_PATH)

    print("Road network loaded successfully!")
    print("Total Nodes:", len(G.nodes))
    print("Total Edges:", len(G.edges))

    # Load manual locations
    manual_df = None
    if os.path.exists(MANUAL_LOCATIONS_PATH):
        manual_df = pd.read_csv(MANUAL_LOCATIONS_PATH)
        print(f"Loaded {len(manual_df)} manual location(s) from {MANUAL_LOCATIONS_PATH}")

    # Reference location
    center_place = (
        "Rajiv Gandhi International Cricket Stadium, "
        "Uppal, Hyderabad, India"
    )

    center_lat, center_lon = ox.geocode(center_place)

    print("\nReference Location: Uppal Stadium")
    print("Latitude:", center_lat)
    print("Longitude:", center_lon)

    # Candidate locations to investigate
    locations = [
        "Uppal Metro Station, Hyderabad, India",
        "Uppal X Roads, Hyderabad, India",
        "Ramanthapur, Hyderabad, India",
        "Nagole Metro Station, Hyderabad, India",
        "Habsiguda, Hyderabad, India",
        "Boduppal, Hyderabad, India",
        "Tarnaka, Hyderabad, India",
        "Ghatkesar, Telangana, India",
        "Stadium Metro Station",
        "NGRI Metro Station"
    ]

    results = []

    for place in locations:

        print("\nProcessing:", place)

        manual_row = find_manual_location(place, manual_df)
        if manual_row is not None:
            lat = float(manual_row["Latitude"])
            lon = float(manual_row["Longitude"])
            source = str(manual_row.get("Source", "Manual"))
            verified = manual_row.get("Verified", True)
            print(f"Using manual location for '{place}' (Source: {source}, Verified: {verified})")
        else:
            lat, lon = None, None
            geocode_error = None
            for attempt in range(2):
                try:
                    lat, lon = ox.geocode(place)
                    break
                except Exception as e:
                    geocode_error = e
                    print(f"Geocoding attempt {attempt + 1} failed for '{place}': {type(e).__name__} - {e}")
                    if attempt == 0:
                        print(f"Retrying geocoding for '{place}'...")
                        time.sleep(2.0)

            if lat is None or lon is None:
                print(f"FAILED to geocode '{place}'. Reason: {type(geocode_error).__name__} - {geocode_error}")
                time.sleep(1.2)
                continue

            verified = "UNVERIFIED"

        try:
            # Distance from Uppal Stadium
            center_distance = calculate_distance(
                center_lat, center_lon, lat, lon
            )

            # Check candidate metro stations distance to stadium centre
            stadium_candidates = ["Stadium Metro Station", "NGRI Metro Station"]
            if any(cand in place for cand in stadium_candidates):
                if center_distance > 600:
                    verified = "UNVERIFIED"
                    print(f"WARNING: Geocoded location for '{place}' is {center_distance:.2f} m from stadium centre (> 600 m). Marked UNVERIFIED.")
                else:
                    verified = "VERIFIED"

            # Find nearest road network node
            nearest_node = ox.distance.nearest_nodes(
                G,
                X=lon,
                Y=lat
            )

            node_data = G.nodes[nearest_node]

            node_lat = node_data["y"]
            node_lon = node_data["x"]

            # Distance from location to nearest road node
            road_distance = calculate_distance(
                lat, lon, node_lat, node_lon
            )

            # Check coverage and road proximity
            if center_distance > SEARCH_RADIUS:
                status = "OUTSIDE 3 KM"

            elif road_distance > MAX_SNAP_DISTANCE:
                status = "ROAD TOO FAR"

            else:
                status = "MAPPED SUCCESSFULLY"

            results.append({
                "Location": place,
                "Latitude": lat,
                "Longitude": lon,
                "Distance_From_Stadium_m": round(center_distance, 2),
                "Nearest_Node": nearest_node,
                "Road_Distance_m": round(road_distance, 2),
                "Status": status,
                "Verified": verified
            })

            print("Distance from Stadium:", round(center_distance, 2), "m")
            print("Nearest Node:", nearest_node)
            print("Distance to Road:", round(road_distance, 2), "m")
            print("Status:", status)
            print("Verified:", verified)

        except Exception as e:
            print("Could not process location road mapping:", e)

        # Avoid sending geocoding requests too quickly
        time.sleep(1.2)

    # Save results
    if results:

        os.makedirs(OUTPUT_DIR, exist_ok=True)

        df = pd.DataFrame(results)
        df.to_csv(OUTPUT_PATH, index=False)

        print("\n========== LOCATION MAPPING SUMMARY ==========")

        print(df[
            ["Location", "Distance_From_Stadium_m",
             "Road_Distance_m", "Status", "Verified"]
        ].to_string(index=False))

        print("\nTotal Locations:", len(df))
        print(
            "Successfully Mapped:",
            (df["Status"] == "MAPPED SUCCESSFULLY").sum()
        )

        print("\nResults saved to:", OUTPUT_PATH)

    print("\nLOCATION MAPPING COMPLETED!")

if __name__ == "__main__":
    map_locations()
