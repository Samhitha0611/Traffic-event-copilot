"""
Generates a SYNTHETIC typical-day traffic pattern (24 hours x 7 days x 4 road categories).

IMPORTANT: every number here (daily totals, day-of-week factors, hourly shares, vehicle mix) is an
ASSUMED planning shape written by hand. It is NOT measured data and NOT taken from the HMDA
Comprehensive Transportation Study or any other report. Use it only to show the SHAPE of a typical day.
For real published counts see data/real_count_anchors.csv. Replace with police/ITMS counts when available.
"""
import pandas as pd
import numpy as np
from pathlib import Path

SOURCE_LABEL = "SYNTHETIC-ASSUMED (not measured)"
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
OUTPUT_FILE = DATA_DIR / "hyderabad_hourly_traffic_profiles.csv"

# Daily Average Traffic (ADT) by Road Category in Hyderabad (vehicles / 24 hours)
# ASSUMED planning values (NOT from any survey). Real published anchors: data/real_count_anchors.csv
ROAD_ADT = {
    "Trunk_Highway": 72000,       # e.g. NH-65, ORR feeder, Mumbai Hwy
    "Primary_Arterial": 48000,    # e.g. Inner Ring Road, Gachibowli Main Rd, Uppal-Secunderabad Rd
    "Secondary_Arterial": 26000,  # e.g. Street No 8, Road No 36 Jubilee Hills, Habsiguda link
    "Collector_Road": 12000       # e.g. Sector access, residential distributor
}

# ASSUMED day-of-week factors relative to weekly average (not measured)
DAY_FACTORS = {
    "Monday": 1.02,
    "Tuesday": 1.00,
    "Wednesday": 1.01,
    "Thursday": 1.03,
    "Friday": 1.08,    # Friday evening rush
    "Saturday": 0.96,  # Mixed shopping/leisure
    "Sunday": 0.85     # Lower commercial/office, higher evening leisure
}

# 24-hour diurnal share profile (% of 24h traffic occurring in each 1-hour window)
# Weekday vs Weekend: ASSUMED shapes (not measured)
WEEKDAY_HOURLY_SHARE = [
    0.008, 0.006, 0.005, 0.005, 0.008, 0.018,  # 00:00 - 05:00 (Late night / early dawn)
    0.038, 0.065, 0.088, 0.092, 0.075, 0.060,  # 06:00 - 11:00 (Morning Peak)
    0.052, 0.050, 0.053, 0.058, 0.072, 0.089,  # 12:00 - 17:00 (Afternoon into Evening Peak)
    0.094, 0.082, 0.058, 0.040, 0.026, 0.016   # 18:00 - 23:00 (Evening Peak into Night)
]

WEEKEND_HOURLY_SHARE = [
    0.012, 0.008, 0.006, 0.005, 0.006, 0.012,  # 00:00 - 05:00
    0.024, 0.042, 0.058, 0.070, 0.072, 0.070,  # 06:00 - 11:00 (Gradual waking)
    0.068, 0.065, 0.066, 0.072, 0.082, 0.090,  # 12:00 - 17:00 (Sustained shopping/events)
    0.095, 0.088, 0.068, 0.050, 0.035, 0.020   # 18:00 - 23:00 (High evening leisure)
]

# ASSUMED vehicle mix (not taken from RTA or HMDA)
VEHICLE_MIX = {
    "Two_Wheeler": 0.52,   # PCU = 0.4
    "Car": 0.28,           # PCU = 1.0
    "Auto_Rickshaw": 0.10, # PCU = 0.9
    "Bus": 0.04,           # PCU = 3.5
    "LCV_Truck": 0.06      # PCU = 3.0 (restricted 08:00-11:00 & 17:00-21:00 by police)
}

PCU_WEIGHTS = {
    "Two_Wheeler": 0.4,
    "Car": 1.0,
    "Auto_Rickshaw": 0.9,
    "Bus": 3.5,
    "LCV_Truck": 3.0
}

def generate_profiles():
    rows = []
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for road_type, base_adt in ROAD_ADT.items():
        for day in days:
            day_mult = DAY_FACTORS[day]
            is_weekend = day in ("Saturday", "Sunday")
            hourly_shares = WEEKEND_HOURLY_SHARE if is_weekend else WEEKDAY_HOURLY_SHARE
            day_volume = base_adt * day_mult

            for hour in range(24):
                h_share = hourly_shares[hour]
                tot_hour_veh = round(day_volume * h_share)
                
                # Heavy vehicle police restrictions during urban peak hours (08:00-11:00, 17:00-21:00)
                is_peak_window = (8 <= hour <= 11) or (17 <= hour <= 21)
                lcv_share = 0.02 if is_peak_window else 0.08
                car_share = 0.30 if is_peak_window else 0.26
                tw_share = 0.54 if is_peak_window else 0.50
                auto_share = 0.10
                bus_share = 0.04

                tw_count = round(tot_hour_veh * tw_share)
                car_count = round(tot_hour_veh * car_share)
                auto_count = round(tot_hour_veh * auto_share)
                bus_count = round(tot_hour_veh * bus_share)
                lcv_count = round(tot_hour_veh * lcv_share)

                # Total PCU calculation
                pcu_val = round(
                    tw_count * PCU_WEIGHTS["Two_Wheeler"] +
                    car_count * PCU_WEIGHTS["Car"] +
                    auto_count * PCU_WEIGHTS["Auto_Rickshaw"] +
                    bus_count * PCU_WEIGHTS["Bus"] +
                    lcv_count * PCU_WEIGHTS["LCV_Truck"]
                )

                time_label = f"{hour:02d}:00 - {(hour+1)%24:02d}:00"
                rows.append({
                    "Day_Of_Week": day,
                    "Hour": hour,
                    "Time_Window": time_label,
                    "Road_Category": road_type,
                    "Total_Vehicles": tot_hour_veh,
                    "Total_PCU": pcu_val,
                    "Two_Wheeler_Count": tw_count,
                    "Car_Count": car_count,
                    "Auto_Rickshaw_Count": auto_count,
                    "Bus_Count": bus_count,
                    "LCV_Truck_Count": lcv_count,
                    "Peak_Status": "Peak Rush" if is_peak_window else "Off-Peak",
                    "Source": SOURCE_LABEL
                })

    df = pd.DataFrame(rows)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Generated {len(df)} hourly baseline traffic records -> {OUTPUT_FILE}")
    return df

if __name__ == "__main__":
    generate_profiles()

