import os
import networkx as nx
import osmnx as ox
import pandas as pd

# Project paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GRAPH_PATH = os.path.join(
    BASE_DIR, "data", "uppal_road_network.graphml"
)
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
CSV_PATH = os.path.join(
    OUTPUT_DIR, "location_mapping.csv"
)
OUTPUT_PATH = os.path.join(
    OUTPUT_DIR, "connectivity_results.csv"
)


def check_connectivity():

    print("\n========== ROAD CONNECTIVITY ANALYSIS ==========")

    # Load road network
    G = ox.load_graphml(GRAPH_PATH)

    print("Road network loaded!")
    print("Nodes:", len(G.nodes))
    print("Edges:", len(G.edges))

    # Load mapped locations
    df = pd.read_csv(CSV_PATH)

    # Keep successfully mapped locations only
    df = df[df["Status"] == "MAPPED SUCCESSFULLY"]

    # Create location-to-node mapping
    location_nodes = dict(
        zip(df["Location"], df["Nearest_Node"])
    )

    # Select location pairs for testing
    test_pairs = [
        (
            "Uppal X Roads, Hyderabad, India",
            "Ramanthapur, Hyderabad, India"
        ),
        (
            "Uppal Metro Station, Hyderabad, India",
            "Habsiguda, Hyderabad, India"
        ),
        (
            "Boduppal, Hyderabad, India",
            "Tarnaka, Hyderabad, India"
        )
    ]

    results = []

    for source_name, destination_name in test_pairs:

        print("\n------------------------------------")
        print("Source:", source_name)
        print("Destination:", destination_name)

        source = location_nodes[source_name]
        destination = location_nodes[destination_name]

        try:

            # Check directed road connectivity
            if nx.has_path(G, source, destination):

                route = nx.shortest_path(
                    G,
                    source,
                    destination,
                    weight="length"
                )

                distance = nx.shortest_path_length(
                    G,
                    source,
                    destination,
                    weight="length"
                )

                status = "CONNECTED"

                print("Status:", status)
                print("Route Nodes:", len(route))
                print("Road Distance:", round(distance, 2), "meters")

            else:

                distance = None
                route = []
                status = "NO DIRECTED PATH"

                print("Status:", status)

            results.append({
                "Source": source_name,
                "Destination": destination_name,
                "Status": status,
                "Road_Distance_m": (
                    round(distance, 2)
                    if distance is not None else None
                ),
                "Route_Node_Count": len(route)
            })

        except nx.NetworkXNoPath:

            print("No route available!")

        except Exception as e:

            print("Error:", e)

    # Save connectivity results
    if results:

        os.makedirs(OUTPUT_DIR, exist_ok=True)

        result_df = pd.DataFrame(results)

        result_df.to_csv(
            OUTPUT_PATH,
            index=False
        )

        print("\n========== CONNECTIVITY SUMMARY ==========")

        print(result_df.to_string(index=False))

        print("\nResults saved to:", OUTPUT_PATH)

    print("\nCONNECTIVITY ANALYSIS COMPLETED!")

if __name__ == "__main__":
    check_connectivity()
