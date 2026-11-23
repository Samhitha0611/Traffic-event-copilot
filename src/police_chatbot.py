"""
Police Copilot Chatbot Engine.
Provides grounded, accurate tactical explanations of generated event traffic plans.
Answers police queries regarding bottlenecks, diversions, emergency corridors, and deployment.
Supports bilingual output: English and Telugu (తెలుగు).
"""
from __future__ import annotations

import os
import re
from typing import Any
import pandas as pd


def generate_police_response(query: str, res: dict[str, Any] | None, lang: str = "English") -> str:
    """
    Generate a factual, grounded response to a police officer's question based on the active traffic scenario.
    Labels all planning parameters and deployment heuristics as ASSUMED.
    Supports English and Telugu (తెలుగు).
    """
    is_te = (str(lang).strip() == "తెలుగు") or bool(re.search(r'[\u0C00-\u0C7F]', str(query)))

    if not res:
        if is_te:
            return (
                "యాక్టివ్ ట్రాఫిక్ దృశ్యం కనుగొనబడలేదు. దయచేసి సైడ్‌బార్‌లో ఈవెంట్ వివరాలను ఎంచుకుని "
                "'▶ Run Co-Pilot' బటన్ క్లిక్ చేసి ప్రణాళికను రూపొందించండి."
            )
        return (
            "No active scenario found. Please run a traffic scenario first by selecting an event or "
            "entering event parameters in the sidebar and clicking '▶ Run Co-Pilot'."
        )

    q = str(query).strip().lower()
    params = res.get("params", {})
    demand = res.get("demand", {})
    hotspots = res.get("hotspots", pd.DataFrame())
    diversions = res.get("diversions", [])
    corridor = res.get("corridor")
    approaches = res.get("approaches", {})
    so = res.get("sum_opt", {})
    sn = res.get("sum_naive", {})

    event_name = params.get("event_name", "Event")
    attendance = params.get("attendance", 0)
    phase = params.get("phase", "ingress")
    start_time = params.get("start_time", "19:30")
    phase_str = "రాక (Ingress)" if phase == "ingress" else "నిష్క్రమణ (Egress)"

    # 1. Bottlenecks / Hotspots / Congestion
    if any(w in q for w in ["hotspot", "bottleneck", "congest", "traffic jam", "red road", "v/c", "over capacity", "worst", "h-", "రద్దీ", "జామ్", "హాట్‌స్పాట్", "బాటిల్"]):
        if is_te:
            lines = [f"### 🚨 {event_name} కోసం ట్రాఫిక్ రద్దీ హాట్‌స్పాట్లు"]
            lines.append(
                f"ఆప్టిమైజ్డ్ అసైన్‌మెంట్ మోడల్ ప్రకారం, **{so.get('congested', 0)} రోడ్డు విభాగాలు** సామర్థ్యానికి మించి (V/C > 1.0) నడుస్తున్నాయి. "
                f"**{so.get('near', 0)} విభాగాలు** రద్దీ సమీపంలో (V/C 0.8–1.0) ఉన్నాయి. గరిష్ట V/C నిష్పత్తి **{so.get('max_vc', 0):.2f}**."
            )
            if not hotspots.empty:
                lines.append("\n**అత్యంత తీవ్ర రద్దీ కేంద్రాలు (Top Hotspots):**")
                for idx, r in hotspots.head(5).iterrows():
                    tag = f"[H-{idx+1}]"
                    st_name = r.get("street", "Unnamed road")
                    vc = r.get("vc", 0.0)
                    load = r.get("load_pcu_hr", 0.0)
                    cap = r.get("capacity_pcu_hr", 0.0)
                    fed = r.get("fed_by", "అన్ని మార్గాలు")
                    lines.append(f"- **{tag} {st_name}**: V/C నిష్పత్తి **{vc:.2f}** ({load:,.0f} PCU/గం ట్రాఫిక్ లోడ్ vs {cap:,.0f} సామర్థ్యం). ఫీడ్ మార్గం: *{fed}*.")
                lines.append(
                    "\n*పోలీసు కార్యాచరణ ఆదేశం:* ఈ కూడళ్ల వద్ద ఈవెంట్ ప్రారంభానికి 90 నిమిషాల ముందే ట్రాఫిక్ కానిస్టేబుళ్లను మోహరించాలి (*అనుకోబడిన పీక్ సమయం / ASSUMED*). "
                    "రోడ్డు పక్కన అక్రమ పార్కింగ్ మరియు ఆకస్మిక డ్రాప్-ఆఫ్‌లను నివారించాలి."
                )
            return "\n".join(lines)

        lines = [f"### 🚨 Congestion Hotspots for {event_name}"]
        lines.append(
            f"Under the spread-out assignment model, **{so.get('congested', 0)} road segment(s)** operate over capacity (V/C > 1.0), "
            f"and **{so.get('near', 0)} segment(s)** are near capacity (V/C 0.8–1.0). Peak V/C reaches **{so.get('max_vc', 0):.2f}**."
        )
        if not hotspots.empty:
            lines.append("\n**Top Critical Bottlenecks:**")
            for idx, r in hotspots.head(5).iterrows():
                tag = f"[H-{idx+1}]"
                st_name = r.get("street", "Unnamed road")
                vc = r.get("vc", 0.0)
                load = r.get("load_pcu_hr", 0.0)
                cap = r.get("capacity_pcu_hr", 0.0)
                fed = r.get("fed_by", "all approaches")
                lines.append(f"- **{tag} {st_name}**: V/C **{vc:.2f}** ({load:,.0f} PCU/h vs {cap:,.0f} capacity). Fed by traffic from: *{fed}*.")
            lines.append(
                "\n*Tactical Recommendation:* Deploy traffic marshals at these bottleneck intersections 90 minutes before "
                "event start (*ASSUMED peak ingress window*). Prevent curb parking and lane-blocking drop-offs."
            )
        return "\n".join(lines)

    # 2. Emergency / Ambulance / Green Corridor
    if any(w in q for w in ["emergency", "ambulance", "corridor", "hospital", "green channel", "green corridor", "e-", "trauma", "అత్యవసర", "అంబులెన్స్", "ఆసుపత్రి", "గ్రీన్ కారిడార్"]):
        if not corridor:
            if is_te:
                return "ఈ రోడ్డు నెట్‌వర్క్‌లో వేదిక మరియు ఆసుపత్రి మధ్య అత్యవసర గ్రీన్ కారిడార్ మార్గం లెక్కించబడలేదు."
            return "No emergency corridor path could be computed between the venue and destination hospital on this network."
        hosp_note = (
            "ఆసుపత్రి లొకేషన్ ప్లేస్‌హోల్డర్ (అనుకోబడినది / ASSUMED)"
            if res.get("hospital_is_placeholder", True)
            else "ఆసుపత్రి లొకేషన్ వెరిఫై చేయబడింది"
        ) if is_te else (
            "Hospital location is currently a placeholder (ASSUMED)"
            if res.get("hospital_is_placeholder", True)
            else "Hospital location verified from manual/catalog records"
        )
        if is_te:
            lines = [
                f"### 🚑 రక్షిత అత్యవసర గ్రీన్ కారిడార్ (`[E-1]`)",
                f"- **నిర్దేశిత మార్గం పొడవు:** {corridor.get('length_m', 0):,} మీటర్లు.",
                f"- **క్లియర్ లేన్ ప్రయాణ సమయం (ETA):** **{corridor.get('free_min', 0)} నిమిషాలు** (ఈవెంట్ ట్రాఫిక్ లేకుండా క్లియర్‌గా ఉంచినప్పుడు).",
                f"- **రద్దీ సమయం (అన్‌ప్రొటెక్టెడ్):** **{corridor.get('unprotected_min', 0)} నిమిషాలు** (సాధారణ ట్రాఫిక్‌తో కలిసినప్పుడు).",
                f"- **గ్రీన్ కారిడార్ ద్వారా ఆదా అయ్యే సమయం:** **{max(0, corridor.get('unprotected_min', 0) - corridor.get('free_min', 0)):.1f} నిమిషాలు**.",
                f"- **పరిస్థితి:** {hosp_note}.",
                "\n*పోలీస్ ఎస్‌ఓపీ (SOP):* ఈ కారిడార్‌లోని ప్రతి కూడలి వద్ద ఒక మొబైల్ పెట్రోలింగ్ బైక్‌ను ఉంచాలి. "
                "ఏ పరిస్థితుల్లోనూ ప్రేక్షకుల వాహనాల పార్కింగ్ లేదా డ్రాపింగ్ ఈ లేన్‌లోకి రాకుండా నిరోధించాలి."
            ]
            return "\n".join(lines)

        lines = [
            f"### 🚑 Protected Emergency Green Corridor (`[E-1]`)",
            f"- **Designated Route Length:** {corridor.get('length_m', 0):,} metres.",
            f"- **Free-flow ETA (Protected):** **{corridor.get('free_min', 0)} minutes** when kept strictly clear of event traffic.",
            f"- **Unprotected ETA (Event Congestion):** **{corridor.get('unprotected_min', 0)} minutes** if general spectator traffic mixes in.",
            f"- **Time Saved by Green Corridor Enforcement:** **{max(0, corridor.get('unprotected_min', 0) - corridor.get('free_min', 0)):.1f} minutes**.",
            f"- **Status:** {hosp_note}.",
            "\n*SOP for Police:* Station one stationary interceptor bike at each intersection along this corridor. "
            "Under no circumstances should spectator parking or spectator queuing encroach onto this designated lane."
        ]
        return "\n".join(lines)

    # 3. Diversions / Closures / Turn-backs / Barricades
    if any(w in q for w in ["diversion", "divert", "turnback", "turn-back", "barricade", "closure", "detour", "alternate route", "d-", "మళ్లింపు", "డైవర్షన్", "దారి", "బారికేడ్"]):
        if is_te:
            lines = [f"### 🔀 {event_name} ట్రాఫిక్ మళ్లింపు వ్యూహం (Diversions)"]
            if diversions:
                lines.append("ప్రధాన రద్దీని తగ్గించడానికి లెక్కించబడిన మళ్లింపు మార్గాలు:\n")
                for idx, d in enumerate(diversions[:6]):
                    tag = f"[D-{idx+1}]"
                    name = d.get("name", "Hotspot")
                    vc = d.get("vc", 0.0)
                    if d.get("feasible"):
                        extra_m = d.get("extra_m", 0)
                        extra_s = d.get("extra_s", 0)
                        lines.append(
                            f"- **{tag} {name} (V/C {vc:.2f})**: ప్రత్యామ్నాయ దారి సాధ్యం. "
                            f"అదనంగా **+{extra_m:,} మీటర్లు** మరియు **+{extra_s} సెకన్ల** సమయం పడుతుంది. ప్రైవేట్ వాహనాలను ఇక్కడికి మళ్లించాలి."
                        )
                    else:
                        note = d.get("note", "ప్రత్యామ్నాయం లేదు")
                        lines.append(
                            f"- **{tag} {name} (V/C {vc:.2f})**: **సురక్షిత ప్రత్యామ్నాయ దారి లేదు** ({note}). "
                            f"యూ-టర్న్ లేదా హోల్డ్-అండ్-రిలీజ్ విధానాన్ని అమలు చేయాలి."
                        )
            adv = res.get("advisory")
            if adv is not None and not adv.empty:
                lines.append("\n**పోలీసు సలహా మళ్లింపులు:**")
                for _, a in adv.drop_duplicates(["Movement", "Diversion_Point"]).head(4).iterrows():
                    lines.append(f"- *{a.get('Movement')}*: **{a.get('Diversion_Point')}** వద్ద **{a.get('Diverted_Route')}** మీదుగా మళ్లించాలి.")
            lines.append("\n*బారికేడింగ్ సూచన:* ప్రతి డైవర్షన్ పాయింట్ వద్ద ఎల్‌ఈడీ బాణం సూచికలతో కూడిన భౌతిక బారికేడ్లను అమర్చాలి.")
            return "\n".join(lines)

        lines = [f"### 🔀 Tactical Diversion Scheme for {event_name}"]
        if diversions:
            lines.append("Here are the recommended route diversions calculated to relieve key bottlenecks:\n")
            for idx, d in enumerate(diversions[:6]):
                tag = f"[D-{idx+1}]"
                name = d.get("name", "Hotspot")
                vc = d.get("vc", 0.0)
                if d.get("feasible"):
                    extra_m = d.get("extra_m", 0)
                    extra_s = d.get("extra_s", 0)
                    lines.append(
                        f"- **{tag} {name} (V/C {vc:.2f})**: Alternate detour feasible. "
                        f"Adds **+{extra_m:,} m** and **+{extra_s} seconds** detour penalty. Divert general private traffic here."
                    )
                else:
                    note = d.get("note", "No alternate bypass")
                    lines.append(
                        f"- **{tag} {name} (V/C {vc:.2f})**: **No safe alternate diversion available** ({note}). "
                        f"Implement strict turn-back enforcement or hold-and-release staging."
                    )
        adv = res.get("advisory")
        if adv is not None and not adv.empty:
            lines.append("\n**Published Police Advisory Diversions:**")
            for _, a in adv.drop_duplicates(["Movement", "Diversion_Point"]).head(4).iterrows():
                lines.append(f"- *{a.get('Movement')}*: Divert at **{a.get('Diversion_Point')}** via **{a.get('Diverted_Route')}**.")
        lines.append("\n*Barricade Guidance:* Place physical barricades with LED directional arrow boards at each diversion point.")
        return "\n".join(lines)

    # 4. Deployment / Police Personnel / Manpower
    if any(w in q for w in ["personnel", "officer", "manpower", "deployment", "duty", "staff", "police", "సిబ్బంది", "పోలీసులు", "మోహరింపు", "బందోబస్తు", "ఆఫీసర్"]):
        tot_veh = demand.get("total_vehicles", 0)
        num_hotspots = len(hotspots)
        # ASSUMED planning ratio for traffic police staffing
        traffic_si = max(2, round(num_hotspots * 0.8))                # ASSUMED SI per major sector
        traffic_constables = max(10, round(tot_veh / 800) + num_hotspots * 4)  # ASSUMED constable ratio
        marshals = max(6, round(demand.get("pedestrians", 0) / 2500)) # ASSUMED crowd control ratio

        if is_te:
            lines = [
                f"### 👮 పోలీసు సిబ్బంది మోహరింపు అంచనా (అనుకోబడినది / ASSUMED)",
                f"అంచనా హాజరు **{attendance:,}** ({tot_veh:,} వాహనాలు, గరిష్ట రద్దీ {demand.get('peak_hourly_pcu', 0):,.0f} PCU/గం):",
                f"- **సెక్టార్ అధికారులు (ఎస్సైలు/ఇన్‌స్పెక్టర్లు):** ~{traffic_si} మంది అధికారులు (కీలక కారిడార్ సెక్టార్ల పర్యవేక్షణ).",
                f"- **ట్రాఫిక్ కానిస్టేబుళ్లు & హోమ్‌గార్డులు:** ~{traffic_constables} మంది సిబ్బంది (కూడళ్లు, బారికేడ్లు మరియు యూ-టర్న్ క్లోజర్ల వద్ద).",
                f"- **పాదచారుల క్రౌడ్ మార్షల్స్:** ~{marshals} మంది సిబ్బంది (మెట్రో ఎగ్జిట్‌లు, బస్సు స్టాప్‌లు మరియు ఎంట్రీ గేట్ల వద్ద).",
                "\n*కీలక డ్యూటీ పాయింట్లు:*",
                "- చెక్‌పాయింట్ ఎంట్రీ కూడళ్లు [J-1] నుండి [J-4]: ప్రతి కూడలికి 2 కానిస్టేబుళ్లు.",
                "- డైవర్షన్ పాయింట్లు [D-1] నుండి [D-3]: ప్రతి పాయింట్‌కు 2 కానిస్టేబుళ్లు + 1 పెట్రోలింగ్ బైక్.",
                "- ఎమర్జెన్సీ గ్రీన్ కారిడార్ [E-1]: ప్రత్యేక ఎస్కార్ట్ మోటార్‌సైకిల్ నిరంతర నిఘా."
            ]
            return "\n".join(lines)

        lines = [
            f"### 👮 Tactical Police Deployment Estimate (ASSUMED Heuristic)",
            f"For an expected attendance of **{attendance:,}** ({tot_veh:,} vehicles, peak {demand.get('peak_hourly_pcu', 0):,.0f} PCU/h):",
            f"- **Sector Officers (Sub-Inspectors/Inspectors):** ~{traffic_si} officers (assigned to major corridor sectors).",
            f"- **Traffic Constables & Home Guards:** ~{traffic_constables} personnel for intersection duty, diversion barricades, and U-turn closures.",
            f"- **Crowd & Pedestrian Marshals:** ~{marshals} personnel stationed at metro exits, bus drop-offs, and venue approach gates.",
            "\n*Key Duty Posts:*",
            "- Checkpoint [J-1] to [J-4] entry approaches: 2 constables each.",
            "- Diversion points [D-1] to [D-3]: 2 constables + 1 patrol bike each.",
            "- Emergency corridor [E-1]: Dedicated roving motorcycle escort."
        ]
        return "\n".join(lines)

    # 5. Parking / Transit / Metro / Buses
    if any(w in q for w in ["park", "bus", "metro", "transit", "walk", "crowd", "p-", "drop", "పార్కింగ్", "బస్సు", "మెట్రో", "నడక"]):
        p_note = (
            "పార్కింగ్ లొకేషన్లు అల్గారిథమిక్‌గా రూపొందించబడ్డాయి (అనుకోబడినవి / ASSUMED)"
            if res.get("parking_is_generated", True)
            else "పార్కింగ్ జోన్లు రికార్డుల నుండి వెరిఫై చేయబడ్డాయి"
        ) if is_te else (
            "Parking locations are algorithmically generated near the venue (ASSUMED)"
            if res.get("parking_is_generated", True)
            else "Parking zones verified from records"
        )
        if is_te:
            lines = [
                f"### 🅿️ {event_name} పార్కింగ్ మరియు ప్రజా రవాణా నిర్వహణ",
                f"- **ప్రయాణ సాధనాల విభజన (ASSUMED):** ప్రైవేట్ కార్లు {demand.get('mode_share', {}).get('car', 0.25)*100:.0f}%, "
                f"ద్విచక్ర వాహనాలు {demand.get('mode_share', {}).get('two_wheeler', 0.25)*100:.0f}%.",
                f"- **వాహనాల పరిమాణం:** {demand.get('vehicles', {}).get('car', 0):,} కార్లు, {demand.get('vehicles', {}).get('two_wheeler', 0):,} ద్విచక్ర వాహనాలు, "
                f"{demand.get('vehicles', {}).get('bus', 0):,} బస్సులు.",
                f"- **ప్రజా రవాణా & పాదచారులు:** **{demand.get('metro_riders', 0):,.0f}** మెట్రో ప్రయాణికులు, **{demand.get('pedestrians', 0):,.0f}** పాదచారులు.",
                f"- **పార్కింగ్ పరిస్థితి:** {p_note}.",
                "\n*పోలీస్ మార్గదర్శకం:* ప్రైవేట్ వాహనాలను ముందుగానే నిర్దేశిత పార్కింగ్ కేంద్రాలు `[P-1]` నుండి `[P-4]` వైపు మళ్లించండి. "
                "రద్దీ వేళల్లో ప్రతి 5 నిమిషాలకు మెట్రో ఫ్రీక్వెన్సీ ఉండేలా HMRL తో సమన్వయం చేసుకోండి."
            ]
            return "\n".join(lines)

        lines = [
            f"### 🅿️ Parking & Transit Management for {event_name}",
            f"- **Mode Share (ASSUMED):** Private vehicles {demand.get('mode_share', {}).get('car', 0.25)*100:.0f}% cars, "
            f"{demand.get('mode_share', {}).get('two_wheeler', 0.25)*100:.0f}% 2-wheelers.",
            f"- **Vehicle Volume:** {demand.get('vehicles', {}).get('car', 0):,} cars, {demand.get('vehicles', {}).get('two_wheeler', 0):,} two-wheelers, "
            f"{demand.get('vehicles', {}).get('bus', 0):,} buses.",
            f"- **Off-road transit:** **{demand.get('metro_riders', 0):,.0f}** metro riders, **{demand.get('pedestrians', 0):,.0f}** pedestrians.",
            f"- **Parking Status:** {p_note}.",
            "\n*Police Directive:* Direct private vehicles to designated peripheral parking clusters `[P-1]` through `[P-4]` early. "
            "Coordinate with HMRL for high-frequency metro feeder trains (5-minute headway) during the peak arrival window."
        ]
        return "\n".join(lines)

    # 6. Default / General Plan Summary
    if is_te:
        lines = [
            f"### 📋 ట్రాఫిక్ కో-పైలట్ ప్రణాళిక అవలోకనం: {event_name}",
            f"- **ఈవెంట్ సమయం & ప్రేక్షకులు:** ప్రారంభ సమయం {start_time}, {attendance:,} మంది హాజరు ({phase_str}).",
            f"- **పీక్ ట్రాఫిక్ ప్రవాహం:** **{demand.get('total_vehicles', 0):,} వాహనాలు**, పీక్ సమయంలో **{demand.get('peak_hourly_pcu', 0):,.0f} PCU/గం**.",
            f"- **రోడ్డు నెట్‌వర్క్ ప్రభావం:** గరిష్ట V/C **{so.get('max_vc', 0):.2f}**, **{so.get('congested', 0)} రోడ్డు విభాగాలు సామర్థ్యానికి మించి రద్దీగా ఉన్నాయి**.",
            f"- **కీలక కార్యాచరణ అంశాలు:**",
            f"  1. ప్రధాన హాట్‌స్పాట్లు `[H-1]` నుండి `[H-4]` వరకు గమనించండి.",
            f"  2. ట్రాఫిక్ నిలిచిపోకుండా `[D-1]` మరియు `[D-2]` మళ్లింపులను అమలు చేయండి.",
            f"  3. అత్యవసర వాహనాల కోసం గ్రీన్ కారిడార్ `[E-1]` ని నిరంతరం క్లియర్‌గా ఉంచండి.",
            f"  4. వాహనాలను నిర్దేశిత పార్కింగ్ కేంద్రాల `[P-1]` కు మళ్లించి మెట్రో వినియోగాన్ని ప్రోత్సహించండి.",
            "\n*మీరు నిర్దిష్ట ప్రశ్నలు అడగవచ్చు: 'రద్దీ హాట్‌స్పాట్లు ఏవి?', 'మళ్లింపు మార్గాలు ఏమిటి?', 'అంబులెన్స్ ETA ఎంత?', లేదా 'ఎంతమంది పోలీసు సిబ్బంది అవసరం?'*"
        ]
        return "\n".join(lines)

    lines = [
        f"### 📋 Traffic Copilot Plan Overview: {event_name}",
        f"- **Event Window & Crowd:** Start time {start_time}, {attendance:,} attendance ({phase.title()} phase).",
        f"- **Peak Flow:** **{demand.get('total_vehicles', 0):,} vehicles** generating **{demand.get('peak_hourly_pcu', 0):,.0f} PCU/h** at peak.",
        f"- **Network Impact:** Peak V/C is **{so.get('max_vc', 0):.2f}** with **{so.get('congested', 0)} road(s) over capacity**.",
        f"- **Action Summary:**",
        f"  1. Monitor top bottlenecks `[H-1]` to `[H-4]`.",
        f"  2. Enforce diversions `[D-1]` and `[D-2]` to prevent gridlock.",
        f"  3. Keep the green corridor `[E-1]` clear for emergency vehicles.",
        f"  4. Guide spectators to peripheral parking `[P-1]` and promote metro usage.",
        "\n*You can ask me specific questions like: 'What are the hotspots?', 'What are the diversions?', 'What is the ambulance ETA?', or 'How many officers are needed?'*"
    ]
    return "\n".join(lines)
