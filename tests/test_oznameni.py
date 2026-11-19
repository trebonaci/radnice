"""Testy oznámení z běhu: právě jedno issue na nový zápis, jedno issue „Běh selhal“, shrnutí."""
import json
import shutil
from pathlib import Path

import pytest

from pipeline import oznameni

KOREN = Path(__file__).resolve().parent.parent


class FakeGh:
    """Pamatuje si issue; `issue list` vrací, co bylo založeno."""
    def __init__(self, selze_spusteni: set[int] | None = None):
        self.issues, self.komentare, self.volani = [], [], []
        self.selze_spusteni = selze_spusteni if selze_spusteni is not None else set()

    def __call__(self, args):
        self.volani.append(args)
        if args[:2] == ["issue", "list"]:
            stav = args[args.index("--state") + 1]
            stitek = args[args.index("--label") + 1] if "--label" in args else None
            res = [{"number": i["number"], "title": i["title"], "body": i["body"],
                    "labels": [{"name": n} for n in i["labels"]]} for i in self.issues
                   if (stav == "all" or (stav == "open" and i["labels"])) and (stitek is None or stitek in i["labels"])]
            return json.dumps(res)
        if args[:2] == ["issue", "create"]:
            self.issues.append({"number": len(self.issues) + 41, "title": args[args.index("--title") + 1],
                                "body": args[args.index("--body") + 1], "labels": [args[args.index("--label") + 1]]})
            return f"https://github.com/trebonaci/radnice/issues/{self.issues[-1]['number']}\n"
        if args[:2] == ["workflow", "run"]:
            cislo = int(args[-1].split("=")[1])
            if cislo in self.selze_spusteni:
                raise RuntimeError("HTTP 500")
            return ""
        if args[:2] == ["label", "create"]:
            return ""
        if args[:2] == ["issue", "edit"]:
            next(i for i in self.issues if i["number"] == int(args[2]))["labels"].append(args[args.index("--add-label") + 1])
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


def _beh_oznameni(koren, f):
    """Totéž co `main zapisy`: založit issue a spustit Clauda pro nová i dříve nespuštěná."""
    cisla: list[int] = []
    oznameni.zaloz_issue_zapisu(oznameni.zapisy_bez_anotace(koren), f, cisla=cisla)
    return oznameni.spust_claude(sorted(set(cisla) | set(oznameni.cekajici_issue(f))), f)


def test_nove_issue_spusti_clauda_prave_jednou(koren):
    """Issue založené přes GITHUB_TOKEN štítkem Clauda nespustí – běh ho proto spustí přes workflow_dispatch."""
    pridej_novy_zapis(koren)
    f = FakeGh()
    assert _beh_oznameni(koren, f) == ([41], [])
    assert _beh_oznameni(koren, f) == ([], [])
    spusteni = [a for a in f.volani if a[:2] == ["workflow", "run"]]
    assert spusteni == [["workflow", "run", "claude.yml", "-f", "issue=41"]]
    assert "claude-spusten" in f.issues[0]["labels"]


def test_neuspesne_spusteni_zkusi_dalsi_beh_a_nezastavi_ostatni(koren):
    pridej_novy_zapis(koren)
    m = json.loads((koren / "raw/manifest.json").read_text(encoding="utf-8"))
    druhy = json.loads(json.dumps(m[-1]))
    druhy.update(dokument_id="zapis-zm-2026-11-20", jednani_id="zm-2026-11-20")
    (koren / "raw/manifest.json").write_text(json.dumps(m + [druhy], ensure_ascii=False), encoding="utf-8")
    f = FakeGh(selze_spusteni={41})
    assert _beh_oznameni(koren, f) == ([42], [41])     # selhání prvního nezastaví druhé
    f.selze_spusteni.clear()
    assert _beh_oznameni(koren, f) == ([41], [])       # další běh dožene jen to nespuštěné
    assert len(f.issues) == 2
    spusteni = [a[-1] for a in f.volani if a[:2] == ["workflow", "run"]]
    assert spusteni == ["issue=41", "issue=42", "issue=41"]


def test_bez_noveho_zapisu_se_claude_nespousti(koren):
    f = FakeGh()
    assert _beh_oznameni(koren, f) == ([], [])
    assert not [a for a in f.volani if a[:2] == ["workflow", "run"]]
