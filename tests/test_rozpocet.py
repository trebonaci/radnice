"""Rozpočtová opatření z textu usnesení (pipeline/rozpocet.py). Texty doslova ze zápisů RM/ZM 2026."""
from pipeline import rozpocet as r

RO_57 = """I. schvaluje
provedení rozpočtového opatření č. 57, které spočívá v přesunutí finančních prostředků ve výdajové části
rozpočtu
-z položky 6121 „Přístavba tělocvičen“, § 3412, ORJ 750, ORG 6230000000, UZ 0 v částce Kč 253.000,00,
-do položky 5137 „Přístavba tělocvičen - vybavení“, § 3412, ORJ 750, ORG 9750000000, UZ 0 v částce Kč
253.000,00.
Rozpočtové výdaje (Kč):
57.          0    6230000000     750        3412    6121     70 000 000,00   59 245 143,49   - 253 000,00    58 992 143,49
0    9750000000     750        3412    5137              0,00     334 000,00    +253 000,00        587 000,00
II. ukládá
odboru rozvoje a investic a odboru finančnímu a majetkovému provést a evidovat RO v IS GINIS."""

RO_54 = """III. schvaluje
provedení rozpočtového opatření č. 54, které spočívá v přesunutí finančních prostředků ve výdajové části
rozpočtu takto:
-ponížení výdajové položky 5222 Příspěvky v oblasti ostatních činností, § 3429, ORJ 0800, ORG 9800003147,
NZUZ 0 o částku 20 000 Kč,
-navýšení výdajové položky 5331 Příspěvky v oblasti ostatních činností - dar, § 3113, ORJ 0800, ORG
9800003150, NZUZ 0 o částku 20 000 Kč.
Rozpočtové výdaje (Kč):
54.          0     9800003147     0800       3429      5222      300 000       292 000   -   20 000       272 000
0     9800003150     0800       3113      5331            0         8 000   + 20 000          28 000"""

RO_48 = """I. schvaluje
provedení rozpočtového opatření č. 48, které spočívá v:
-navýšení příjmové položky 4134 „Jednotný příděl do lázeňského investičního fondu“, § 6330, ORJ 800, ORG
5040004040, UZ o částku 20.000.000,00 Kč,
-navýšení výdajové položky 6121 „TZ nemovitého majetku v pronájmu společnosti SLT“, § 3613, ORJ 750,
ORG 5040005041, UZ 0 o částku 20.000.000,00 Kč.
Rozpočtové příjmy LIF (Kč):
48.             0       5040005040     800    6330     4134             0               0    + 20 000 000    20 000 000,00
Rozpočtové výdaje LIF (Kč):
48.             0       5040005041     750    3613     6121     54 200 000     54 200 000    + 20 000 000       74 200 000"""


def usn(text, uid="rm-2026-j113-u542", cislo="RM 542/2026-113"):
    return {"id": uid, "cislo": cislo, "jednani_id": "rm-2026-10-21", "vysledek_hlasovani": "prijato",
            "text": text, "citace": {"dokument_id": "zapis-rm-2026-10-21", "strany": [9]}}


def test_na_halere():
    assert r.na_halere("80.000,00") == 8_000_000
    assert r.na_halere("20 000") == 2_000_000
    assert r.na_halere("59 245 143,49") == 5_924_514_349
    assert r.na_halere("1.165.000,00") == 116_500_000


def test_presun_z_do_s_tabulkou():
    zaznamy, chyby = r.polozky_ro(usn(RO_57))
    assert chyby == []
    z, do = zaznamy
    assert (z["cislo_ro"], z["smer"], z["polozka"], z["org"], z["nazev"]) == \
        (57, "z", "6121", "6230000000", "Přístavba tělocvičen")
    assert z["zmena"] == -253000.0 and z["castka"]["hodnota"] == 253000.0
    assert z["rozpocet"] == {"schvaleny": 70000000.0, "pred_ro": 59245143.49, "po_ro": 58992143.49,
                             "fond": None, "citace": z["rozpocet"]["citace"]}
    assert do["smer"] == "do" and do["zmena"] == 253000.0 and do["rozpocet"]["po_ro"] == 587000.0
    assert z["strana"] == "vydaje" and z["organ"] == "rada" and z["rok"] == 2026
    assert r.zkontroluj(zaznamy, [usn(RO_57)]) == []


def test_nazev_bez_uvozovek_a_orj_s_nulou():
    zaznamy, chyby = r.polozky_ro(usn(RO_54))
    assert chyby == []
    assert [z["smer"] for z in zaznamy] == ["snizeni", "navyseni"]
    assert zaznamy[0]["nazev"] == "Příspěvky v oblasti ostatních činností" and zaznamy[0]["orj"] == "800"
    assert zaznamy[0]["rozpocet"]["po_ro"] == 272000.0


def test_fond_a_rozdilne_org_v_tabulce():
    zaznamy, chyby = r.polozky_ro(usn(RO_48, "zm-2026-j31-u77", "ZM 77/2026-31"))
    assert chyby == []
    prijem, vydaj = zaznamy
    assert prijem["organ"] == "zastupitelstvo" and prijem["strana"] == "prijmy" and prijem["uz"] is None
    assert prijem["rozpocet"]["fond"] == "LIF" and "5040005040" in prijem["poznamka"]
    assert vydaj["rozpocet"]["po_ro"] == 74200000.0 and vydaj["poznamka"] is None


def test_nesedici_tabulka_je_chyba():
    spatne = RO_57.replace("58 992 143,49", "58 992 143,48")
    _, chyby = r.polozky_ro(usn(spatne))
    assert any("≠ po" in c for c in chyby)


def test_presun_musi_byt_vyrovnany_a_citace_doslova():
    zaznamy, _ = r.polozky_ro(usn(RO_57))
    zaznamy[1]["zmena"] = 250000.0
    zaznamy[0]["citace"]["text"] = "vymyšlená citace"
    chyby = r.zkontroluj(zaznamy, [usn(RO_57)])
    assert any("nesedí" in c for c in chyby) and any("doslova" in c for c in chyby)


def test_usneseni_bez_ro():
    assert r.polozky_ro(usn("I. schvaluje\nprogram jednání.")) == ([], [])
