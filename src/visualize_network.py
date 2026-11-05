import os
import osmnx as ox

# Project paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GRAPH_PATH = os.path.join(
    BASE_DIR, "data", "uppal_road_network.graphml"
)
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
OUTPUT_PATH = os.path.join(
    OUTPUT_DIR, "uppal_road_network.png"
)


def visualize_network():

    print("\n========== ROAD NETWORK VISUALIZATION ==========")

    # Load downloaded graph
    G = ox.load_graphml(GRAPH_PATH)

    print("Graph loaded successfully!")
    print("Total Nodes:", len(G.nodes))
    print("Total Edges:", len(G.edges))

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Save road network visualization
    fig, ax = ox.plot_graph(
        G,
        node_size=0,
        edge_linewidth=0.5,
        show=False,
        close=True,
        save=True,
        filepath=OUTPUT_PATH,
        dpi=200
    )

    print("\nRoad network visualization saved!")
    print("Location:", OUTPUT_PATH)

    print("\nNETWORK VISUALIZATION COMPLETED!")


if __name__ == "__main__":
    visualize_network()
