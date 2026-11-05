"""
Traffic Event Co-Pilot: SIPOC demo for Uppal Stadium, Hyderabad.
Run:  streamlit run app.py
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))
import event_engine as E  # noqa: E402
from map_view import make_map  # noqa: E402

st.set_page_config(page_title="Traffic Event Co-Pilot", page_icon="🚦", layout="wide")


@st.cache_resource(show_spinner="Loading Uppal road network...")
def get_network():
    return E.build_network()


@st.cache_data(show_spinner=False)
def get_pack():
    return E.load_pack()


try:
    D, NET = get_network()
except Exception as exc:  # readable error, no stack trace for the mentor
    st.error(f"Could not load the road network ({exc}). Check that data/uppal_road_network.graphml exists.")
    st.stop()
PACK = get_pack()
EVENTS = E.event_options(PACK)

# ------------------------------------------------------------------ sidebar
st.sidebar.title("🚦 Event setup")
labels = [e["label"] for e in EVENTS] + ["Custom event"]
choice = st.sidebar.selectbox("Event (from police advisories)", labels, index=min(5, len(labels) - 1))
ev = next((e for e in EVENTS if e["label"] == choice), None)
attendance = st.sidebar.number_input("Attendance (ASSUMED: stadium holds about 39,000)", 1000, 80000, 39000, 1000)
start_time = st.sidebar.text_input("Start time (HH:MM)", ev["start"] if ev else "19:30")
if ev and not ev["start_known"]:
    st.sidebar.caption("Start time was not confirmed in the sources, so 19:30 is an assumption.")
phase = st.sidebar.radio("Phase", ["ingress", "egress"], horizontal=True,
                         help="ingress = people arriving before the event, egress = leaving after it")
private = st.sidebar.slider("Share arriving by own/hired vehicle (%)", 20, 90, 60)
shift = st.sidebar.slider("What-if: move this % of 2-wheeler and car riders to metro", 0, 40, 0)
with st.sidebar.expander("Approach shares (ASSUMED)"):
    shares = {k: st.slider(k, 0, 50, int(v * 100)) for k, v in E.DEFAULT_APPROACH_SHARE.items()}
run = st.sidebar.button("▶ Run Co-Pilot", type="primary")

if run or "res" not in st.session_state:
    with st.spinner("Estimating demand, loading roads, finding hotspots..."):
        st.session_state["res"] = E.run_scenario(D, {
            "attendance": int(attendance), "start_time": start_time, "phase": phase,
            "mode_share": E.mode_share_with_private_total(private / 100),
            "approach_share": {k: v / 100 for k, v in shares.items()}, "shift_pct": float(shift),
            "event_date": ev["date"] if ev else None, "event_name": ev["name"] if ev else "Custom event"}, PACK)
res = st.session_state["res"]
dem, so, sn = res["demand"], res["sum_opt"], res["sum_naive"]

st.title("Traffic Event Co-Pilot")
st.caption("Uppal (Rajiv Gandhi International Cricket) Stadium, Hyderabad. Plans traffic for an event "
           "before it happens. Demo flow follows SIPOC: Suppliers, Inputs, Process, Outputs, Customers.")

t1, t2, t3, t4, t5 = st.tabs(["1 · SIPOC overview", "2 · Suppliers → Inputs", "3 · Process",
                              "4 · Outputs", "5 · Customers"])

# ------------------------------------------------------------------ 1. SIPOC
with t1:
    st.subheader("SIPOC of the Traffic Event Co-Pilot")
    sipoc = pd.DataFrame({
        "S: Suppliers": ["OpenStreetMap (road network)", "Traffic police advisories (Rachakonda / Malkajgiri)",
                         "HMRL metro and TGSRTC bus provisions", "News and event schedules (dates, start times)",
                         "Event organiser (attendance): not yet connected", "RTA vehicle data (fleet mix): planned"],
        "I: Inputs": ["Event name, date, start time, attendance", "3 km road graph around the stadium",
                      "Mode split and occupancy (assumed)", "Diversion points and time windows",
                      "Metro and bus support on match days", "Approach shares (where traffic comes from)"],
        "P: Process": ["1 Collect and clean data", "2 Build road graph, estimate capacity", "3 Snap locations to roads",
                       "4 Demand per mode in PCU, 15-min peak", "5 Load roads: naive vs optimised, V/C and delay",
                       "6 Hotspots, diversions, emergency corridor, plan text"],
        "O: Outputs": ["Congestion hotspots with V/C", "Colour-coded congestion map",
                       "Diversion routes with extra distance", "Protected emergency corridor and ETA",
                       "What-if comparison", "Event traffic plan (downloadable)"],
        "C: Customers": ["Traffic police planners", "Event organiser", "Emergency services (ambulance, fire)",
                         "Commuters and attendees", "Metro and bus operators", "Project mentor / evaluator"],
    })
    st.dataframe(sipoc, hide_index=True)
    c1, c2, c3 = st.columns(3)
    c1.success("**Real data used**\n\nOSM road network\n\nPolice advisories and diversions\n\nEvent dates, metro and bus provisions")
    c2.warning("**Assumed (labelled in the app)**\n\nMode split, occupancy, PCU factors\n\nRoad capacity and speeds\n\n"
               "Approach shares, background traffic, parking zones")
    c3.error("**Missing (needs police data)**\n\nClassified vehicle counts on event days\n\nSpeeds and queue lengths\n\n"
             "Real hospital and parking coordinates")

# ------------------------------------------------------------------ 2. Suppliers -> Inputs
with t2:
    st.subheader("Suppliers → Inputs")
    a, b = st.columns(2)
    with a:
        st.markdown("**Event selected**")
        st.write({"Event": res["params"]["event_name"], "Date": str(res["params"]["event_date"] or "custom"),
                  "Start": res["params"]["start_time"], "Phase": res["params"]["phase"],
                  "Attendance": f"{res['params']['attendance']:,}"})
        if ev:
            st.caption(f"Source: {ev['source']}")
        st.markdown("**Data pack (Excel)**")
        st.write({k: f"{len(v)} rows" for k, v in PACK.items()} if PACK else "Data pack not found")
    with b:
        st.markdown("**Road network quality**")
        st.write({"Routable junctions": NET["nodes"], "Road segments": NET["edges"],
                  "Lanes missing in OSM (defaulted)": f"{NET['pct_lanes_defaulted']}%",
                  "Speeds missing in OSM (defaulted)": f"{NET['pct_speed_defaulted']}%",
                  "Real event-day vehicle counts": "0 (not public)"})
        st.caption("Almost all roads have no lane or speed tag in OSM, so capacities are estimates. "
                   "This is why we show model estimates, not measurements.")
    st.markdown("**Police advisory diversions for this date**")
    adv = res["advisory"]
    if adv is not None and not adv.empty:
        st.dataframe(adv[["Movement", "Vehicle_Class", "Diversion_Point", "Diverted_Route", "Window_Start", "Window_End"]]
                     .drop_duplicates(), hide_index=True)
    else:
        st.info("No advisory rows for this date in the data pack.")
    st.markdown("**Mode split used (share of people)**")
    ms = pd.DataFrame({"mode": list(dem["mode_share"]), "share_%": [round(v * 100, 1) for v in dem["mode_share"].values()]})
    st.bar_chart(ms.set_index("mode"))

# ------------------------------------------------------------------ 3. Process
with t3:
    st.subheader("Process: what the Co-Pilot does, step by step")
    st.markdown("**Step 1-2. Data and road graph**")
    st.write(f"{NET['nodes']:,} junctions, {NET['edges']:,} road segments, road types: {NET['road_types']}")
    st.markdown("**Step 3. Locations snapped to road junctions (approach entry points)**")
    rows = [{"Approach": n, "Share of traffic": f"{a['share']*100:.0f}%", "Entry junctions": len(a["nodes"]),
             "Lat/Lon": f"{a['latlon'][0]:.4f}, {a['latlon'][1]:.4f}"} for n, a in res["approaches"].items()]
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.caption("Uppal metro station uses verified coordinates because the geocoder result was about 1 km off.")
    st.markdown("**Step 4. Demand per mode (people → vehicles → PCU)**")
    dtab = pd.DataFrame({"mode": list(E.MODES),
                         "people": [round(dem["persons"][m]) for m in E.MODES],
                         "vehicles": [dem["vehicles"].get(m, 0) for m in E.MODES],
                         "PCU": [round(dem["pcu"].get(m, 0)) for m in E.MODES]})
    st.dataframe(dtab, hide_index=True)
    st.write(f"Total {dem['total_vehicles']:,} vehicles = {dem['total_pcu']:,.0f} PCU. Busiest 15 minutes start at "
             f"**{dem['peak_bucket']}**: {dem['peak_15min_pcu']:,.0f} PCU = {dem['peak_hourly_pcu']:,.0f} PCU/hour.")
    st.line_chart(dem["curve"].set_index("Time")["PCU"])
    st.markdown("**Step 5. Load the roads: naive vs optimised**")
    st.write("Naive = everyone takes the shortest empty-road path (what a plain route finder does). "
             "Optimised = repeated re-routing as roads fill up (method of successive averages).")
    st.line_chart(pd.DataFrame({"max V/C": res["history"]}, index=[f"iter {i}" for i in range(len(res["history"]))]))
    st.markdown("**Step 6-7. Hotspots, diversions, emergency corridor** are shown in the Outputs tab.")

# ------------------------------------------------------------------ 4. Outputs
with t4:
    st.subheader("Outputs")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Vehicles", f"{dem['total_vehicles']:,}")
    m2.metric("Peak PCU / hour", f"{dem['peak_hourly_pcu']:,.0f}")
    m3.metric("Max V/C (Co-Pilot)", f"{so['max_vc']:.2f}", f"{so['max_vc'] - sn['max_vc']:+.2f} vs naive", delta_color="inverse")
    m4.metric("Roads over capacity", so["congested"], f"{so['congested'] - sn['congested']:+d} vs naive", delta_color="inverse")
    view = st.radio("Map shows", ["Co-Pilot (optimised)", "Naive shortest path"], horizontal=True)
    try:
        from streamlit_folium import st_folium
        st_folium(make_map(D, res, use_naive=view.startswith("Naive")), height=560, width=1200,
                  returned_objects=[])
    except Exception as exc:
        st.warning(f"Map could not be drawn: {exc}")
    st.markdown("**Congestion hotspots (streets)**")
    hs = res["hotspots"]
    if len(hs):
        st.dataframe(hs[["street", "road_type", "lanes", "segments", "load_pcu_hr", "capacity_pcu_hr", "vc", "fed_by"]]
                     .rename(columns={"vc": "V/C"}).head(10), hide_index=True)
    st.markdown("**Recommended diversions for the worst hotspots**")
    dv = pd.DataFrame([{"Hotspot": d["name"], "V/C": d["vc"], "Feasible": d["feasible"],
                        "Extra metres": d.get("extra_m"), "Extra seconds": d.get("extra_s"), "Note": d["note"]}
                       for d in res["diversions"]])
    if len(dv):
        st.dataframe(dv, hide_index=True)
    c = res["corridor"]
    if c:
        st.info(f"Protected emergency corridor: {c['length_m']:,} m. ETA {c['free_min']} min if kept clear, "
                f"about {c['unprotected_min']} min if open to event traffic. Hospital point is a placeholder.")
    st.markdown("**What-if: shifting riders to metro**")
    if st.button("Run what-if comparison (0, 10, 20, 30%)"):
        rows = []
        for sh in (0, 10, 20, 30):
            r2 = E.run_scenario(D, {**res["params"], "shift_pct": float(sh)}, PACK)
            rows.append({"Shift to metro %": sh, "Vehicles": r2["demand"]["total_vehicles"],
                         "Peak PCU/h": round(r2["demand"]["peak_hourly_pcu"]), "Max V/C": r2["sum_opt"]["max_vc"],
                         "Roads over capacity": r2["sum_opt"]["congested"]})
        st.dataframe(pd.DataFrame(rows), hide_index=True)

# ------------------------------------------------------------------ 5. Customers
with t5:
    st.subheader("Customers: who gets what")
    top = hs.head(3)["street"].tolist() if len(hs) else []
    cols = st.columns(2)
    with cols[0]:
        st.markdown("##### Traffic police planners")
        st.write("Full plan with hotspots, diversions and emergency corridor (below, downloadable).")
        st.markdown("##### Event organiser")
        st.write(f"Plan for about {dem['buses']} event buses and {dem['metro_riders']:,.0f} metro riders. "
                 f"{dem['pedestrians']:,.0f} people arrive on foot, so gate queues and metro exits need crowd control.")
    with cols[1]:
        st.markdown("##### Emergency services")
        c = res["corridor"]
        st.write(f"Keep the purple corridor clear ({c['length_m']:,} m, {c['free_min']} min)." if c else "No corridor computed.")
        st.markdown("##### Commuters (draft public message)")
        msg = (f"Heavy traffic expected around Uppal from midday. Avoid {', '.join(top) if top else 'the stadium roads'}. "
               "Use Metro (Blue Line: Stadium, Uppal or NGRI stations) or TGSRTC special buses.")
        st.code(msg, language=None)
    st.markdown("---")
    st.markdown(res["report"])
    d1, d2 = st.columns(2)
    d1.download_button("Download plan (Markdown)", res["report"], "event_traffic_plan.md")
    d2.download_button("Download hotspots (CSV)", res["table_opt"].to_csv(index=False), "hotspots.csv")
