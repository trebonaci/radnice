"""Datum ukončení plnění stavební smlouvy z E-ZAK (#207, archiv dokončených projektů po letech).

XML export E-ZAK uvádí jen stav „ukončeno plnění“, datum je jen na HTML stránce zakázky
(`contract_display_<n>.html`, oddíl „Plnění smlouvy na základě veřejné zakázky“: „Plnění smlouvy ukončeno 07.05.2026“).
Pro stavební zakázky karet investic (`data/projekty.json`) ve stavu „ukončeno plnění“ stáhne stránku a uloží
do `raw/ezak/plneni.json` jen doslovné věty „Plnění smlouvy ukončeno DD.MM.RRRR“ (+ sha256 stránky).
Každá zakázka se stahuje jednou (datum se už nemění). Datum čte `pipeline/sestav.py` (`ukonceni_plneni`).
Spouští se z `python -m pipeline.zdroje.ezak` (krok E-ZAK v `beh.yml`), chyba běh nezastaví.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import date
from pathlib import Path

KOREN = Path(__file__).resolve().parents[2]
RE_UKONCENO = re.compile(r"Plnění smlouvy ukončeno \d{2}\.\d{2}\.\d{4}")


def citace(stranka: str) -> list[str]:
    text = " ".join(re.sub(r"<[^>]+>", " ", html.unescape(stranka)).split())
    return list(dict.fromkeys(RE_UKONCENO.findall(text)))


def ke_stazeni(projekty: list[dict]) -> list[tuple[str, str]]:
    vysledek = {}
    for k in projekty:
        for z in k.get("zakazky", []):
            if z.get("role") == "stavba" and z.get("url") and any(
                    c.get("stav") == "ukončeno plnění" for c in z.get("casti", [])):
                vysledek[z["id"]] = z["url"]
    return sorted(vysledek.items())


def stahni(koren: Path = KOREN, ziskej=None, dnes: date | None = None) -> tuple[int, list[str]]:
    if ziskej is None:
        from pipeline.zdroje.ezak import ziskej_http as ziskej
    cesta_p = koren / "data" / "projekty.json"
    if not cesta_p.exists():
        return 0, []
    cil = koren / "raw" / "ezak" / "plneni.json"
    ulozeno = json.loads(cil.read_text(encoding="utf-8")) if cil.exists() else {}
    nove, chyby = 0, []
    for zid, url in ke_stazeni(json.loads(cesta_p.read_text(encoding="utf-8"))):
        if ulozeno.get(zid, {}).get("citace"):
            continue
        try:
            obsah = ziskej(url)
        except Exception as e:  # noqa: BLE001 – jedna stránka nesmí shodit ostatní
            chyby.append(f"{zid}: {e}")
            continue
        ulozeno[zid] = {"url": url, "stazeno": (dnes or date.today()).isoformat(),
                        "sha256": hashlib.sha256(obsah).hexdigest(),
                        "citace": citace(obsah.decode("utf-8", "replace"))}
        nove += 1
    if nove:
        cil.parent.mkdir(parents=True, exist_ok=True)
        cil.write_text(json.dumps(dict(sorted(ulozeno.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return nove, chyby
