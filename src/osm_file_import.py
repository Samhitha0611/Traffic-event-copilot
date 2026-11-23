"""
Build a venue road map from OpenStreetMap XML (a file you downloaded, or tiles from the OSM API).
The result is saved exactly like an automatic download, so the app picks it up.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import osm_api_download as API
import osm_download as OD


def build_and_save(xml_bytes: bytes, lat: float, lon: float, radius_m: int, out_path: Path) -> Path:
    import networkx as nx
    import osmnx as ox
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "roads.osm"
        f.write_bytes(xml_bytes)
        G = ox.graph_from_xml(f, simplify=True)
    keep = [n for n, d in G.nodes(data=True) if OD.haversine_m((lat, lon), (d["y"], d["x"])) <= radius_m]
    if len(keep) < 50:
        raise ValueError("The data has almost no roads within the radius of this venue. "
                         "Check that the area around the venue was downloaded and that lat/lon are right.")
    H = G.subgraph(keep).copy()
    H = H.subgraph(max(nx.strongly_connected_components(H), key=len)).copy()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(H, filepath=out_path)
    OD.write_meta(out_path, (lat, lon), 0.9 * radius_m)
    return out_path


def import_osm_file(osm_path: str | Path, venue_key: str, lat: float, lon: float, radius_m: int = 3000) -> Path:
    """Browser export (map.osm) -> saved venue graph. Non-drivable ways (footpaths etc.) are removed first."""
    osm_path = Path(osm_path)
    if not osm_path.exists():
        raise FileNotFoundError(f"File not found: {osm_path}")
    xml = API.merge_and_filter([osm_path.read_bytes()])
    return build_and_save(xml, lat, lon, radius_m, OD.NETWORKS_DIR / f"{venue_key}.graphml")
