"""Pracovní zásobník projektů (#172): pipeline/zasobnik.py."""
import json

import yaml

from pipeline import zasobnik


def test_priprava_a_dum_s_pecovatelskou_sluzbou():
    assert zasobnik.je_priprava("Parkoviště v Jateční ulici v Třeboni (PD)")
    assert zasobnik.je_priprava("Zpracování studie podchodu pod silnicí I/34")
    assert zasobnik.je_priprava("Vypracování DPS, IS, výkazu výměr na stavbu Oprava hřbitovní zdi")
    assert zasobnik.je_priprava("Zpracování drojektové dokumentace - Páteřní dešťová kanalizace")
    assert not zasobnik.je_priprava("Havarijní oprava zařizovacích předmětů v koupelně bytu č. 7 DPS 1")
    assert not zasobnik.je_priprava("Snížení energetické náročnosti objektu DPS III")
    assert not zasobnik.je_priprava("Stavební úpravy MK v ulici Dvorecké")


def test_stupen_pripravenosti():
    assert zasobnik.stupen("Zpracování studie podchodu") == "studie"
    assert zasobnik.stupen("Parkovací dům Třeboň (PD)") == "projekt"
    assert zasobnik.stupen("Zpracování PD ... zajištění povolení stavby") == "projekt_povoleni"
    assert zasobnik.stupen("Volnočasové sportoviště ve SA Hliník - DSP/DPS a výkaz výměr") == "projekt_provadeci"


def test_faze_podle_stavby_po_priprave():
    pd = [{"datum": "2024-01-04", "text": "Ulice X (PD)"}]
    hotova = [{"datum": "2024-11-29", "stav": "ukončeno plnění"}]
    assert zasobnik._faze(pd, hotova) == "realizovano"
    assert zasobnik._faze(pd, [{"datum": "2024-11-29", "stav": "zadávání"}]) == "stavba"
    # stavba před novou přípravou (jiná, dřívější akce) zásobník neruší
    assert zasobnik._faze([{"datum": "2026-03-30", "text": "Jiráskova (PD)"}], hotova) == "zasobnik"
    # dodatek k PD po stavbě není nová příprava
    assert zasobnik._faze([{"datum": "2025-05-28", "text": "PD Holičky - dodatek č. 1"}],
                          [{"datum": "2023-06-28", "stav": "ukončeno plnění"}]) == "realizovano"


def test_kontrola_realneho_napadu():
    chyby = zasobnik.zkontroluj([{"id": "a", "nazev": "A", "oblast": "doprava"},
                                 {"id": "b", "nazev": "B", "oblast": "doprava", "zdroj": {"url": "https://x"}},
                                 {"id": "b", "nazev": "B2", "oblast": "vesmir", "vazby": {"hledat": ["("]},
                                  "odhad": {"hodnota": 5}}], {})
    assert any("a" in c and "zdroj" in c for c in chyby)
    assert any("duplicitní" in c for c in chyby)
    assert any("neznámá oblast" in c for c in chyby)
    assert any("chybný vzor" in c for c in chyby)
    assert any("odhad" in c for c in chyby)
    assert not any("'b'" in c and "zdroj" in c for c in chyby)


def test_sestaveni(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "raw/sprm").mkdir(parents=True)
    (tmp_path / "config/subjekty.yaml").write_text('- ico: "00247618"\n  nazev: Město Třeboň\n', encoding="utf-8")
    (tmp_path / "raw/sprm/projekty.json").write_text(json.dumps([
        {"id": 1, "aktivita": "Parkovací domy", "osa_nazev": "Doprava", "opatreni": "1", "stav": "Plánováno"},
        {"id": 2, "aktivita": "Hotová věc", "osa_nazev": "Doprava", "opatreni": "1", "stav": "Hotovo"},
        {"id": 3, "aktivita": "Kruhové objezdy", "osa_nazev": "Doprava", "opatreni": "1", "stav": "Plánováno"}]),
        encoding="utf-8")
    (tmp_path / "data/zasobnik.yaml").write_text(yaml.safe_dump({"polozky": [
        {"id": "parkovaci-dum", "nazev": "Parkovací dům", "oblast": "doprava", "sprm": [1],
         "vazby": {"hledat": ["[Pp]arkovací\\w* dům", "parkovacího domu"]}},
        {"id": "napad", "nazev": "Lávka", "oblast": "doprava", "zdroj": {"url": "https://example.cz/zapis.pdf"},
         "odhad": {"hodnota": 2_000_000, "s_dph": True, "url": "https://example.cz/zapis.pdf", "citace": "2 mil."}}]},
        allow_unicode=True), encoding="utf-8")
    data = {
        "zakazky": [{"id": "z1", "nazev": "Parkovací dům Třeboň (PD)", "datum_zahajeni": "2024-01-04",
                     "subjekt_ico": "00247618", "url": "u1", "stav": "dokončen", "casti": [{"vitezove": [{"nazev": "P s.r.o."}]}]},
                    {"id": "z2", "nazev": "Chodník X (PD)", "datum_zahajeni": "2025-01-01", "subjekt_ico": "00247618", "stav": "dokončen", "casti": [{"vitezove": [{"nazev": "P s.r.o."}]}]},
                    {"id": "z3", "nazev": "Ulice Y (PD)", "datum_zahajeni": "2025-02-01", "subjekt_ico": "00247618", "stav": "dokončen", "casti": [{"vitezove": [{"nazev": "P s.r.o."}]}]}],
        "smlouvy": [{"id": "s1", "predmet": "Úprava projektové dokumentace parkovacího domu v Třeboni.",
                     "datum_uzavreni": "2026-04-24", "subjekt_ico": "00247618"}],
    }
    karty = [{"id": "k", "zakazky": [{"id": "z3"}], "smlouvy": [], "sprm": []}]
    vysledek, chyby = zasobnik.sestav(tmp_path, data, karty)
    assert chyby == []
    po_id = {z["id"]: z for z in vysledek}
    pd = po_id["parkovaci-dum"]
    assert [d["id"] for d in pd["doklady"]] == ["z1", "s1"]
    assert pd["pripravenost"]["stupen"] == "projekt" and pd["pripravenost"]["doklad"]["id"] == "s1"
    assert pd["nositele"] == [{"ico": "00247618", "nazev": "Město Třeboň"}]
    assert pd["sprm"][0]["id"] == 1 and pd["sprm"][0]["sprm_ai"] is False and pd["faze"] == "zasobnik"
    napad = po_id["napad"]
    assert napad["pripravenost"]["stupen"] == "zamer" and napad["pripravenost"]["jistota"] == "dolozeno"
    assert napad["odhad"]["druh"] == "odhad" and napad["odhad"]["s_dph"] is True
    # kandidát = příprava mimo karty i položky; z3 je v kartě
    assert [z["doklad"]["id"] for z in vysledek if z["typ"] == "kandidat"] == ["z2"]
    # námět = plánovaná aktivita bez karty a bez položky
    assert [z["id"] for z in vysledek if z["typ"] == "namet"] == ["sprm-3"]


def test_dum_s_pecovatelskou_sluzbou_neni_provadeci_projekt():
    assert zasobnik.stupen("PD rekonstrukce kotelen a výměny plynových kotlů v objektech DPS IA a DPS IC") == "projekt"
    assert zasobnik.stupen("Hřiště Hliník - DSP/DPS a výkaz výměr") == "projekt_provadeci"


def test_zakazka_doklada_zadani_jen_s_vitezem():
    vitez = [{"vitezove": [{"nazev": "Projektant s.r.o."}]}]
    assert zasobnik._zadano({"stav": "dokončen", "casti": vitez})
    assert not zasobnik._zadano({"stav": "zrušen", "casti": vitez})
    assert not zasobnik._zadano({"stav": "zahájen", "casti": [{"vitezove": []}]})
    data = {"zakazky": [{"id": "z1", "nazev": "Ulice X (PD)", "stav": "zrušen", "casti": []}], "smlouvy": []}
    assert zasobnik._doklady(data) == []


def test_beh_kopiruje_zasobnik_do_stagingu():
    from pipeline import beh
    assert "data/zasobnik.yaml" in beh.RUCNI_SOUBORY and "zasobnik" in beh.VYSTUPY
    assert not [c for c in beh.kontrola_poklesu({"zasobnik": []}, beh.KOREN) if "zasobnik" in c]
