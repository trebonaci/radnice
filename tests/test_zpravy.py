"""Zprávy pro „Co se děje“ (#243): pipeline/zpravy.py."""
from pathlib import Path

from pipeline import okruhy as modul_okruhy
from pipeline import zpravy

CFG = modul_okruhy.nacti(Path(__file__).resolve().parent.parent)
J = {"id": "rm-2026-j1", "datum": "2026-11-04", "organ": "rada",
     "dokument": {"url": "https://example.cz/zapis.pdf"}}


def usn(i, tema, **kw):
    return {"id": f"rm-2026-j1-u{i}", "cislo": f"RM {i}/2026-1", "jednani_id": "rm-2026-j1", "tema": tema,
            "text": kw.pop("text", ""), "shrnuti": f"Rada schválila: {tema}.", "shrnuti_ai": True,
            "vysledek_hlasovani": kw.pop("vysledek", "prijato"), "okruh": kw.pop("okruh", "rozvoj_sprava"),
            "citace": {"strany": [3]}, **kw}


def smlouva(i, predmet, hodnota=None, **kw):
    return {"id": f"rs-{i}", "predmet": predmet, "datum_uzavreni": kw.pop("datum", "2026-11-10"),
            "url": f"https://smlouvy.gov.cz/smlouva/{i}", "cislo_smlouvy": kw.pop("cislo", f"750/{i}/26"),
            "strany": kw.pop("strany", [{"nazev": "Stavby a.s.", "fyzicka_osoba": False, "prijemce": True}]),
            "castky": [] if hodnota is None else [{"hodnota": hodnota, "mena": "CZK", "s_dph": True, "druh": "smluvni"}],
            "navazuje_na": kw.pop("navazuje_na", None), "cena_neuvedena": hodnota is None}


def sestav(**v):
    v.setdefault("jednani", [J])
    return zpravy.sestav(v, CFG)


def podle_id(z, id_):
    return next(x for x in z if x["id"] == id_)


def test_usneseni_bez_proceduralnich_a_neschvalene_ma_stitek():
    z = sestav(usneseni=[usn(1, "Program jednání rady"), usn(2, "Zájem o pozemek", vysledek="neprijato"),
                         usn(3, "Najem klubovny")])
    assert {x["id"] for x in z} == {"zprava-rm-2026-j1-u2", "zprava-rm-2026-j1-u3"}
    u = podle_id(z, "zprava-rm-2026-j1-u2")
    assert u["druh"] == "usneseni" and u["stitek"] == "Neschváleno" and u["datum"] == "2026-11-04"
    assert u["zdroje"][0]["url"] == "https://example.cz/zapis.pdf#page=3" and u["shrnuti_ai"] is True


def test_zmena_nahrazuje_usneseni():
    zmena = {"id": "zmena-rm-2026-j1-u3", "text": "Klubovna zůstává seniorům.", "kdo": "Klubovna", "okruh": "bydleni_pece",
             "datum": "2026-11-04", "organ": "rada", "usneseni_id": "rm-2026-j1-u3", "usneseni_cislo": "RM 3/2026-1",
             "url": "https://example.cz/zapis.pdf#page=3", "plati_od": "2027-01-01"}
    z = sestav(usneseni=[usn(3, "Klubovna")], zmeny=[zmena])
    assert [(x["druh"], x["okruh"]) for x in z] == [("zmena", "bydleni_pece")]
    assert z[0]["plati_od"] == "2027-01-01"


def test_rozpoctove_opatreni_opisuje_castku_a_nahrazuje_usneseni():
    ro = [{"usneseni_id": "rm-2026-j1-u9", "smer": "z", "nazev": "Nájemné", "zmena": -30000.0,
           "castka": {"hodnota": 30000.0, "s_dph": None, "druh": "rozpoctove_opatreni"}},
          {"usneseni_id": "rm-2026-j1-u9", "smer": "do", "nazev": "Cestovné", "zmena": 30000.0,
           "castka": {"hodnota": 30000.0, "s_dph": None, "druh": "rozpoctove_opatreni"}}]
    z = sestav(usneseni=[usn(9, "Rozpočtové opatření č. 61 – cestovné")], rozpoctova_opatreni=ro)
    assert len(z) == 1 and z[0]["druh"] == "rozpoctove_opatreni"
    assert z[0]["castka"] == {"hodnota": 30000.0, "druh": "rozpoctove_opatreni", "s_dph": None}
    assert "30 000 Kč" in z[0]["shrnuti"]


def test_prah_smlouvy_a_vyjimka_pro_kartu():
    sm = [smlouva(1, "Nájem kopírky", 499_999), smlouva(2, "Oprava střechy", 500_000),
          smlouva(3, "Drobná oprava", 1000), smlouva(4, "Bez ceny")]
    karta = {"id": "hriste", "nazev": "Hřiště", "okruh": "sport_kultura", "smlouvy": [{"id": "rs-3"}]}
    z = sestav(smlouvy=sm, projekty=[karta])
    assert {x["id"] for x in z} == {"zprava-rs-2", "zprava-rs-3"}
    v = podle_id(z, "zprava-rs-3")
    assert v["projekt_id"] == "hriste" and v["okruh"] == "sport_kultura" and v["jistota"] == "naše propojení"
    assert podle_id(z, "zprava-rs-2")["castka"] == {"hodnota": 500_000, "druh": "smluvni", "s_dph": True}


def test_okruh_smlouvy_bez_karty_podle_vzoru():
    z = sestav(smlouvy=[smlouva(1, "Rekonstrukce ZŠ Sokolská", 900_000), smlouva(2, "Nákup nábytku", 900_000)])
    assert podle_id(z, "zprava-rs-1")["okruh"] == "skoly"
    assert podle_id(z, "zprava-rs-2")["okruh"] == "rozvoj_sprava"


def test_dodatek_a_usneseni_je_jedna_zprava():
    text = "schvaluje uzavření Dodatku č. 2 ke smlouvě o dílo č. 750/9665/26, kterým se mění termín."
    d = smlouva(5, "Osvětlení - dodatek č. 2", 600_000, cislo="750/9665/26/2", navazuje_na="1")
    z = sestav(usneseni=[usn(7, "Osvětlení – dodatek č. 2", text=text)], smlouvy=[d])
    assert len(z) == 1 and z[0]["druh"] == "dodatek" and z[0]["castka"]["druh"] == "dodatek"
    assert [s["url"] for s in z[0]["zdroje"]] == ["https://smlouvy.gov.cz/smlouva/5", "https://example.cz/zapis.pdf#page=3"]
    assert z[0]["jistota"] == "doloženo"


def test_dodatek_pod_prahem_bez_karty_se_nevypisuje_ale_usneseni_zustane():
    text = "schvaluje uzavření Dodatku č. 1 ke smlouvě o dílo č. 750/1/26, ..."
    d = smlouva(5, "Drobnost - dodatek č. 1", 1000, cislo="750/1/26/1", navazuje_na="1")
    z = sestav(usneseni=[usn(7, "Drobnost – dodatek č. 1", text=text)], smlouvy=[d])
    assert [x["druh"] for x in z] == ["usneseni"]


def test_fyzicka_osoba_v_dodavateli_bez_jmena_v_textu():
    fo = [{"nazev": "fyzická osoba", "fyzicka_osoba": True, "prijemce": True, "jmeno_podnikatele": "Ing. Jan Novák"}]
    z = sestav(smlouvy=[smlouva(1, "Projekt stezky", 900_000, strany=fo)])
    assert "Novák" not in z[0]["shrnuti"] and z[0]["jmeno_podnikatele"] == "Ing. Jan Novák"


def test_vyberove_rizeni_udalosti_a_skupina_v_jeden_den():
    zak = {"id": "ezak-VZ-1", "nazev": "Oprava ulice Valy", "url": "https://zakazky.example/1", "rezim": "Podlimitní",
           "datum_zahajeni": "2026-10-01",
           "casti": [{"nazev": "Oprava ulice Valy", "datum_uzavreni_smlouvy": "2026-11-10", "datum_zruseni": None,
                      "vitezove": [{"nazev": "Stavby a.s.", "fyzicka_osoba": False, "smlouva_uzavrena": True,
                                    "castky": [{"hodnota": 1_200_000.0, "mena": "CZK", "s_dph": True, "druh": "smluvni"}]}]}]}
    karta = {"id": "valy", "nazev": "Valy", "okruh": "doprava_prostor", "zakazky": [{"id": "ezak-VZ-1"}],
             "smlouvy": [{"id": "rs-1"}]}
    z = sestav(zakazky=[zak], smlouvy=[smlouva(1, "Oprava ulice Valy", 1_200_000)], projekty=[karta])
    assert sorted(x["id"] for x in z if x["druh"] == "vyberove_rizeni") == [
        "zprava-ezak-VZ-1-vyber-2026-11-10", "zprava-ezak-VZ-1-vyhlaseni-2026-10-01"]
    vyber = podle_id(z, "zprava-ezak-VZ-1-vyber-2026-11-10")
    assert vyber["castka"]["hodnota"] == 1_200_000.0 and vyber["okruh"] == "doprava_prostor"
    # smlouva a výběr dodavatele ve stejný den ke stejné kartě = společná skupina; vyhlášení má svůj den
    assert vyber["skupina"] == {"id": "valy:2026-11-10", "nazev": "Valy", "pocet": 2}
    assert podle_id(z, "zprava-rs-1")["skupina"]["id"] == "valy:2026-11-10"
    assert "skupina" not in podle_id(z, "zprava-ezak-VZ-1-vyhlaseni-2026-10-01")


def test_razeni_nejnovejsi_nahore():
    z = sestav(smlouvy=[smlouva(1, "A", 900_000, datum="2026-10-01"), smlouva(2, "B", 900_000, datum="2026-11-01")])
    assert [x["id"] for x in z] == ["zprava-rs-2", "zprava-rs-1"]
