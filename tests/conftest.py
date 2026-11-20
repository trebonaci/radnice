"""Společné pomůcky testů.

Testy nesmí záviset na tom, co zrovna stáhl nebo zapsal ostrý běh (`raw/manifest.json`,
`raw/texty/`, `data/beh.json`, `data/udalosti.json`): kopie repozitáře pro test se vrací
do zmrazeného pilotního stavu (`tests/vzorky/manifest_pilot.json`, zápisy RM 4. 11. a ZM 2. 11. 2026).
"""
import shutil
from pathlib import Path

PILOT = ("rm-2026-11-04", "zm-2026-11-02")
MANIFEST_PILOT = Path(__file__).resolve().parent / "vzorky" / "manifest_pilot.json"


def jen_pilot(koren: Path) -> None:
    """Kopii repozitáře vrátí do pilotního stavu: zmrazený manifest, jen pilotní texty,
    žádné výstupy běhu (beh.json, udalosti.json, deník zápisu)."""
    koren = Path(koren)
    shutil.copy(MANIFEST_PILOT, koren / "raw" / "manifest.json")
    texty = koren / "raw" / "texty"
    if texty.exists():
        for d in texty.iterdir():
            if d.is_dir() and d.name not in PILOT:
                shutil.rmtree(d)
    shutil.rmtree(koren / "raw" / "ezak", ignore_errors=True)       # zakázky a smlouvy mají vlastní testy
    shutil.rmtree(koren / "raw" / "smlouvy", ignore_errors=True)
    shutil.rmtree(koren / "raw" / "rozpocet", ignore_errors=True)
    for nazev in ("beh.json", "udalosti.json", ".beh-zapis.json", "zakazky.json", "smlouvy.json",
                  "rozpoctova_opatreni.json", "rozpocet.json", "projekty.json", "dotace.json"):
        (koren / "data" / nazev).unlink(missing_ok=True)
