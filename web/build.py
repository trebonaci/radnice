"""Sestavení statického webu radnice.trebonaci.cz (#191) → `_site/index.html`.

    python -m web.build [--vystup _site] [--nahled]

Šablona `web/site/sablona.html` + data z `data/*.json` (vložená do stránky, žádný server ani databáze).
Zveřejnění (rozhodnutí Ondřeje 22. 11. 2026): vzhled a typy obsahu schvaluje Ondřej (větev `verejne`),
denní data z ověřené pipeline jdou ven automaticky. `--nahled` označí stránku jako neschválený náhled."""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

KOREN = Path(__file__).resolve().parent.parent
SABLONA = KOREN / "web" / "site" / "sablona.html"


def _json(nazev: str):
    cesta = KOREN / "data" / f"{nazev}.json"
    return json.loads(cesta.read_text(encoding="utf-8")) if cesta.exists() else []


def _vloz(hodnota) -> str:
    return json.dumps(hodnota, ensure_ascii=False).replace("</", "<\\/")


def _datum(beh: dict) -> str:
    d = (beh or {}).get("zacatek", "")[:10]
    if not d:
        return ""
    r, m, den = d.split("-")
    return f"{int(den)}. {int(m)}. {r}"


def sestav(nahled: bool = False) -> str:
    beh = json.loads((KOREN / "data" / "beh.json").read_text(encoding="utf-8")) if (KOREN / "data" / "beh.json").exists() else {}
    datum = _datum(beh)
    investice = _json("investice")
    stitek = (f"Náhled · data k {datum} · neschváleno ke zveřejnění" if nahled
              else f"Data aktualizována {datum}" if datum else "Data z veřejných zdrojů")
    nahrady = {
        "__DATA__": _vloz(_json("projekty")),
        "__ZASOBNIK__": _vloz(_json("zasobnik")),
        "__MISTA__": _vloz(_json("mista")),
        "__ZMENY__": _vloz(_json("zmeny")),
        "__HARMONOGRAM__": _vloz(_json("harmonogram")),
        "__UKAZATELE__": _vloz(_json("ukazatele")),
        "__INVESTICE__": _vloz((investice or [None])[-1]),
        "__STITEK__": stitek,
        "__DATUM__": datum,
    }
    html = SABLONA.read_text(encoding="utf-8")
    for klic, hodnota in nahrady.items():
        html = html.replace(klic, hodnota)
    zbyle = sorted(set(re.findall(r"__[A-Z]+__", html)))
    if zbyle:
        raise ValueError(f"nenahrazené značky v šabloně: {zbyle}")
    return html


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("--vystup", default="_site")
    a.add_argument("--nahled", action="store_true")
    args = a.parse_args()
    cil = Path(args.vystup)
    cil.mkdir(parents=True, exist_ok=True)
    (cil / "index.html").write_text(sestav(args.nahled), encoding="utf-8")
    # obrázky šablony (logo Třeboňáků)
    shutil.copytree(SABLONA.parent / "obr", cil / "obr", dirs_exist_ok=True)
    # Cloudflare Pages: bez indexování náhledů, základní bezpečnostní hlavičky
    (cil / "_headers").write_text(
        "/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n"
        + ("  X-Robots-Tag: noindex\n" if args.nahled else ""), encoding="utf-8")
    print(cil / "index.html")


if __name__ == "__main__":
    main()
