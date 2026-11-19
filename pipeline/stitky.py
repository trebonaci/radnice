"""Štítky věcné relevance (issue #18): co se věci týká, s důvodem a citací. Žádné hodnocení.

Pravidla jsou deterministická (kategorie, klíčová slova v textu; `config/stitky.yaml`).
AI může štítek jen navrhnout v anotaci (`stitky:`), vždy s doslovnou citací, a je označen `stitek_ai`.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from pipeline.zapisy import normalizuj

KOREN = Path(__file__).resolve().parent.parent


def nacti_ciselnik(koren: Path | None = None) -> dict:
    return yaml.safe_load(((koren or KOREN) / "config" / "stitky.yaml").read_text(encoding="utf-8"))


def zkontroluj_ciselnik(cfg: dict, kategorie: dict) -> list[str]:
    chyby = []
    ids = set()
    for p in cfg["pravidla"]:
        if p["id"] in ids:
            chyby.append(f"stitky: duplicitní pravidlo {p['id']}")
        ids.add(p["id"])
        if p["stitek"] not in cfg["stitky"]:
            chyby.append(f"stitky: pravidlo {p['id']} odkazuje na neznámý štítek {p['stitek']}")
        if ("kategorie" in p) == ("vzor" in p):
            chyby.append(f"stitky: pravidlo {p['id']} má mít právě jedno z kategorie / vzor")
        if p.get("kategorie") and p["kategorie"] not in kategorie:
            chyby.append(f"stitky: pravidlo {p['id']} má neznámou kategorii {p['kategorie']}")
        if p.get("faze") and p["faze"] not in cfg["faze_investice"]:
            chyby.append(f"stitky: pravidlo {p['id']} má neznámou fázi {p['faze']}")
        if p.get("faze") and p["stitek"] != "investice":
            chyby.append(f"stitky: fáze lze mít jen štítek investice ({p['id']})")
    return chyby


def _zaznam(cfg, kod, zdroj, duvod, citace, ai, faze=None):
    return {"stitek": kod, "skupina": cfg["stitky"][kod]["skupina"], "zdroj": zdroj, "duvod": duvod,
            "citace": citace, "stitek_ai": ai, "faze": faze}


def pravidlove_stitky(cfg: dict, text: str, kategorie: list[str], citace: dict) -> list[dict]:
    """Štítky z pravidel. `text` je veřejný (anonymizovaný) text, `citace` citace usnesení
    ({dokument_id, strany, text}), která se použije u pravidel podle kategorie."""
    vysledek = []
    for p in cfg["pravidla"]:
        if "kategorie" in p:
            if p["kategorie"] in kategorie:
                # kategorie jsou návrh AI → štítek je také označen jako AI
                vysledek.append(_zaznam(cfg, p["stitek"], p["id"], p["duvod"], citace, True))
        else:
            m = re.search(p["vzor"], text, re.IGNORECASE)
            if m:
                c = {"dokument_id": citace["dokument_id"], "strany": citace["strany"], "text": m.group(0)}
                vysledek.append(_zaznam(cfg, p["stitek"], p["id"], p["duvod"], c, False, p.get("faze")))
    return vysledek


def ai_stitky(cfg: dict, navrhy: list[dict], text: str, citace: dict, anon_retezce: list[str],
              kontext: str, chyby: list[str]) -> list[dict]:
    """Štítky navržené AI v anotaci; každý musí mít štítek z číselníku, důvod a citaci doslova v textu."""
    vysledek = []
    for n in navrhy or []:
        kod = n.get("stitek")
        if kod not in cfg["stitky"]:
            chyby.append(f"{kontext}: neznámý štítek {kod!r}")
            continue
        if not n.get("duvod") or not n.get("citace"):
            chyby.append(f"{kontext}: štítek {kod} nemá důvod nebo citaci")
            continue
        if normalizuj(n["citace"]) not in normalizuj(text):
            chyby.append(f"{kontext}: citace štítku {kod} nenalezena: {n['citace']!r}")
            continue
        if any(r in n["citace"] or r in n["duvod"] for r in anon_retezce):
            chyby.append(f"{kontext}: štítek {kod} obsahuje anonymizovaný údaj")
            continue
        faze = n.get("faze")
        if faze is not None and (kod != "investice" or faze not in cfg["faze_investice"]):
            chyby.append(f"{kontext}: neplatná fáze {faze!r} u štítku {kod}")
            continue
        c = {"dokument_id": citace["dokument_id"], "strany": citace["strany"], "text": n["citace"]}
        vysledek.append(_zaznam(cfg, kod, "ai", n["duvod"], c, True, faze))
    return vysledek


def jeden_na_stitek(zaznamy: list[dict]) -> list[dict]:
    """Každý štítek u usnesení jen jednou. Přednost má záznam s fází, pak pravidlo z textu
    (doslovná citace, ne AI), pak ostatní v pořadí pravidel."""
    def poradi(z):
        return (z.get("faze") is None, z.get("stitek_ai", True))
    vybrane: dict[str, dict] = {}
    for z in zaznamy:
        if z["stitek"] not in vybrane or poradi(z) < poradi(vybrane[z["stitek"]]):
            vybrane[z["stitek"]] = z
    return [vybrane[k] for k in dict.fromkeys(z["stitek"] for z in zaznamy)]
