import json
from pathlib import Path

import pytest

from pipeline import sestav
from pipeline.sestav import anonymizuj, cisla_v_textu
from pipeline.zapisy import normalizuj, rozloz

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
    assert all(u["vysledek"] == "schvaleno" for u in v["usneseni"])
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
    for d in ("raw", "anotace"):
        shutil.copytree(KOREN / d, tmp_path / d)
    p = tmp_path / "anotace" / "rm-2026-11-04.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace(
        "v celkové hodnotě 25.000 Kč\"", "v celkové hodnotě 26.000 Kč\""), encoding="utf-8")
    monkeypatch.setattr(sestav, "KOREN", tmp_path)
    assert sestav.main() == 1
