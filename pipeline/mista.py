"""Karty míst a služeb (měkké aktivity, #183) a proud „Co se mění“ → `data/mista.json`, `data/zmeny.json`.

Rozhodnutí Ondřeje 21. 11. 2026: měkké aktivity se uspořádají jako karty míst a služeb (knihovna, DPS,
sportovní hala…). Karta sbírá změny z usnesení (`pro_obcany`, „Co se mění pro vás“) i investice a položky
zásobníku do toho místa; místo je bod na mapě. Pod tím proud „Co se mění“ – všechny změny podle data.
Katalog míst je ruční (`data/mista.yaml`): přiřazení změny podle vzoru = naše propojení, investice a zásobník
podle id = doloženo ručně. Text změny je AI výstup s ověřenou citací (`pro_obcany_ai`, `overeni` usnesení).
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from pipeline import mapa as modul_mapa

OBLASTI = {"sport", "kultura", "socialni", "skolstvi", "komunity_spolky", "doprava", "voda_odpady", "jine"}


def nacti(koren: Path) -> list[dict]:
    cesta = koren / "data" / "mista.yaml"
    if not cesta.exists():
        return []
    return (yaml.safe_load(cesta.read_text(encoding="utf-8")) or {}).get("mista") or []


def zkontroluj(mista: list[dict], projekty: list[dict], zasobnik: list[dict]) -> list[str]:
    chyby, ids = [], set()
    for m in mista:
        mid = m.get("id")
        for pole in ("id", "nazev", "oblast"):
            if not m.get(pole):
                chyby.append(f"místa {mid!r}: chybí pole {pole}")
        if mid in ids:
            chyby.append(f"místa {mid}: duplicitní id")
        ids.add(mid)
        if m.get("oblast") and m["oblast"] not in OBLASTI:
            chyby.append(f"místa {mid}: neznámá oblast {m['oblast']!r}")
        for vzor in m.get("zmeny") or []:
            try:
                re.compile(vzor)
            except re.error as e:
                chyby.append(f"místa {mid}: chybný vzor {vzor!r}: {e}")
    return chyby


def zmeny(data: dict) -> list[dict]:
    """Všechny změny „Co se mění pro vás“ z přijatých usnesení, nejnovější první."""
    jednani = {j["id"]: j for j in data["jednani"]}
    url_dokumentu = {j["dokument"]["dokument_id"]: j["dokument"]["url"] for j in data["jednani"] if j.get("dokument")}
    vysledek = []
    for u in data["usneseni"]:
        po = u.get("pro_obcany")
        if not po or u.get("vysledek_hlasovani") != "prijato":
            continue
        c = po.get("citace") or {}
        url = url_dokumentu.get(c.get("dokument_id"))
        strany = c.get("strany") or []
        j = jednani.get(u["jednani_id"], {})
        vysledek.append({"id": f"zmena-{u['id']}", "text": po["text"], "kdo": po.get("kdo"), "oblast": po.get("oblast"),
                         "plati_od": po.get("plati_od"), "datum": j.get("datum"), "organ": j.get("organ"),
                         "usneseni_id": u["id"], "usneseni_cislo": u.get("cislo"),
                         "ukony": sorted({x["ukon"] for x in u.get("ukony") or [] if x.get("ukon")}),
                         "url": f"{url}#page={strany[0]}" if url and strany else url,
                         "pro_obcany_ai": bool(u.get("pro_obcany_ai")), "overeni": u.get("overeni"), "misto_id": None,
                         "misto_jistota": None})
    return sorted(vysledek, key=lambda z: (z["datum"] or "", z["usneseni_id"]), reverse=True)


def sestav(koren: Path, data: dict, projekty: list[dict], zasobnik: list[dict]) -> tuple[list[dict], list[dict], list[str]]:
    katalog = nacti(koren)
    chyby = zkontroluj(katalog, projekty, zasobnik)
    if chyby:
        return [], [], chyby
    vsechny = zmeny(data)
    karty = {p["id"]: p for p in projekty}
    polozky = {z["id"]: z for z in zasobnik if z["typ"] == "polozka"}
    ruian = modul_mapa.Ruian(koren)
    vysledek = []
    for m in katalog:
        moje = []
        for z in vsechny:
            text = f"{z['kdo'] or ''} {z['text']}"
            if z["misto_id"] is None and any(re.search(v, text) for v in m.get("zmeny") or []):
                z["misto_id"], z["misto_jistota"] = m["id"], "nase_propojeni"
                moje.append(z["id"])
        casti, ch, _ = modul_mapa.vyres_rucni(m.get("misto") or [], ruian, f"místo {m['id']}")
        chyby += ch
        vysledek.append({
            "id": m["id"], "nazev": m["nazev"], "oblast": m["oblast"], "popis": m.get("popis"),
            "zmeny": moje,
            # karta nebo položka, která (zatím) neexistuje – např. automatická karta mimo stažená data – se vynechá
            "investice": [{"id": i, "nazev": karty[i]["nazev"], "faze": karty[i].get("faze"), "jistota": "dolozeno"}
                          for i in m.get("investice") or [] if i in karty],
            "zasobnik": [{"id": i, "nazev": polozky[i]["nazev"], "pripravenost": polozky[i]["pripravenost"]["nazev"],
                          "jistota": "dolozeno"} for i in m.get("zasobnik") or [] if i in polozky],
            "misto": casti, "geometrie": modul_mapa._geometrie(casti),
            "posledni_zmena": max((z["datum"] for z in vsechny if z["id"] in moje and z["datum"]), default=None),
        })
    return vysledek, vsechny, chyby
