"""
Download roads from the main OpenStreetMap API (api.openstreetmap.org) in small tiles.

Used automatically when the Overpass servers are slow or refuse the request. No API key needed.
The API refuses areas with more than 50,000 nodes, so the area is cut into tiles and any tile that is
still too big is split again. Only drivable roads are kept (same idea as OSMnx's 'drive' filter).
Please keep usage light: a few venues, once. Results are cached on disk.
"""
from __future__ import annotations

import math
import time
import xml.etree.ElementTree as ET
from typing import Callable, Iterator

API_URL = "https://api.openstreetmap.org/api/0.6/map"
HEADERS = {"User-Agent": "traffic_event_copilot_student_project (OSM API tiles)"}
TILE_M = 1000
MAX_SPLIT_DEPTH = 3
PAUSE_S = 0.6

EXCLUDED_HIGHWAY = {"abandoned", "bridleway", "bus_guideway", "construction", "corridor", "cycleway", "elevator",
                    "escalator", "footway", "no", "path", "pedestrian", "planned", "platform", "proposed",
                    "raceway", "razed", "steps", "track"}
EXCLUDED_SERVICE = {"alley", "driveway", "emergency_access", "parking", "parking_aisle", "private"}


class TooManyNodes(RuntimeError):
    pass


def bbox_around(lat: float, lon: float, radius_m: float) -> tuple[float, float, float, float]:
    dlat = radius_m / 111320.0
    dlon = radius_m / (111320.0 * math.cos(math.radians(lat)))
    return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)          # west, south, east, north


def tile_boxes(lat: float, lon: float, radius_m: float, tile_m: float = TILE_M) -> list[tuple]:
    w, s, e, n = bbox_around(lat, lon, radius_m)
    k = max(1, math.ceil(2 * radius_m / tile_m))
    out = []
    for i in range(k):
        for j in range(k):
            out.append((w + (e - w) * j / k, s + (n - s) * i / k, w + (e - w) * (j + 1) / k, s + (n - s) * (i + 1) / k))
    return out


def _split(b):
    w, s, e, n = b
    mx, my = (w + e) / 2, (s + n) / 2
    return [(w, s, mx, my), (mx, s, e, my), (w, my, mx, n), (mx, my, e, n)]


def _fetch(bbox, session, retries: int = 4) -> bytes:
    params = {"bbox": ",".join(f"{x:.6f}" for x in bbox)}
    for attempt in range(retries):
        r = session.get(API_URL, params=params, headers=HEADERS, timeout=(15, 120))
        if r.status_code == 400:
            raise TooManyNodes("tile has too many nodes")
        if r.status_code in (429, 509, 503):
            time.sleep(5 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.content
    raise RuntimeError("OpenStreetMap API is rate-limiting this computer. Wait a few minutes and retry.")


def fetch_area(bbox, session, depth: int = 0, sleep: Callable = time.sleep) -> Iterator[bytes]:
    try:
        sleep(PAUSE_S)
        yield _fetch(bbox, session)
    except TooManyNodes:
        if depth >= MAX_SPLIT_DEPTH:
            raise
        for sub in _split(bbox):
            yield from fetch_area(sub, session, depth + 1, sleep)


def is_drivable(tags: dict) -> bool:
    hw = tags.get("highway")
    if not hw or hw in EXCLUDED_HIGHWAY:
        return False
    if tags.get("area") == "yes" or tags.get("motor_vehicle") == "no" or tags.get("motorcar") == "no":
        return False
    if tags.get("service") in EXCLUDED_SERVICE:
        return False
    return True


def merge_and_filter(chunks: list[bytes]) -> bytes:
    """Merge OSM XML pieces, drop duplicates, keep only drivable ways and the nodes they use."""
    nodes, ways = {}, {}
    for c in chunks:
        root = ET.fromstring(c)
        for el in root:
            if el.tag == "node":
                nodes.setdefault(el.get("id"), el)
            elif el.tag == "way":
                if el.get("id") in ways:
                    continue
                tags = {t.get("k"): t.get("v") for t in el.findall("tag")}
                if is_drivable(tags):
                    ways[el.get("id")] = el
    used = {nd.get("ref") for w in ways.values() for nd in w.findall("nd")}
    out = ET.Element("osm", version="0.6")
    for nid in used:
        if nid in nodes:
            out.append(nodes[nid])
    for w in ways.values():
        out.append(w)
    return ET.tostring(out, encoding="utf-8", xml_declaration=True)


def download_area_xml(lat: float, lon: float, radius_m: float, session=None, progress: Callable | None = None,
                      sleep: Callable = time.sleep) -> bytes:
    if session is None:
        import requests
        session = requests
    tiles = tile_boxes(lat, lon, radius_m)
    chunks = []
    for i, b in enumerate(tiles, 1):
        chunks.extend(fetch_area(b, session, 0, sleep))
        if progress:
            progress(i, len(tiles))
    return merge_and_filter(chunks)
