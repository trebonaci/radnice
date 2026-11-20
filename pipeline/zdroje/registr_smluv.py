"""Registr smluv: měsíční XML dumpy (https://data.smlouvy.gov.cz/, `index.xml`) → záznamy sledovaných subjektů.

- Dump `dump_<RRRR>_<MM>.xml` obsahuje metadata všech záznamů zveřejněných v daném měsíci; aktuální měsíc
  se přegenerovává denně a i starší dumpy se mohou změnit (znepřístupnění, opravy) → zpracuje se každý
  dump, jehož hash v indexu se liší od posledně zpracovaného.
- Dumpy mají stovky MB: stahují se do dočasného souboru, čtou proudově a zahodí se. Uloží se jen záznamy,
  kde je sledovaný subjekt (IČO s `smlouvy: true` v `config/subjekty.yaml`) subjektem nebo smluvní stranou:
  `raw/smlouvy/<RRRR>-<MM>.json` (bez příloh, jinak beze změny polí) + `raw/smlouvy/manifest.json`.
- Zpětné doplnění historie: nejvýš `MAX_DUMPU` dumpů za běh, nejnovější první.

Spuštění: `python -m pipeline.zdroje.registr_smluv` (v GitHub Actions).
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Callable, IO

import yaml

KOREN = Path(__file__).resolve().parents[2]
INDEX_URL = "https://data.smlouvy.gov.cz/index.xml"
NS_INDEX = "{http://portal.gov.cz/rejstriky/ISRS/1.2/}"
OD = (2016, 7)              # registr smluv od 1. 7. 2016
MAX_DUMPU = 5               # za jeden běh (zpětné doplnění historie po částech)
USER_AGENT = "trebonaci-radnice/0.1 (+https://github.com/trebonaci/radnice; obcansky prehled)"


def otevri_http(url: str) -> IO[bytes]:
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=300)


def sledovana_ico(koren: Path) -> set[str]:
    subjekty = yaml.safe_load((koren / "config" / "subjekty.yaml").read_text(encoding="utf-8"))
    return {s["ico"] for s in subjekty if s.get("smlouvy")}


def mesicni_dumpy(index_xml: bytes) -> list[dict]:
    """[{klic: 'RRRR-MM', url, hash, dokonceny}] jen měsíčních dumpů (bez denních), od OD."""
    koren = ET.fromstring(index_xml)
    vysledek = []
    for d in koren.iter(f"{NS_INDEX}dump"):
        if d.find(f"{NS_INDEX}den") is not None:
            continue
        rok, mesic = int(d.findtext(f"{NS_INDEX}rok")), int(d.findtext(f"{NS_INDEX}mesic"))
        if (rok, mesic) < OD:
            continue
        vysledek.append({"klic": f"{rok}-{mesic:02d}", "url": d.findtext(f"{NS_INDEX}odkaz"),
                         "hash": d.findtext(f"{NS_INDEX}hashDumpu"),
                         "dokonceny": d.findtext(f"{NS_INDEX}dokoncenyMesic") == "1"})
    return sorted(vysledek, key=lambda x: x["klic"])


def _lokalni(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _na_slovnik(e: ET.Element):
    """Prvek → slovník (opakované prvky jako seznam); listy jako text."""
    deti = list(e)
    if not deti:
        return (e.text or "").strip()
    v: dict = {}
    for c in deti:
        k = _lokalni(c.tag)
        if k == "prilohy":
            continue
        hodnota = _na_slovnik(c)
        if k in v:
            v[k] = v[k] if isinstance(v[k], list) else [v[k]]
            v[k].append(hodnota)
        else:
            v[k] = hodnota
    return v


def vyber_zaznamy(soubor: IO[bytes], ico: set[str], znama_id: set[str] | None = None) -> tuple[list[dict], int]:
    """Projde dump proudově; vrátí (záznamy se sledovaným IČO, počet všech záznamů). Vezme i novější verzi
    už známé smlouvy (`znama_id`), ze které sledované IČO zmizelo – jinak by dál platila stará verze
    (Codex P2, #75)."""
    znama_id = znama_id or set()
    vybrane, celkem = [], 0
    for udalost, e in ET.iterparse(soubor, events=("end",)):
        if _lokalni(e.tag) != "zaznam":
            continue
        celkem += 1
        ica = {x.text.strip() for x in e.iter() if _lokalni(x.tag) == "ico" and x.text}
        id_sml = next((x.text.strip() for x in e.iter() if _lokalni(x.tag) == "idSmlouvy" and x.text), None)
        if ica & ico or id_sml in znama_id:
            vybrane.append(_na_slovnik(e))
        e.clear()
    return vybrane, celkem


def _zastarale(manifest: dict, d: dict, ico: set[str]) -> bool:
    """Dump je třeba zpracovat znovu, když se změnil hash nebo množina sledovaných IČO."""
    m = manifest.get(d["klic"], {})
    return m.get("hash") != d["hash"] or m.get("ico") != sorted(ico)


def stahni(koren: Path = KOREN, otevri: Callable[[str], IO[bytes]] = otevri_http,
           max_dumpu: int = MAX_DUMPU) -> tuple[list[str], list[str]]:
    adresar = koren / "raw" / "smlouvy"
    cesta_manifestu = adresar / "manifest.json"
    manifest = json.loads(cesta_manifestu.read_text(encoding="utf-8")) if cesta_manifestu.exists() else {}
    ico = sledovana_ico(koren)
    zmeny, chyby = [], []
    try:
        with otevri(INDEX_URL) as r:
            dumpy = mesicni_dumpy(r.read())
    except Exception as e:  # noqa: BLE001
        return [], [f"index: {e}"]
    if not dumpy:
        return [], ["index: žádné měsíční dumpy"]
    k_zpracovani = [d for d in reversed(dumpy) if _zastarale(manifest, d, ico)][:max_dumpu]
    znama_id = {str(z.get("identifikator", {}).get("idSmlouvy")) for f in adresar.glob("*-*.json")
                for z in json.loads(f.read_text(encoding="utf-8"))} if adresar.exists() else set()
    for d in k_zpracovani:
        try:
            with tempfile.TemporaryFile() as tmp:
                with otevri(d["url"]) as r:
                    shutil.copyfileobj(r, tmp)
                tmp.seek(0)
                zaznamy, celkem = vyber_zaznamy(tmp, ico, znama_id)
        except Exception as e:  # noqa: BLE001 – ohlásit, zbytek dávky dál
            chyby.append(f"{d['klic']}: {e}")
            continue
        if celkem == 0:
            chyby.append(f"{d['klic']}: dump bez záznamů – ponechána poslední data")
            continue
        zaznamy.sort(key=lambda z: (z.get("casZverejneni", ""), z.get("identifikator", {}).get("idVerze", "")))
        adresar.mkdir(parents=True, exist_ok=True)
        cil = adresar / f"{d['klic']}.json"
        obsah = json.dumps(zaznamy, ensure_ascii=False, indent=1) + "\n"
        if not cil.exists() or cil.read_text(encoding="utf-8") != obsah:
            tmp_cil = cil.with_suffix(".json.tmp")
            tmp_cil.write_text(obsah, encoding="utf-8")
            tmp_cil.replace(cil)
            zmeny.append(cil.name)
        # Rozpracovaný (aktuální) měsíc se do manifestu nezapisuje: jeho dump se mění denně a samotná změna
        # hashe nesmí zakládat PR (Codex P2, #75); zpracuje se při každém běhu, změní se jen při změně výběru.
        if d["dokonceny"]:
            manifest[d["klic"]] = {"url": d["url"], "hash": d["hash"], "ico": sorted(ico),
                                   "zaznamu_sledovanych": len(zaznamy)}
        else:
            manifest.pop(d["klic"], None)
        novy = json.dumps(dict(sorted(manifest.items())), ensure_ascii=False, indent=2) + "\n"
        if not cesta_manifestu.exists() or cesta_manifestu.read_text(encoding="utf-8") != novy:
            cesta_manifestu.write_text(novy, encoding="utf-8")
    zbyva = sum(1 for d in dumpy if _zastarale(manifest, d, ico))
    if zbyva:
        print(f"Registr smluv: zbývá zpracovat {zbyva} dumpů (příští běhy)")
    return zmeny, chyby


def main() -> int:
    zmeny, chyby = stahni()
    for z in zmeny:
        print("změněno:", z)
    for c in chyby:
        print("CHYBA:", c, file=sys.stderr)
    print(f"Registr smluv: změněno {len(zmeny)} souborů, chyb {len(chyby)}")
    return 1 if chyby else 0


if __name__ == "__main__":
    sys.exit(main())
