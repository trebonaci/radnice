"""Rozpočet města a přehled rozpočtových opatření (PDF finančního odboru) → `raw/rozpocet/` (#129).

Stránka `…/odbor-financni-a-majetkovy/rozpocet.html` odkazuje na
- „Rozpočet města Třeboně na rok RRRR.pdf“ (schválený rozpočet: usnesení ZM, zmocnění rady k RO,
  tabulky příjmů a výdajů po ORJ, paragrafech a akcích),
- „Rozpoctova_opatreni_schvalena do DD_MM_RRRR.pdf“ (souhrnný přehled RO za rok, v tis. Kč).
Každý dokument se stáhne, převede `pdftotext -layout` na text po stranách a uloží do
`raw/rozpocet/<rok>/<druh>/strana-N.txt`; `raw/rozpocet/manifest.json` drží URL, sha256 a datum stažení.
Nový text se zapíše jen při změně obsahu (sha256). Chyba jednoho dokumentu nezastaví ostatní ani běh.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import sys
import urllib.parse
from datetime import date
from pathlib import Path

from pipeline.zdroje.zapisy_mesta import ChybaZdroje, extrahuj_pdftotext, ziskej_url

STRANKA = ("https://www.mesto-trebon.cz/cz/mestsky-urad-trebon/organizacni-struktura/"
           "odbor-financni-a-majetkovy/rozpocet.html")
ZAKLAD = "https://www.mesto-trebon.cz/"
RE_ODKAZ = re.compile(r'href="([^"]+\.pdf)"', re.I)
DRUHY = (
    ("rozpocet", re.compile(r"Rozpočet města Třeboně na rok (\d{4})\.pdf$", re.I)),
    ("rozpoctova_opatreni", re.compile(r"Rozpoctova_opatreni_schvalena do (\d{1,2})_(\d{1,2})_(\d{4})\.pdf$", re.I)),
)
MIN_ZNAKU = 500


def najdi_dokumenty(stranka_html: str, od_roku: int) -> list[dict]:
    """Odkazy na rozpočet a přehled RO od roku `od_roku` (u RO jen nejnovější za rok)."""
    vysledek: dict[tuple, dict] = {}
    for href in RE_ODKAZ.findall(stranka_html):
        # web města vkládá do odkazů i nezakódovanou diakritiku a mezery → zakódovat (už zakódované %XX ponechat)
        url = urllib.parse.quote(urllib.parse.urljoin(ZAKLAD, html.unescape(href)), safe=":/%?=&#~")
        soubor = urllib.parse.unquote(url.rsplit("/", 1)[-1])
        for druh, vzor in DRUHY:
            m = vzor.search(soubor)
            if not m:
                continue
            rok = int(m[m.lastindex])
            if rok < od_roku:
                continue
            # datum z názvu (u RO „do D_M_RRRR“): pořadí odkazů na stránce nesmí vrátit starší přehled
            datum = (rok, int(m[2]), int(m[1])) if m.lastindex == 3 else (rok, 0, 0)
            stary = vysledek.get((druh, rok))
            if stary is None or datum > stary["_datum"]:
                vysledek[(druh, rok)] = {"druh": druh, "rok": rok, "url": url, "soubor": soubor,
                                         "_datum": datum}
    return [{k: v for k, v in d.items() if k != "_datum"}
            for d in sorted(vysledek.values(), key=lambda d: (d["rok"], d["druh"]))]


def stahni(koren: Path, ziskej=ziskej_url, extrahuj=extrahuj_pdftotext, dnes: date | None = None,
           od_roku: int = 2026) -> list[str]:
    """Stáhne dokumenty a zapíše texty; vrací seznam upozornění (prázdný = vše v pořádku)."""
    dnes = dnes or date.today()
    cil = koren / "raw" / "rozpocet"
    manifest_cesta = cil / "manifest.json"
    manifest = json.loads(manifest_cesta.read_text(encoding="utf-8")) if manifest_cesta.exists() else {}
    upozorneni = []
    zmena = False
    try:
        stranka = ziskej(STRANKA).decode("utf-8", "replace")
    except ChybaZdroje as e:
        return [f"stránka rozpočtu: {e}"]
    dokumenty = najdi_dokumenty(stranka, od_roku)
    if not dokumenty:
        return ["na stránce rozpočtu nejsou odkazy na rozpočet ani přehled RO"]
    for d in dokumenty:
        klic = f"{d['rok']}/{d['druh']}"
        try:
            obsah = ziskej(d["url"])
            sha = hashlib.sha256(obsah).hexdigest()
            if manifest.get(klic, {}).get("sha256") == sha:
                continue                      # beze změny – manifest ani texty se nepřepisují
            strany = extrahuj(obsah)
            if sum(len(s.strip()) for s in strany) < MIN_ZNAKU:
                raise ChybaZdroje("málo textu (sken nebo prázdný dokument)")
        except (ChybaZdroje, OSError, ValueError) as e:
            upozorneni.append(f"{klic}: {e}")
            continue
        adresar = cil / str(d["rok"]) / d["druh"]
        nove = adresar.with_name(adresar.name + ".nove")
        zaloha = adresar.with_name(adresar.name + ".stare")
        try:
            for tmp in (nove, zaloha):
                if tmp.exists():
                    shutil.rmtree(tmp)
            nove.mkdir(parents=True)
            for i, text in enumerate(strany, start=1):
                (nove / f"strana-{i}.txt").write_text(text, encoding="utf-8")
            if adresar.exists():
                adresar.rename(zaloha)
            try:
                nove.rename(adresar)
            except OSError:
                if zaloha.exists() and not adresar.exists():
                    zaloha.rename(adresar)
                raise
            if zaloha.exists():
                shutil.rmtree(zaloha)
        except OSError as e:
            shutil.rmtree(nove, ignore_errors=True)
            upozorneni.append(f"{klic}: zápis selhal, ponechána předchozí data ({e})")
            continue
        manifest[klic] = {"url": d["url"], "soubor": d["soubor"], "sha256": sha, "stran": len(strany),
                          "stazeno": dnes.isoformat()}
        zmena = True
    if not zmena:
        return upozorneni
    cil.mkdir(parents=True, exist_ok=True)
    manifest_cesta.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                              encoding="utf-8")
    return upozorneni


if __name__ == "__main__":
    chyby = stahni(Path(__file__).resolve().parents[2])
    for c in chyby:
        print("UPOZORNĚNÍ:", c)
    sys.exit(1 if chyby else 0)
