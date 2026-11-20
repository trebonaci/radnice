"""Dotace, které město poskytuje, z tabulek v usneseních („poskytnutí dotací žadatelům … takto:“) – bez AI.

Tabulka má sloupce Žadatel | Účel | Dotace (Kč) a víceřádkové buňky. Čte se z textu stran s rozložením
(`pdftotext -layout`), po anonymizaci stejnými řetězci jako text usnesení, aby šlo poznat, ke kterému
sloupci patří pokračovací řádek. Částka se opisuje; citace = řádek s částkou (doslova v textu usnesení).
Fyzická osoba jako žadatel zůstává anonymní („fyzická osoba“, bez pokračovacích řádků – bydliště).
"""
from __future__ import annotations

import re

from pipeline.zapisy import normalizuj

RE_UVOD = re.compile(r"poskytnutí dotací žadatelům(?: v oblasti (?P<oblast>.+?))? takto:")
RE_CASTKA = re.compile(r"(?P<c>\d{1,3}(?:\.\d{3})*,\d{2})\s*$")
RE_UCEL = re.compile(r"\s(?=(?:Činnost|Akce|Reprezentace)\b)")
RE_KONEC = re.compile(r"^\s*(?:I{1,3}V?|V)\.\s")
RE_ZAHLAVI = re.compile(r"^\s*Zápis ze \d+\. jednání")
ANONYM = "[fyzická osoba]"


def _halere(s: str) -> int:
    cela, des = s.split(",")
    return int(cela.replace(".", "")) * 100 + int(des)


def _rozdel(levy: str) -> tuple[str, str, int]:
    """Řádek s částkou (bez ní) → (žadatel, účel, sloupec začátku účelu)."""
    m = re.search(r"\S\s{2,}(?=\S)", levy)
    if m:
        zac = m.end()
    else:
        k = RE_UCEL.search(levy)
        zac = k.end() if k else len(levy)
    return levy[:zac].strip(), levy[zac:].strip(), zac


def druh_ucelu(ucel: str) -> str:
    for slovo, druh in (("Činnost", "cinnost"), ("Akce", "akce"), ("Reprezentace", "reprezentace")):
        if ucel.startswith(slovo):
            return druh
    return "jine"


def tabulka(radky_stran: list[str], uvod: str) -> list[dict]:
    """Řádky tabulky za úvodní větou `uvod` (porovnání po sjednocení mezer) do „II.“."""
    start = next((i for i, r in enumerate(radky_stran) if normalizuj(uvod) in normalizuj(r)), None)
    if start is None:
        return []
    vysledek: list[dict] = []
    ucel_sloupec = None
    for r in radky_stran[start + 1:]:
        if RE_KONEC.match(r):
            break
        if not r.strip() or RE_ZAHLAVI.match(r) or r.strip().isdigit() or ("Žadatel" in r and "Účel" in r):
            continue
        m = RE_CASTKA.search(r)
        if m:
            zad, ucel, ucel_sloupec = _rozdel(r[:m.start()])
            vysledek.append({"zadatel": [zad], "ucel": [ucel] if ucel else [], "castka": m["c"],
                             "radek": r.strip()})
            continue
        if not vysledek:
            continue
        posl = vysledek[-1]
        odsazeni = len(r) - len(r.lstrip())
        casti = re.split(r"\s{2,}", r.strip())
        if ucel_sloupec is not None and odsazeni >= ucel_sloupec - 3:
            posl["ucel"].append(r.strip())
        elif len(casti) >= 2:
            posl["zadatel"].append(casti[0])
            posl["ucel"].append(" ".join(casti[1:]))
        else:
            posl["zadatel"].append(r.strip())
    return vysledek


def z_usneseni(u: dict, radky_stran: list[str], verejny_text: str, dokument_id: str, datum: str | None
               ) -> tuple[list[dict], list[str]]:
    """Dotace z jednoho usnesení. `radky_stran` už anonymizované; `verejny_text` = text usnesení ve výstupu."""
    m = RE_UVOD.search(" ".join(verejny_text.split()))
    if not m:
        return [], []
    chyby = []
    radky = tabulka(radky_stran, m.group(0))
    if not radky:
        return [], [f"{u['id']}: tabulka dotací nenalezena"]
    vysledek = []
    for i, r in enumerate(radky, start=1):
        fo = ANONYM in " ".join(r["zadatel"])
        zadatel = "fyzická osoba" if fo else " ".join(r["zadatel"]).replace(" – ", " – ").strip()
        ucel = " ".join(r["ucel"]).strip()
        # citace bez nahrazeného jména: u fyzické osoby jen účel a částka (úsek, který je doslova i ve zdroji)
        citace = r["radek"].split(ANONYM, 1)[1].strip() if fo else r["radek"]
        if ANONYM in citace or normalizuj(citace) not in normalizuj(verejny_text):
            chyby.append(f"{u['id']}: řádek dotace není doslova v usnesení: {citace!r}")
        vysledek.append({
            "id": f"{u['id']}-d{i}",
            "usneseni_id": u["id"], "usneseni_cislo": u["cislo"], "jednani_id": u["jednani_id"], "datum": datum,
            "vysledek_hlasovani": u["vysledek_hlasovani"],
            "oblast": m["oblast"], "prijemce": zadatel, "fyzicka_osoba": fo,
            "ucel": ucel, "druh_ucelu": druh_ucelu(ucel),
            "castka": {"hodnota": _halere(r["castka"]) / 100, "mena": "CZK", "jednotka": "Kč", "s_dph": None,
                       "druh": "dotace_priznana", "citace": citace},
            "citace": {"dokument_id": dokument_id, "strany": u.get("strany", []), "text": citace},
        })
    return vysledek, chyby
