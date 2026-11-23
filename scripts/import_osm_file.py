"""
Use a road map file downloaded in your browser (no Overpass needed).

1. Open https://www.openstreetmap.org/export , zoom to the venue (about 2 km x 2 km),
   press the blue Export button. You get a file called map.osm.
   (If it says the area is too large, zoom in a little and try again.)
2. Run, for example:
   py scripts/import_osm_file.py map.osm shilpakala_vedika 17.451408 78.379375
3. Restart the app. That venue now works offline.
Optional: --radius 2000 (metres, default 2000 because browser exports are small).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from osm_file_import import import_osm_file  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("osm_file")
ap.add_argument("venue_key", help="e.g. shilpakala_vedika, hitex_centre (see data/hyderabad_venues.csv)")
ap.add_argument("lat", type=float)
ap.add_argument("lon", type=float)
ap.add_argument("--radius", type=int, default=2000)
a = ap.parse_args()
print("Saved:", import_osm_file(a.osm_file, a.venue_key, a.lat, a.lon, a.radius))
