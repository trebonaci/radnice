"""Hlavní důvod uzavření dodatku (#274): z úryvků textu dodatků (`raw/smlouvy/terminy.json`, stahuje
`pipeline/zdroje/prilohy_smluv.py`) čte kód – ne AI – hlavní důvod, proč se dodatek uzavíral.

Dodatky k smlouvám o dílo popisují změnu slovy jako „spočívající ve změně ceny díla / termínu dokončení“,
„vícepráce / méněpráce podle Změnového listu č. N“, „rozšíření předmětu díla“. Kód najde v úryvku tyto
**druhy změny** (normalizované štítky) a ke každému doslovnou `citace` (kontroluje se, že v úryvku je) –
stejný princip jako věcné štítky usnesení. Hlavní druh se vybere podle priority (podstata změny před jejím
důsledkem: vícepráce/méněpráce/rozšíření před změnou ceny/termínu). Úryvek musí patřit dodatku (zmiňuje
„dodatek“ nebo „změnový list“), aby se nepletl obecný text původní smlouvy. Osobní údaje se vynechají.
Výstup `data/duvody_dodatku.json`. Text důvodu je vždy doložen citací, proto `duvod_ai = False`.
"""
from __future__ import annotations

import re

# druh změny → vzor; pořadí je priorita (hlavní důvod = první nalezený): podstata změny před jejím důsledkem
DRUHY = [
    ("vícepráce", r"v[ií]cepr[aá]c\w*|dodate[čc]n[ýíe]\w*\s+(?:stavebn\w*\s+)?prac\w*"),
    ("méněpráce", r"m[ée]n[ěe]pr[aá]c\w*"),
    ("rozšíření předmětu díla", r"roz[šs][ií][řr]en\w*\s+(?:p[řr]edm[ěe]tu|rozsahu)\s+d[ií]la|zm[ěe]n\w*\s+rozsahu\s+d[ií]la"),
    ("změna ceny díla", r"zm[ěe]n[ěaěy]\w*\s+ceny\s+d[ií]la|[úu]prav\w*\s+ceny\s+d[ií]la"),
    ("změna termínu dokončení", r"zm[ěe]n[ěaěy]\w*\s+(?:termínu|doby\s+pln[ěe]n\w*)|prodlou[žz]en\w*\s+(?:termínu|doby\s+pln\w*)"),
]
RE_DRUHY = [(n, re.compile(p, re.I)) for n, p in DRUHY]
# úryvek patří dodatku (ne obecnému textu původní smlouvy)
RE_DODATEK = re.compile(r"dodatk\w*|zm[ěe]nov[ýé]\w*\s+list", re.I)
RE_OSOBNI = re.compile(
    r"bytem|bydli\w+|trval\w+\s+pobyt|s[ií]dlo\w*|adres\w+|e-?mail|\btel\b|mobil|podpis\w*|"
    r"I[ČC]O?\b|DI[ČC]\b|[\w.+-]+@[\w-]+\.\w+|\+?\d{3}\s?\d{3}\s?\d{3}\b|nar\.|datum\s+narozen", re.I)
OKOLI = 90   # citace = okolí klíčového slova, oříznuté na hranici věty


def _citace(text: str, m: re.Match) -> str | None:
    """Doslovný výňatek kolem shody, oříznutý na nejbližší hranici věty/čísla článku. Bez osobních údajů."""
    zac = text.rfind(". ", max(0, m.start() - OKOLI), m.start())
    zac = zac + 2 if zac != -1 else max(0, m.start() - OKOLI)
    kon = re.search(r"[.;]\s|\s+v\s+[čc]l\.|$", text[m.end():m.end() + OKOLI])
    cit = text[zac:m.end() + (kon.start() if kon else OKOLI)].strip(" ,–-\n")
    cit = re.sub(r"\s+", " ", cit)
    return cit if 12 <= len(cit) <= 200 and not RE_OSOBNI.search(cit) else None


def z_uryvku(text: str) -> dict | None:
    """Hlavní druh změny v úryvku dodatku + doslovná citace, nebo None. Úryvek musí patřit dodatku."""
    if not RE_DODATEK.search(text):
        return None
    for druh, rx in RE_DRUHY:            # pořadí = priorita hlavního důvodu
        for m in rx.finditer(text):
            cit = _citace(text, m)
            if cit:
                dalsi = [n for n, r in RE_DRUHY if n != druh and r.search(text)]
                return {"druh": druh, "dalsi": dalsi, "citace": cit}
    return None


def sestav(raw: dict) -> tuple[list[dict], list[str]]:
    """`raw/smlouvy/terminy.json` → seznam důvodů dodatků s doslovnou citací (jen kde se druh změny najde)."""
    vysledek, chyby = [], []
    for zid, zaznam in sorted(raw.items()):
        nalez = None
        for soubor in zaznam.get("soubory", []):
            for u in soubor.get("uryvky", []):
                d = z_uryvku(u["text"])
                if d:
                    if d["citace"] not in re.sub(r"\s+", " ", u["text"]):
                        chyby.append(f"{zid}: citace důvodu není v úryvku")
                        continue
                    nalez = d | {"strana": u["strana"], "url": f"{soubor['url']}#page={u['strana']}"}
                    break
            if nalez:
                break
        if nalez:
            text = nalez["druh"] + (f" (a {', '.join(nalez['dalsi'])})" if nalez["dalsi"] else "")
            vysledek.append({"zdroj_id": zid, "text": text, "druh": nalez["druh"], "dalsi": nalez["dalsi"],
                             "citace": nalez["citace"], "strana": nalez["strana"], "url": nalez["url"],
                             "jistota": "dolozeno", "duvod_ai": False})
    return vysledek, chyby
