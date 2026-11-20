"""Přehled rozpočtových opatření z PDF (pipeline/rozpocet_zmeny.py)."""
from pipeline import rozpocet_zmeny as rz
from pipeline.rozpocet import na_halere

STRANA = """                       Rozpočtová opatření schválená orgány města Třeboně v roce 2026
                                        800   64   BV   Výdaje z finančního vypořádání                       100,00       100,00          4,23            104,23
    1.        66/2026-95     RM
                                        800    0    F   Změna stavu finančních prostředků                  77 577,29    77 577,29          4,23        77 581,52
                                        800   43   BV   Příspěvky v oblasti sociálních služeb               2 200,00     2 200,00        -10,00          2 190,00
    8.       178/2026-99     RM         800   35   BV   Příspěvky v oblasti sociálních služeb                   0,00         0,00          5,00               5,00
                                        800   35   BV   Příspěvky v oblasti sociálních služeb                   0,00         0,00          5,00               5,00
                                        770   61   BV   SF - příspěvek na stravování                        2 400,00     2 400,00     -2 257,00            143,00
  úprava
             128/2026-97     RM         770   61   BV   SF - příspěvek na stravování MěÚ                        0,00         0,00      1 917,00          1 917,00
rozpisu SF
                                        770   53   BV   SF - příspěvek na stravování MěPo                       0,00         0,00        340,00            340,00
          RM č. 442/2026-               800   64   KV   Rezervy kapitálových výdajů                        26 000,00    30 227,14    -20 000,00        10 227,14
            109 ZM č.                   800   63   BV   Jednotný příděl do lázeňského investičního fondu        0,00         0,00     20 000,00        20 000,00
   48.                    RM/ZM
           77/2026-31                   800   63   BP   Jednotný příděl do lázeňského investičního fondu*       0,00         0,00     20 000,00        20 000,00
                                        750   36   BV   TZ nemovitého majetku v pronájmu společnosti SLT*  54 200,00    54 200,00     20 000,00        74 200,00
                                        750   34   KV   Přístavba tělocvičen                               70 000,00    59 245,14      -253,00        58 992,14
   57.     542/2026-113      RM
                                        750   34   BV   Přístavba tělocvičen - vybavení                         0,00       334,00       253,00            587,00
                                                        * položky fondů
"""


def test_zaporna_castka_v_halerich():
    assert na_halere("-522,85") == -52285 and na_halere("-0,60") == -60 and na_halere("1 917,00") == 191700


def test_prirazeni_radku_k_opatrenim_podle_soumernosti():
    r, chyby, _ = rz.zmeny([STRANA], 2026, "url")
    assert chyby == []
    po_ro = {}
    for x in r:
        po_ro.setdefault(x["cislo_ro"], []).append(x["ucel"])
    assert [len(po_ro[k]) for k in (1, 8, None, 48, 57)] == [2, 3, 3, 4, 2]
    r48 = [x for x in r if x["cislo_ro"] == 48]
    assert r48[0]["usneseni"] == ["442/2026-109", "77/2026-31"] and r48[0]["organ"] == "RM/ZM"
    assert r48[2]["fond"] is True and r48[2]["ucel"].endswith("fondu")
    sf = [x for x in r if x["cislo_ro"] is None]
    assert sf[0]["nazev_ro"] == "úprava rozpisu SF" and sf[0]["usneseni"] == ["128/2026-97"]
    t = next(x for x in r if x["ucel"] == "Přístavba tělocvičen")
    assert (t["schvaleny"], t["upraveny_pred"], t["zmena"], t["po_zmene"]) == (70000000, 59245140, -253000, 58992140)
    assert t["castka"]["druh"] == "rozpoctove_opatreni" and t["castka"]["citace"] == "-253,00"


def test_aritmeticka_chyba_a_zbyle_radky():
    _, chyby, _ = rz.zmeny([STRANA.replace("58 992,14", "58 992,15")], 2026, "u")
    assert any("Přístavba tělocvičen" in c for c in chyby)
    _, chyby, _ = rz.zmeny([STRANA + "            750   34   KV   Navíc     0,00   0,00   1,00   1,00\n"], 2026, "u")
    assert any("zbývá" in c for c in chyby)


def test_porovnani_s_usnesenimi_toleruje_zaokrouhleni_na_tisice():
    r, _, _ = rz.zmeny([STRANA], 2026, "u")
    usn = [{"rok": 2026, "cislo_ro": 57, "strana": "vydaje", "vysledek_hlasovani": "prijato", "zmena": -253000.0},
           {"rok": 2026, "cislo_ro": 57, "strana": "vydaje", "vysledek_hlasovani": "prijato", "zmena": 253000.0},
           # RO 57 jiného roku se s přehledem 2026 neporovnává
           {"rok": 2027, "cislo_ro": 57, "strana": "vydaje", "vysledek_hlasovani": "prijato", "zmena": 1.0}]
    assert rz.porovnej_s_usnesenimi(r, usn) == []
    usn[0]["zmena"] = -252999.4
    assert rz.porovnej_s_usnesenimi(r, usn) == []
    usn[0]["zmena"] = -250000.0
    assert len(rz.porovnej_s_usnesenimi(r, usn)) == 1


def test_doplnit_rozpocet_a_retez():
    r, _, upozorneni = rz.zmeny([STRANA], 2026, "u")
    assert any("Příspěvky v oblasti sociálních služeb" in u for u in upozorneni)     # dvakrát tentýž řádek v RO 8
    rozpocet = [{"rok": 2026, "orj": "750", "oddil": 34, "trida": "kapitalove", "nazev": "Přístavba tělocvičen"},
                {"rok": 2026, "orj": "750", "oddil": 34, "trida": "bezne", "nazev": "Přístavba tělocvičen"}]
    rz.doplnit_rozpocet(rozpocet, r)
    assert rozpocet[0]["po_zmenach"]["hodnota"] == 58992140.0 and rozpocet[0]["zmeny_ro"] == [57]
    assert rozpocet[1]["po_zmenach"] is None
