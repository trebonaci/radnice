"""Stažení aktivit SPRM z trebonaci.cz (pipeline/zdroje/sprm.py)."""
import json
from datetime import date

from pipeline.zdroje import sprm


def polozky(n=60):
    return [{"id": i, "aktivita": f"Aktivita {i}", "osa_id": 1, "osa_nazev": "Osa", "opatreni": "1.1",
             "stav": "Plánováno", "komentar": "", "geometrie": None, "navic": "x"} for i in range(n, 0, -1)]


def test_stazeni_a_zapis_jen_pri_zmene(tmp_path):
    ziskej = lambda url: json.dumps(polozky()).encode()
    assert sprm.stahni(tmp_path, ziskej, date(2026, 11, 21)) == []
    data = json.loads((tmp_path / "raw/sprm/projekty.json").read_text())
    assert len(data) == 60 and data[0]["id"] == 1 and "navic" not in data[0]
    m = json.loads((tmp_path / "raw/sprm/manifest.json").read_text())
    assert m["polozek"] == 60 and m["stazeno"] == "2026-11-21"
    assert sprm.stahni(tmp_path, ziskej, date(2026, 11, 22)) == []
    assert json.loads((tmp_path / "raw/sprm/manifest.json").read_text())["stazeno"] == "2026-11-21"


def test_chyba_ponecha_data(tmp_path):
    assert sprm.stahni(tmp_path, lambda u: json.dumps(polozky()).encode()) == []
    for spatne in (b"<html>", json.dumps({"a": 1}).encode(), json.dumps(polozky(5)).encode(),
                   json.dumps([{"id": 1}] * 60).encode()):
        chyby = sprm.stahni(tmp_path, lambda u, s=spatne: s)
        assert chyby and "ponechána předchozí data" in chyby[0]
    assert len(json.loads((tmp_path / "raw/sprm/projekty.json").read_text())) == 60
