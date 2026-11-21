"""Mapa investic (#180): výtah z RÚIAN (pipeline/zdroje/ruian.py) a místa akcí (pipeline/mapa.py)."""
import io
import json
from datetime import date

from pipeline import mapa
from pipeline.zdroje import ruian

VFR = """<?xml version="1.0" encoding="UTF-8"?>
<vf:VymennyFormat xmlns:vf="urn:cz:isvs:ruian:schemas:VymennyFormatTypy:v1" xmlns:gml="http://www.opengis.net/gml/3.2"
 xmlns:obi="urn:cz:isvs:ruian:schemas:ObecIntTypy:v1" xmlns:coi="urn:cz:isvs:ruian:schemas:CastObceIntTypy:v1"
 xmlns:uli="urn:cz:isvs:ruian:schemas:UliceIntTypy:v1" xmlns:soi="urn:cz:isvs:ruian:schemas:StavObjIntTypy:v1"
 xmlns:ami="urn:cz:isvs:ruian:schemas:AdrMisIntTypy:v1" xmlns:com="urn:cz:isvs:ruian:schemas:CommonTypy:v1">
<vf:Data>
 <vf:Obce><vf:Obec gml:id="OB.547336"><obi:Kod>547336</obi:Kod><obi:Nazev>Třeboň</obi:Nazev></vf:Obec></vf:Obce>
 <vf:CastiObci><vf:CastObce gml:id="CO.1"><coi:Kod>1</coi:Kod><coi:Nazev>Třeboň I</coi:Nazev></vf:CastObce></vf:CastiObci>
 <vf:Ulice><vf:Ulice gml:id="UL.10"><uli:Kod>10</uli:Kod><uli:Nazev>Budějovická</uli:Nazev>
  <uli:Geometrie><uli:DefinicniCara><gml:MultiCurve><gml:curveMember><gml:LineString gml:id="L.1">
   <gml:posList srsDimension="2">1 2 3 4 5 6</gml:posList></gml:LineString></gml:curveMember></gml:MultiCurve></uli:DefinicniCara></uli:Geometrie></vf:Ulice>
  <vf:Ulice gml:id="UL.11"><uli:Kod>11</uli:Kod><uli:Nazev>Chelčického</uli:Nazev>
  <uli:Geometrie><uli:DefinicniCara><gml:MultiCurve><gml:curveMember><gml:LineString>
   <gml:posList>7 8 9 10</gml:posList></gml:LineString></gml:curveMember></gml:MultiCurve></uli:DefinicniCara></uli:Geometrie></vf:Ulice></vf:Ulice>
 <vf:StavebniObjekty><vf:StavebniObjekt gml:id="SO.100"><soi:Kod>100</soi:Kod><soi:CislaDomovni><com:CisloDomovni>1</com:CisloDomovni></soi:CislaDomovni>
  <soi:CastObce><coi:Kod>1</coi:Kod></soi:CastObce><soi:TypStavebnihoObjektuKod>1</soi:TypStavebnihoObjektuKod>
  <soi:Geometrie><soi:DefinicniBod><gml:Point gml:id="P.1"><gml:pos>11 12</gml:pos></gml:Point></soi:DefinicniBod></soi:Geometrie></vf:StavebniObjekt></vf:StavebniObjekty>
 <vf:AdresniMista><vf:AdresniMisto gml:id="AD.200"><ami:Kod>200</ami:Kod><ami:CisloDomovni>206</ami:CisloDomovni><ami:CisloOrientacni>1</ami:CisloOrientacni>
  <ami:StavebniObjekt><soi:Kod>100</soi:Kod></ami:StavebniObjekt><ami:Ulice><uli:Kod>11</uli:Kod></ami:Ulice>
  <ami:Geometrie><ami:DefinicniBod><gml:Point gml:id="P.2"><gml:pos>13 14</gml:pos></gml:Point></ami:DefinicniBod></ami:Geometrie></vf:AdresniMisto></vf:AdresniMista>
</vf:Data></vf:VymennyFormat>""".encode("utf-8")

WGS = lambda xy: [xy[0], xy[1]]


def test_rozlozeni_vfr():
    v = ruian.rozloz(io.BytesIO(VFR), WGS)
    assert v["obec"] == {"kod": "547336", "nazev": "Třeboň"}
    assert v["ulice"][0] == {"kod": "10", "nazev": "Budějovická", "linie": [[[1, 2], [3, 4], [5, 6]]]}
    assert v["budovy"] == [{"kod": "100", "typ_cisla": "1", "cisla": ["1"], "bod": [11, 12], "cast_obce": "Třeboň I"}]
    a = v["adresy"][0]
    assert a["ulice"] == "Chelčického" and a["cislo_domovni"] == "206" and a["cislo_orientacni"] == "1" and a["bod"] == [13, 14]


def test_kontrola_a_url():
    v = ruian.rozloz(io.BytesIO(VFR), WGS)
    chyby = ruian.zkontroluj(v)
    assert any("ulic" in c for c in chyby) and any("bod mimo" in c for c in chyby)
    assert ruian.url(date(2026, 10, 31)).endswith("/soucasna/20261031_OB_547336_UKSH.xml.zip")
    assert ruian.kandidati_dnu(date(2026, 11, 21)) == [date(2026, 10, 31), date(2026, 9, 30)]


def test_prevod_sjtsk_na_wgs84():
    lon, lat = ruian._prevod()((-743000, -1174000))
    assert 14.6 < lon < 14.9 and 48.9 < lat < 49.1


def _koren(tmp_path):
    v = ruian.rozloz(io.BytesIO(VFR), WGS)
    # body do okolí Třeboně, aby prošla kontrola ručního bodu
    (tmp_path / "raw/ruian").mkdir(parents=True)
    for n in ("ulice", "budovy", "adresy"):
        (tmp_path / f"raw/ruian/{n}.json").write_text(json.dumps(v[n], ensure_ascii=False), encoding="utf-8")
    (tmp_path / "data/projekty").mkdir(parents=True)
    return tmp_path


def test_misto_z_nazvu(tmp_path):
    r = mapa.Ruian(_koren(tmp_path))
    assert [c["nazev"] for c in mapa.z_nazvu("Stavební úpravy MK v ul. Budějovické v Třeboni", r)] == ["Budějovická"]
    assert mapa.z_nazvu("Chodník v Budějovické ulici", r)[0]["druh"] == "ulice"
    kotle = mapa.z_nazvu("Výměna kotlů v objektu DPS IA, Chelčického 1, Třeboň", r)
    assert [(c["druh"], c["nazev"]) for c in kotle] == [("adresa", "Chelčického 1")]
    radnice = mapa.z_nazvu("Oprava staré radnice č.p. 1/I – V. etapa", r)
    assert radnice[0]["druh"] == "budova" and radnice[0]["bod"] == [11, 12] and radnice[0]["jistota"] == "nase_propojeni"
    assert mapa.z_nazvu("Sportovní hala – ubytování", r) == []


def test_rucni_misto_a_vystup(tmp_path):
    koren = _koren(tmp_path)
    (koren / "data/projekty/a.yaml").write_text(
        "id: a\nmisto:\n  - ulice: Budějovická\n  - bod: [49.0035, 14.7706]\n    popis: Parkoviště\n", encoding="utf-8")
    (koren / "data/projekty/b.yaml").write_text("id: b\nmisto:\n  - ulice: Neexistující\n", encoding="utf-8")
    karty = [{"id": "a", "nazev": "A", "faze": "probiha"}, {"id": "b", "nazev": "B"},
             {"id": "c", "nazev": "Stavební úpravy MK v ul. Budějovické"}]
    zasobnik = [{"typ": "namet", "id": "sprm-5", "nazev": "Kompostárna", "osa": "Životní prostředí"}]
    vys, chyby, _ = mapa.sestav(koren, karty, zasobnik, [], {5: {"geometrie": {"type": "Point", "coordinates": [14.75, 49.01]}}})
    po = {m["id"]: m for m in vys}
    assert po["a"]["geometrie"]["type"] == "GeometryCollection"
    assert po["a"]["geometrie"]["geometries"][1] == {"type": "Point", "coordinates": [14.7706, 49.0035]}
    assert po["c"]["geometrie"] == {"type": "MultiLineString", "coordinates": [[[1, 2], [3, 4], [5, 6]]]}
    assert po["sprm-5"]["geometrie"] == {"type": "Point", "coordinates": [14.75, 49.01]}
    assert chyby == ["mapa b: ulice 'Neexistující' v RÚIAN není"]


def test_bez_ruian_jen_upozorneni(tmp_path):
    (tmp_path / "data/projekty").mkdir(parents=True)
    (tmp_path / "data/projekty/a.yaml").write_text("id: a\nmisto:\n  - ulice: Valy\n", encoding="utf-8")
    vys, chyby, upozorneni = mapa.sestav(tmp_path, [{"id": "a", "nazev": "A"}], [], [], {})
    assert chyby == [] and vys[0]["geometrie"] is None and any("RÚIAN" in u for u in upozorneni)
