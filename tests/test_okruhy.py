"""Šest okruhů webu (audit 23. 11. 2026): config/okruhy.yaml a pipeline/okruhy.py."""
import json
import re
from pathlib import Path

import yaml

from pipeline import okruhy

KOREN = Path(__file__).resolve().parents[1]
CFG = okruhy.nacti(KOREN)
KATEGORIE = yaml.safe_load((KOREN / "config" / "kategorie.yaml").read_text(encoding="utf-8"))


def test_ciselnik_je_v_poradku():
    assert okruhy.zkontroluj(CFG, KATEGORIE) == []
    assert [o["nazev"] for o in CFG["okruhy"]] == [
        "Doprava a veřejný prostor", "Bydlení a péče", "Školy a školky", "Sport, kultura a spolky",
        "Městské společnosti", "Rozvoj a správa města"]
    # každé ze 16 témat právě v jednom okruhu
    vsechna = [t for o in CFG["okruhy"] for t in o["temata"]]
    assert sorted(vsechna) == sorted(CFG["temata"]) and len(vsechna) == 16


def test_kontrola_najde_chyby():
    spatne = okruhy.nacti(KOREN)
    spatne["okruhy"][0]["temata"].append("sport")
    spatne["okruhy"][1]["temata"].remove("bydleni")
    chyby = okruhy.zkontroluj(spatne, {**KATEGORIE, "nova": "x"})
    assert any("'sport' je v okruzích" in c for c in chyby)
    assert any("'bydleni' nemá okruh" in c for c in chyby)
    assert any("'nova' nemá téma" in c for c in chyby)


def test_web_ma_stejna_temata_jako_ciselnik():
    html = (KOREN / "web" / "site" / "sablona.html").read_text(encoding="utf-8")
    oblast = dict(re.findall(r'(\w+):"([^"]+)"', re.search(r"const OBLAST=\{(.*?)\};", html).group(1)))
    assert oblast == CFG["temata"]
    usn = dict(re.findall(r'(\w+):"(\w+)"', re.search(r"const USN_TEMA=\{(.*?)\};", html).group(1)))
    for k in KATEGORIE:   # temaU v šabloně: USN_TEMA[k] || (OBLAST[k] ? k : "jine")
        assert (usn.get(k) or (k if k in oblast else "jine")) == okruhy.tema_kategorie(CFG, k), k


def test_polozka_podle_tematu_osy_a_nazvu():
    assert okruhy.pro_polozku(CFG, {"oblast": "zelen"}) == ("doprava_prostor", "téma")
    assert okruhy.pro_polozku(CFG, {"osa": "Sociální oblast", "opatreni": "3. Mateřské školy"}) == ("skoly", "osa SPRM")
    assert okruhy.pro_polozku(CFG, {"osa": "Sociální oblast", "opatreni": "1. Sociální služby"}) == ("bydleni_pece", "osa SPRM")
    assert okruhy.pro_polozku(CFG, {"nazev": "Zpracování PD Novostavba městského bytového domu v ulici Lázeňská"}) \
        == ("bydleni_pece", "název")
    assert okruhy.pro_polozku(CFG, {"nazev": "Parkoviště pro potřeby lázní v Lázeňské ulici"})[0] == "doprava_prostor"
    # „DPS“ bez čísla = dokumentace pro provedení stavby, ne dům s pečovatelskou službou
    assert okruhy.pro_polozku(CFG, {"nazev": "Vypracování DPS, IS a rozpočtu na stavbu Oprava fasády čp. 1/I"}) \
        == ("rozvoj_sprava", "bez tématu")
    assert okruhy.pro_polozku(CFG, {"nazev": "Kotle v objektu DPS IA a DPS IC"})[0] == "bydleni_pece"
    # adresa v ulici okruh neurčuje
    assert okruhy.pro_polozku(CFG, {"nazev": "Pronájem části pozemku u Husovy ulice"})[0] == "rozvoj_sprava"
    assert okruhy.pro_polozku(CFG, {"oblast": "tělovýchovy a sportu"}, "oblast") == ("sport_kultura", "název")


def test_usneseni_dostane_vecny_okruh():
    u = {"id": "u1", "tema": "Rozpočtové opatření č. 56 – sportovní hala", "kategorie": ["rozpocet", "investice"]}
    okruhy.pro_usneseni(CFG, u, {"u1": [("socialni", "karta dps3"), ("sport", "karta hala")]})
    assert u["okruhy"] == ["bydleni_pece", "sport_kultura", "rozvoj_sprava"]
    assert u["okruh"] == "sport_kultura"          # karta + vzor v názvu > jen karta
    assert u["okruhy_podle"]["rozvoj_sprava"] == ["kategorie rozpocet", "kategorie investice"]
    u = {"id": "u2", "tema": "Program jednání", "kategorie": ["samosprava"]}
    okruhy.pro_usneseni(CFG, u, {})
    assert u["okruhy"] == ["rozvoj_sprava"] and u["okruh"] == "rozvoj_sprava"
    u = {"id": "u3", "tema": "Rozdělení Změny č. 9 územního plánu", "kategorie": ["ostatni"]}
    okruhy.pro_usneseni(CFG, u, {})
    assert u["okruhy_podle"]["rozvoj_sprava"] == ["kategorie ostatni", "název (uzemni-plan)"]


def test_data_maji_okruh():
    platne = set(CFG["_poradi"])
    for nazev in ("projekty", "zasobnik", "zmeny", "mista", "harmonogram", "prehled", "mapa", "dotace", "usneseni"):
        for p in json.loads((KOREN / "data" / f"{nazev}.json").read_text(encoding="utf-8")):
            assert p["okruh"] in platne, (nazev, p.get("id"))
    usn = {u["id"]: u for u in json.loads((KOREN / "data" / "usneseni.json").read_text(encoding="utf-8"))}
    # hasiči v Branné nejsou sociální služby (oprava štítku 23. 11. 2026)
    assert usn["rm-2026-j113-u534"]["okruhy"] == ["rozvoj_sprava"]
