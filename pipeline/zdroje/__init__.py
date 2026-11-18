"""Moduly zdrojů dat. Každý zdroj má stejné rozhraní (třída `Zdroj`):

1. `stahni(manifest, dnes)`: stáhne seznam a jen nové nebo k dnešní kontrole určené dokumenty;
2. `zkontroluj(stazeno, manifest)`: vrátí seznam chyb; neprázdný seznam = běh se zastaví
   a zůstanou poslední správná data;
3. záznamy (`Stazeno.dokumenty`) pak do `raw/` a `data/` zapisuje běh (`pipeline/beh.py`),
   zdroj sám na disk nezapisuje.

Zdroj nikdy nemění `manifest`; ten dostane jen ke čtení.
"""
from __future__ import annotations

from dataclasses import dataclass, field


class ChybaZdroje(Exception):
    """Zdroj je nedostupný nebo vrátil nepoužitelnou odpověď (HTTP chyba, síť)."""


@dataclass
class Dokument:
    dokument_id: str
    typ: str
    jednani_id: str
    nazev: str
    url: str
    stranka_zdroje: str
    vyveseno: str | None = None
    sha256: str = ""
    bytes: int = 0
    je_pdf: bool = False
    # text po stranách; None = obsah se nezměnil, text se nevytěžoval
    strany: list[str] | None = None


@dataclass
class Stazeno:
    odkazu: int                                   # kolik dokumentů zdroj nabízí (celý seznam)
    dokumenty: list[Dokument] = field(default_factory=list)   # skutečně stažené
    upozorneni: list[str] = field(default_factory=list)       # nezastavují běh


class Zdroj:
    nazev: str = ""
    typy: tuple[str, ...] = ()   # hodnoty `typ` v manifestu, které zdroj spravuje

    def stahni(self, manifest: list[dict], dnes) -> Stazeno:
        raise NotImplementedError

    def zkontroluj(self, stazeno: Stazeno, manifest: list[dict]) -> list[str]:
        raise NotImplementedError
