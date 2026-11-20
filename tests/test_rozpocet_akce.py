"""Schválený rozpočet po položkách z textu PDF (pipeline/rozpocet_akce.py)."""
import json

from pipeline import projekty, rozpocet_akce as ra

STRANA = """                                                       Schválený rozpočet    Upravený rozpočet    Skutečnost       Schválený rozpočet
            OD/
Třída ORJ                                Popis                       2025             k 30.11.2025      k 30.11.2025             2026
            Pol                                                     tis. Kč              tis. Kč             Kč                   Kč

VÝDAJE
5 Běžné výdaje
Třída ORJ OD
    5 700     10 Hubení komárů                                       80,00                80,00             0,00            80 000,00
                 St.spr.lesů - opatření + Úhrada nákladů na
                                                                     20,00                20,00              0,00           20 000,00
                 zpracování osnov
          10 Zemědělství, lesní hospodářství a rybářství                                                                   100 000,00
             61 Školení a vzdělávání                                 25,00                25,00        16 161,98            25 000,00
          61 Státní moc celkem                                                                                               25 000,00
     ORJ 700 odbor životního prostředí                                                                                      125 000,00
5 Běžné výdaje celkem                                                                                                       125 000,00
5 Běžné výdaje - souhrnný přehled dle ORJ
    700 odbor životního prostředí                                                                                           125 000,00
6 Kapitálové výdaje
Třída ORJ OD
    6 750      34 Přístavba tělocvičen                                                                                  70 000 000,00
                  Dětská hřiště                                   20 000,00          20 500,00    20 048 077,35        16 800 000,00
           34 Sport a zájmová činnost celkem                                                                        86 800 000,00
      ORJ 750 odbor rozvoje a investic celkem                                                                       86 800 000,00
6 Kapitálové výdaje celkem                                                                                          86 800 000,00
"""


def test_polozky_soucty_a_zalomeny_nazev():
    p, chyby = ra.polozky([STRANA], 2026, "url")
    assert chyby == []
    assert [(x["trida"], x["orj"], x["oddil"], x["nazev"], x["castka"]["hodnota"]) for x in p] == [
        ("bezne", "700", 10, "Hubení komárů", 80000.0),
        ("bezne", "700", 10, "St.spr.lesů - opatření + Úhrada nákladů na zpracování osnov", 20000.0),
        ("bezne", "700", 61, "Školení a vzdělávání", 25000.0),
        ("kapitalove", "750", 34, "Přístavba tělocvičen", 70000000.0),
        ("kapitalove", "750", 34, "Dětská hřiště", 16800000.0),
    ]
    assert p[4]["castka"]["citace"] == "16 800 000,00" and p[4]["castka"]["s_dph"] is None
    assert p[4]["castka"]["druh"] == "rozpocet" and p[4]["rozpocet_2025_upraveny_tis"] == 20500.0


def test_nesouhlasici_soucet_je_chyba():
    _, chyby = ra.polozky([STRANA.replace("70 000 000,00", "71 000 000,00")], 2026, "url")
    assert any("oddíl 34" in c for c in chyby) and any("třída 6" in c for c in chyby)


def test_nacti_a_zkontroluj_citace(tmp_path):
    adr = tmp_path / "raw/rozpocet/2026/rozpocet"
    adr.mkdir(parents=True)
    (adr / "strana-1.txt").write_text(STRANA, encoding="utf-8")
    (tmp_path / "raw/rozpocet/manifest.json").write_text(json.dumps(
        {"2026/rozpocet": {"url": "u", "stran": 1}, "2026/rozpoctova_opatreni": {"url": "v", "stran": 1}}))
    p, chyby = ra.nacti(tmp_path)
    assert chyby == [] and len(p) == 5
    assert ra.zkontroluj(p, tmp_path) == []
    p[0]["castka"]["citace"] = "81 000,00"
    assert ra.zkontroluj(p, tmp_path) == [f"{p[0]['id']}: citace částky není v citovaném řádku"]
    # popis jedné položky s částkou jiné neprojde, i když jsou obě slova i částka na straně
    p[0]["castka"]["citace"] = "20 000,00"
    p[0]["citace"]["text"] = "Hubení komárů 20 000,00"
    assert ra.zkontroluj(p, tmp_path) == [f"{p[0]['id']}: citace není doslova ve zdroji"]


def test_souhrn_schvaleneho_rozpoctu_po_letech():
    s = [{"rok": 2026, "trida": "kapitalove", "castka": {"hodnota": 56000000.0}},
         {"rok": 2026, "trida": "kapitalove", "castka": {"hodnota": 500000.0}},
         {"rok": 2026, "trida": "bezne", "castka": {"hodnota": 5000000.0}}]
    (r,) = projekty.souhrn_schvaleny(s)
    assert (r["celkem"], r["investicni"], r["neinvesticni"], r["druh"]) == (61500000.0, 56500000.0, 5000000.0, "rozpocet")
