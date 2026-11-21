"""Samostatný náhled datového přehledu (#177): python -m web.nahled [výstup.html]

Vloží data/ukazatele.json, radnice.css a radnice.js do jedné stránky ke schválení (bez WordPressu)."""
import json
import sys
from pathlib import Path

KOREN = Path(__file__).resolve().parent.parent
MODUL = KOREN / "web" / "radnice"


def sestav() -> str:
    data = json.loads((KOREN / "data" / "ukazatele.json").read_text(encoding="utf-8"))
    css = (MODUL / "radnice.css").read_text(encoding="utf-8")
    js = (MODUL / "radnice.js").read_text(encoding="utf-8")
    vlozena = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!DOCTYPE html><html lang="cs"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Přehled radnice – náhled</title><style>body{{margin:0;background:#fbfaf7;font:16px/1.5 system-ui,sans-serif}}{css}</style></head><body>
<main class="trb-radnice" id="trb-radnice" data-src="">
<header class="trb-radnice__hlava"><span class="trb-radnice__stitek">Přehled radnice · náhled, neschváleno ke zveřejnění</span>
<h1>Co se děje na radnici</h1>
<p class="trb-radnice__lead">Co rada a zastupitelstvo projednávají, jaké smlouvy a zakázky město a jeho organizace uzavírají a kam jdou investice. Čísla počítá kód z veřejných zdrojů uvedených u každého údaje.</p></header>
<div class="trb-radnice__obsah" aria-live="polite"></div>
<p class="trb-radnice__pata">Nejde o web Města Třeboň. Data pocházejí z veřejných zdrojů uvedených u každého údaje.</p></main>
<script>window.TRB_RADNICE_DATA={vlozena};</script><script>{js}</script></body></html>
"""


if __name__ == "__main__":
    vystup = Path(sys.argv[1] if len(sys.argv) > 1 else "nahled-radnice.html")
    vystup.write_text(sestav(), encoding="utf-8")
    print(vystup)
