"""Ukončení plnění stavební smlouvy z E-ZAK (#207): pipeline/ukonceni.py, pipeline/zdroje/ezak_plneni.py."""
import json

from pipeline import ukonceni
from pipeline.zdroje import ezak_plneni


def _karta(*zakazky):
    return {"zakazky": [{"id": z, "role": "stavba", "casti": [{"stav": "ukončeno plnění"}]} for z in zakazky]}


def test_datum_z_citace():
    assert ukonceni.datum("Plnění smlouvy ukončeno 07.05.2026") == "2026-05-07"
    assert ukonceni.datum("Plnění smlouvy ukončeno 31.02.2026") is None


def test_karta_bere_nejpozdejsi_a_jen_kdyz_maji_datum_vsechny_stavby():
    pl = {"a": {"url": "ua", "citace": ["Plnění smlouvy ukončeno 13.12.2024"]},
          "b": {"url": "ub", "citace": ["Plnění smlouvy ukončeno 20.10.2025"]}}
    r = ukonceni.pro_kartu(_karta("a", "b"), pl)
    assert (r["datum"], r["url"], r["zakazka_id"], r["jistota"]) == ("2025-10-20", "ub", "b", "dolozeno")
    assert ukonceni.pro_kartu(_karta("a", "c"), pl) is None
    assert ukonceni.pro_kartu({"zakazky": [{"id": "a", "role": "projekt", "casti": [{"stav": "ukončeno plnění"}]}]}, pl) is None


def test_citace_ze_stranky_a_stazeni(tmp_path):
    stranka = ('<tr><td>Skutečně uhrazená cena</td></tr><tr><td>Stav:</td><td>Plnění smlouvy ukončeno'
               '&nbsp;07.05.2026</td></tr>').encode()
    assert ezak_plneni.citace(stranka.decode()) == ["Plnění smlouvy ukončeno 07.05.2026"]
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "projekty.json").write_text(json.dumps([
        {"zakazky": [{"id": "ezak-VZ-916", "role": "stavba", "url": "https://x/916", "casti": [{"stav": "ukončeno plnění"}]},
                     {"id": "ezak-VZ-1", "role": "stavba", "url": "https://x/1", "casti": [{"stav": "dokončen"}]}]}]))
    stazeno = []
    def ziskej(u):
        stazeno.append(u)
        return stranka
    assert ezak_plneni.stahni(tmp_path, ziskej) == (1, []) and stazeno == ["https://x/916"]
    ulozeno = json.loads((tmp_path / "raw" / "ezak" / "plneni.json").read_text())
    assert ulozeno["ezak-VZ-916"]["citace"] == ["Plnění smlouvy ukončeno 07.05.2026"]
    assert ezak_plneni.stahni(tmp_path, ziskej) == (0, []) and len(stazeno) == 1
