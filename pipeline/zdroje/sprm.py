"""Aktivity Strategického plánu rozvoje města 2021–2030 z evidence trebonaci.cz → `raw/sprm/projekty.json` (#168).

Endpoint `https://trebonaci.cz/wp-json/trebonaci/v1/projekty` (WordPress, typ `trebonaci_projekt`) vrací celé
pole bez stránkování (docs/ZDROJE.md). Ukládají se jen pole potřebná k propojení s kartami investic:
`id`, `aktivita`, `osa_id`, `osa_nazev`, `opatreni`, `stav`, `komentar`, `geometrie`. Jde o redakční evidenci
Třeboňáků – záznam nedokládá, že město akci schválilo nebo financuje; slouží jen k přiřazení opatření SPRM.

Kontrola před zápisem: JSON pole, aspoň `MIN_POLOZEK` položek, každá s `id` a `aktivita`. Při chybě zůstanou
předchozí data. Zapisuje se jen při změně obsahu (sha256), manifest drží URL, sha256 a datum stažení.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

from pipeline.zdroje.zapisy_mesta import ChybaZdroje, ziskej_url

URL = "https://trebonaci.cz/wp-json/trebonaci/v1/projekty"
POLE = ("id", "aktivita", "osa_id", "osa_nazev", "opatreni", "stav", "komentar", "geometrie")
MIN_POLOZEK = 50


def vycisti(data) -> list[dict]:
    if not isinstance(data, list):
        raise ChybaZdroje("SPRM: odpověď není JSON pole")
    vysledek = []
    for x in data:
        if not isinstance(x, dict) or x.get("id") in (None, "") or not str(x.get("aktivita") or "").strip():
            raise ChybaZdroje(f"SPRM: položka bez id nebo aktivity: {str(x)[:80]}")
        vysledek.append({k: x.get(k) for k in POLE})
    if len(vysledek) < MIN_POLOZEK:
        raise ChybaZdroje(f"SPRM: jen {len(vysledek)} položek (čekáno aspoň {MIN_POLOZEK})")
    return sorted(vysledek, key=lambda x: int(x["id"]) if str(x["id"]).isdigit() else str(x["id"]))


def stahni(koren: Path, ziskej=ziskej_url, dnes: date | None = None) -> list[str]:
    """Vrací seznam upozornění (prázdný = v pořádku)."""
    try:
        polozky = vycisti(json.loads(ziskej(URL).decode("utf-8")))
    except (ChybaZdroje, OSError, ValueError) as e:
        return [f"SPRM: {e} – ponechána předchozí data"]
    obsah = json.dumps(polozky, ensure_ascii=False, indent=1) + "\n"
    sha = hashlib.sha256(obsah.encode("utf-8")).hexdigest()
    adresar = koren / "raw" / "sprm"
    manifest_cesta = adresar / "manifest.json"
    manifest = json.loads(manifest_cesta.read_text(encoding="utf-8")) if manifest_cesta.exists() else {}
    if manifest.get("sha256") == sha:
        return []
    adresar.mkdir(parents=True, exist_ok=True)
    docasny = adresar / "projekty.json.nove"
    docasny.write_text(obsah, encoding="utf-8")
    docasny.replace(adresar / "projekty.json")
    manifest = {"url": URL, "sha256": sha, "polozek": len(polozky), "stazeno": (dnes or date.today()).isoformat()}
    manifest_cesta.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return []


if __name__ == "__main__":
    chyby = stahni(Path(__file__).resolve().parents[2])
    for c in chyby:
        print("UPOZORNĚNÍ:", c)
    sys.exit(1 if chyby else 0)
