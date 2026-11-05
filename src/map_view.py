"""Folium map for the demo: roads coloured by V/C, diversions, emergency corridor, zones."""
import folium
import pandas as pd

from event_engine import STADIUM, UPPAL_METRO_VERIFIED, node_xy, load_manual_locations

ARTERIAL = {"tertiary", "secondary", "primary", "trunk", "motorway"}


def _coords(D, u, v):
    g = D[u][v].get("geom")
    if g is not None and hasattr(g, "coords"):
        return [(lat, lon) for lon, lat in g.coords]
    return [node_xy(D, u), node_xy(D, v)]


def _colour(vc):
    return "#d62728" if vc > 1.0 else "#ffbf00" if vc >= 0.8 else "#2ca02c"


def make_map(D, res, use_naive=False, show_zones=True):
    m = folium.Map(location=STADIUM, zoom_start=14, tiles="OpenStreetMap", control_scale=True)
    base = folium.FeatureGroup("Main roads (grey)")
    for u, v, d in D.edges(data=True):
        if d["road_type"] in ARTERIAL:
            folium.PolyLine(_coords(D, u, v), color="#b0b0b0", weight=1.5, opacity=.7).add_to(base)
    base.add_to(m)

    tbl = res["table_naive" if use_naive else "table_opt"]
    roads = folium.FeatureGroup("Event load (V/C)")
    for _, r in tbl.iterrows():
        if r.vc < 0.5:
            continue
        tip = (f"<b>{r['name']}</b><br>{r.road_type}, {r.lanes} lane(s)<br>"
               f"load {r.load_pcu_hr:,.0f} / capacity {r.capacity_pcu_hr:,.0f} PCU/h<br>"
               f"<b>V/C {r.vc:.2f}</b>, delay {r.delay_sec:.0f}s<br>fed by: {r.fed_by or 'n/a'}")
        folium.PolyLine(_coords(D, int(r.u), int(r.v)), color=_colour(r.vc),
                        weight=3 + min(r.vc, 3) * 1.5, opacity=.9, tooltip=folium.Tooltip(tip)).add_to(roads)
    roads.add_to(m)

    if res["corridor"]:
        em = folium.FeatureGroup("Emergency corridor (protected)")
        for u, v in res["corridor"]["edges"]:
            folium.PolyLine(_coords(D, u, v), color="#6a0dad", weight=6, opacity=.9, dash_array="10 8",
                            tooltip="Protected emergency corridor").add_to(em)
        em.add_to(m)
        la, lo = node_xy(D, res["corridor"]["path"][0])
        folium.Marker((la, lo), tooltip="Hospital (PLACEHOLDER location)",
                      icon=folium.Icon(color="purple", icon="plus", prefix="fa")).add_to(m)

    dv = folium.FeatureGroup("Recommended diversions")
    for d in res["diversions"]:
        if d["feasible"] and d.get("path"):
            pts = [node_xy(D, n) for n in d["path"]]
            folium.PolyLine(pts, color="#1f77b4", weight=5, dash_array="4 6",
                            tooltip=f"Diversion for {d['name']}: +{d['extra_m']} m, +{d['extra_s']} s").add_to(dv)
    dv.add_to(m)

    # Turn-back points from data/manual_locations.csv
    manual_df = load_manual_locations()
    if not manual_df.empty and "Type" in manual_df.columns:
        tb_mask = manual_df["Type"].astype(str).str.strip().str.lower() == "turnback"
        tb_rows = manual_df[tb_mask]
        tb_with_coords = []
        for _, r in tb_rows.iterrows():
            lat = r.get("Latitude")
            lon = r.get("Longitude")
            if pd.notna(lat) and pd.notna(lon) and str(lat).strip() != "" and str(lon).strip() != "":
                try:
                    tb_with_coords.append((float(lat), float(lon), str(r.get("Location", "")).strip()))
                except (ValueError, TypeError):
                    continue

        if tb_with_coords:
            tb_group = folium.FeatureGroup("Police turn-back points")
            adv = res.get("advisory")
            for lat, lon, loc_name in tb_with_coords:
                adv_lines = []
                if adv is not None and not adv.empty:
                    for _, a in adv.iterrows():
                        dp = str(a.get("Diversion_Point", "")).strip().lower()
                        loc_lower = loc_name.lower()
                        if dp and (dp in loc_lower or loc_lower in dp):
                            adv_lines.append(
                                f"<b>Movement:</b> {a.get('Movement', '')}<br>"
                                f"<b>Divert at:</b> {a.get('Diversion_Point', '')}<br>"
                                f"<b>Diverted route:</b> {a.get('Diverted_Route', '')}"
                            )
                if adv_lines:
                    tip = f"<b>Turn-back: {loc_name}</b><br>" + "<hr style='margin:4px 0;'>".join(adv_lines)
                else:
                    tip = f"<b>Turn-back: {loc_name}</b><br><i>(No specific advisory recorded for this date)</i>"

                folium.Marker(
                    (lat, lon),
                    tooltip=folium.Tooltip(tip),
                    icon=folium.Icon(color="red", icon="ban", prefix="fa")
                ).add_to(tb_group)
            tb_group.add_to(m)

    pts = folium.FeatureGroup("Approaches and zones")
    for name, a in res["approaches"].items():
        folium.CircleMarker(a["latlon"], radius=7, color="#1f4e9c", fill=True, fill_opacity=.9,
                            tooltip=f"Approach: {name} ({a['share']*100:.0f}% of traffic)").add_to(pts)
    if show_zones:
        for p in res["parking"]:
            folium.CircleMarker(node_xy(D, p), radius=3, color="#555", fill=True,
                                tooltip="Assumed parking / drop-off zone").add_to(pts)
    folium.Marker(UPPAL_METRO_VERIFIED, tooltip="Uppal metro station (verified coordinates)",
                  icon=folium.Icon(color="green", icon="train", prefix="fa")).add_to(pts)
    folium.Marker(STADIUM, tooltip="Rajiv Gandhi International Cricket Stadium",
                  icon=folium.Icon(color="darkblue", icon="star", prefix="fa")).add_to(pts)
    pts.add_to(m)
    folium.LayerControl(collapsed=True).add_to(m)

    legend = """<div style="position:fixed;bottom:25px;left:25px;z-index:9999;background:white;padding:8px 12px;
    border:1px solid #888;border-radius:6px;font-size:12px;line-height:1.5">
    <b>V/C (load / capacity)</b><br>
    <span style="color:#2ca02c">&#9632;</span> under 0.8 OK<br>
    <span style="color:#ffbf00">&#9632;</span> 0.8 to 1.0 near capacity<br>
    <span style="color:#d62728">&#9632;</span> over 1.0 congested<br>
    <span style="color:#6a0dad">&#9473;&#9473;</span> emergency corridor<br>
    <span style="color:#1f77b4">&#9473;&#9473;</span> diversion<br>
    <span style="color:red">&#9679;</span> turn-back point<br>
    <i>Model estimate, not measured counts</i></div>"""
    m.get_root().html.add_child(folium.Element(legend))
    return m
