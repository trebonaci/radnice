"""Harmonogram investic a dlouhodobých projektů (#194): pipeline/harmonogram.py."""
from pipeline import harmonogram


def _karta(faze="probiha", udalosti=None):
    return {"id": "k", "nazev": "Karta", "oblast": "doprava", "faze": faze, "faze_jistota": "nase_propojeni",
            "dokonceni": None, "udalosti": udalosti or []}


UD = [
    {"datum": "2025-05-16", "typ": "smlouva", "role": "projekt", "url": "p"},
    {"datum": "2026-01-23", "typ": "soutez", "role": "stavba", "zdroj_id": "ezak-1", "zruseno": False, "url": "s"},
    {"datum": "2026-02-06", "typ": "smlouva", "role": "stavba", "url": "d"},
    {"datum": "2026-05-18", "typ": "dodatek", "role": "stavba", "kratce": "dodatek 1", "url": "x"},
]


def test_faze_karty_z_dokladu():
    r = harmonogram.karta(_karta(udalosti=UD), {"ezak-1": {"datum_zahajeni": "2026-01-09"}})
    assert [(u["faze"], u["od"], u["do"], u["otevreno"]) for u in r["useky"]] == [
        ("priprava", "2025-05-16", "2026-01-09", False),
        # zahájení zakázky v E-ZAK je dřív než dodatečně zveřejněné vyhlášení
        ("soutez", "2026-01-09", "2026-02-06", False),
        ("stavba", "2026-02-06", None, True)]
    assert [m["typ"] for m in r["milniky"]] == ["dodatek"]


def test_dokoncena_stavba_konci_poslednim_dokladem():
    r = harmonogram.karta(_karta("dokonceno", UD), {})
    st = r["useky"][-1]
    assert (st["do"], st["otevreno"], st["konec_jistota"]) == ("2026-05-18", False, "posledni_doklad")


def test_zrusena_soutez_je_milnik_a_soutez_po_smlouve_se_nepocita():
    ud = [{"datum": "2025-01-10", "typ": "soutez", "role": "stavba", "zruseno": True},
          {"datum": "2025-03-01", "typ": "smlouva", "role": "stavba"},
          {"datum": "2025-04-01", "typ": "soutez", "role": "stavba", "zruseno": False}]
    r = harmonogram.karta(_karta(udalosti=ud), {})
    assert [u["faze"] for u in r["useky"]] == ["stavba"]
    assert [m["typ"] for m in r["milniky"]] == ["soutez"]


def test_priprava_bez_stavby_je_otevrena():
    r = harmonogram.karta(_karta("pripravuje_se", [{"datum": "2026-03-01", "typ": "usneseni", "role": None}]), {})
    assert [(u["faze"], u["do"], u["otevreno"]) for u in r["useky"]] == [("priprava", None, True)]


def test_polozka_zasobniku():
    z = {"typ": "polozka", "id": "z", "nazev": "Z", "oblast": "sport", "faze": "zasobnik",
         "doklady": [{"datum": "2025-02-01", "typ": "smlouva", "text": "PD", "url": "u2"},
                     {"datum": "2024-11-12", "typ": "zakazka", "text": "PD", "url": "u1"}]}
    r = harmonogram.polozka_zasobniku(z)
    assert (r["useky"][0]["od"], r["useky"][0]["url"], len(r["milniky"])) == ("2024-11-12", "u1", 2)
    assert harmonogram.polozka_zasobniku(z | {"faze": "realizovano"}) is None
    assert harmonogram.polozka_zasobniku(z | {"doklady": []}) is None


def test_aktivita_z_usneseni():
    a = {"id": "up9", "nazev": "Změna č. 9 ÚP", "oblast": "uzemni_plan",
         "vazby": {"hledat": [r"Změn\w* č\. ?9[ab]? územního plánu"]}, "zacatek_pred_daty": True}
    assert harmonogram.zkontroluj([a]) == []
    usn = [{"id": "u1", "jednani_id": "j", "cislo": "ZM 86/2026-31", "vysledek_hlasovani": "prijato",
            "text": "I. schvaluje\nrozdělení Změny č. 9 územního plánu Třeboň", "shrnuti": "Rozdělení změny.",
            "shrnuti_ai": True, "citace": {"dokument_id": "d", "strany": [7]}},
           {"id": "u2", "jednani_id": "j", "cislo": "ZM 99/2026-31", "vysledek_hlasovani": "neprijato",
            "text": "Změna č. 9 územního plánu"}]
    r = harmonogram.aktivita(a, usn, {"j": {"datum": "2026-09-21", "organ": "zastupitelstvo"}}, {"d": "https://z.pdf"})
    assert [m["cislo"] for m in r["milniky"]] == ["ZM 86/2026-31"]
    assert r["milniky"][0]["url"] == "https://z.pdf#page=7" and r["milniky"][0]["text_ai"] is True
    assert r["useky"][0] | {} == {"faze": "prubeh", "nazev": "průběh", "od": "2026-09-21", "do": None, "otevreno": True,
                                  "jistota": "nase_propojeni", "url": "https://z.pdf#page=7", "zacatek_pred_daty": True}


def test_kontrola_aktivit():
    chyby = harmonogram.zkontroluj([{"id": "a", "nazev": "A", "oblast": "vesmir"},
                                    {"id": "a", "nazev": "B", "oblast": "jine", "vazby": {"hledat": ["("]},
                                     "ukonceno": {"datum": "2026-01-01"}}])
    assert any("neznámá oblast" in c for c in chyby) and any("vazby.hledat" in c for c in chyby)
    assert any("duplicitní" in c for c in chyby) and any("chybný vzor" in c for c in chyby)
    assert any("ukonceno" in c for c in chyby)
