"""Dotace z tabulek v usneseních (pipeline/dotace.py). Řádky ve tvaru pdftotext -layout ze zápisu RM 30. 10. 2026."""
from pipeline import dotace as d

RADKY = """I. schvaluje
poskytnutí dotací žadatelům v oblasti tělovýchovy a sportu takto:
    Žadatel                          Účel                                      Dotace 2026 (Kč)

  Sportovní klub – SK Boxing                 Činnost                           10.500,00
  TŘEBOŇ, z.s.
  [fyzická osoba]                            Akce Běh kolem Světa              10.000,00
  Praha
  TJ Jiskra Třeboň, z.s. – oddíl             Akce Turnaj 4+1 házená            10.500,00
  házené                                     08.11.2026
3
Zápis ze 114. jednání RM ze dne 30.10.2026
  TJ Jiskra Třeboň, z.s. – oddíl             Reprezentace – Turnaj            15.000,00
  házené                                     v rakouském Linzi mladší
                                             dorost + muži, Rakousko
    Dům dětí a mládeže, Jindřichův Akce Mikulášská nadílka            8.000,00
    Hradec, Růžová 10, Pracoviště
II. schvaluje
uzavření veřejnoprávních smluv""".splitlines()


def test_tabulka_dotaci():
    verejny = "\n".join(r.strip() for r in RADKY)
    u = {"id": "rm-u548", "cislo": "RM 548/2026-114", "jednani_id": "rm-2026-10-30", "vysledek_hlasovani": "prijato"}
    zaz, chyby = d.z_usneseni(u, RADKY, verejny, "zapis", "2026-10-30")
    assert chyby == []
    assert [(z["prijemce"], z["ucel"], z["castka"]["hodnota"], z["druh_ucelu"]) for z in zaz] == [
        ("Sportovní klub – SK Boxing TŘEBOŇ, z.s.", "Činnost", 10500.0, "cinnost"),
        ("fyzická osoba", "Akce Běh kolem Světa", 10000.0, "akce"),
        ("TJ Jiskra Třeboň, z.s. – oddíl házené", "Akce Turnaj 4+1 házená 08.11.2026", 10500.0, "akce"),
        ("TJ Jiskra Třeboň, z.s. – oddíl házené", "Reprezentace – Turnaj v rakouském Linzi mladší dorost + muži, Rakousko",
         15000.0, "reprezentace"),
        ("Dům dětí a mládeže, Jindřichův Hradec, Růžová 10, Pracoviště", "Akce Mikulášská nadílka", 8000.0, "akce")]
    assert zaz[1]["fyzicka_osoba"] is True and "Praha" not in str(zaz[1])
    assert zaz[1]["citace"]["text"] == "Akce Běh kolem Světa              10.000,00"      # bez nahrazeného jména
    assert zaz[0]["oblast"] == "tělovýchovy a sportu" and zaz[0]["castka"]["druh"] == "dotace_priznana"


def test_bez_tabulky():
    u = {"id": "x", "cislo": "RM 1/2026-1", "jednani_id": "j", "vysledek_hlasovani": "prijato"}
    assert d.z_usneseni(u, [], "I. schvaluje program jednání.", "z", None) == ([], [])
