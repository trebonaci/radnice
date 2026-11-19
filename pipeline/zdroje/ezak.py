"""Stažení exportů veřejných zakázek z profilů zadavatele E-ZAK (XML podle vyhlášky č. 345/2023 Sb.).

Export `…/profile_display_N.html/XMLdataVZ?od=DDMMRRRR&do=DDMMRRRR` vrací zakázky, u nichž se
v daném období něco změnilo (nejvýš 366 dní na dotaz). Stahujeme po kalendářních letech do
`raw/ezak/<ico>/<rok>.xml`; novější rok obsahuje novější stav zakázky (`pipeline/zakazky.py`).

- Uzavřené roky se stahují, dokud nejsou staženy aspoň týden po svém konci (pak `uzavreno: true`).
- Aktuální rok se stahuje při každém běhu.
- Kontrola před zápisem: odpověď musí být XML s kořenem `profil` a IČO zadavatele musí sedět;
  jinak zůstane poslední správný soubor a chyba se ohlásí.

Spuštění: `python -m pipeline.zdroje.ezak` (v GitHub Actions; z prostředí Clauda web E-ZAK nejde).
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

import yaml

KOREN = Path(__file__).resolve().parents[2]
NS = "{urn:cz:isvz:mmr:schemas:vz-z-profilu-zadavatele:v100}"
PRVNI_ROK = 2019          # profil města má evidenční číslo Z2019-003053
USER_AGENT = "trebonaci-radnice/0.1 (+https://github.com/trebonaci/radnice; obcansky prehled)"
PAUZA_S = 2.0


class ChybaZdroje(Exception):
    pass


def ziskej_http(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as r:
        if r.status != 200:
            raise ChybaZdroje(f"HTTP {r.status}: {url}")
        return r.read()


def profily(koren: Path) -> list[dict]:
    """Subjekty s funkčním XML exportem (`ezak_xml: true` v config/subjekty.yaml)."""
    subjekty = yaml.safe_load((koren / "config" / "subjekty.yaml").read_text(encoding="utf-8"))
    return [s for s in subjekty if s.get("ezak_xml") and s.get("ezak_profil")]


def url_exportu(profil: str, od: date, do: date) -> str:
    return f"{profil}/XMLdataVZ?od={od:%d%m%Y}&do={do:%d%m%Y}"


def zkontroluj_xml(obsah: bytes, ico: str) -> int:
    """Vrátí počet zakázek; při neplatné odpovědi vyhodí ChybaZdroje."""
    try:
        koren = ET.fromstring(obsah)
    except ET.ParseError as e:
        raise ChybaZdroje(f"odpověď není XML ({e})") from e
    if koren.tag != f"{NS}profil":
        raise ChybaZdroje(f"neočekávaný kořen XML {koren.tag!r}")
    ico_xml = koren.findtext(f"{NS}zadavatel/{NS}ico_zadavatele")
    if ico_xml != ico:
        raise ChybaZdroje(f"IČO zadavatele v XML {ico_xml!r} neodpovídá {ico!r}")
    return len(koren.findall(f"{NS}zakazka"))


def potreba_stahnout(rok: int, zaznam: dict | None, dnes: date) -> bool:
    if rok >= dnes.year or zaznam is None:
        return True
    # uzavřený rok: stahovat, dokud není stažen aspoň týden po svém konci (zachytí změny z konce roku)
    return not zaznam.get("uzavreno")


def stahni(koren: Path = KOREN, dnes: date | None = None,
           ziskej: Callable[[str], bytes] = ziskej_http, pauza: float = PAUZA_S) -> tuple[list[str], list[str]]:
    """Stáhne chybějící a aktuální roky. Vrací (změněné soubory, chyby). Chyba jednoho souboru
    nezastaví ostatní a nepřepíše poslední správnou verzi. Manifest se mění jen se změnou obsahu
    (nebo když se rok uzavře), aby samotné stažení beze změny nezakládalo PR (Codex P1, #74)."""
    dnes = dnes or date.today()
    adresar = koren / "raw" / "ezak"
    cesta_manifestu = adresar / "manifest.json"
    manifest = json.loads(cesta_manifestu.read_text(encoding="utf-8")) if cesta_manifestu.exists() else {}
    puvodni = json.dumps(manifest, sort_keys=True)
    zmeny, chyby = [], []
    for s in profily(koren):
        for rok in range(PRVNI_ROK, dnes.year + 1):
            rel = f"{s['ico']}/{rok}.xml"
            if not potreba_stahnout(rok, manifest.get(rel), dnes):
                continue
            od, do = date(rok, 1, 1), min(date(rok, 12, 31), dnes)
            url = url_exportu(s["ezak_profil"], od, do)
            try:
                obsah = ziskej(url)
                pocet = zkontroluj_xml(obsah, s["ico"])
            except Exception as e:  # noqa: BLE001 – ohlásit a pokračovat
                chyby.append(f"{rel}: {e}")
                continue
            finally:
                if pauza:
                    time.sleep(pauza)
            soubor = adresar / rel
            sha = hashlib.sha256(obsah).hexdigest()
            stary = manifest.get(rel, {})
            if not soubor.exists() or stary.get("sha256") != sha:
                soubor.parent.mkdir(parents=True, exist_ok=True)
                docasny = soubor.with_suffix(".xml.tmp")
                docasny.write_bytes(obsah)
                docasny.replace(soubor)
                zmeny.append(rel)
                stary = {"url": url_exportu(s["ezak_profil"], od, date(rok, 12, 31)), "sha256": sha,
                         "zakazek": pocet, "zmeneno": dnes.isoformat()}
            stary["uzavreno"] = dnes >= date(rok + 1, 1, 8)
            manifest[rel] = stary
    if json.dumps(manifest, sort_keys=True) != puvodni:
        adresar.mkdir(parents=True, exist_ok=True)
        cesta_manifestu.write_text(json.dumps(dict(sorted(manifest.items())), ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8")
    return zmeny, chyby


def main() -> int:
    zmeny, chyby = stahni()
    for z in zmeny:
        print("změněno:", z)
    for c in chyby:
        print("CHYBA:", c, file=sys.stderr)
    print(f"E-ZAK: změněno {len(zmeny)} souborů, chyb {len(chyby)} "
          f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)")
    return 1 if chyby else 0


if __name__ == "__main__":
    sys.exit(main())
