"""
Robust OpenStreetMap road download for ANY Hyderabad location.

Why this exists: the public Overpass server (overpass-api.de) can time out on some networks
(college/office wifi, firewalls, busy server). The old code then silently reused the Uppal roads,
which produced a plan for the wrong place. This module:
  1. reuses a cached graph if one already covers the venue,
  2. otherwise tests several Overpass mirrors quickly (6 s each, not 180 s),
  3. downloads once and caches the result,
  4. NEVER falls back to another area. If nothing works it raises NetworkUnavailable.
No API key is needed for OpenStreetMap.
"""
from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
NETWORKS_DIR = DATA_DIR / "networks"
UPPAL_GRAPHML = DATA_DIR / "uppal_road_network.graphml"
ENDPOINT_FILE = DATA_DIR / ".overpass_endpoint.json"

# Public Overpass servers. Edit freely, or set OVERPASS_URLS="https://a/api,https://b/api" in your environment.
DEFAULT_ENDPOINTS = [
    "https://overpass-api.de/api",
    "https://overpass.kumi.systems/api",
    "https://overpass.private.coffee/api",
    "https://overpass.openstreetmap.fr/api",
]
PROBE_TIMEOUT_S = 10
DOWNLOAD_TIMEOUT_S = 120
ENDPOINT_TTL_S = 6 * 3600
RETRY_AFTER_S = 600          # after a failed download, do not retry the same venue for 10 minutes
MIN_COVER_RADIUS_M = 2000    # a cached graph must leave at least this radius around the venue

_FAILED: dict[str, tuple[float, str]] = {}


class NetworkUnavailable(RuntimeError):
    """Raised when road data for a location cannot be obtained. The app must show this, not guess."""


def endpoints() -> list[str]:
    env = os.environ.get("OVERPASS_URLS", "").strip()
    return [u.strip().rstrip("/") for u in env.split(",") if u.strip()] if env else list(DEFAULT_ENDPOINTS)


def haversine_m(a, b) -> float:
    R = 6371000
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


# ------------------------------------------------------------------ endpoints
def probe_detail(endpoint: str, timeout: float = PROBE_TIMEOUT_S) -> tuple[bool, str]:
    """(reachable, note). Any HTTP answer below 500 means the server is reachable. A read timeout means
    it is reachable but too slow right now (Overpass is often overloaded), not blocked."""
    try:
        import requests
        r = requests.get(endpoint + "/status", timeout=(timeout, timeout * 2), headers={"User-Agent": "traffic_copilot"})
        return r.status_code < 500, f"HTTP {r.status_code}"
    except Exception as exc:
        return False, type(exc).__name__


def probe(endpoint: str, timeout: float = PROBE_TIMEOUT_S) -> bool:
    return probe_detail(endpoint, timeout)[0]


def check_endpoints() -> list[tuple[str, bool]]:
    return [(e, probe(e)) for e in endpoints()]


def pick_endpoint(force: bool = False) -> str:
    """First reachable Overpass server (result remembered for 6 hours)."""
    if not force and ENDPOINT_FILE.exists():
        try:
            d = json.loads(ENDPOINT_FILE.read_text())
            if time.time() - d["time"] < ENDPOINT_TTL_S and d["url"] in endpoints():
                return d["url"]
        except Exception:
            pass
    for e in endpoints():
        if probe(e):
            try:
                ENDPOINT_FILE.write_text(json.dumps({"url": e, "time": time.time()}))
            except Exception:
                pass
            return e
    raise NetworkUnavailable(
        "Cannot reach any OpenStreetMap (Overpass) server from this computer. "
        "Try a mobile hotspot or VPN, or run `py scripts/diagnose_network.py` to see why. "
        "If your browser works but Python does not, download the area as a file and use `py scripts/import_osm_file.py` (see its header). "
        "No API key is needed; this is a network block or timeout."
    )


# ------------------------------------------------------------------ cache + coverage
def _meta_path(graph_path: Path) -> Path:
    return graph_path.with_suffix(".meta.json")


def write_meta(graph_path: Path, center: tuple[float, float], radius_m: float) -> None:
    _meta_path(graph_path).write_text(json.dumps({"lat": center[0], "lon": center[1], "radius_m": radius_m}))


def ensure_meta(graph_path: Path) -> dict | None:
    """Coverage info for a cached graph. Computed once from the graph itself if no sidecar exists."""
    mp = _meta_path(graph_path)
    if mp.exists():
        try:
            return json.loads(mp.read_text())
        except Exception:
            pass
    try:
        import osmnx as ox
        G = ox.load_graphml(graph_path)
        ys = [d["y"] for _, d in G.nodes(data=True)]
        xs = [d["x"] for _, d in G.nodes(data=True)]
        c = (sum(ys) / len(ys), sum(xs) / len(xs))
        r = 0.9 * max(haversine_m(c, (y, x)) for y, x in zip(ys, xs))
        write_meta(graph_path, c, r)
        return {"lat": c[0], "lon": c[1], "radius_m": r}
    except Exception:
        return None


def find_covering_graph(lat: float, lon: float, min_radius_m: float = MIN_COVER_RADIUS_M) -> Path | None:
    """A cached graph whose area contains a disc of min_radius_m around the venue."""
    files = list(NETWORKS_DIR.glob("*.graphml")) + ([UPPAL_GRAPHML] if UPPAL_GRAPHML.exists() else [])
    for f in files:
        m = ensure_meta(f)
        if m and haversine_m((m["lat"], m["lon"]), (lat, lon)) + min_radius_m <= m["radius_m"]:
            return f
    return None


# ------------------------------------------------------------------ download
def _download_overpass(lat, lon, dist_m, out_path: Path) -> Path:
    import osmnx as ox
    first = pick_endpoint()
    order = [first] + [e for e in endpoints() if e != first]
    last = None
    for ep in order[:2]:      # two tries at most: Overpass is often overloaded, the OSM API is the safety net
        try:
            ox.settings.overpass_url = ep
            ox.settings.requests_timeout = DOWNLOAD_TIMEOUT_S
            ox.settings.overpass_rate_limit = False
            G = ox.graph_from_point((lat, lon), dist=dist_m, network_type="drive", simplify=True)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            ox.save_graphml(G, filepath=out_path)
            write_meta(out_path, (lat, lon), 0.9 * dist_m)
            return out_path
        except Exception as exc:
            last = exc
    raise NetworkUnavailable(f"Overpass failed ({last})")


def download_graph_via_api(lat, lon, dist_m, out_path: Path, session=None, progress=None) -> Path:
    """Fallback: roads from api.openstreetmap.org in tiles (needs only www/api.openstreetmap.org)."""
    import osm_api_download as API
    import osm_file_import as OFI
    xml = API.download_area_xml(lat, lon, dist_m, session=session, progress=progress)
    return OFI.build_and_save(xml, lat, lon, dist_m, out_path)


def download_graph(lat: float, lon: float, dist_m: int, out_path: Path) -> Path:
    """Overpass first (quick attempt), then the main OSM API in tiles. ROAD_SOURCE=api|overpass|auto."""
    mode = os.environ.get("ROAD_SOURCE", "auto").lower()
    errors = []
    if mode in ("auto", "overpass"):
        try:
            return _download_overpass(lat, lon, dist_m, out_path)
        except Exception as exc:
            errors.append(f"Overpass: {exc}")
    if mode in ("auto", "api"):
        try:
            return download_graph_via_api(lat, lon, dist_m, out_path)
        except Exception as exc:
            errors.append(f"OSM API: {exc}")
    raise NetworkUnavailable("Road download failed. " + " | ".join(errors) +
                             " Try again later, or export the area in your browser and use scripts/import_osm_file.py.")


def get_graph_for_venue(venue_key: str, lat: float | None, lon: float | None, dist_m: int = 3000,
                        force_retry: bool = False) -> Path:
    """Path to a road graph that really covers the venue, or raise NetworkUnavailable. Never returns another area."""
    if (venue_key.startswith("uppal")) and UPPAL_GRAPHML.exists():
        return UPPAL_GRAPHML
    NETWORKS_DIR.mkdir(parents=True, exist_ok=True)
    cached = NETWORKS_DIR / f"{venue_key}.graphml"
    if cached.exists():
        return cached
    if lat is None or lon is None:
        raise NetworkUnavailable(f"No road network saved for '{venue_key}' and no coordinates were given.")
    cover = find_covering_graph(lat, lon)
    if cover is not None:
        return cover
    if not force_retry and venue_key in _FAILED and time.time() - _FAILED[venue_key][0] < RETRY_AFTER_S:
        raise NetworkUnavailable(_FAILED[venue_key][1])
    try:
        return download_graph(lat, lon, dist_m, cached)
    except NetworkUnavailable as exc:
        _FAILED[venue_key] = (time.time(), str(exc))
        raise
