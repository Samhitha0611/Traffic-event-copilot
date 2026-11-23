"""
Traffic Event Co-Pilot: demo engine (works on the project's existing OSM graph).

Pipeline (maps to SIPOC):
  Inputs   -> event details + mode split + advisory data (Excel) + road graph (OSM)
  Process  -> demand per mode (PCU) -> load roads (naive vs optimised) -> V/C + delay
              -> hotspots -> alternate routes -> emergency corridor -> plan text
  Outputs  -> numbers, map layers, report

Every constant marked ASSUMED is a planning assumption, not measured data.
Traffic counts for Uppal event days are NOT public, so all loads are model estimates.
"""
from __future__ import annotations

import math
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
GRAPH_PATH = BASE_DIR / "data" / "uppal_road_network.graphml"
DATA_FILE = BASE_DIR / "data" / "uppal_stadium_event_traffic_data_pack.xlsx"
LOCATION_CSV = BASE_DIR / "outputs" / "location_mapping.csv"
MANUAL_LOCATION_CSV = BASE_DIR / "data" / "manual_locations.csv"

STADIUM = (17.4065, 78.5505)  # same centre point used in osm_network.py
# SOURCE: Wikipedia coordinates of Uppal metro station. The geocoder result stored in
# location_mapping.csv is about 1 km away from this point, so we override it.
UPPAL_METRO_VERIFIED = (17.3987948, 78.5538439)

# ---------------- travel modes (share of PEOPLE) ----------------
MODES = ("two_wheeler", "car", "auto_rickshaw", "cab", "bus", "metro", "walk")
ROAD_MODES = ("two_wheeler", "car", "auto_rickshaw", "cab", "bus")
DEFAULT_MODE_SHARE = {"two_wheeler": .25, "car": .25, "auto_rickshaw": .05, "cab": .05,
                      "bus": .15, "metro": .15, "walk": .10}          # ASSUMED
OCCUPANCY = {"two_wheeler": 1.25, "car": 2.5, "auto_rickshaw": 2.5, "cab": 2.0, "bus": 50.0}  # ASSUMED
PCU = {"two_wheeler": .4, "car": 1.0, "auto_rickshaw": .9, "cab": 1.0, "bus": 3.5}  # IRC:106-style, verify

# ---------------- time profile (triangular) ----------------
BUCKET_MIN = 15
ARRIVAL = (90, 60)      # ASSUMED window, mode (minutes) before start
DEPARTURE = (60, 20)    # ASSUMED window, mode (minutes) after end

# ---------------- road capacity / speed ----------------
CAP_PER_LANE = 1800     # ASSUMED PCU/lane/hour, likely optimistic for Indian mixed traffic
CAP_FACTOR = {"motorway": 1.0, "trunk": 1.0, "primary": .95, "secondary": .9, "tertiary": .8,
              "residential": .6, "unclassified": .6, "living_street": .5}   # ASSUMED friction
DEFAULT_LANES = {"motorway": 3, "trunk": 2, "primary": 2, "secondary": 2, "tertiary": 1,
                 "residential": 1, "unclassified": 1, "living_street": 1}   # per direction, ASSUMED
DEFAULT_SPEED = {"motorway": 50, "trunk": 40, "primary": 35, "secondary": 30, "tertiary": 25,
                 "residential": 20, "unclassified": 20, "living_street": 15}  # km/h ASSUMED urban
BPR_ALPHA, BPR_BETA, BPR_VC_CAP = 0.15, 4.0, 3.0
BACKGROUND_VC = {"trunk": .35, "primary": .35, "secondary": .30, "tertiary": .25}  # ASSUMED normal-day load
BACKGROUND_DEFAULT = .10
EMERGENCY_PENALTY = 3.0
MAX_EXTRA_M = 1000   # ASSUMED: police would not send traffic more than about 1 km extra

# ASSUMED share of event traffic arriving from each approach (edit in the app)
DEFAULT_APPROACH_SHARE = {"Habsiguda": .30, "Tarnaka": .10, "Ramanthapur": .20,
                          "Boduppal": .15, "Uppal X Roads": .25}
# Fallback coordinates (copied from outputs/location_mapping.csv) so the engine runs standalone
FALLBACK_LOCATIONS = {
    "Uppal Metro Station": UPPAL_METRO_VERIFIED,
    "Uppal X Roads": (17.4007724, 78.5604947),
    "Ramanthapur": (17.4018585, 78.5403825),
    "Habsiguda": (17.4154761, 78.5426918),
    "Boduppal": (17.3988408, 78.5366218),
    "Tarnaka": (17.4285479, 78.5379433),
}


# =====================================================================
# 1. ROAD NETWORK
# =====================================================================
def _first(v):
    return v[0] if isinstance(v, (list, tuple)) else v


def _num(v):
    try:
        m = re.search(r"\d+(\.\d+)?", str(_first(v)))
        return float(m.group()) if m else None
    except Exception:
        return None


def _rtype(h):
    h = str(_first(h) or "unclassified").replace("_link", "")
    return h if h in CAP_FACTOR else "unclassified"


def build_network(graph_path: Path = GRAPH_PATH):
    """Load the OSM graph, keep the largest strongly connected part, annotate every road.
    Returns (D, stats). D is a simple DiGraph (one edge per direction)."""
    import osmnx as ox
    G = ox.load_graphml(graph_path)
    G = ox.truncate.largest_component(G, strongly=True)
    D = nx.DiGraph()
    for n, d in G.nodes(data=True):
        D.add_node(n, lat=float(d["y"]), lon=float(d["x"]))
    lane_def = speed_def = total = 0
    for u, v, k, d in G.edges(keys=True, data=True):
        if D.has_edge(u, v) and D[u][v]["length"] <= float(d.get("length", 0)):
            continue
        rt = _rtype(d.get("highway"))
        total += 1
        lanes_tag = _num(d.get("lanes"))
        oneway = str(d.get("oneway")).lower() in ("true", "1", "yes")
        if lanes_tag:
            lanes = max(1, int(round(lanes_tag if oneway else lanes_tag / 2)))
        else:
            lanes, lane_def = DEFAULT_LANES[rt], lane_def + 1
        sp = _num(d.get("maxspeed"))
        if sp is None or sp <= 0:
            sp, speed_def = DEFAULT_SPEED[rt], speed_def + 1
        length = float(d.get("length", 1.0))
        D.add_edge(u, v, length=length, road_type=rt, lanes=lanes,
                   name=str(_first(d.get("name")) or ""),
                   cap=lanes * CAP_PER_LANE * CAP_FACTOR[rt],
                   t0=length / (sp / 3.6), speed=sp,
                   bg=BACKGROUND_VC.get(rt, BACKGROUND_DEFAULT),
                   geom=d.get("geometry"))
    types = pd.Series([d["road_type"] for _, _, d in D.edges(data=True)]).value_counts().to_dict()
    stats = {"nodes": D.number_of_nodes(), "edges": D.number_of_edges(),
             "pct_lanes_defaulted": round(100 * lane_def / max(total, 1), 1),
             "pct_speed_defaulted": round(100 * speed_def / max(total, 1), 1),
             "road_types": types}
    return D, stats


def nearest_node(D, lat, lon):
    ids = list(D.nodes)
    la = np.array([D.nodes[n]["lat"] for n in ids])
    lo = np.array([D.nodes[n]["lon"] for n in ids])
    d = (la - lat) ** 2 + ((lo - lon) * math.cos(math.radians(lat))) ** 2
    return ids[int(np.argmin(d))]


def haversine(a, b):
    R = 6371000
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def node_xy(D, n):
    return D.nodes[n]["lat"], D.nodes[n]["lon"]


def pick_parking_nodes(D, stadium_node, sectors=8, per_sector=3, target_m=800):
    """ASSUMED parking / drop-off zones around the stadium: per_sector nodes in each bearing sector,
    closest to target_m from the stadium. Spreading the zones stops dead-end streets from looking
    like false bottlenecks (real parking lists are not public coordinates)."""
    s = node_xy(D, stadium_node)
    cand = {}
    for n in D.nodes:
        la, lo = node_xy(D, n)
        dist = haversine(s, (la, lo))
        if not 400 <= dist <= 1300 or D.out_degree(n) < 2:
            continue
        brg = (math.degrees(math.atan2((lo - s[1]) * math.cos(math.radians(s[0])), la - s[0])) + 360) % 360
        cand.setdefault(int(brg // (360 / sectors)), []).append((abs(dist - target_m), n))
    out = []
    for sec in sorted(cand):
        out += [n for _, n in sorted(cand[sec])[:per_sector]]
    return out


def entry_nodes(D, latlon, n=4, radius_m=700):
    """Entry points for one approach: the n nearest junctions that touch an arterial road
    (tertiary or higher). Traffic arrives on main roads, not on one single junction."""
    arterial = {"tertiary", "secondary", "primary", "trunk", "motorway"}
    cand = []
    for node in D.nodes:
        dist = haversine(latlon, node_xy(D, node))
        if dist > radius_m:
            continue
        types = {D[node][w]["road_type"] for w in D.successors(node)} | {D[w][node]["road_type"] for w in D.predecessors(node)}
        if types & arterial:
            cand.append((dist, node))
    cand = [x[1] for x in sorted(cand)[:n]]
    return cand or [nearest_node(D, *latlon)]


ARTERIAL_RANK = {"trunk": 4, "primary": 3, "secondary": 2, "tertiary": 1}
COMPASS = ["North", "North-East", "East", "South-East", "South", "South-West", "West", "North-West"]


def auto_approaches(D, venue_latlon, n_sectors=8, n_entry=3, min_frac=0.55):
    """Approaches for ANY venue, taken from the real road map.
    Entry points are junctions on main roads (tertiary or higher) in the outer part of the graph.
    The share of traffic per direction is proportional to the capacity of the main roads there
    (ASSUMED proxy: wider roads bring more vehicles). Police can override shares in the app."""
    dist = {n: haversine(venue_latlon, node_xy(D, n)) for n in D.nodes}
    R = max(dist.values()) if dist else 0
    sectors = {}
    for n, dn in dist.items():
        if dn < min_frac * R:
            continue
        w, names = 0.0, []
        for v in D.successors(n):
            e = D[n][v]
            if e["road_type"] in ARTERIAL_RANK:
                w += e["cap"]
                if e["name"]:
                    names.append(e["name"])
        if w <= 0:
            continue
        la, lo = node_xy(D, n)
        brg = (math.degrees(math.atan2((lo - venue_latlon[1]) * math.cos(math.radians(venue_latlon[0])),
                                       la - venue_latlon[0])) + 360) % 360
        sec = int(((brg + 180 / n_sectors) % 360) // (360 / n_sectors))
        sectors.setdefault(sec, []).append((w, n, names))
    out, total = {}, sum(sum(x[0] for x in v) for v in sectors.values())
    for sec, items in sorted(sectors.items()):
        items.sort(key=lambda x: -x[0])
        top = items[:n_entry]
        weight = sum(x[0] for x in items)
        roads = [nm for x in top for nm in x[2]]
        via = max(set(roads), key=roads.count) if roads else None
        label = f"{COMPASS[sec]} approach" + (f" via {via}" if via else "")
        pts = [node_xy(D, x[1]) for x in top]
        out[label] = {"nodes": [x[1] for x in top], "share": weight / total if total else 0,
                      "latlon": (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)),
                      "auto": True}
    return out


def load_approaches(D, shares=None, n_entry=4, center_latlon=None):
    """Approach origins from the project's location_mapping.csv (fallback: built-in list or cardinal points)."""
    shares = dict(shares or DEFAULT_APPROACH_SHARE)
    coords = dict(FALLBACK_LOCATIONS)
    if LOCATION_CSV.exists():
        df = pd.read_csv(LOCATION_CSV)
        for _, r in df.iterrows():
            short = str(r["Location"]).split(",")[0].strip()
            if short in coords and short != "Uppal Metro Station":
                coords[short] = (float(r["Latitude"]), float(r["Longitude"]))

    # The named Uppal approaches only make sense for the Uppal stadium itself.
    # Any other venue gets approaches detected from its own road map.
    if center_latlon is not None and haversine(center_latlon, STADIUM) > 300:
        auto = auto_approaches(D, center_latlon, n_entry=n_entry)
        if auto:
            return auto
        clat, clon = center_latlon
        cardinal = {"North Corridor": (clat + 0.022, clon), "South Corridor": (clat - 0.022, clon),
                    "East Corridor": (clat, clon + 0.023), "West Corridor": (clat, clon - 0.023)}
        return {name: {"nodes": entry_nodes(D, pt, n_entry), "share": 1.0 / len(cardinal), "latlon": pt}
                for name, pt in cardinal.items()}

    tot = sum(shares.values()) or 1.0
    out = {}
    for name, sh in shares.items():
        if name in coords and sh > 0:
            out[name] = {"nodes": entry_nodes(D, coords[name], n_entry), "share": sh / tot, "latlon": coords[name]}
    return out


# =====================================================================
# 2. DEMAND (per mode)
# =====================================================================
def _tri_cdf(x, a, c, b):
    if x <= a: return 0.0
    if x >= b: return 1.0
    if x <= c: return (x - a) ** 2 / ((b - a) * (c - a))
    return 1.0 - (b - x) ** 2 / ((b - a) * (b - c))


def bucket_shares(window, mode, bucket=BUCKET_MIN):
    n = math.ceil(window / bucket)
    return [_tri_cdf(min((i + 1) * bucket, window), 0, mode, window) - _tri_cdf(i * bucket, 0, mode, window)
            for i in range(n)]


def time_curve(total, start_time, phase="ingress", duration_h=3.0):
    """15-minute buckets. ingress: before start. egress: after end (start + duration)."""
    t0 = datetime.strptime(start_time, "%H:%M")
    if phase == "ingress":
        window, mode = ARRIVAL; first = t0 - timedelta(minutes=window)
    else:
        window, mode = DEPARTURE; first = t0 + timedelta(hours=duration_h)
    sh = bucket_shares(window, mode)
    return pd.DataFrame({"Time": [(first + timedelta(minutes=BUCKET_MIN * i)).strftime("%H:%M") for i in range(len(sh))],
                         "PCU": [round(total * s, 1) for s in sh], "share": sh})


PRIVATE_MODES = ("two_wheeler", "car", "auto_rickshaw", "cab")


def mode_share_with_private_total(private_share):
    """Rescale DEFAULT_MODE_SHARE so private modes total `private_share` (0-1), keeping the relative mix."""
    bp = sum(DEFAULT_MODE_SHARE[m] for m in PRIVATE_MODES)
    return {m: DEFAULT_MODE_SHARE[m] * (private_share / bp if m in PRIVATE_MODES else (1 - private_share) / (1 - bp))
            for m in MODES}


def compute_demand(attendance, mode_share=None, start_time="19:30", phase="ingress", duration_h=3.0,
                   shift_to_metro_pct=0.0):
    ms = dict(mode_share or DEFAULT_MODE_SHARE)
    if shift_to_metro_pct > 0:   # what-if lever: move part of two-wheeler + car riders to metro
        for m in ("two_wheeler", "car"):
            moved = ms[m] * shift_to_metro_pct / 100
            ms[m] -= moved; ms["metro"] += moved
    s = sum(ms.values()); ms = {k: v / s for k, v in ms.items()}
    persons = {m: attendance * ms[m] for m in MODES}
    vehicles = {m: int(math.floor(persons[m] / OCCUPANCY[m] + .5)) for m in ROAD_MODES}
    pcu = {m: vehicles[m] * PCU[m] for m in ROAD_MODES}
    total_pcu = sum(pcu.values())
    window, mode = ARRIVAL if phase == "ingress" else DEPARTURE
    sh = bucket_shares(window, mode); peak = max(sh)
    curve = time_curve(total_pcu, start_time, phase, duration_h)
    return {"mode_share": ms, "persons": persons, "vehicles": vehicles, "pcu": pcu,
            "total_vehicles": sum(vehicles.values()), "total_pcu": total_pcu,
            "peak_share": peak, "peak_15min_pcu": total_pcu * peak, "peak_hourly_pcu": total_pcu * peak * 4,
            "peak_bucket": curve.loc[curve.share.idxmax(), "Time"], "curve": curve,
            "pedestrians": persons["metro"] + persons["walk"], "metro_riders": persons["metro"],
            "buses": vehicles["bus"]}


# =====================================================================
# 3. LOAD ASSIGNMENT (naive vs optimised) + metrics
# =====================================================================
def _bpr(t0, v, c):
    vc = v / c if c > 0 else 99
    return t0 * (1 + BPR_ALPHA * min(vc, BPR_VC_CAP) ** BPR_BETA)


class Router:
    """Fast shortest paths on the road graph (scipy). Weights live in D[u][v][attr]."""
    def __init__(self, D):
        from scipy.sparse import csr_matrix
        self.D, self.csr_matrix = D, csr_matrix
        self.ids = list(D.nodes)
        self.ix = {n: i for i, n in enumerate(self.ids)}
        self.edges = [(u, v) for u, v in D.edges]
        self.eu = np.array([self.ix[u] for u, _ in self.edges])
        self.ev = np.array([self.ix[v] for _, v in self.edges])

    def solve(self, sources, attr):
        from scipy.sparse.csgraph import dijkstra
        w = np.array([self.D[u][v][attr] for u, v in self.edges])
        g = self.csr_matrix((w, (self.eu, self.ev)), shape=(len(self.ids),) * 2)
        idx = [self.ix[s] for s in sources]
        dist, pred = dijkstra(g, directed=True, indices=idx, return_predecessors=True)
        return dist, pred

    def path(self, pred_row, src, tgt):
        a, b, out = self.ix[src], self.ix[tgt], []
        while b != a and b >= 0:
            out.append(b); b = pred_row[b]
        if b != a:
            return None
        out.append(a)
        return [self.ids[i] for i in reversed(out)]


def _aon(R, src_ids, src_nodes, flows, label):
    """All-or-nothing: send each OD flow along the current cheapest path (weight t_cur)."""
    dist, pred = R.solve(src_nodes, "t_cur")
    load, fed = {}, {}
    for si, sid in enumerate(src_ids):
        for (s2, tnode), f in flows[sid].items():
            if f <= 0:
                continue
            p = R.path(pred[si], src_nodes[si], tnode)
            if not p:
                continue
            lab = label(sid, tnode)
            for a, b in zip(p[:-1], p[1:]):
                load[(a, b)] = load.get((a, b), 0.0) + f
                fed.setdefault((a, b), set()).add(lab)
    return load, fed


def assign(D, approaches, parking, hourly_pcu, phase="ingress", iterations=6, protected=frozenset(), R=None):
    """Naive = every vehicle takes the free-flow shortest path (what a plain route optimiser does).
    Optimised = method of successive averages with BPR travel times (spreads load across roads)."""
    R = R or Router(D)
    for u, v, d in D.edges(data=True):
        d["t_cur"] = d["t0"] * (EMERGENCY_PENALTY if (u, v) in protected else 1.0)
    k = len(parking)
    node_to_app = {n: name for name, a in approaches.items() for n in a["nodes"]}
    if phase == "ingress":
        src_ids, src_nodes, flows = [], [], {}
        for name, a in approaches.items():
            for i, n in enumerate(a["nodes"]):
                sid = f"{name}#{i}"
                src_ids.append(sid); src_nodes.append(n)
                flows[sid] = {(sid, p): hourly_pcu * a["share"] / len(a["nodes"]) / k for p in parking}
        label = lambda sid, t: sid.split("#")[0]
    else:  # egress: from destination zones back to every approach
        src_ids = [f"P{i}" for i in range(k)]; src_nodes = list(parking)
        flows = {sid: {} for sid in src_ids}
        for sid in src_ids:
            for name, a in approaches.items():
                for n in a["nodes"]:
                    flows[sid][(sid, n)] = hourly_pcu * a["share"] / len(a["nodes"]) / k
        label = lambda sid, t: node_to_app.get(t, "?")
    runner = lambda: _aon(R, src_ids, src_nodes, flows, label)

    naive, fed_all = runner()
    v = dict(naive); history = []
    def maxvc(vload):
        return max(((vload.get(e, 0) + D[e[0]][e[1]]["bg"] * D[e[0]][e[1]]["cap"]) / D[e[0]][e[1]]["cap"]
                    for e in vload), default=0)
    history.append(round(maxvc(v), 2))
    for it in range(1, iterations + 1):
        for a, b, d in D.edges(data=True):
            load = v.get((a, b), 0.0) + d["bg"] * d["cap"]
            d["t_cur"] = _bpr(d["t0"], load, d["cap"]) * (EMERGENCY_PENALTY if (a, b) in protected else 1.0)
        y, fed = runner()
        for key, st in fed.items():
            fed_all.setdefault(key, set()).update(st)
        keys = set(v) | set(y)
        v = {e: v.get(e, 0.0) + (y.get(e, 0.0) - v.get(e, 0.0)) / (it + 1) for e in keys}
        history.append(round(maxvc(v), 2))
    return naive, v, fed_all, history


def edge_table(D, loads, fed=None):
    rows = []
    for (u, v), f in loads.items():
        d = D[u][v]
        tot = f + d["bg"] * d["cap"]
        m = _bpr(d["t0"], tot, d["cap"])
        rows.append({"edge": f"{u}-{v}", "u": u, "v": v, "name": d["name"] or f"({d['road_type']}, unnamed)",
                     "road_type": d["road_type"], "lanes": d["lanes"], "length_m": round(d["length"], 1),
                     "event_pcu_hr": round(f, 1), "background_pcu_hr": round(d["bg"] * d["cap"], 1),
                     "load_pcu_hr": round(tot, 1), "capacity_pcu_hr": round(d["cap"], 1),
                     "vc": round(tot / d["cap"], 2), "delay_sec": round(m - d["t0"], 1),
                     "fed_by": ", ".join(sorted(fed.get((u, v), []))) if fed else ""})
    return pd.DataFrame(rows).sort_values("vc", ascending=False).reset_index(drop=True) if rows else pd.DataFrame()


def group_hotspots(D, tbl, min_vc=0.8):
    """Merge neighbouring edges of the same street so the report lists streets, not fragments."""
    t = tbl[tbl.vc > min_vc].copy()
    if t.empty:
        return t.assign(street=[], segments=[])
    def label(r):
        if not r["name"].startswith("("):
            return r["name"]
        la, lo = node_xy(D, int(r.u))
        return f"Unnamed {r.road_type} road near {la:.3f}N {lo:.3f}E"
    t["street"] = t.apply(label, axis=1)
    g = (t.sort_values("vc", ascending=False).groupby("street", sort=False)
          .agg(u=("u", "first"), v=("v", "first"), edge=("edge", "first"), road_type=("road_type", "first"),
               lanes=("lanes", "first"), vc=("vc", "max"), load_pcu_hr=("load_pcu_hr", "max"),
               capacity_pcu_hr=("capacity_pcu_hr", "first"), delay_sec=("delay_sec", "sum"),
               segments=("edge", "count"), length_m=("length_m", "sum"),
               fed_by=("fed_by", lambda x: ", ".join(sorted({a.strip() for v in x for a in str(v).split(",") if a.strip()})))))
    return g.reset_index().sort_values("vc", ascending=False).reset_index(drop=True)


def summarize(tbl):
    if tbl.empty:
        return {"max_vc": 0, "congested": 0, "near": 0, "loaded_edges": 0}
    return {"max_vc": float(tbl.vc.max()), "congested": int((tbl.vc > 1.0).sum()),
            "near": int(((tbl.vc >= .8) & (tbl.vc <= 1.0)).sum()), "loaded_edges": int(len(tbl)),
            "total_delay_veh_hr": round(float((tbl.delay_sec * tbl.event_pcu_hr).sum() / 3600), 1)}


def corridor_times(D, approaches, parking, loads, R=None):
    """Average minutes from each approach to the destination zones: empty roads vs event peak."""
    R = R or Router(D)
    for u, v, d in D.edges(data=True):
        tot = loads.get((u, v), 0.0) + d["bg"] * d["cap"]
        d["t_ev"] = _bpr(d["t0"], tot, d["cap"])
    pidx = [R.ix[p] for p in parking]
    out = {}
    for name, a in approaches.items():
        d0, _ = R.solve(a["nodes"], "t0"); d1, _ = R.solve(a["nodes"], "t_ev")
        out[name] = {"free_min": round(float(np.mean(d0[:, pidx])) / 60, 1),
                     "peak_min": round(float(np.mean(d1[:, pidx])) / 60, 1)}
    return out


# =====================================================================
# 4. DIVERSIONS + EMERGENCY CORRIDOR
# =====================================================================
def alternate_route(D, u, v, protected=frozenset()):
    """Shortest alternative u->v without using edge (u,v) or protected edges. Never forces a bad one."""
    orig = D[u][v]
    H = D.copy()
    H.remove_edge(u, v)
    H.remove_edges_from([e for e in protected if H.has_edge(*e)])
    try:
        p = nx.shortest_path(H, u, v, weight="t0")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return {"feasible": False, "note": "No alternative road exists", "path": []}
    length = sum(H[a][b]["length"] for a, b in zip(p[:-1], p[1:]))
    t = sum(H[a][b]["t0"] for a, b in zip(p[:-1], p[1:]))
    extra = length - orig["length"]
    ok = extra <= MAX_EXTRA_M
    return {"feasible": bool(ok), "path": p, "extra_m": round(extra),
            "extra_s": round(t - orig["t0"]),
            "note": "OK" if ok else f"Detour adds {extra:.0f} m (limit {MAX_EXTRA_M} m)"}


def emergency_corridor(D, from_node, stadium_node):
    try:
        p = nx.shortest_path(D, from_node, stadium_node, weight="t0")
    except nx.NetworkXNoPath:
        return None
    edges = list(zip(p[:-1], p[1:]))
    return {"path": p, "edges": edges, "length_m": round(sum(D[a][b]["length"] for a, b in edges)),
            "free_min": round(sum(D[a][b]["t0"] for a, b in edges) / 60, 1)}


# =====================================================================
# 5. ORCHESTRATION + REPORT
# =====================================================================
def load_pack(path: Path = DATA_FILE):
    return pd.read_excel(path, sheet_name=None) if Path(path).exists() else {}


def event_options(pack):
    ev = pack.get("Events")
    if ev is None:
        return []
    out = []
    for _, r in ev.iterrows():
        if "calendar only" in str(r["Event_Type"]):
            continue
        m = re.search(r"(\d{1,2}:\d{2})", str(r["Match/Event_Start"]))
        out.append({"label": f"{pd.to_datetime(r['Date']).date()}  {r['Event_Name']}",
                    "date": pd.to_datetime(r["Date"]).date(), "name": r["Event_Name"],
                    "start": m.group(1) if m else "19:30", "start_known": bool(m),
                    "day_type": r["Day_Type"], "source": r["Source_URL"]})
    return out


def load_manual_locations(path=None) -> pd.DataFrame:
    """Read data/manual_locations.csv if present, returning empty DataFrame otherwise."""
    p = MANUAL_LOCATION_CSV if path is None else Path(path)
    if p.exists():
        try:
            return pd.read_csv(p)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def get_manual_hospital_and_parking(manual_df: pd.DataFrame | None = None, near_latlon=None, max_km: float = 5.0) -> tuple[tuple[float, float] | None, list[tuple[float, float]] | None]:
    """Extract first hospital coordinate and all parking coordinates from manual locations.
    Returns (hospital_latlon, parking_latlons). Either may be None if not found."""
    if manual_df is None:
        manual_df = load_manual_locations()
    if manual_df.empty:
        return None, None

    cols = {str(c).strip().lower(): c for c in manual_df.columns}
    if "type" not in cols or "latitude" not in cols or "longitude" not in cols:
        return None, None

    type_col = cols["type"]
    lat_col = cols["latitude"]
    lon_col = cols["longitude"]

    # Filter hospital rows (case-insensitive)
    h_mask = manual_df[type_col].astype(str).str.strip().str.lower() == "hospital"
    h_df = manual_df[h_mask]
    def _near(la, lo):
        return near_latlon is None or haversine(near_latlon, (la, lo)) <= max_km * 1000

    hospital_latlon = None
    for _, hr in h_df.iterrows():
        try:
            la, lo = float(hr[lat_col]), float(hr[lon_col])
        except (ValueError, TypeError):
            continue
        if _near(la, lo):
            hospital_latlon = (la, lo)
            break

    # Filter parking rows (case-insensitive)
    p_mask = manual_df[type_col].astype(str).str.strip().str.lower() == "parking"
    p_df = manual_df[p_mask]
    parking_latlons = []
    for _, r in p_df.iterrows():
        try:
            la, lo = float(r[lat_col]), float(r[lon_col])
        except (ValueError, TypeError):
            continue
        if _near(la, lo):
            parking_latlons.append((la, lo))

    return hospital_latlon, (parking_latlons if parking_latlons else None)


def run_scenario(D, params, pack=None):
    """params: attendance, start_time, phase, mode_share, approach_share, shift_pct, iterations,
    hospital_latlon (optional), event_date (optional), venue_latlon (optional), venue_name (optional)."""
    P = {"attendance": 39000, "start_time": "19:30", "phase": "ingress", "duration_h": 3.0,
         "mode_share": None, "approach_share": None, "shift_pct": 0.0, "iterations": 6,
         "hospital_latlon": None, "event_date": None, "event_name": "Custom event",
         "venue_latlon": None}
    P.update(params)
    venue_coords = P.get("venue_latlon") or STADIUM
    stadium = nearest_node(D, *venue_coords)

    # Read data/manual_locations.csv for hospital and parking zones
    manual_hosp, manual_parking = get_manual_hospital_and_parking(near_latlon=venue_coords)

    # Destination zones: rows with Type = parking, else generated zones
    if manual_parking:
        parking_nodes = [nearest_node(D, lat, lon) for lat, lon in manual_parking]
        parking = list(dict.fromkeys(parking_nodes))
        parking_is_generated = False
    else:
        parking = pick_parking_nodes(D, stadium)  # ASSUMED generated parking zones
        parking_is_generated = True

    # Emergency corridor start: rows with Type = hospital, else placeholder
    if P.get("hospital_latlon") is not None:
        hospital_latlon = P["hospital_latlon"]
        hospital_is_placeholder = False
    elif manual_hosp is not None:
        hospital_latlon = manual_hosp
        hospital_is_placeholder = False
    elif haversine(venue_coords, STADIUM) <= 300:
        hospital_latlon = FALLBACK_LOCATIONS["Habsiguda"]  # ASSUMED placeholder, Uppal demo only
        hospital_is_placeholder = True
    else:
        hospital_latlon = None   # no hospital known near this venue: say so, do not invent one
        hospital_is_placeholder = True
    P["hospital_latlon"] = hospital_latlon

    approaches = load_approaches(D, P["approach_share"], center_latlon=venue_coords)
    dem = compute_demand(P["attendance"], P["mode_share"], P["start_time"], P["phase"], P["duration_h"], P["shift_pct"])

    corridor = emergency_corridor(D, nearest_node(D, *hospital_latlon), stadium) if hospital_latlon else None
    if corridor:
        corridor["is_placeholder"] = hospital_is_placeholder
        corridor["tag"] = "E-1"
    protected = frozenset(corridor["edges"]) if corridor else frozenset()

    R = Router(D)
    naive, opt, fed, hist = assign(D, approaches, parking, dem["peak_hourly_pcu"], P["phase"], P["iterations"], protected, R)
    t_naive, t_opt = edge_table(D, naive), edge_table(D, opt, fed)
    s_naive, s_opt = summarize(t_naive), summarize(t_opt)
    times = corridor_times(D, approaches, parking, opt, R)

    hot = group_hotspots(D, t_opt)
    divs = []
    for idx, (_, r) in enumerate(hot.head(6).iterrows()):
        a = alternate_route(D, int(r.u), int(r.v), protected)
        a.update({"edge": r.edge, "name": r["street"], "vc": r.vc, "tag": f"D-{idx+1}"})
        divs.append(a)

    if corridor:  # ETA with and without protection (event load from the naive run)
        unprot = sum(_bpr(D[a][b]["t0"], naive.get((a, b), 0) + D[a][b]["bg"] * D[a][b]["cap"], D[a][b]["cap"])
                     for a, b in corridor["edges"]) / 60
        corridor["unprotected_min"] = round(unprot, 1)

    advis = pd.DataFrame()
    if pack and P["event_date"] is not None and "Diversions" in pack:
        dv = pack["Diversions"].copy(); dv["Date"] = pd.to_datetime(dv["Date"]).dt.date
        advis = dv[dv["Date"] == P["event_date"]]

    # Build operational tags dictionary
    tagged_junctions = []
    for idx, (app_name, a) in enumerate(approaches.items()):
        tagged_junctions.append({
            "tag": f"J-{idx+1}",
            "name": app_name,
            "share": a["share"],
            "latlon": a["latlon"],
            "nodes": a.get("nodes", [])
        })

    tagged_hotspots = []
    for idx, (_, r) in enumerate(hot.head(10).iterrows()):
        tagged_hotspots.append({
            "tag": f"H-{idx+1}",
            "street": r["street"],
            "road_type": r["road_type"],
            "lanes": r["lanes"],
            "vc": r["vc"],
            "load_pcu_hr": r["load_pcu_hr"],
            "capacity_pcu_hr": r["capacity_pcu_hr"],
            "fed_by": r["fed_by"],
            "u": r["u"],
            "v": r["v"]
        })

    tagged_parking = []
    for idx, p_node in enumerate(parking):
        tagged_parking.append({
            "tag": f"P-{idx+1}",
            "node": p_node,
            "xy": node_xy(D, p_node)
        })

    res = {"params": P, "demand": dem, "stadium": stadium, "parking": parking, "approaches": approaches,
           "naive": naive, "opt": opt, "table_naive": t_naive, "table_opt": t_opt,
           "sum_naive": s_naive, "sum_opt": s_opt, "history": hist, "times": times,
           "diversions": divs, "corridor": corridor, "advisory": advis, "hotspots": hot,
           "hospital_is_placeholder": hospital_is_placeholder, "parking_is_generated": parking_is_generated,
           "tagged_junctions": tagged_junctions, "tagged_hotspots": tagged_hotspots,
           "tagged_parking": tagged_parking}
    res["report"] = build_report(D, res)
    return res


def build_report(D, r):
    P, dem, so, sn = r["params"], r["demand"], r["sum_opt"], r["sum_naive"]
    L = []
    L.append(f"# Traffic Operation Plan: {P['event_name']}")
    L.append(f"*{P['phase'].title()} phase, event start {P['start_time']}, expected crowd {P['attendance']:,} (ASSUMED if not stated).*\n")
    
    L.append("## 1. Impact summary")
    L.append(f"- Road vehicle demand: **{dem['total_vehicles']:,} vehicles = {dem['total_pcu']:,.0f} PCU** (buses: {dem['buses']}).")
    L.append(f"- Peak 15-minute rush starts at **{dem['peak_bucket']}**: {dem['peak_15min_pcu']:,.0f} PCU, equal to **{dem['peak_hourly_pcu']:,.0f} PCU/hour**.")
    L.append(f"- Transit off-road: **{dem['metro_riders']:,.0f}** by metro and **{dem['persons']['walk']:,.0f}** on foot ({dem['pedestrians']:,.0f} pedestrians total).")
    
    L.append("\n## 2. Bottlenecks (model estimate)")
    L.append(f"- Naive unmanaged routing: max V/C **{sn['max_vc']:.2f}**, {sn['congested']} road(s) over capacity.")
    L.append(f"- Co-Pilot managed distribution: max V/C **{so['max_vc']:.2f}**, {so['congested']} road(s) over capacity, {so['near']} near capacity (0.8–1.0).")
    L.append("\n**Tactical Hotspot Deployments (`[H]` tags):**")
    for idx, x in enumerate(r["hotspots"].head(6).iterrows()):
        _, row = x
        tag = f"[H-{idx+1}]"
        L.append(f"- **{tag} {row.street}** ({row.road_type}, {row.lanes} lane): peak load {row.load_pcu_hr:,.0f} vs capacity {row.capacity_pcu_hr:,.0f} PCU/h (V/C **{row.vc:.2f}**); incoming stream: *{row.fed_by}*.")
    
    L.append("\n## 3. Diversion scheme")
    L.append("**Tactical Diversion Directives (`[D]` tags):**")
    for idx, d in enumerate(r["diversions"]):
        tag = d.get("tag", f"[D-{idx+1}]")
        if d["feasible"]:
            L.append(f"- **{tag} {d['name']}** (relieving bottleneck V/C {d['vc']:.2f}): Alternate detour adds **+{d['extra_m']:,} m** and **+{d['extra_s']} s**. Divert non-pass private vehicles.")
        else:
            L.append(f"- **{tag} {d['name']}** (relieving bottleneck V/C {d['vc']:.2f}): **No safe detour route available** ({d['note']}). Enforce hard turn-back.")
    
    if not r["advisory"].empty:
        L.append("\n- **Official Police Advisory Diversions for this Date:**")
        for _, a in r["advisory"].drop_duplicates(["Movement", "Diversion_Point"]).iterrows():
            L.append(f"  - *{a['Movement']}*: Divert at **{a['Diversion_Point']}** -> {a['Diverted_Route']}")
    
    L.append("\n## 4. Emergency protection")
    c = r["corridor"]
    if c:
        hosp_note = "hospital location is a placeholder (ASSUMED)" if r.get("hospital_is_placeholder", True) else "hospital location verified from records"
        L.append(f"- Protected Emergency Green Corridor **`[E-1]`**: **{c['length_m']:,} metres**.")
        L.append(f"  - Protected Free-Flow ETA: **{c['free_min']} minutes** (if corridor lane is kept clear).")
        L.append(f"  - Unprotected ETA: **{c['unprotected_min']} minutes** under event gridlock ({hosp_note}).")
        L.append(f"  - Time saved for trauma transport: **{max(0, c['unprotected_min'] - c['free_min']):.1f} minutes**.")

    L.append("\n## 5. Sectorization & Approach Checkpoints (`[J]` and `[P]` tags)")
    L.append("**Entry Checkpoint Junctions (`[J]` tags):**")
    for j in r.get("tagged_junctions", []):
        L.append(f"- **{j['tag']} {j['name']}**: Entry checkpoint handling **{j['share']*100:.0f}%** of spectator traffic.")
    L.append("\n**Spectator Parking Zones (`[P]` tags):**")
    for p in r.get("tagged_parking", []):
        L.append(f"- **{p['tag']}**: Designated spectator parking / holding zone (Coordinates: {p['xy'][0]:.4f}, {p['xy'][1]:.4f}).")

    L.append("\n## 6. Police Deployment Guidance (ASSUMED Heuristics)")
    tot_veh = dem.get("total_vehicles", 0)
    hs_count = len(r["hotspots"])
    traffic_si = max(2, round(hs_count * 0.8))
    traffic_constables = max(10, round(tot_veh / 800) + hs_count * 4)
    marshals = max(6, round(dem.get("pedestrians", 0) / 2500))
    L.append(f"- **Sector Officers (Sub-Inspectors/Inspectors):** ~{traffic_si} officers assigned across sectors.")
    L.append(f"- **Traffic Constables / Marshals:** ~{traffic_constables} personnel for checkpoints `[J-1]`–`[J-4]` and diversions `[D-1]`–`[D-3]`.")
    L.append(f"- **Crowd Controllers:** ~{marshals} marshals at transit stations and entry turnstiles.")

    L.append("\n## 7. Public Advisory Bulletin")
    top_str = ", ".join(r["hotspots"].head(3)["street"].tolist()) if len(r["hotspots"]) else "the venue vicinity"
    L.append(f"> Heavy congestion expected around the venue from {P['start_time']}. Avoid {top_str}. "
             f"Commuters are urged to take Metro or TGSRTC special shuttle services.")

    L.append("\n## 8. Data status")
    L.append("- Road network: OpenStreetMap (real). Event dates, advisories, diversions: public police advisories (real).")
    L.append("- Vehicle counts, speeds, queues on event days: **not available**; all loads here are model estimates (ASSUMED parameters).")
    return "\n".join(L)
