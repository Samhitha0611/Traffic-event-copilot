import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import osm_api_download as API  # noqa: E402
import osm_download as OD  # noqa: E402
from test_osm_file_import import _tiny_osm  # noqa: E402

LAT, LON = 17.4532, 78.3832


class Resp:
    def __init__(self, code, content=b""):
        self.status_code, self.content = code, content
    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


def _xml(tmp_path):
    f = tmp_path / "t.osm"
    _tiny_osm(f)
    f.write_text(f.read_text().replace("</osm>", '<way id="9"><nd ref="1"/><nd ref="2"/><tag k="highway" v="footway"/></way></osm>'))
    return f.read_bytes()


def test_tiles_cover_the_whole_circle_box():
    tiles = API.tile_boxes(LAT, LON, 3000)
    w, s, e, n = API.bbox_around(LAT, LON, 3000)
    assert len(tiles) == 36
    assert min(t[0] for t in tiles) == pytest.approx(w) and max(t[2] for t in tiles) == pytest.approx(e)
    assert min(t[1] for t in tiles) == pytest.approx(s) and max(t[3] for t in tiles) == pytest.approx(n)


def test_footpaths_are_dropped_and_duplicates_merged(tmp_path):
    x = _xml(tmp_path)
    merged = API.merge_and_filter([x, x])
    assert b"footway" not in merged
    assert merged.count(b"<way ") == 16      # 8 residential + 8 tertiary lines, not doubled


def test_too_big_tile_is_split_and_retried(tmp_path):
    x = _xml(tmp_path)
    calls = []
    class S:
        def get(self, url, params=None, **k):
            w, s, e, n = map(float, params["bbox"].split(","))
            calls.append(e - w)
            return Resp(400) if (e - w) > 0.012 else Resp(200, x)
    chunks = list(API.fetch_area((78.37, 17.44, 78.39, 17.46), S(), sleep=lambda s: None))
    assert len(chunks) == 4                  # one 400, then four sub-tiles
    assert len(calls) == 5


def test_rate_limit_is_retried(monkeypatch, tmp_path):
    x = _xml(tmp_path)
    monkeypatch.setattr(API.time, "sleep", lambda s: None)
    seq = [Resp(509), Resp(200, x)]
    class S:
        def get(self, *a, **k): return seq.pop(0)
    assert API._fetch((78.37, 17.44, 78.38, 17.45), S()) == x


def test_full_api_download_builds_a_venue_graph(monkeypatch, tmp_path):
    x = _xml(tmp_path)
    monkeypatch.setattr(API.time, "sleep", lambda s: None)
    class S:
        def get(self, *a, **k): return Resp(200, x)
    out = tmp_path / "networks" / "v.graphml"
    p = OD.download_graph_via_api(LAT, LON, 800, out, session=S())
    assert p.exists() and p.with_suffix(".meta.json").exists()


def test_auto_mode_falls_back_to_api_when_overpass_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(OD, "_download_overpass", lambda *a, **k: (_ for _ in ()).throw(OD.NetworkUnavailable("slow")))
    monkeypatch.setattr(OD, "download_graph_via_api", lambda lat, lon, d, out, **k: out)
    monkeypatch.delenv("ROAD_SOURCE", raising=False)
    assert OD.download_graph(LAT, LON, 3000, tmp_path / "x.graphml") == tmp_path / "x.graphml"


def test_both_sources_failing_raises_clear_error(monkeypatch, tmp_path):
    monkeypatch.setattr(OD, "_download_overpass", lambda *a, **k: (_ for _ in ()).throw(OD.NetworkUnavailable("slow")))
    monkeypatch.setattr(OD, "download_graph_via_api", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("blocked")))
    with pytest.raises(OD.NetworkUnavailable):
        OD.download_graph(LAT, LON, 3000, tmp_path / "x.graphml")


def test_probe_treats_http_403_as_reachable_and_timeout_as_slow(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: Resp(403))
    assert OD.probe_detail("https://x")[0] is True
    monkeypatch.setattr(requests, "get", lambda *a, **k: (_ for _ in ()).throw(requests.ReadTimeout()))
    ok, note = OD.probe_detail("https://x")
    assert ok is False and note == "ReadTimeout"
