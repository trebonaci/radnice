"""Testy oznámení z běhu: právě jedno issue na nový zápis, jedno issue „Běh selhal“, shrnutí."""
import json
import shutil
from pathlib import Path

import pytest

from pipeline import oznameni

KOREN = Path(__file__).resolve().parent.parent


class FakeGh:
    """Pamatuje si issue; `issue list` vrací, co bylo založeno."""
    def __init__(self):
        self.issues, self.komentare, self.volani = [], [], []

    def __call__(self, args):
        self.volani.append(args)
        if args[:2] == ["issue", "list"]:
            stav = args[args.index("--state") + 1]
            res = [{"number": i["number"], "title": i["title"], "body": i["body"]} for i in self.issues
                   if stav == "all" or (stav == "open" and "potrebuje-cloveka" in i["labels"])]
            return json.dumps(res)
        if args[:2] == ["issue", "create"]:
            self.issues.append({"number": len(self.issues) + 1, "title": args[args.index("--title") + 1],
                                "body": args[args.index("--body") + 1], "labels": [args[args.index("--label") + 1]]})
            return ""
        if args[:2] == ["issue", "comment"]:
            self.komentare.append((args[2], args[args.index("--body") + 1]))
            return ""
        raise AssertionError(args)


@pytest.fixture
def koren(tmp_path):
    for d in ("raw", "anotace", "data"):
        shutil.copytree(KOREN / d, tmp_path / d)
    return tmp_path


def pridej_novy_zapis(koren):
    m = json.loads((koren / "raw/manifest.json").read_text(encoding="utf-8"))
    novy = json.loads(json.dumps(m[0]))
    novy.update(dokument_id="zapis-rm-2026-11-18", jednani_id="rm-2026-11-18")
    (koren / "raw/manifest.json").write_text(json.dumps(m + [novy], ensure_ascii=False), encoding="utf-8")


def test_zapisy_s_anotaci_issue_nezaklada(koren):
    assert oznameni.zapisy_bez_anotace(koren) == []
    f = FakeGh()
    assert oznameni.zaloz_issue_zapisu([], f) == []
    assert f.issues == []


def test_novy_zapis_bez_anotace_vytvori_prave_jedno_issue_i_pri_opakovani(koren):
    pridej_novy_zapis(koren)
    f = FakeGh()
    for _ in range(3):
        oznameni.zaloz_issue_zapisu(oznameni.zapisy_bez_anotace(koren), f, vetev="claude/beh-2026-11-19")
    assert len(f.issues) == 1
    i = f.issues[0]
    assert i["labels"] == ["agent:claude"] and i["title"] == "Nový zápis: RM 18. 11. 2026"
    assert "anotace/rm-2026-11-18.yaml" in i["body"] and "novy-zapis:rm-2026-11-18" in i["body"]
    assert "claude/beh-2026-11-19" in i["body"]


def test_zavrene_issue_se_neduplikuje(koren):
    pridej_novy_zapis(koren)
    f = FakeGh()
    oznameni.zaloz_issue_zapisu(oznameni.zapisy_bez_anotace(koren), f)
    f.issues[0]["labels"] = []            # „zavřené“ – dál je vidět jen ve --state all
    assert oznameni.zaloz_issue_zapisu(oznameni.zapisy_bez_anotace(koren), f) == []


def test_selhani_zalozi_jedno_issue_a_dalsi_selhani_jen_komentuje(koren):
    (koren / "data/beh.json").write_text(json.dumps(
        {"stav": "zastaveno", "zacatek": "2026-11-19T06:00:00", "zdroje": [{"nazev": "zapisy_mesta", "stav": "nedostupny"}],
         "chyby": ["zapisy_mesta: zdroj nedostupný: HTTP 503 `x`"], "upozorneni": []}), encoding="utf-8")
    f = FakeGh()
    assert oznameni.oznam_selhani("https://run/1", koren, f) == "issue"
    assert oznameni.oznam_selhani("https://run/2", koren, f) == "komentar"
    assert len(f.issues) == 1 and f.issues[0]["labels"] == ["potrebuje-cloveka"] and len(f.komentare) == 1
    assert "HTTP 503" in f.issues[0]["body"] and "https://run/1" in f.issues[0]["body"]


def test_shrnuti_obsahuje_pocty_a_zapisy_bez_anotace(koren):
    pridej_novy_zapis(koren)
    (koren / "data/beh.json").write_text(json.dumps(
        {"stav": "ok", "konec": "2026-11-19", "pocty": {"jednani": 2, "usneseni": 20, "hlasovani": 26},
         "nove_dokumenty": 1, "nove_verze": 0}), encoding="utf-8")
    t = oznameni.shrnuti(koren)
    assert "nové dokumenty 1" in t and "usnesení 20" in t and "rm-2026-11-18" in t
