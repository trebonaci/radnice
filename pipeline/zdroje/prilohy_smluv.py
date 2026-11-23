"""Termíny ze smluv o dílo (#205): úryvky o termínu dokončení z příloh smluv v registru smluv.

Registr smluv má jen metadata; termín dokončení je v textu smlouvy (PDF přílohy). Pro smlouvy na stavbu,
které patří ke kartám investic (`data/projekty.json`: původní smlouva a dodatky části s rolí `stavba`):
1. stránka záznamu `https://smlouvy.gov.cz/smlouva/<id>` → odkazy na přílohy `/smlouva/soubor/<n>/<název>`,
2. PDF → `pdftotext -layout` po stranách,
3. uloží se **jen úryvky** kolem slov o termínu (dokončení, předání díla, doba plnění) – ne celý text
   (smlouvy obsahují jména a adresy osob, AGENTS.md: velké soubory a osobní údaje do repozitáře nepatří).

Výstup `raw/smlouvy/terminy.json`: {zdroj_id: {url, stazeno, soubory: [{url, sha256, stran, uryvky: [{strana, text}]}]}}.
Smlouva se stahuje jednou (je v souboru → přeskočí se). Nejvýš `MAX_SMLUV` za běh. Naskenované PDF bez textové
vrstvy mají `stran > 0` a žádné úryvky. Datum z úryvku čte až `pipeline/terminy.py` (testovaný kód).

Spouští se z `python -m pipeline.zdroje.registr_smluv` (stejný zdroj, krok v `beh.yml` už existuje).
Z prostředí Clauda registr nejde – stahuje běh v Actions.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

from pipeline.zdroje.zapisy_mesta import ChybaZdroje, extrahuj_pdftotext, ziskej_url

KOREN = Path(__file__).resolve().parents[2]
ZAKLAD = "https://smlouvy.gov.cz/smlouva/"
MAX_SMLUV = 25
MAX_PRILOH = 4
RE_PRILOHA = re.compile(r'href="([^"]*/smlouva/soubor/\d+/[^"]+)"', re.I)
RE_KLIC = re.compile(r"term[ií]n\w*\s+(dokon[čc]en|p[řr]ed[aá]n|pln[ěe]n|proveden)|dokon[čc]it\s+d[ií]lo|"
                     r"p[řr]edat\s+(d[ií]lo|stavbu)|doba\s+(pln[ěe]n|proveden)|lh[ůu]t\w*\s+(?:pro\s+)?(pln[ěe]n|dokon[čc]en)", re.I)
OKOLI = 350
RE_OSOBNI = re.compile(
    r"kontakt\w*|zastoup\w+|jedn[aá]\w*\s+jm[ée]nem|jm[ée]nem|bytem|bydli\w+|trval\w+\s+pobyt\w*|"
    r"s[ií]dlo\w*|adres\w+|e-?mail\w*|\btel(?:efon\w*)?\b\.?|\bmobil\w*|podpis\w*|za\s+(?:objednatele|zhotovitele|prod[aá]vaj[ií]c[ií]ho)|"
    r"I[ČC]O?\b|DI[ČC]\b|[\w.+-]+@[\w-]+\.\w+|\+?\d{3}\s?\d{3}\s?\d{3}\b|\b\d{3}\s?\d{2}\s+[A-ZČŘŠŽÝÁÍÉ]\w+|"
    r"datum\s+narozen\w*|r\.\s?[čc]\.|nar\.", re.I)


def smlouvy_ke_stazeni(projekty: list[dict]) -> list[tuple[str, str]]:
    """[(zdroj_id, url záznamu)] smluv na stavbu a jejich dodatků z karet investic."""
    vysledek = {}
    for k in projekty:
        for c in k.get("casti", []):
            if c.get("role") != "stavba":
                continue
            for d in [c.get("puvodni") or {}] + list(c.get("dodatky") or []):
                zid, url = d.get("zdroj_id"), d.get("url")
                if zid and zid.startswith("rs-") and url:
                    vysledek[zid] = url
    return sorted(vysledek.items())


def odkazy_priloh(stranka: str, zaklad: str = ZAKLAD) -> list[str]:
    videno = []
    for h in RE_PRILOHA.findall(stranka):
        u = urljoin(zaklad, html.unescape(h))
        if u not in videno:
            videno.append(u)
    return videno


def _bez_osobnich(t: str, m: re.Match) -> tuple[int, int]:
    """Meze úryvku kolem shody; okolí s osobními údaji (kontakt, podpis, adresa, e-mail, telefon) se odřízne.

    Je-li značka osobních údajů v okolí před klíčem, úryvek začíná až klíčem; je-li za ním, končí před ní.
    """
    od, do = max(0, m.start() - 80), min(len(t), m.end() + OKOLI)
    pred = [x for x in RE_OSOBNI.finditer(t, od, m.start())]
    if pred:
        od = m.start()
    po = RE_OSOBNI.search(t, m.end(), do)
    if po:
        do = po.start()
    return od, max(do, m.end())


def uryvky(strany: list[str]) -> list[dict]:
    """Úryvky textu kolem zmínek o termínu (mezery sjednocené, ±OKOLI znaků, překryvy sloučené).

    Okolí s osobními údaji se do úryvku nedostane (AGENTS.md: jména fyzických osob se neukládají)."""
    vysledek = []
    for i, s in enumerate(strany, 1):
        t = " ".join(s.split())
        useky = []
        for m in RE_KLIC.finditer(t):
            od, do = _bez_osobnich(t, m)
            if useky and od <= useky[-1][1]:
                useky[-1][1] = max(useky[-1][1], do)
            else:
                useky.append([od, do])
        vysledek += [{"strana": i, "text": t[od:do]} for od, do in useky]
    return vysledek


def stahni(koren: Path = KOREN, ziskej=ziskej_url, extrahuj=extrahuj_pdftotext, dnes: date | None = None,
           max_smluv: int = MAX_SMLUV) -> tuple[int, list[str]]:
    projekty_cesta = koren / "data" / "projekty.json"
    if not projekty_cesta.exists():
        return 0, []
    projekty = json.loads(projekty_cesta.read_text(encoding="utf-8"))
    cil = koren / "raw" / "smlouvy" / "terminy.json"
    ulozeno = json.loads(cil.read_text(encoding="utf-8")) if cil.exists() else {}
    chyby, nove = [], 0
    for zid, url in smlouvy_ke_stazeni(projekty):
        if zid in ulozeno or nove >= max_smluv:
            continue
        try:
            stranka = ziskej(url).decode("utf-8", "replace")
            soubory = []
            for u in odkazy_priloh(stranka)[:MAX_PRILOH]:
                if not u.lower().split("?")[0].endswith(".pdf"):
                    soubory.append({"url": u, "preskoceno": "není PDF"})
                    continue
                obsah = ziskej(u)
                strany = extrahuj(obsah)
                soubory.append({"url": u, "sha256": hashlib.sha256(obsah).hexdigest(), "stran": len(strany),
                                "uryvky": uryvky(strany)})
        except ChybaZdroje as e:
            chyby.append(f"{zid}: {e}")
            continue
        ulozeno[zid] = {"url": url, "stazeno": (dnes or date.today()).isoformat(), "soubory": soubory}
        nove += 1
    if nove:
        cil.parent.mkdir(parents=True, exist_ok=True)
        cil.write_text(json.dumps(dict(sorted(ulozeno.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return nove, chyby


def main() -> int:
    nove, chyby = stahni()
    print(f"Termíny ze smluv: {nove} nových smluv")
    for c in chyby:
        print("CHYBA", c, file=sys.stderr)
    return 1 if chyby and not nove else 0


if __name__ == "__main__":
    sys.exit(main())
