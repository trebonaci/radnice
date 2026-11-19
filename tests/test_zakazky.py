"""Zakázky z E-ZAK: stažení (bez sítě) a převod XML → data/zakazky.json."""
import json
import shutil
from datetime import date
from pathlib import Path

import pytest

from pipeline import zakazky
from pipeline.zdroje import ezak

VZORKY = Path(__file__).resolve().parent / "vzorky" / "ezak"
KOREN = Path(__file__).resolve().parent.parent


@pytest.fixture
def koren(tmp_path):
    shutil.copytree(KOREN / "config", tmp_path / "config")
    return tmp_path


def s_vzorky(koren):
    d = koren / "raw" / "ezak" / "00247618"
    d.mkdir(parents=True)
    for f in ("2025.xml", "2026.xml"):
        shutil.copy(VZORKY / f, d / f)
    return zakazky.nacti_zakazky(koren)


def test_novejsi_rok_prepise_stav(koren):
    z = {x["id"]: x for x in s_vzorky(koren)}
    assert set(z) == {"ezak-VZ-957", "ezak-VZ-960", "ezak-VZ-966", "ezak-VZ-970"}
    assert z["ezak-VZ-957"]["stav"] == "dokončen" and z["ezak-VZ-957"]["zdroj"] == "00247618/2026.xml"


def test_udaje_se_opisuji_ze_zdroje(koren):
    z = {x["id"]: x for x in s_vzorky(koren)}["ezak-VZ-957"]
    assert z["druh"] == "stavebni" and z["subjekt_ico"] == "00247618"
    assert z["url"] == "https://zakazky.mesto-trebon.cz/contract_display_957.html"
    c = z["casti"][0]
    assert c["pocet_nabidek"] == 3 and c["datum_uzavreni_smlouvy"] == "2026-08-10" and c["lhuta_nabidek"] == "2026-06-30"
    assert c["registr_smluv"] == ["https://smlouvy.gov.cz/smlouva/31161940"]
    v = c["vitezove"][0]
    assert (v["nazev"], v["ico"], v["fyzicka_osoba"]) == ("VH-TRES spol. s r. o.", "15771822", False)
    castky = {(k["druh"], k["s_dph"], k["obdobi"]): k["hodnota"] for k in v["castky"]}
    assert castky == {("smluvni", True, None): 1010955.0, ("smluvni", False, None): 835500.0,
                      ("zaplaceno", True, "2026"): 287980.0, ("zaplaceno", False, "2026"): 238000.0}


def test_citace_castky_je_ve_zdroji(koren):
    zz = s_vzorky(koren)
    z = {x["id"]: x for x in zz}["ezak-VZ-957"]
    k = z["casti"][0]["vitezove"][0]["castky"][0]
    assert k["citace"].startswith("<smluvni_cena_s_DPH>") and "VZ-957" in k["poznamka"]
    assert zakazky.zkontroluj(zz, koren) == []
    k["citace"] = "<smluvni_cena_s_DPH>1</smluvni_cena_s_DPH>"
    assert any("citace" in ch for ch in zakazky.zkontroluj(zz, koren))


def test_fyzicka_osoba_je_anonymizovana(koren):
    z = {x["id"]: x for x in s_vzorky(koren)}["ezak-VZ-960"]
    v = z["casti"][0]["vitezove"][0]
    assert v == {**v, "nazev": "fyzická osoba", "ico": None, "fyzicka_osoba": True}
    assert "Novák" not in json.dumps(z, ensure_ascii=False) and "87654321" not in json.dumps(z)
    assert zakazky.zkontroluj([z]) == []


@pytest.mark.parametrize("nazev, fo", [("Jan Novák", True), ("Petr Svoboda – stavby", True),
                                       ("VH-TRES spol. s r. o.", False), ("EUROVIA CZ a.s.", False),
                                       ("Lesy České republiky, s. p.", False),
                                       ("Jan Novák – správa nemovitostí", True), ("Petr Svoboda – stavby obce", True),
                                       ("STRABAG a.s., odštěpný závod Morava", False),
                                       ("Správa a údržba silnic Jihočeského kraje", False)])
def test_podnikajici_fyzicka_osoba_bez_pravni_formy(nazev, fo):
    import xml.etree.ElementTree as ET
    e = ET.fromstring(f'<subjekt xmlns="{zakazky.NS[1:-1]}"><ico>12345678</ico><nazev_subjektu>{nazev}</nazev_subjektu>'
                      f'<misto_podnikani>CZ</misto_podnikani></subjekt>')
    assert zakazky.subjekt(e)["fyzicka_osoba"] is fo


def test_zrusena_a_vicedilna(koren):
    z = {x["id"]: x for x in s_vzorky(koren)}
    assert z["ezak-VZ-966"]["stav"] == "zrušen" and z["ezak-VZ-966"]["casti"][0]["datum_zruseni"] == "2026-05-05"
    assert z["ezak-VZ-970"]["stav"] is None and [c["id"] for c in z["ezak-VZ-970"]["casti"]] == ["970-1", "970-2"]


def test_stahni_jen_potrebne_roky_a_kontroluje_ico(koren):
    obsah = (VZORKY / "2026.xml").read_bytes()
    volano = []

    def ziskej(url):
        volano.append(url)
        if "profile_display_190" in url:
            return obsah            # IČO města, ne lázní → odmítnout
        if "profile_display_354" in url:
            return b"<html>Chyba</html>"
        return obsah

    zmeny, chyby = ezak.stahni(koren, date(2026, 11, 20), ziskej, pauza=0)
    assert "00247618/2026.xml" in zmeny and (koren / "raw/ezak/00247618/2019.xml").exists()
    assert any("IČO" in c for c in chyby) and any("kořen" in c for c in chyby)
    assert not (koren / "raw/ezak/25179896").exists()
    assert "od=01012026&do=20112026" in [u for u in volano if "profile_display_2." in u][-1]
    # druhý běh: uzavřené roky už ne, aktuální ano
    volano.clear()
    ezak.stahni(koren, date(2026, 11, 21), ziskej, pauza=0)
    assert [u for u in volano if "profile_display_2." in u] == [
        "https://zakazky.mesto-trebon.cz/profile_display_2.html/XMLdataVZ?od=01012026&do=21112026"]
    m = json.loads((koren / "raw/ezak/manifest.json").read_text(encoding="utf-8"))
    assert m["00247618/2026.xml"]["zakazek"] == 4


def test_uzavreny_rok_se_po_skonceni_stahne_jeste_jednou():
    assert ezak.potreba_stahnout(2026, {"uzavreno": False}, date(2027, 1, 3))
    assert not ezak.potreba_stahnout(2026, {"uzavreno": True}, date(2027, 1, 9))


def test_stazeni_beze_zmeny_nemeni_manifest(koren):
    """Jen nové datum stažení nesmí měnit raw/ezak (jinak by každý běh zakládal PR; Codex P1, #74)."""
    obsah = (VZORKY / "2026.xml").read_bytes()
    ezak.stahni(koren, date(2026, 11, 20), lambda u: obsah if "display_2." in u else b"<x/>", pauza=0)
    m = koren / "raw/ezak/manifest.json"
    pred = m.read_bytes()
    ezak.stahni(koren, date(2026, 11, 21), lambda u: obsah if "display_2." in u else b"<x/>", pauza=0)
    assert m.read_bytes() == pred
