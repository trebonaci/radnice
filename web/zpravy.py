"""Zprávy pro stránku „Co se děje“ (#244): příprava `data/zpravy.json` pro web.

Nic se tu nevymýšlí ani nepočítá z cizích údajů: zprávy se jen slučují a počítají se zprávy za 30 dní.
Pravidla (zadání docs/navrhy/2026-11-23/README.md, doplnění Ondřeje 23. 11. 2026 v #244):
1. výběr dodavatele (E-ZAK) a smlouva (registr smluv) o téže zakázce = jeden řádek se dvěma zdroji;
   „téže“ = stejný den, stejný dodavatel a stejný projekt, nebo stejná částka,
2. seskupení zpráv k jedné akci (pole `skupina`) se po sloučení přepočítá,
3. KPI = počet zpráv za posledních 30 dní podle okruhu, počítáno k datu dat (ne k datu návštěvy).
"""
from __future__ import annotations

import re
from datetime import date, timedelta

DNI_KPI = 30
RE_DODAVATEL = re.compile(r"dodavatelem\s+(.+?)\.?\s*$")
POLE_WEB = ("id", "druh", "datum", "okruh", "titulek", "shrnuti", "castka", "projekt_id", "zdroje", "jistota",
            "shrnuti_ai", "plati_od", "stitek", "skupina", "druhy")


def dodavatel(zprava: dict) -> str | None:
    """Dodavatel ze šablonového shrnutí smlouvy nebo výběru dodavatele (jinak None)."""
    m = RE_DODAVATEL.search(zprava.get("shrnuti") or "")
    return m.group(1).strip().lower() if m else None


def _hodnota(zprava: dict):
    return (zprava.get("castka") or {}).get("hodnota")


def _stejna_zakazka(vyber: dict, smlouva: dict) -> bool:
    if vyber["datum"] != smlouva["datum"] or not dodavatel(vyber) or dodavatel(vyber) != dodavatel(smlouva):
        return False
    if vyber.get("projekt_id") and vyber.get("projekt_id") == smlouva.get("projekt_id"):
        return True
    h = _hodnota(vyber)
    return h is not None and h == _hodnota(smlouva)


def slouc_vyber_a_smlouvu(zpravy: list[dict]) -> list[dict]:
    """Spojí výběr dodavatele a smlouvu o téže zakázce; výsledek nese `druhy` a oba zdroje."""
    smlouvy = [z for z in zpravy if z["druh"] == "smlouva"]
    pouzite: set[str] = set()
    vysledek = []
    for z in zpravy:
        if z["druh"] == "vyberove_rizeni" and dodavatel(z):
            s = next((x for x in smlouvy if x["id"] not in pouzite and _stejna_zakazka(z, x)), None)
            if s:
                pouzite.add(s["id"])
                castka = z["castka"] if (z.get("castka") or {}).get("s_dph") is not None else s.get("castka") or z.get("castka")
                slite = {**z, "druhy": ["vyberove_rizeni", "smlouva"], "castka": castka,
                         "zdroje": z["zdroje"] + [x for x in s["zdroje"] if x not in z["zdroje"]],
                         "jistota": "naše propojení" if "naše propojení" in (z["jistota"], s["jistota"]) else z["jistota"]}
                if s.get("skupina") and not z.get("skupina"):
                    slite["skupina"] = s["skupina"]
                vysledek.append(slite)
                continue
        vysledek.append(z)
    return [z for z in vysledek if z["id"] not in pouzite]


def prepocitej_skupiny(zpravy: list[dict]) -> list[dict]:
    """Po sloučení přepočítá počet zpráv ve skupině; skupina s jedinou zprávou se zruší."""
    pocty: dict[str, int] = {}
    for z in zpravy:
        if z.get("skupina"):
            pocty[z["skupina"]["id"]] = pocty.get(z["skupina"]["id"], 0) + 1
    vysledek = []
    for z in zpravy:
        s = z.get("skupina")
        if s:
            z = {k: v for k, v in z.items() if k != "skupina"}
            if pocty[s["id"]] > 1:
                z["skupina"] = {**s, "pocet": pocty[s["id"]]}
        vysledek.append(z)
    return vysledek


def kpi_30_dni(zpravy: list[dict], okruhy: list[str], dnes: date) -> dict:
    """Počet zpráv za posledních 30 dní (včetně dne `dnes`) celkem a podle okruhu."""
    od = (dnes - timedelta(days=DNI_KPI - 1)).isoformat()
    do = dnes.isoformat()
    vybrane = [z for z in zpravy if od <= z["datum"] <= do]
    return {"dni": DNI_KPI, "od": od, "do": do, "celkem": len(vybrane),
            "okruhy": {o: sum(1 for z in vybrane if z["okruh"] == o) for o in okruhy}}


def zpravy_pro_web(zpravy: list[dict], okruhy: list[str], dnes: date) -> dict:
    """Zprávy seřazené od nejnovějších (sloučené, seskupené) a KPI pro stránku."""
    sloucene = prepocitej_skupiny(slouc_vyber_a_smlouvu(zpravy))
    sloucene.sort(key=lambda z: (z["datum"], z["id"]), reverse=True)
    return {"zpravy": [{k: z[k] for k in POLE_WEB if k in z} for z in sloucene],
            "kpi": kpi_30_dni(sloucene, okruhy, dnes)}
