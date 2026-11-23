import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import osm_download as OD  # noqa: E402
import osm_file_import as OFI  # noqa: E402


def _tiny_osm(path, lat0=17.45, lon0=78.38, n=8, step=0.0008):
    nodes, ways, nid = [], [], 1
    ids = {}
    for i in range(n):
        for j in range(n):
            ids[(i, j)] = nid
            nodes.append(f'<node id="{nid}" lat="{lat0 + i * step}" lon="{lon0 + j * step}"/>')
            nid += 1
    wid = 1000
    for i in range(n):
        refs = "".join(f'<nd ref="{ids[(i, j)]}"/>' for j in range(n))
        ways.append(f'<way id="{wid}">{refs}<tag k="highway" v="residential"/></way>'); wid += 1
    for j in range(n):
        refs = "".join(f'<nd ref="{ids[(i, j)]}"/>' for i in range(n))
        ways.append(f'<way id="{wid}">{refs}<tag k="highway" v="tertiary"/></way>'); wid += 1
    path.write_text('<?xml version="1.0"?><osm version="0.6">' + "".join(nodes) + "".join(ways) + "</osm>")


def test_import_osm_file_creates_graph_and_is_found_as_cover(tmp_path, monkeypatch):
    monkeypatch.setattr(OD, "NETWORKS_DIR", tmp_path / "networks")
    f = tmp_path / "map.osm"
    _tiny_osm(f)
    out = OFI.import_osm_file(f, "test_venue", 17.4532, 78.3832, radius_m=800)
    assert out.exists() and out.with_suffix(".meta.json").exists()
    assert OD.get_graph_for_venue("test_venue", 17.4532, 78.3832) == out


def test_import_rejects_wrong_area(tmp_path, monkeypatch):
    monkeypatch.setattr(OD, "NETWORKS_DIR", tmp_path / "networks")
    f = tmp_path / "map.osm"
    _tiny_osm(f)
    with pytest.raises(ValueError):
        OFI.import_osm_file(f, "far_venue", 12.97, 77.59, radius_m=800)    # file is Hyderabad, venue is Bengaluru
