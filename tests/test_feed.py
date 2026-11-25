"""Atom feed „Co se děje“ (web/feed.py): well-formed, opisuje jen už sestavené zprávy."""
from xml.dom.minidom import parseString

from web import feed

NS = "http://www.w3.org/2005/Atom"

OKRUHY = [{"id": "skoly", "nazev": "Školy a školky"},
          {"id": "doprava_prostor", "nazev": "Doprava a veřejný prostor"}]
VSTUP = {"zpravy": [
    {"id": "z1", "datum": "2026-11-20", "okruh": "skoly", "titulek": "Nová třída v MŠ",
     "shrnuti": "Rada schválila & upravila <plán>.", "projekt_id": "ms-nova",
     "zdroje": [{"nazev": "Registr smluv", "url": "https://smlouvy.gov.cz/smlouva/1"}]},
    {"id": "z2", "datum": "2026-11-18", "okruh": "doprava_prostor", "titulek": "Oprava chodníku",
     "shrnuti": "Smlouva s dodavatelem.", "projekt_id": None,
     "zdroje": [{"nazev": "E-ZAK", "url": "https://zakazky.example/2"}]},
]}


def _feed():
    return parseString(feed.atom(VSTUP, OKRUHY, "2026-11-21"))


def test_feed_je_validni_atom():
    d = _feed()
    assert d.documentElement.tagName == "feed"
    entries = d.getElementsByTagNameNS(NS, "entry")
    assert len(entries) == 2
    # feed-level updated = datum nejnovější zprávy
    upd = d.getElementsByTagNameNS(NS, "updated")[0].firstChild.nodeValue
    assert upd == "2026-11-20T12:00:00Z"


def test_entry_odkaz_a_kategorie():
    d = _feed()
    e = d.getElementsByTagNameNS(NS, "entry")[0]
    # zpráva s projekt_id míří na kartu akce na webu radnice
    assert e.getElementsByTagNameNS(NS, "link")[0].getAttribute("href") == "https://radnice.trebonaci.cz/#ms-nova"
    # stabilní unikátní id (ne odkaz, který mohou dvě zprávy sdílet)
    assert e.getElementsByTagNameNS(NS, "id")[0].firstChild.nodeValue == "urn:radnice:zprava:z1"
    cat = e.getElementsByTagNameNS(NS, "category")[0]
    assert cat.getAttribute("term") == "skoly" and cat.getAttribute("label") == "Školy a školky"


def test_bez_projektu_vede_na_zdroj():
    d = _feed()
    e = d.getElementsByTagNameNS(NS, "entry")[1]
    assert e.getElementsByTagNameNS(NS, "link")[0].getAttribute("href") == "https://zakazky.example/2"


def test_specialni_znaky_jsou_escapovane():
    # & a < v shrnutí nesmí rozbít XML; parse projde (viz výše), tady kontrola obsahu
    d = _feed()
    s = d.getElementsByTagNameNS(NS, "summary")[0].firstChild.nodeValue
    assert s == "Rada schválila & upravila <plán>."  # DOM vrací odescapované


def test_prazdny_vstup_nespadne():
    out = feed.atom({"zpravy": []}, OKRUHY, "2026-11-21")
    d = parseString(out)
    assert d.getElementsByTagNameNS(NS, "entry") == []
    assert d.getElementsByTagNameNS(NS, "updated")[0].firstChild.nodeValue == "2026-11-21T12:00:00Z"
