"""Jména fyzických osob bez titulu ve volném textu (předmět smlouvy, název zakázky) → „[jméno]“.

Titulovaná jména zachytí `pipeline.sestav.najdi_osobni_udaje`; tady jde o „Vystoupení Jana Nováka“.
Pravidlo: křestní jméno ze seznamu `config/krestni_jmena.txt` (i v ohýbaném tvaru) a za ním slovo
s velkým počátečním písmenem = jméno osoby. Zastupitelé (`config/osoby.yaml`) zůstávají.
Raději zakryje víc (např. ulici „Boženy Němcové“) než méně.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

KOREN = Path(__file__).resolve().parent.parent
VELKE = "A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ"
MALE = "a-záčďéěíňóřšťúůýž"


def _tvary(jmeno: str) -> set[str]:
    """Hrubé tvary 2.–7. pádu (stačí pro rozpoznání, ne pro jazykovou správnost)."""
    t = {jmeno}
    if jmeno.endswith("a"):
        z = jmeno[:-1]
        t |= {z + "y", z + "e", z + "ě", z + "u", z + "ou", z + "i"}
    elif jmeno.endswith(("e", "ie")):
        t |= {jmeno[:-1] + "i", jmeno[:-1] + "í"}
    else:
        z = jmeno[:-2] + jmeno[-1] if jmeno.endswith(("ek", "el")) and len(jmeno) > 4 else jmeno
        t |= {z + "a", z + "ovi", z + "em", z + "e", z + "u", jmeno + "a", jmeno + "ovi", jmeno + "em"}
    return t


@lru_cache(maxsize=1)
def _vzor(koren: str) -> re.Pattern:
    radky = (Path(koren) / "config" / "krestni_jmena.txt").read_text(encoding="utf-8").splitlines()
    jmena = {j for r in radky if not r.startswith("#") for j in r.split()}
    tvary = sorted({t for j in jmena for t in _tvary(j)}, key=len, reverse=True)
    return re.compile(rf"(?<![{VELKE}{MALE}])(?:{'|'.join(map(re.escape, tvary))})\s+[{VELKE}][{MALE}]+(?:ová|ové|ovou)?"
                      rf"(?:-[{VELKE}][{MALE}]+)?")


def zakryj_jmena(text: str | None, osoby: dict, koren: Path = KOREN) -> str | None:
    if not text:
        return text
    from pipeline.sestav import je_zastupitel     # pozdní import (sestav importuje zdroje)
    def nahrad(m: re.Match) -> str:
        return m.group(0) if je_zastupitel(m.group(0), osoby) else "[jméno]"
    return _vzor(str(koren)).sub(nahrad, text)
