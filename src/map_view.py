"""Folium map for the demo: roads coloured by V/C, diversions, emergency corridor, zones with tactical tags."""
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
    venue_center = res.get("params", {}).get("venue_latlon") or STADIUM
    m = folium.Map(location=venue_center, zoom_start=14, tiles="OpenStreetMap", control_scale=True)
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

    # Tactical Hotspot Markers [H]
    hotspot_group = folium.FeatureGroup("Hotspot checkpoints [H]")
    tagged_hs = res.get("tagged_hotspots", [])
    for h in tagged_hs[:6]:
        u, v = int(h["u"]), int(h["v"])
        mid_lat, mid_lon = node_xy(D, v)
        h_tip = (
            f"<b>[{h['tag']}] Hotspot: {h['street']}</b><br>"
            f"V/C: <b>{h['vc']:.2f}</b> | Load: {h['load_pcu_hr']:,.0f} PCU/h<br>"
            f"Capacity: {h['capacity_pcu_hr']:,.0f} PCU/h ({h['lanes']} lanes)<br>"
            f"Traffic stream: {h['fed_by']}"
        )
        icon_color = "red" if h["vc"] > 1.0 else "orange"
        folium.Marker(
            (mid_lat, mid_lon),
            tooltip=folium.Tooltip(h_tip),
            icon=folium.Icon(color=icon_color, icon="exclamation-triangle", prefix="fa")
        ).add_to(hotspot_group)
    hotspot_group.add_to(m)

    # Emergency Corridor [E-1]
    if res.get("corridor"):
        c = res["corridor"]
        em = folium.FeatureGroup("Emergency corridor [E-1]")
        for u, v in c["edges"]:
            folium.PolyLine(_coords(D, u, v), color="#6a0dad", weight=6, opacity=.9, dash_array="10 8",
                            tooltip="Protected emergency corridor [E-1]").add_to(em)
        em.add_to(m)
        la, lo = node_xy(D, c["path"][0])
        hosp_tip = f"<b>[E-1] Hospital Gate</b><br>Protected ETA: {c.get('free_min', 0)} min (Congested ETA: {c.get('unprotected_min', 0)} min)"
        folium.Marker((la, lo), tooltip=hosp_tip,
                      icon=folium.Icon(color="purple", icon="plus", prefix="fa")).add_to(m)

    # Recommended Diversions [D]
    dv = folium.FeatureGroup("Recommended diversions [D]")
    for idx, d in enumerate(res.get("diversions", [])):
        d_tag = d.get("tag", f"D-{idx+1}")
        if d.get("feasible") and d.get("path"):
            pts = [node_xy(D, n) for n in d["path"]]
            d_tip = f"<b>[{d_tag}] Diversion for {d['name']}</b><br>Detour penalty: +{d['extra_m']:,} m, +{d['extra_s']} s"
            folium.PolyLine(pts, color="#1f77b4", weight=5, dash_array="4 6",
                            tooltip=d_tip).add_to(dv)
            folium.Marker(pts[0], tooltip=f"[{d_tag}] Diversion Entry: {d['name']}",
                          icon=folium.Icon(color="blue", icon="share", prefix="fa")).add_to(dv)
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

    # Approaches [J] and Parking [P]
    pts = folium.FeatureGroup("Approaches [J] and zones [P]")
    tagged_juncs = res.get("tagged_junctions", [])
    if tagged_juncs:
        for j in tagged_juncs:
            folium.Marker(
                j["latlon"],
                tooltip=f"<b>[{j['tag']}] Checkpoint: {j['name']}</b><br>Approach share: {j['share']*100:.0f}%",
                icon=folium.Icon(color="darkblue", icon="shield", prefix="fa")
            ).add_to(pts)
    else:
        for name, a in res["approaches"].items():
            folium.CircleMarker(a["latlon"], radius=7, color="#1f4e9c", fill=True, fill_opacity=.9,
                                tooltip=f"Approach: {name} ({a['share']*100:.0f}% of traffic)").add_to(pts)

    if show_zones:
        tagged_p = res.get("tagged_parking", [])
        if tagged_p:
            for p in tagged_p:
                folium.Marker(
                    p["xy"],
                    tooltip=f"<b>[{p['tag']}] Parking / Holding Zone</b>",
                    icon=folium.Icon(color="cadetblue", icon="car", prefix="fa")
                ).add_to(pts)
        else:
            for p in res["parking"]:
                folium.CircleMarker(node_xy(D, p), radius=3, color="#555", fill=True,
                                    tooltip="Assumed parking / drop-off zone").add_to(pts)

    # Venue Marker
    venue_name = res.get("params", {}).get("event_name", "Event Venue")
    folium.Marker(venue_center, tooltip=f"<b>Venue: {venue_name}</b>",
                  icon=folium.Icon(color="darkblue", icon="star", prefix="fa")).add_to(pts)

    if venue_center == STADIUM:
        folium.Marker(UPPAL_METRO_VERIFIED, tooltip="Uppal metro station (verified coordinates)",
                      icon=folium.Icon(color="green", icon="train", prefix="fa")).add_to(pts)

    pts.add_to(m)
    folium.LayerControl(collapsed=True).add_to(m)

    legend = """<div style="position:fixed;bottom:25px;left:25px;z-index:9999;background:white;padding:8px 12px;
    border:1px solid #888;border-radius:6px;font-size:12px;line-height:1.5">
    <b>Tactical Map Tags</b><br>
    <span style="color:#003366">&#9632;</span> <b>[J]</b> Checkpoint Junctions<br>
    <span style="color:#d62728">&#9632;</span> <b>[H]</b> Hotspots (V/C &gt; 1.0)<br>
    <span style="color:#1f77b4">&#9632;</span> <b>[D]</b> Diversions &amp; Detours<br>
    <span style="color:#6a0dad">&#9473;&#9473;</span> <b>[E]</b> Emergency Corridor<br>
    <span style="color:#5f9ea0">&#9632;</span> <b>[P]</b> Parking Clusters<br>
    <span style="color:red">&#9679;</span> Turn-back points<br>
    <i>Model estimate, not measured counts</i></div>"""
    m.get_root().html.add_child(folium.Element(legend))
    return m
