"""Samostatný náhled přehledu radnice (#177, #187) bez WordPressu.

    python -m web.nahled nahled.html [--sablona CESTA_K_TREBONACI_THEME]

Vloží data (prehled, ukazatele, beh) a styl i skript stránky. S `--sablona` použije skutečné tokeny,
základ, layout a hero ze šablony trebonaci-theme (soubory šablony se do repozitáře nekopírují)."""
import argparse
import json
from pathlib import Path

KOREN = Path(__file__).resolve().parent.parent
MODUL = KOREN / "web" / "radnice"
SABLONA_CSS = ("css/01-tokens.css", "css/02-base.css", "css/03-layout.css", "css/components/hero.css")


def _data(nazev):
    cesta = KOREN / "data" / f"{nazev}.json"
    return json.loads(cesta.read_text(encoding="utf-8")) if cesta.exists() else None


def sestav(sablona: Path | None = None) -> str:
    data = {"prehled": _data("prehled"), "ukazatele": _data("ukazatele"), "beh": _data("beh")}
    css_sablony = "\n".join((sablona / c).read_text(encoding="utf-8") for c in SABLONA_CSS if sablona and (sablona / c).exists())
    css = (MODUL / "css" / "pages" / "radnice-prehled.css").read_text(encoding="utf-8")
    js = (MODUL / "js" / "radnice-prehled.js").read_text(encoding="utf-8")
    php = (MODUL / "page-radnice-prehled.php").read_text(encoding="utf-8")
    telo = php[php.index("<main"):php.index("</main>") + len("</main>")]
    telo = telo.replace("<?php the_title(); ?>", "Co se děje na radnici")
    for atribut in ("data-prehled", "data-ukazatele", "data-beh"):
        zacatek = telo.index(atribut + '="')
        konec = telo.index('"', zacatek + len(atribut) + 2)
        telo = telo[:zacatek] + atribut + '=""' + telo[konec + 1:]
    vlozena = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!DOCTYPE html><html lang="cs"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Přehled radnice – náhled</title><style>{css_sablony}
{css}</style></head><body class="page-template-page-radnice-prehled">
<p style="margin:0;padding:8px 24px;background:#fff3cd;font:14px system-ui">Náhled mimo WordPress · neschváleno ke zveřejnění · hlavička a patička webu chybí</p>
{telo}
<script>window.TRB_RADNICE_DATA={vlozena};</script><script>{js}</script></body></html>
"""


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("vystup", nargs="?", default="nahled-radnice.html")
    a.add_argument("--sablona", type=Path)
    args = a.parse_args()
    Path(args.vystup).write_text(sestav(args.sablona), encoding="utf-8")
    print(args.vystup)
