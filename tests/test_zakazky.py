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

    zmeny, chyby = ezak.stahni(koren, date(2026, 11, 20), ziskej, pauza=0, max_stazeni=100)
    assert "00247618/2026-2.xml" in zmeny and (koren / "raw/ezak/00247618/2019-1.xml").exists()
    assert any("IČO" in c for c in chyby) and any("kořen" in c for c in chyby)
    assert not (koren / "raw/ezak/25179896").exists()
    assert any("od=01072026&do=20112026" in u for u in volano if "profile_display_2." in u)
    # druhý běh: uzavřené roky už ne, aktuální ano
    volano.clear()
    ezak.stahni(koren, date(2026, 11, 21), ziskej, pauza=0, max_stazeni=100)
    assert [u for u in volano if "profile_display_2." in u] == [
        "https://zakazky.mesto-trebon.cz/profile_display_2.html/XMLdataVZ?od=01072026&do=21112026"]
    m = json.loads((koren / "raw/ezak/manifest.json").read_text(encoding="utf-8"))
    assert m["00247618/2026-2.xml"]["zakazek"] == 4


def test_uzavreny_rok_se_po_skonceni_stahne_jeste_jednou():
    assert ezak.potreba_stahnout(date(2026, 12, 31), {"uzavreno": False}, date(2027, 1, 3))
    assert not ezak.potreba_stahnout(date(2026, 12, 31), {"uzavreno": True}, date(2027, 1, 9))
    assert ezak.obdobi(2024, 2) == (date(2024, 7, 1), date(2024, 12, 31))    # přestupný rok celý nejde (HTTP 400)


def test_prazdne_obdobi_bez_zadavatele_je_v_poradku():
    prazdne = f'<profil xmlns="{ezak.NS[1:-1]}"><profil_kod>Z2019-003053</profil_kod></profil>'.encode()
    assert ezak.zkontroluj_xml(prazdne, "00247618") == 0
    with pytest.raises(ezak.ChybaZdroje):
        ezak.zkontroluj_xml((VZORKY / "2026.xml").read_bytes(), "25179896")


def test_jmeno_s_titulem_v_predmetu_zakazky_se_maskuje(koren):
    from pipeline.sestav import sestav
    for d in ("anotace",):
        shutil.copytree(KOREN / d, koren / d)
    (koren / "raw" / "ezak" / "00247618").mkdir(parents=True)
    (koren / "raw" / "manifest.json").write_text("[]", encoding="utf-8")
    xml = (VZORKY / "2026.xml").read_text(encoding="utf-8").replace(
        "Předmětem je rozšíření veřejného osvětlení v branné.",
        "Předmětem je stavba podle projektu Ing. Františka Stráského.")
    (koren / "raw/ezak/00247618/2026-2.xml").write_text(xml, encoding="utf-8")
    vystup, chyby = sestav(koren)
    z = {x["id"]: x for x in vystup["zakazky"]}["ezak-VZ-957"]
    assert z["predmet"] == "Předmětem je stavba podle projektu [jméno]." and not [c for c in chyby if "zakazky" in c]


def test_stazeni_beze_zmeny_nemeni_manifest(koren):
    """Jen nové datum stažení nesmí měnit raw/ezak (jinak by každý běh zakládal PR; Codex P1, #74)."""
    obsah = (VZORKY / "2026.xml").read_bytes()
    ezak.stahni(koren, date(2026, 11, 20), lambda u: obsah if "display_2." in u else b"<x/>", pauza=0, max_stazeni=100)
    m = koren / "raw/ezak/manifest.json"
    pred = m.read_bytes()
    ezak.stahni(koren, date(2026, 11, 21), lambda u: obsah if "display_2." in u else b"<x/>", pauza=0, max_stazeni=100)
    assert m.read_bytes() == pred



def test_urednik_bez_titulu_v_zakazce_funkci(koren):
    """Úředník ze seznamu se nahradí funkcí, ne jen příjmení (Codex P1, #80)."""
    import yaml
    from pipeline.sestav import anonymizuj_urednici, nacti_osoby
    osoby = nacti_osoby(KOREN)
    jmeno = next(v if isinstance(v, str) else v["text"] for u in osoby["urednici"] for v in u["varianty"]
                 if "Ing." not in (v if isinstance(v, str) else v["text"]))
    vysl = anonymizuj_urednici(f"Kontaktní osoba: {jmeno}.", osoby)
    assert jmeno not in vysl



def test_limit_za_beh_rozpracovane_prvni_a_jistic(koren):
    obsah = (VZORKY / "2026.xml").read_bytes()
    volano = []
    ezak.stahni(koren, date(2026, 11, 20), lambda u: volano.append(u) or (obsah if "display_2." in u else b"<x/>"),
                pauza=0, max_stazeni=8)
    assert len(volano) == 8 and "od=01072026" in volano[0]               # limit; aktuální pololetí jako první

    def vypadek(url):
        volano.append(url)
        raise TimeoutError("timed out")
    volano.clear()
    _, chyby = ezak.stahni(koren, date(2026, 11, 20), vypadek, pauza=0, max_stazeni=8)
    assert len(volano) == 3 and any("server neodpovídá" in c for c in chyby)   # 3 timeouty za sebou → konec
