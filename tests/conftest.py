"""Společné pomůcky testů.

Testy nesmí záviset na tom, co zrovna stáhl ostrý běh do `raw/manifest.json`: kopie repozitáře
pro test obsahuje jen pilotní zápisy, ke kterým má test vzorky (PDF hlavičky, strany, anotace).
"""
import json
from pathlib import Path

PILOT = ("rm-2026-11-04", "zm-2026-11-02")


def jen_pilot(koren: Path) -> None:
    """V kopii repozitáře ponechá v manifestu jen pilotní zápisy."""
    cesta = Path(koren) / "raw" / "manifest.json"
    manifest = json.loads(cesta.read_text(encoding="utf-8"))
    cesta.write_text(json.dumps([z for z in manifest if z["jednani_id"] in PILOT], ensure_ascii=False, indent=2),
                     encoding="utf-8")
