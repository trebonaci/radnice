"""Verze dokumentů v raw/manifest.json: otisk obsahu, historie verzí, plán kontrol.

Každý záznam manifestu má:
- `sha256`, `bytes`: otisk AKTUÁLNÍ verze (stejný jako u poslední položky `verze`);
- `verze[]`: {`cislo`, `zjisteno`, `sha256`, `bytes`, `zmena`, `texty`}; stará verze se nikdy nemaže;
- `posledni_kontrola`, `dalsi_kontrola`: plán podle stáří dokumentu.

Při změně otisku vznikne nová verze. Odvozená data se přegenerují
(`python -m pipeline.sestav`) a změna je vidět v historii verzí i v diffu PR.

Použití:
    python -m pipeline.verze              # doplní verze a plán, vypíše dokumenty k dnešní kontrole
    python -m pipeline.verze --dnes 2026-12-01
Stažení nového otisku zaznamenává `zaznamenej_kontrolu` (volá ho běh pipeline, #16).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

KOREN = Path(__file__).resolve().parent.parent
MANIFEST = KOREN / "raw" / "manifest.json"

# (nejvyšší stáří dokumentu ve dnech, interval kontroly ve dnech); starší než poslední řádek → INTERVAL_STARY
PLAN = ((14, 1), (60, 7), (365, 30))
INTERVAL_STARY = 90


def interval_kontroly(stari_dnu: int) -> int:
    """Čerstvé dokumenty kontrolujeme častěji, staré zřídka."""
    for hranice, interval in PLAN:
        if stari_dnu <= hranice:
            return interval
    return INTERVAL_STARY


def _datum(text: str) -> date:
    return date.fromisoformat(text)


def zakladni_datum(zaznam: dict) -> date:
    """Stáří počítáme od vyvěšení, jinak od prvního zjištění."""
    if zaznam.get("vyveseno"):
        return _datum(zaznam["vyveseno"])
    return _datum(zaznam["verze"][0]["zjisteno"])


def naplanuj(zaznam: dict, kontrola: date) -> None:
    stari = max((kontrola - zakladni_datum(zaznam)).days, 0)
    zaznam["posledni_kontrola"] = kontrola.isoformat()
    zaznam["dalsi_kontrola"] = (kontrola + timedelta(days=interval_kontroly(stari))).isoformat()


def doplni_historii(zaznam: dict) -> bool:
    """Starý záznam bez `verze` dostane první verzi z aktuálního otisku. Vrací True při změně."""
    if zaznam.get("verze"):
        return False
    zaznam["verze"] = [{
        "cislo": 1,
        "zjisteno": zaznam["stazeno"],
        "sha256": zaznam["sha256"],
        "bytes": zaznam.get("bytes"),
        "zmena": "první zjištěná verze",
        "texty": f"raw/texty/{zaznam['jednani_id']}" if zaznam.get("jednani_id") else None,
    }]
    naplanuj(zaznam, _datum(zaznam["stazeno"]))
    return True


def zaznamenej_kontrolu(zaznam: dict, sha256: str, dnes: date, bytes_: int | None = None,
                        zmena: str | None = None, texty: str | None = None) -> bool:
    """Zapíše výsledek kontroly. Nový otisk = nová verze (stará zůstane). Vrací True, pokud verze přibyla."""
    doplni_historii(zaznam)
    posledni = zaznam["verze"][-1]
    nova = sha256 != posledni["sha256"]
    if nova:
        zaznam["verze"].append({
            "cislo": posledni["cislo"] + 1,
            "zjisteno": dnes.isoformat(),
            "sha256": sha256,
            "bytes": bytes_,
            "zmena": zmena or "změněný obsah (jiný otisk sha256)",
            "texty": texty,
        })
        zaznam["sha256"] = sha256
        zaznam["bytes"] = bytes_
        zaznam["stazeno"] = dnes.isoformat()
    naplanuj(zaznam, dnes)
    return nova


def k_kontrole(manifest: list[dict], dnes: date) -> list[dict]:
    """Dokumenty, jejichž další kontrola nastala (nebo nemají plán)."""
    return [z for z in manifest if not z.get("dalsi_kontrola") or _datum(z["dalsi_kontrola"]) <= dnes]


def zkontroluj(manifest: list[dict]) -> list[str]:
    """Konzistence: aktuální otisk = poslední verze, čísla verzí jdou po jedné, otisky po sobě nejsou stejné."""
    chyby = []
    for z in manifest:
        i = z.get("dokument_id", "?")
        v = z.get("verze") or []
        if not v:
            chyby.append(f"{i}: chybí historie verzí")
            continue
        if [x["cislo"] for x in v] != list(range(1, len(v) + 1)):
            chyby.append(f"{i}: čísla verzí nejdou po řadě")
        if v[-1]["sha256"] != z["sha256"]:
            chyby.append(f"{i}: sha256 dokumentu není otiskem poslední verze")
        for a, b in zip(v, v[1:]):
            if a["sha256"] == b["sha256"]:
                chyby.append(f"{i}: verze {b['cislo']} má stejný otisk jako předchozí")
    return chyby


def nacti() -> list[dict]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def uloz(manifest: list[dict]) -> None:
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dnes", default=date.today().isoformat(), help="datum YYYY-MM-DD (pro testy)")
    args = p.parse_args(argv)
    dnes = _datum(args.dnes)
    manifest = nacti()
    zmeneno = [doplni_historii(z) for z in manifest]
    if any(zmeneno):
        uloz(manifest)
    chyby = zkontroluj(manifest)
    for c in chyby:
        print("CHYBA:", c, file=sys.stderr)
    for z in k_kontrole(manifest, dnes):
        print(f"k kontrole: {z['dokument_id']} (naplánováno {z.get('dalsi_kontrola')})")
    return 1 if chyby else 0


if __name__ == "__main__":
    sys.exit(main())
