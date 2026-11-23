"""Šest okruhů webu (audit 23. 11. 2026): téma → okruh pro všechny výstupy.

Číselník je v `config/okruhy.yaml`. Každá položka dostane `okruh` a `okruh_podle` (odkud okruh je):
- `téma` – vlastní téma položky (`oblast`),
- `osa SPRM` – osa a opatření námětu ze Strategického plánu,
- `název` – vzor v názvu (naše propojení),
- `bez tématu` – nic z toho; položka spadne do Rozvoje a správy města.

Usnesení může patřit do víc okruhů (`okruhy`, `okruhy_podle`): podle kategorií, podle karty projektu nebo
změny, které na usnesení odkazují, a podle vzoru v názvu. `okruh` je hlavní okruh – nejvíc doložený
věcný okruh (ne Rozvoj a správa), jinak Rozvoj a správa města.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ZBYTEK = "rozvoj_sprava"


def nacti(koren: Path) -> dict:
    cfg = yaml.safe_load((koren / "config" / "okruhy.yaml").read_text(encoding="utf-8"))
    cfg["_okruh_tematu"] = {t: o["id"] for o in cfg["okruhy"] for t in o["temata"]}
    cfg["_poradi"] = [o["id"] for o in cfg["okruhy"]]
    cfg["_vzory"] = [(v["id"], v["tema"], re.compile(v["vzor"], re.I)) for v in cfg.get("vzory") or []]
    return cfg


def zkontroluj(cfg: dict, kategorie: dict) -> list[str]:
    chyby = []
    temata = cfg["temata"]
    videno: dict[str, str] = {}
    for o in cfg["okruhy"]:
        for t in o["temata"]:
            if t not in temata:
                chyby.append(f"okruhy: okruh {o['id']} má neznámé téma {t!r}")
            if t in videno:
                chyby.append(f"okruhy: téma {t!r} je v okruzích {videno[t]} i {o['id']}")
            videno[t] = o["id"]
    for t in temata:
        if t not in videno:
            chyby.append(f"okruhy: téma {t!r} nemá okruh")
    if ZBYTEK not in cfg["_poradi"]:
        chyby.append(f"okruhy: chybí okruh {ZBYTEK}")
    for k in kategorie:
        if k not in temata and cfg["kategorie_usneseni"].get(k) not in temata:
            chyby.append(f"okruhy: kategorie usnesení {k!r} nemá téma")
    for klic, t in (cfg.get("sprm") or {}).items():
        if t not in temata:
            chyby.append(f"okruhy: SPRM {klic!r} má neznámé téma {t!r}")
    for vid, t, _ in cfg["_vzory"]:
        if t not in temata:
            chyby.append(f"okruhy: vzor {vid} má neznámé téma {t!r}")
    return chyby


def okruh_tematu(cfg: dict, tema: str | None) -> str:
    return cfg["_okruh_tematu"].get(tema) or ZBYTEK


def tema_kategorie(cfg: dict, kategorie: str) -> str:
    if kategorie in cfg["temata"]:
        return kategorie
    return cfg["kategorie_usneseni"].get(kategorie, "jine")


def temata_z_nazvu(cfg: dict, text: str | None) -> list[tuple[str, str]]:
    """Všechny shody vzorů v pořadí číselníku: [(téma, id vzoru)]."""
    return [(t, vid) for vid, t, rx in cfg["_vzory"] if text and rx.search(text)]


def tema_sprm(cfg: dict, osa: str | None, opatreni: str | None) -> str | None:
    sprm = cfg.get("sprm") or {}
    return sprm.get(f"{osa} / {opatreni}") or sprm.get(osa)


def pro_polozku(cfg: dict, polozka: dict, nazev_pole: str = "nazev") -> tuple[str, str]:
    """(okruh, podle) pro položku s jedním okruhem."""
    if polozka.get("oblast") in cfg["temata"]:
        return okruh_tematu(cfg, polozka["oblast"]), "téma"
    tema = tema_sprm(cfg, polozka.get("osa"), polozka.get("opatreni")) if polozka.get("osa") else None
    if tema:
        return okruh_tematu(cfg, tema), "osa SPRM"
    shody = temata_z_nazvu(cfg, polozka.get(nazev_pole)) or temata_z_nazvu(cfg, polozka.get("oblast"))
    if shody:
        return okruh_tematu(cfg, shody[0][0]), "název"
    return ZBYTEK, "bez tématu"


def _serad(cfg: dict, okruhy) -> list[str]:
    return sorted(set(okruhy), key=cfg["_poradi"].index)


def pro_usneseni(cfg: dict, u: dict, odkazy: dict[str, list[tuple[str, str]]]) -> None:
    """Doplní usnesení `okruhy`, `okruhy_podle` a hlavní `okruh`.
    `odkazy`: id usnesení → [(téma, odkud)] z karet projektů a změn, které na usnesení odkazují."""
    podle: dict[str, list[str]] = {}

    def pridej(tema: str, duvod: str) -> None:
        duvody = podle.setdefault(okruh_tematu(cfg, tema), [])
        if duvod not in duvody:
            duvody.append(duvod)

    for k in u.get("kategorie") or []:
        pridej(tema_kategorie(cfg, k), f"kategorie {k}")
    for tema, odkud in odkazy.get(u["id"], []):
        pridej(tema, odkud)
    for tema, vid in temata_z_nazvu(cfg, u.get("tema")):
        pridej(tema, f"název ({vid})")
    if not podle:
        pridej("jine", "bez tématu")
    u["okruhy"] = _serad(cfg, podle)
    u["okruhy_podle"] = {o: podle[o] for o in u["okruhy"]}
    vecne = [o for o in u["okruhy"] if o != ZBYTEK]
    # hlavní okruh: nejvíc doložený věcný okruh (kategorie, karta a změna váží 2, vzor v názvu 1),
    # při shodě dřívější v pořadí číselníku
    vaha = {o: sum(1 if d.startswith("název") else 2 for d in podle[o]) for o in vecne}
    u["okruh"] = max(vecne, key=lambda o: (vaha[o], -cfg["_poradi"].index(o))) if vecne else ZBYTEK


def oznac(cfg: dict, vystup: dict) -> list[str]:
    """Doplní okruhy do výstupů. Vrací chyby (neznámé téma ve výstupu)."""
    chyby = []
    for nazev in ("projekty", "zasobnik", "zmeny", "mista", "harmonogram", "prehled", "mapa", "dotace"):
        for p in vystup.get(nazev) or []:
            if p.get("oblast") and nazev != "dotace" and p["oblast"] not in cfg["temata"]:
                chyby.append(f"{nazev} {p.get('id')}: téma {p['oblast']!r} není v config/okruhy.yaml")
    zasobnik = {}
    for p in vystup.get("zasobnik") or []:
        p["okruh"], p["okruh_podle"] = pro_polozku(cfg, p)
        zasobnik[p["id"]] = (p["okruh"], p["okruh_podle"])
    for p in vystup.get("projekty") or []:
        p["okruh"], p["okruh_podle"] = pro_polozku(cfg, p)
    karty = {p["id"]: (p["okruh"], p["okruh_podle"]) for p in vystup.get("projekty") or []}
    for nazev, pole in (("zmeny", "text"), ("mista", "nazev"), ("harmonogram", "nazev"),
                        ("prehled", "titulek"), ("mapa", "nazev"), ("dotace", "oblast")):
        for p in vystup.get(nazev) or []:
            if not p.get("oblast") or nazev == "dotace":
                prevzato = zasobnik.get(p.get("id")) or karty.get(p.get("karta_id") or p.get("id"))
                if prevzato and nazev != "dotace":
                    p["okruh"], p["okruh_podle"] = prevzato
                    continue
            p["okruh"], p["okruh_podle"] = pro_polozku(cfg, p, pole)
    # usnesení: věcný okruh z karet projektů a změn, které na ně odkazují
    odkazy: dict[str, list[tuple[str, str]]] = {}
    for p in vystup.get("projekty") or []:
        if p.get("oblast") in cfg["temata"]:
            for u in p.get("usneseni") or []:
                odkazy.setdefault(u["id"], []).append((p["oblast"], f"karta {p['id']}"))
    for z in vystup.get("zmeny") or []:
        if z.get("usneseni_id") and z.get("oblast") in cfg["temata"]:
            odkazy.setdefault(z["usneseni_id"], []).append((z["oblast"], f"změna {z['id']}"))
    for u in vystup.get("usneseni") or []:
        pro_usneseni(cfg, u, odkazy)
    return chyby


def ciselnik(cfg: dict) -> list[dict]:
    """data/okruhy.json: okruhy v pořadí webu s tématy a názvy."""
    return [{"id": o["id"], "nazev": o["nazev"], "popis": o["popis"],
             "temata": [{"id": t, "nazev": cfg["temata"][t]} for t in o["temata"]]} for o in cfg["okruhy"]]
