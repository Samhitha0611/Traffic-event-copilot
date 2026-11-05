# Traffic Event Co-Pilot: SIPOC demo (Uppal Stadium, Hyderabad)

Shows a mentor, in about 7 minutes, how the project turns an event announcement into a traffic plan.

## Run it
```powershell
py -m pip install -r requirements.txt
py -m pytest -q            # 12 tests should pass
py -m streamlit run app.py
```
Keep your existing `data/` (graphml + Excel pack) and `outputs/location_mapping.csv`. Run from the project root.

## SIPOC
| Suppliers | Inputs | Process | Outputs | Customers |
|---|---|---|---|---|
| OpenStreetMap | Event name, date, start, attendance | 1 Collect and clean data | Hotspots with V/C | Traffic police planners |
| Traffic police advisories | 3 km road graph | 2 Build graph, estimate capacity | Congestion map | Event organiser |
| HMRL metro, TGSRTC buses | Mode split, occupancy (assumed) | 3 Snap locations to roads | Diversion routes + extra distance | Emergency services |
| News / event schedules | Diversion points and windows | 4 Demand per mode in PCU | Emergency corridor + ETA | Commuters |
| Organiser (not yet connected) | Metro and bus support | 5 Load roads: naive vs optimised | What-if comparison | Metro and bus operators |
| RTA vehicle data (planned) | Approach shares | 6 Hotspots, diversions, corridor, plan | Downloadable plan | Mentor / evaluator |

## 7-minute demo script
1. **Tab 1 SIPOC (1 min).** Read the table left to right. Point at the three boxes: real, assumed, missing.
2. **Tab 2 Inputs (1 min).** Show the event (3 May 2026 SRH vs KKR, 15:30), the police diversions for that date, and the road-network quality box (99% of roads have no lane tag in OSM).
3. **Tab 3 Process (2 min).** Walk through steps 3-5: snapped approach points, people → vehicles → PCU table (13,572 vehicles, 10,624 PCU/hour at the peak), then the naive-vs-optimised line chart.
4. **Tab 4 Outputs (2 min).** Open the map. Hover red roads. Show hotspots, diversions, emergency corridor ETA. Click "Run what-if": moving riders to metro lowers max V/C.
5. **Tab 5 Customers (1 min).** Show the draft public message and download the plan.

## Honest limitations (say these first, mentors respect it)
- No public event-day vehicle counts, speeds or queues exist for Uppal, so every load is a model estimate.
- Capacity, speeds, mode split, approach shares, parking zones and background traffic are labelled assumptions.
- Hospital location is a placeholder. Parking zones are generated, not surveyed.
- Roads are loaded by repeated shortest-path re-routing, not a full traffic-assignment model.
- Next step: replace assumptions with police ITMS counts (see data pack, sheet Data_Sources).
