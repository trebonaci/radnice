import json
from pathlib import Path

import pytest

from pipeline import sestav
from pipeline.sestav import anonymizuj, anonymizuj_urednici, cisla_v_textu, nacti_osoby, najdi_osobni_udaje
from pipeline.zapisy import normalizuj, rozloz, urci_ukon

KOREN = Path(__file__).resolve().parent.parent
TEXTY = KOREN / "raw" / "texty"


@pytest.mark.parametrize("text,ocekavano", [
    ("v částce Kč 223.850,00.", 223850.0),
    ("v celkové hodnotě 25.000 Kč", 25000.0),
    ("1 246 300", 1246300.0),
    ("ve výši 2.100,00 Kč/m2/rok", 2100.0),
    ("16,34 m2", 16.34),
])
def test_cisla_v_textu(text, ocekavano):
    assert ocekavano in cisla_v_textu(text)


def test_normalizace_spojuje_zalomeni():
    assert normalizuj("a\n  b\tc ") == "a b c"


def test_anonymizace():
    assert anonymizuj("smlouva s Janem Novákem, IČO: 123", ["Janem Novákem", "123"]) == \
        "smlouva s [fyzická osoba], IČO: [fyzická osoba]"


def test_rada_struktura():
    v = rozloz("rm-2026-11-04", TEXTY / "rm-2026-11-04")
    assert len(v["body"]) == 11
    assert [u["cislo"] for u in v["usneseni"]] == [f"RM {i}/2026-1" for i in range(1, 10)]
    assert all(u["vysledek_hlasovani"] == "prijato" for u in v["usneseni"])
    assert all(u["vysledek_zapis"] == "SCHVÁLENO" for u in v["usneseni"])
    assert all((h["pro"], h["proti"], h["zdrzel"]) == (5, 0, 0) for h in v["hlasovani"])
    assert v["upozorneni"] == []


def test_zastupitelstvo_hlasovani():
    v = rozloz("zm-2026-11-02", TEXTY / "zm-2026-11-02")
    assert len(v["usneseni"]) == 11
    podle = {}
    for h in v["hlasovani"]:
        podle.setdefault(h["usneseni_id"], []).append(h)
    # usnesení ve dvou částech se dvěma hlasováními
    assert [(h["cast"], h["pro"], h["zdrzel"]) for h in podle["zm-2026-j1-u10"]] == [("I", 19, 4), ("II", 20, 3)]
    # volba radních: jen hlasování o kandidátech
    assert [h["typ"] for h in podle["zm-2026-j1-u11"]] == ["volba_kandidata"] * 4
    # dva protinávrhy, jeden přijatý, jeden nepřijatý
    protinavrhy = [h for h in v["hlasovani"] if h["typ"] == "protinavrh"]
    assert [h["vysledek"] for h in protinavrhy] == ["prijato", "neprijato"]
    assert (protinavrhy[1]["pro"], protinavrhy[1]["proti"], protinavrhy[1]["zdrzel"]) == (6, 17, 2)


def test_neprijate_usneseni_rm_111():
    """RM 476/2026-111: „NÁVRH NESCHVÁLEN – USNESENÍ NEPŘIJATO“ = návrh neprošel (2 pro, 5 proti)."""
    r = rozloz("rm-2026-09-23", TEXTY / "rm-2026-09-23" / "v1")
    u = next(x for x in r["usneseni"] if x["cislo"] == "RM 476/2026-111")
    assert u["vysledek_hlasovani"] == "neprijato"
    h = next(x for x in r["hlasovani"] if x.get("usneseni_id") == u["id"])
    assert (h["pro"], h["proti"], h["zdrzel"]) == (2, 5, 0)
    assert not any("476/2026-111" in w for w in r["upozorneni"])


def test_sestaveni_bez_chyb():
    assert sestav.main() == 0
    usneseni = json.loads((KOREN / "data" / "usneseni.json").read_text(encoding="utf-8"))
    assert all(u["overeni"] == "overeno_kodem" for u in usneseni)
    texty = " ".join(u["text"] for u in usneseni)
    for zakazane in ("Sojkov", "71996117", "01267647", "Svobody č. p. 272"):
        assert zakazane not in texty
    jednani = json.loads((KOREN / "data" / "jednani.json").read_text(encoding="utf-8"))
    nazvy = " ".join(b["nazev"] for j in jednani for b in j["body"])
    assert "Sojkov" not in nazvy
    detaily = " ".join(b["text"] or "" for j in jednani for b in j["body"])
    assert "Petřík" not in detaily and "podnět občana" in detaily
    assert "Zavadilová" not in texty and "Filípková" not in texty


def test_spatna_citace_selze(tmp_path, monkeypatch):
    """Kontrola citací musí odhalit citaci, která ve zdroji není."""
    import shutil
    for d in ("raw", "anotace", "config"):
        shutil.copytree(KOREN / d, tmp_path / d)
    p = tmp_path / "anotace" / "rm-2026-11-04.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace(
        "v celkové hodnotě 25.000 Kč\"", "v celkové hodnotě 26.000 Kč\""), encoding="utf-8")
    monkeypatch.setattr(sestav, "KOREN", tmp_path)
    assert sestav.main() == 1


def test_vysledek_oddelen_od_ukonu():
    """„SCHVÁLENO“ u usnesení „bere na vědomí“ neznamená, že rada věc schválila."""
    v = rozloz("rm-2026-11-04", TEXTY / "rm-2026-11-04")
    u = {x["cislo"]: x for x in v["usneseni"]}
    for cislo in ("RM 4/2026-1", "RM 6/2026-1"):
        assert u[cislo]["vysledek_hlasovani"] == "prijato"
        assert [x["ukon"] for x in u[cislo]["ukony"]] == ["bere_na_vedomi"]
    assert [x["ukon"] for x in u["RM 5/2026-1"]["ukony"]] == ["schvaluje", "uklada"]
    z = rozloz("zm-2026-11-02", TEXTY / "zm-2026-11-02")
    assert [x["ukon"] for x in z["usneseni"][6]["ukony"]] == ["urcuje"]
    assert [(x["cast"], x["ukon"]) for x in z["usneseni"][9]["ukony"]] == [("I", "voli"), ("II", "voli")]
    assert not any("neznámý úkon" in w for w in v["upozorneni"] + z["upozorneni"])


def test_vystup_nema_vysledek_bez_rozliseni():
    usneseni = json.loads((KOREN / "data" / "usneseni.json").read_text(encoding="utf-8"))
    assert all("vysledek" not in u for u in usneseni)
    assert all(u["ukony"] for u in usneseni)


def test_anonymizace_uredniku_zalomeni_radku():
    osoby = nacti_osoby()
    text = "Skrutátorem byla určena tajemnice úřadu Ing. Petra Pikna Jánská a zpracovatelem zápisu Mgr. Hana\nBurešová."
    vysledek = anonymizuj_urednici(text, osoby)
    assert "Pikna" not in vysledek and "Burešová" not in vysledek
    assert vysledek == "Skrutátorem byla určena tajemnice úřadu a zpracovatelkou zápisu pracovnice úřadu."


def test_kontrola_najde_neznamou_osobu():
    osoby = nacti_osoby()
    assert najdi_osobni_udaje("Předkladatel: Ing. Jan Neznámý", osoby) == ["Ing. Jan Neznámý"]
    assert najdi_osobni_udaje("Zapsala: Pavlína Bohuslávková", osoby)
    assert najdi_osobni_udaje("starostou města Třeboně Mgr. Aleše Koláře.", osoby) == []
    assert najdi_osobni_udaje("Zapsala: zapisovatelka", osoby) == []


def test_vystup_bez_jmen_uredniku():
    """Žádný řetězec v odvozených datech nesmí obsahovat jméno úředníka ani jinou nevolenou osobu."""
    assert sestav.main() == 0
    osoby = nacti_osoby()
    for nazev in ("jednani", "usneseni", "hlasovani"):
        obsah = json.loads((KOREN / "data" / f"{nazev}.json").read_text(encoding="utf-8"))
        for r in sestav._retezce(obsah):
            assert najdi_osobni_udaje(r, osoby) == [], (nazev, r[:120])
            for jmeno in ("Pikna Jánská", "Burešová", "Bohuslávková", "Baštová", "Hajna", "Karásková"):
                assert jmeno not in r, (nazev, jmeno)


@pytest.mark.parametrize("jmeno", [
    "Ing. Jana Piklová",          # začíná kmenem zastupitele Pikl
    "Mgr. Petra Koubová",         # začíná kmenem Koub
    "Bc. Vladan Piklík",          # stejné křestní jméno, jiné příjmení
    "Ing. Ondřej Zbudilík",
    "Mgr. Aleš Kolářský",
])
def test_kontrola_nepropusti_podobne_jmeno(jmeno):
    """Regrese: dřívější podřetězcová shoda kmene by tato jména propustila."""
    assert najdi_osobni_udaje(f"Předkladatel: {jmeno}", nacti_osoby()) == [jmeno]


@pytest.mark.parametrize("text", [
    "starostou města Třeboně Mgr. Aleše Koláře.",
    "ověřovatele zápisu Bc. Vladana Pikla, MPA.",
    "Ing. Jiří\nVopátek, Ph.D. navrhl",
    "Ing. Lenka Blažková\nPro: 17",
])
def test_kontrola_propusti_zastupitele(text):
    assert najdi_osobni_udaje(text, nacti_osoby()) == []


@pytest.mark.parametrize("text,kod", [
    ("bere na vědomí", "bere_na_vedomi"),
    ("Bere na vědomí", "bere_na_vedomi"),
    ("SCHVALUJE", "schvaluje"),
    ("Volí", "voli"),
    ("neschvaluje", "neschvaluje"),
    ("projednala", "jiny"),
])
def test_urci_ukon_bez_ohledu_na_velikost(text, kod):
    assert urci_ukon(text)[0] == kod


def test_seznam_zastupitelu_uplny():
    osoby = nacti_osoby()
    vse = osoby["zastupitele"]
    assert len({x["jmeno"] for x in vse}) == len(vse)
    assert all(x["tvary"][0] == x["jmeno"] for x in vse)
    z = [x for x in vse if "2026-2030" in x["obdobi"]]
    assert len(z) == 25 and all(x["strana"] for x in z)
    z22 = [x for x in vse if "2022-2026" in x["obdobi"]]
    assert len(z22) == 25 and all(x["strana_2022"] for x in z22)
    funkce = sorted(x["funkce"] for x in z if x["funkce"])
    assert funkce == sorted(["starosta", "1. místostarosta", "2. místostarosta", "radní", "radní", "radní", "radní"])
    # žádný tvar jména zastupitele nesmí být zároveň jménem úředníka
    urednici = {(v if isinstance(v, str) else v["text"]) for u in osoby["urednici"] for v in u["varianty"]}
    assert not any(t in u for x in vse for t in x["tvary"] for u in urednici)


@pytest.mark.parametrize("text", ["Mgr. Bc. Petr Michal", "JUDr. Pavel Pumpr", "Ing. Martina Trubače", "Bc. Radku Kaiseršatovou",
                                  "PaedDr. Jan Váňa", "Ing. Zdeňka Kukačky", "Mgr. Terezii Jenisovou"])
def test_novi_zastupitele_projdou(text):
    assert najdi_osobni_udaje(text, nacti_osoby()) == []


def test_zastupitel_jen_ve_svem_obdobi():
    """Bývalý zastupitel (jen 2022–2026) v zápisu nového období neprojde jako volený zástupce."""
    osoby = nacti_osoby()
    assert najdi_osobni_udaje("Ing. Zdeněk Kukačka", osoby, "2022-2026") == []
    assert najdi_osobni_udaje("Ing. Zdeněk Kukačka", osoby, "2026-2030") == ["Ing. Zdeněk Kukačka"]
    assert najdi_osobni_udaje("PaedDr. Jan Váňa", osoby, "2026-2030") == []
    assert najdi_osobni_udaje("JUDr. Pavel Pumpr", osoby, "2022-2026") == ["JUDr. Pavel Pumpr"]
