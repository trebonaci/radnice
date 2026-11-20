"""Stav schválení usnesení: rada sama / rada doporučila zastupitelstvu / zastupitelstvo rozhodlo (#115).

Rada u věcí vyhrazených zastupitelstvu přijme usnesení „doporučuje Zastupitelstvu města … schválit“ a
zastupitelstvo pak o téže věci rozhoduje (text usnesení přebírá). Párování je bez AI: pozdější usnesení
zastupitelstva s překryvem slov textu aspoň `PRAH` (vůči kratšímu z textů) – „naše propojení“.

Pole `schvaleni` u každého usnesení:
- `stav`: `konecne` (rada nebo zastupitelstvo rozhodlo s konečnou platností), `ceka_na_zm` (rada
  doporučila, zastupitelstvo zatím nerozhodlo), `neprijato` (návrh neprošel), `zm_neschvalilo`;
- `rada_usneseni_id`, `zm_usneseni_id` (spárovaná usnesení), `jistota` párování.
"""
from __future__ import annotations

import re

PRAH = 0.9
RE_DOPORUCUJE = re.compile(r"doporučuje\s+(?:Zastupitelstvu|zastupitelstvu|ZM)\b")


def _slova(text: str) -> set[str]:
    return set(re.findall(r"\w{4,}", (text or "").lower()))


def _cisla(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:[.,/]\d+)*", text or ""))


def _shoda(a: set[str], b: set[str]) -> float:
    return len(a & b) / max(1, min(len(a), len(b)))


def _stejna_cisla(a: set[str], b: set[str], sa: set[str], sb: set[str]) -> bool:
    """Čísla (dodatek, parcela, částka) kratšího textu musí být i v delším – jiné číslo = jiná věc."""
    return (a <= b) if len(sa) <= len(sb) else (b <= a)


def _zamitnuti(u: dict) -> bool:
    """Usnesení zastupitelstva, jehož výrok je zamítavý (`neschvaluje`) – i když samo bylo přijato."""
    return (any(x.get("ukon") == "neschvaluje" for x in u.get("ukony") or [])
            or re.search(r"\bneschvaluje\b", u.get("text") or "") is not None)


def oznac(usneseni: list[dict], datum_jednani: dict[str, str]) -> None:
    zm = [u for u in usneseni if u["id"].startswith("zm-")]
    slova = {u["id"]: _slova(u["text"]) for u in usneseni}
    for u in usneseni:
        u["schvaleni"] = {"stav": "konecne" if u["vysledek_hlasovani"] == "prijato" else "neprijato",
                          "rada_usneseni_id": None, "zm_usneseni_id": None, "jistota": None}
    for r in usneseni:
        if not r["id"].startswith("rm-") or r["vysledek_hlasovani"] != "prijato" or not RE_DOPORUCUJE.search(r["text"]):
            continue
        datum = datum_jednani.get(r["jednani_id"]) or ""
        cisla = _cisla(r["text"])
        kandidati = sorted(((_shoda(slova[r["id"]], slova[z["id"]]), datum_jednani.get(z["jednani_id"]) or "", z)
                            for z in zm if (datum_jednani.get(z["jednani_id"]) or "") >= datum
                            and _stejna_cisla(cisla, _cisla(z["text"]), slova[r["id"]], slova[z["id"]])),
                           key=lambda x: (-x[0], x[1]))
        z = kandidati[0][2] if kandidati and kandidati[0][0] >= PRAH else None
        if z is None:
            r["schvaleni"].update(stav="ceka_na_zm")
            continue
        stav = "konecne" if z["vysledek_hlasovani"] == "prijato" and not _zamitnuti(z) else "zm_neschvalilo"
        r["schvaleni"].update(stav=stav, zm_usneseni_id=z["id"], jistota="nase_propojeni")
        z["schvaleni"].update(stav=stav if stav == "konecne" else "neprijato", rada_usneseni_id=r["id"],
                              jistota="nase_propojeni")
