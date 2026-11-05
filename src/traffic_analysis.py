"""
Command-line script to run traffic scenario analysis for an event and print the report.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure src directory is in sys.path for direct script execution
BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import event_engine as ee


def main():
    parser = argparse.ArgumentParser(
        description="Run traffic analysis for a stadium event and print the report."
    )
    # ASSUMED: Default event index selects the first event in the data pack
    parser.add_argument(
        "--event-index",
        type=int,
        default=0,
        help="0-based index of event from data pack (default: 0)"
    )
    # ASSUMED: 39,000 capacity when attendance is unpublished
    parser.add_argument(
        "--attendance",
        type=int,
        default=39000,
        help="Event attendance (ASSUMED default: 39,000)"
    )
    # ASSUMED: Ingress phase evaluated by default
    parser.add_argument(
        "--phase",
        type=str,
        default="ingress",
        choices=["ingress", "egress"],
        help="Event phase to analyze: 'ingress' or 'egress' (ASSUMED default: ingress)"
    )
    # ASSUMED: Default event duration is 3.0 hours
    parser.add_argument(
        "--duration",
        type=float,
        default=3.0,
        help="Event duration in hours (ASSUMED default: 3.0)"
    )

    args = parser.parse_args()

    print("\n========== UPPAL TRAFFIC SCENARIO ANALYSIS ==========")

    # Load data pack
    pack = ee.load_pack()
    events = ee.event_options(pack)

    if events and 0 <= args.event_index < len(events):
        ev = events[args.event_index]
        event_name = ev["name"]
        event_date = ev["date"]
        start_time = ev["start"]
        print(f"Selected Event [{args.event_index}]: {ev['label']}")
    else:
        # ASSUMED: Fallback event details when data pack event index not found
        event_name = "Custom Uppal Stadium Event"
        event_date = None
        start_time = "19:30"
        print(f"Using default event: {event_name} (ASSUMED start: {start_time})")

    # Build road network
    print("Loading road network...")
    D, stats = ee.build_network()
    print(f"Road network loaded: {stats['nodes']} nodes, {stats['edges']} edges.")

    params = {
        "event_name": event_name,
        "event_date": event_date,
        "start_time": start_time,
        "attendance": args.attendance,  # ASSUMED
        "phase": args.phase,            # ASSUMED
        "duration_h": args.duration     # ASSUMED
    }

    print(f"Simulating {args.phase} phase for {params['attendance']:,} attendees...")
    scenario_result = ee.run_scenario(D, params, pack=pack)

    print("\n" + scenario_result["report"] + "\n")
    print("========== ANALYSIS COMPLETE ==========\n")


if __name__ == "__main__":
    main()

