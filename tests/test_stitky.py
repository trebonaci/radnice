from pathlib import Path

import pytest
import yaml

from pipeline.stitky import ai_stitky, nacti_ciselnik, pravidlove_stitky, zkontroluj_ciselnik

KOREN = Path(__file__).resolve().parent.parent
CFG = nacti_ciselnik(KOREN)
CIT = {"dokument_id": "zapis-x", "strany": [1], "text": "citace usnesení"}


def kody(zaznamy):
    return {(z["stitek"], z["zdroj"]) for z in zaznamy}


def test_ciselnik_je_konzistentni():
    kategorie = yaml.safe_load((KOREN / "config" / "kategorie.yaml").read_text(encoding="utf-8"))
    assert zkontroluj_ciselnik(CFG, kategorie) == []


def test_klicove_slovo_ma_citaci_ze_textu():
    text = "schvaluje pronájem sportovní haly"
    z = pravidlove_stitky(CFG, text, [], CIT)
    assert kody(z) == {("sport", "txt-sport")}
    assert z[0]["citace"]["text"] in text and z[0]["stitek_ai"] is False


def test_kategorie_je_oznacena_jako_ai():
    z = pravidlove_stitky(CFG, "text bez klíčových slov", ["sport"], CIT)
    assert kody(z) == {("sport", "kat-sport")}
    assert z[0]["stitek_ai"] is True and z[0]["citace"] == CIT


def test_nazev_odboru_neni_socialni_sluzba():
    assert pravidlove_stitky(CFG, "odboru školství a sociálních věcí zajistit výpis", [], CIT) == []


def test_faze_investice():
    # budoucí kolaudace dokončení nedokládá (Codex P1, #37) → fáze nevíme
    z = pravidlove_stitky(CFG, "schvaluje rekonstrukci a následnou kolaudaci", [], CIT)
    assert {(s["stitek"], s["faze"]) for s in z} == {("investice", None)}
    z = pravidlove_stitky(CFG, "rekonstrukce dokončena, byl vydán kolaudační souhlas", [], CIT)
    assert {(s["stitek"], s["faze"]) for s in z} == {("investice", None), ("investice", "dokoncena")}


def test_ai_stitek_vyzaduje_doslovnou_citaci():
    chyby = []
    text = "schvaluje opravu střechy kulturního domu"
    ok = ai_stitky(CFG, [{"stitek": "kultura", "duvod": "kulturní dům", "citace": "střechy  kulturního\ndomu"}],
                   text, CIT, [], "t", chyby)
    assert chyby == [] and ok[0]["stitek_ai"] is True and ok[0]["zdroj"] == "ai"
    ai_stitky(CFG, [{"stitek": "kultura", "duvod": "x", "citace": "nic takového"}], text, CIT, [], "t", chyby)
    assert any("nenalezena" in c for c in chyby)


@pytest.mark.parametrize("navrh", [
    {"stitek": "neexistuje", "duvod": "x", "citace": "opravu"},
    {"stitek": "kultura", "duvod": "", "citace": "opravu"},
    {"stitek": "sport", "duvod": "x", "citace": "opravu", "faze": "dokoncena"},
])
def test_ai_stitek_spatny_vstup(navrh):
    chyby = []
    assert ai_stitky(CFG, [navrh], "schvaluje opravu", CIT, [], "t", chyby) == []
    assert chyby


def test_ai_stitek_bez_anonymizovaneho_udaje():
    chyby = []
    assert ai_stitky(CFG, [{"stitek": "komunity_spolky", "duvod": "x", "citace": "Jan Novák"}],
                     "spolek Jan Novák", CIT, ["Jan Novák"], "t", chyby) == []
    assert chyby


def test_stitek_u_usneseni_jen_jednou():
    from pipeline.stitky import jeden_na_stitek
    z = [{"stitek": "sport", "stitek_ai": True, "faze": None, "zdroj": "kat-sport"},
         {"stitek": "sport", "stitek_ai": False, "faze": None, "zdroj": "txt-sport"},
         {"stitek": "investice", "stitek_ai": False, "faze": None, "zdroj": "txt-investice"},
         {"stitek": "investice", "stitek_ai": False, "faze": "planovana", "zdroj": "faze-planovana"}]
    assert [(x["stitek"], x["zdroj"]) for x in jeden_na_stitek(z)] == [("sport", "txt-sport"), ("investice", "faze-planovana")]


def test_komunity_a_spolky_jeden_stitek():
    assert "komunity_spolky" in CFG["stitky"] and "komunity" not in CFG["stitky"] and "spolky" not in CFG["stitky"]


@pytest.mark.parametrize("text", [
    "změna (prodloužení) termínu dokončení díla o 7 kalendářních dnů",
    "-před kolaudací stavby bude uzavřena dohoda vlastníků",
    "kolaudační souhlas bude vydán po dokončení",
])
def test_dokoncena_jen_pri_dolozeni(text):
    """Posun termínu dokončení ani podmínka před kolaudací nejsou dokončení (Codex P1, #37)."""
    c = {"dokument_id": "d", "strany": [1], "text": ""}
    assert not [s for s in pravidlove_stitky(CFG, text, [], c) if s.get("faze") == "dokoncena"]


def test_dokoncena_pri_vydanem_kolaudacnim_souhlasu():
    c = {"dokument_id": "d", "strany": [1], "text": ""}
    assert [s["faze"] for s in pravidlove_stitky(CFG, "byl vydán kolaudační souhlas se stavbou", [], c) if s.get("faze")] == ["dokoncena"]


def test_ai_stitek_s_anonymizovanym_udajem_jinak_zalomenym():
    """Chráněný údaj s jinými mezerami nebo zlomem řádku se nesmí dostat do štítku (Codex P1, #37)."""
    chyby = []
    text = "nájemce Svobody č. p. 272,\nTřeboň"
    c = {"dokument_id": "d", "strany": [1], "text": ""}
    v = ai_stitky(CFG, [{"stitek": "komunity_spolky", "duvod": "x", "citace": "Svobody č. p. 272,\nTřeboň"}],
                  text, c, ["Svobody č. p. 272, Třeboň"], "k", chyby)
    assert v == [] and chyby
