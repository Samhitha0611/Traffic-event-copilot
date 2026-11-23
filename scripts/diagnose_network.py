"""
Find out WHY OpenStreetMap servers fail on this computer.   Run: py scripts/diagnose_network.py
It checks: general internet, DNS, connection, and any proxy Windows/Python is using.
"""
import socket
import urllib.request
from urllib.parse import urlparse

import requests

HOSTS = ["https://pypi.org", "https://www.openstreetmap.org", "https://nominatim.openstreetmap.org", "https://api.openstreetmap.org/api/0.6/capabilities",
         "https://overpass-api.de/api/status", "https://overpass.kumi.systems/api/status",
         "https://overpass.private.coffee/api/status", "https://overpass.openstreetmap.fr/api/status"]

print("Proxy settings Python sees:", urllib.request.getproxies() or "none")
print()
for url in HOSTS:
    host = urlparse(url).hostname
    try:
        ip = socket.gethostbyname(host)
        dns = f"DNS ok ({ip})"
    except Exception as e:
        print(f"FAIL  {host}: DNS lookup failed ({e}). Network or DNS blocks this name.")
        continue
    try:
        r = requests.get(url, timeout=8, headers={"User-Agent": "traffic_copilot"})
        print(f"OK    {host}: {dns}, HTTP {r.status_code}")
    except Exception as e:
        print(f"FAIL  {host}: {dns}, but no answer ({type(e).__name__}). ReadTimeout = server connected but too slow (overloaded), not blocked.")
print("""
How to read this:
- api.openstreetmap.org OK                -> the app can download roads from it automatically (tiles).
- overpass ReadTimeout / HTTP 403          -> Overpass is overloaded or refuses us; this is fine, the API fallback is used.
- api.openstreetmap.org FAIL too          -> use a browser export + scripts/import_osm_file.py.
- everything FAIL                         -> no internet from Python (check VPN/proxy/antivirus).
- A proxy is listed                       -> it may need to allow these hosts, or set HTTPS_PROXY correctly.""")
