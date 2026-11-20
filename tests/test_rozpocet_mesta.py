"""Stažení rozpočtu a přehledu RO (pipeline/zdroje/rozpocet_mesta.py) bez sítě."""
import json

from pipeline.zdroje import ChybaZdroje
from pipeline.zdroje import rozpocet_mesta as rm

STRANKA = """<a href="uploads/_mestsky-urad/financni/rozpocet/Rozpo%C4%8Det%202026/Rozpo%C4%8Det%20m%C4%9Bsta%20T%C5%99ebon%C4%9B%20na%20rok%202026.pdf">Rozpočet 2026</a>
<a href="uploads/_mestsky-urad/financni/rozpocet/Rozpo%C4%8Det%202026/Rozpoctova_opatreni_schvalena%20do%2021_10_2026.pdf">zde</a>
<a href="uploads/_mestsky-urad/financni/rozpocet/Rozpo%C4%8Det%202025/Rozpo%C4%8Det%20m%C4%9Bsta%20T%C5%99ebon%C4%9B%20na%20rok%202025.pdf">2025</a>"""


def test_najdi_dokumenty():
    d = rm.najdi_dokumenty(STRANKA, 2026)
    assert [(x["rok"], x["druh"]) for x in d] == [(2026, "rozpocet"), (2026, "rozpoctova_opatreni")]
    assert d[0]["url"].startswith("https://www.mesto-trebon.cz/uploads/") and d[0]["soubor"].endswith("2026.pdf")


def web(obsahy, volano=None):
    def ziskej(url):
        if volano is not None:
            volano.append(url)
        if url == rm.STRANKA:
            return STRANKA.encode()
        if url not in obsahy:
            raise ChybaZdroje("404")
        return obsahy[url]
    return ziskej


def test_stahni_zapise_texty_a_pri_stejnem_obsahu_nic_nemeni(tmp_path):
    d = rm.najdi_dokumenty(STRANKA, 2026)
    obsahy = {d[0]["url"]: b"pdf-rozpocet", d[1]["url"]: b"pdf-ro"}
    extrahuj = lambda b: [("Strana 1 " + b.decode()) * 100, "Strana 2"]
    assert rm.stahni(tmp_path, web(obsahy), extrahuj) == []
    m = json.loads((tmp_path / "raw/rozpocet/manifest.json").read_text())
    assert set(m) == {"2026/rozpocet", "2026/rozpoctova_opatreni"} and m["2026/rozpocet"]["stran"] == 2
    assert (tmp_path / "raw/rozpocet/2026/rozpocet/strana-2.txt").read_text() == "Strana 2"
    pred = (tmp_path / "raw/rozpocet/manifest.json").stat().st_mtime_ns
    assert rm.stahni(tmp_path, web(obsahy), extrahuj) == []
    assert (tmp_path / "raw/rozpocet/manifest.json").stat().st_mtime_ns == pred


def test_chyba_jednoho_dokumentu_nezastavi_druhy_a_malo_textu(tmp_path):
    d = rm.najdi_dokumenty(STRANKA, 2026)
    chyby = rm.stahni(tmp_path, web({d[1]["url"]: b"x"}), lambda b: ["kratke"])
    assert any("2026/rozpocet" in c for c in chyby) and any("málo textu" in c for c in chyby)
    assert not (tmp_path / "raw/rozpocet/manifest.json").exists()


def test_ro_vybere_nejnovejsi_prehled_podle_data_v_nazvu():
    stranka = ('<a href="u/Rozpoctova_opatreni_schvalena%20do%2021_10_2026.pdf">a</a>'
               '<a href="u/Rozpoctova_opatreni_schvalena%20do%201_2_2026.pdf">b</a>')
    d = rm.najdi_dokumenty(stranka, 2026)
    assert len(d) == 1 and d[0]["soubor"].endswith("21_10_2026.pdf")


def test_selhani_zapisu_ponecha_predchozi_texty(tmp_path, monkeypatch):
    d = rm.najdi_dokumenty(STRANKA, 2026)
    extrahuj = lambda b: [("Strana 1 " + b.decode()) * 100, "Strana 2"]
    assert rm.stahni(tmp_path, web({d[0]["url"]: b"v1", d[1]["url"]: b"ro"}), extrahuj) == []
    puvodni = rm.Path.write_text

    def rozbity(self, text, **kw):
        if self.name == "strana-2.txt":
            raise OSError("disk plný")
        return puvodni(self, text, **kw)

    monkeypatch.setattr(rm.Path, "write_text", rozbity)
    chyby = rm.stahni(tmp_path, web({d[0]["url"]: b"v2", d[1]["url"]: b"ro"}), extrahuj)
    monkeypatch.undo()
    assert any("ponechána předchozí data" in c for c in chyby)
    adr = tmp_path / "raw/rozpocet/2026/rozpocet"
    assert "v1" in (adr / "strana-1.txt").read_text() and (adr / "strana-2.txt").exists()
    assert not adr.with_name("rozpocet.nove").exists()


def test_odkaz_s_nezakodovanou_diakritikou_je_ascii():
    stranka = '<a href="/uploads/Rozpočet 2026/Rozpočet města Třeboně na rok 2026.pdf">x</a>'
    d = rm.najdi_dokumenty(stranka, 2026)
    assert d[0]["url"].isascii() and " " not in d[0]["url"]
    assert d[0]["soubor"] == "Rozpočet města Třeboně na rok 2026.pdf"
    # už zakódovaný odkaz se nezakóduje podruhé
    assert "%25" not in rm.najdi_dokumenty(STRANKA, 2026)[0]["url"]


def test_neocekavana_chyba_stazeni_je_upozorneni(tmp_path):
    def ziskej(url):
        if url == rm.STRANKA:
            return STRANKA.encode()
        raise UnicodeEncodeError("ascii", "č", 0, 1, "x")
    chyby = rm.stahni(tmp_path, ziskej, lambda b: [])
    assert len(chyby) == 2
