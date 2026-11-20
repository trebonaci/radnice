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
