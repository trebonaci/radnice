"""Datový přehled (#177): pipeline/ukazatele.py – počty a součty počítá kód."""
import pytest

from pipeline import ukazatele

SUBJ = {"00247618": "Město Třeboň", "25179896": "Slatinné lázně Třeboň s.r.o."}


def test_jednani_a_usneseni():
    j = [{"id": "rm-1", "organ": "rada", "datum": "2026-09-09"}, {"id": "rm-2", "organ": "rada", "datum": "2026-09-23"},
         {"id": "zm-1", "organ": "zastupitelstvo", "datum": "2026-09-21"}]
    u = ukazatele.jednani(j)
    assert u["hodnota"] == [{"klic": "rada", "nazev": "Rada města", "hodnota": 2},
                            {"klic": "zastupitelstvo", "nazev": "Zastupitelstvo", "hodnota": 1}]
    assert u["obdobi"] == {"od": "2026-09-09", "do": "2026-09-23"}
    us = [{"jednani_id": "rm-1", "kategorie": ["sport", "investice"], "vysledek_hlasovani": "prijato"},
          {"jednani_id": "rm-2", "kategorie": ["sport", "sport"], "vysledek_hlasovani": "neprijato"},
          {"jednani_id": "zm-1", "kategorie": [], "vysledek_hlasovani": "prijato"}]
    o = ukazatele.usneseni_oblasti(us, j)
    assert [(r["klic"], r["hodnota"]) for r in o["hodnota"]] == [("sport", 2), ("investice", 1), ("ostatni", 1)]
    assert o["celkem"] == 3 and o["neprijato"] == 1


def test_smlouvy_verze_jednou_a_u_obou_organizaci():
    s = [{"id_smlouvy": "1", "subjekt_ico": "00247618", "strany": [{"ico": "25179896"}], "datum_zverejneni": "2025-01-02"},
         {"id_smlouvy": "1", "subjekt_ico": "00247618", "strany": [], "datum_zverejneni": "2025-02-02"},
         {"id_smlouvy": "2", "subjekt_ico": "99999999", "strany": [{"ico": "00247618"}], "datum_zverejneni": "2026-03-01"},
         {"id_smlouvy": "3", "subjekt_ico": "00247618", "strany": [], "datum_zverejneni": "2024-01-15"}]
    u = ukazatele.smlouvy(s, SUBJ)
    po = {r["klic"]: r for r in u["hodnota"]}
    assert po["00247618"]["hodnota"] == 2 and po["00247618"]["podle_let"] == {"2025": 1, "2026": 1}
    assert po["25179896"]["hodnota"] == 1
    assert u["celkem"] == 2 and u["obdobi"] == {"od": "2024-03-01", "do": "2026-03-01"}


def test_dotace_jen_jeden_druh():
    d = [{"oblast": "tělovýchovy a sportu", "datum": "2026-10-30", "castka": {"hodnota": 20000.0, "druh": "dotace_priznana"}},
         {"oblast": "tělovýchovy a sportu", "datum": "2026-10-30", "castka": {"hodnota": 5000.5, "druh": "dotace_priznana"}},
         {"oblast": "kultury", "datum": "2026-10-30", "castka": {"hodnota": 30000.0, "druh": "dotace_priznana"}}]
    u = ukazatele.dotace(d)
    assert u["hodnota"] == [{"klic": "kultury", "nazev": "Kultura", "pocet": 1, "hodnota": 30000.0},
                            {"klic": "tělovýchovy a sportu", "nazev": "Sport a tělovýchova", "pocet": 2, "hodnota": 25000.5}]
    assert u["druh"] == "dotace_priznana"
    d[0]["castka"]["druh"] = "zaplaceno"
    with pytest.raises(ValueError):
        ukazatele.dotace(d)


def test_zakazky_a_projekty():
    z = [{"subjekt_ico": "00247618", "datum_zahajeni": "2025-01-01", "stav": "dokončen"},
         {"subjekt_ico": "00247618", "datum_zahajeni": None, "stav": None}]
    u = ukazatele.zakazky(z, SUBJ)
    assert u["hodnota"][0]["podle_let"] == {"2025": 1, "neuvedeno": 1}
    assert u["hodnota"][0]["podle_stavu"] == {"dokončen": 1, "neuvedeno": 1}
    p = ukazatele.projekty([{"faze": "probiha"}, {"faze": "probiha"}, {"faze": "dokonceno"}],
                           [{"typ": "polozka", "faze": "zasobnik"}, {"typ": "polozka", "faze": "realizovano"}, {"typ": "namet"}])
    assert p["hodnota"] == [{"klic": "probiha", "nazev": "Stavba probíhá", "hodnota": 2},
                            {"klic": "dokonceno", "nazev": "Dokončeno", "hodnota": 1}]
    assert p["zasobnik"] == 1 and p["namety"] == 1


def test_investice_bez_rezervy():
    i = [{"rok": 2026, "schvaleny": 130.0, "bez_rezervy_po_zmenach": 110.0, "fondy_poznamka": None,
          "oblasti": [{"oblast": "Sport", "schvaleny": 100.0, "po_zmenach": 110.0},
                      {"oblast": "Rezerva", "schvaleny": 30.0, "po_zmenach": 5.0}]}]
    u = ukazatele.investice(i)
    assert [r["klic"] for r in u["hodnota"]] == ["Sport"]
    assert u["schvaleny"] == 100.0 and u["po_zmenach"] == 110.0
