"""AI nezávislá na poskytovateli (#20): role -> pořadí poskytovatelů z `config/ai.yaml`.

Rozhraní: `zeptej_se(role, prompt, schema)` -> `Vysledek(data, poskytovatel, model)` nebo `None`,
když není dostupný žádný poskytovatel (AI krok se pak přeskočí). Všem výstupům se stejně
kontroluje JSON a schéma; citace ověřuje `overit_citace` (doslovná shoda ve zdroji).
Text ze zdrojů do `prompt` patří jen jako data. Tajné hodnoty jen z prostředí (GitHub Secrets).
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import yaml

KOREN = Path(__file__).resolve().parent.parent.parent
KONFIG = KOREN / "config" / "ai.yaml"


class AIChyba(Exception):
    """Poskytovatel selhal nebo vrátil nepoužitelný výstup."""


class StropVyčerpán(AIChyba):
    pass


@dataclass
class Vysledek:
    data: dict
    poskytovatel: str
    model: str

    def puvod(self) -> dict:
        """Pole do dat: kdo výstup vytvořil (příznak `*_ai` doplňuje volající)."""
        return {"poskytovatel": self.poskytovatel, "model": self.model}


def nacti_konfig(cesta: Path = KONFIG) -> dict:
    return yaml.safe_load(cesta.read_text(encoding="utf-8"))


def zkontroluj_konfig(k: dict) -> list[str]:
    """Chyby konfigurace; hlavně: ověření nesmí být od stejného výrobce jako anotace."""
    chyby = []
    p, role = k.get("poskytovatele", {}), k.get("role", {})
    for r, kroky in role.items():
        for s in kroky:
            if s["poskytovatel"] not in p:
                chyby.append(f"role {r}: neznámý poskytovatel {s['poskytovatel']}")
    if not chyby and "anotace" in role and "overeni" in role:
        va = {p[s["poskytovatel"]]["vyrobce"] for s in role["anotace"]}
        vo = {p[s["poskytovatel"]]["vyrobce"] for s in role["overeni"]}
        if va & vo and len(vo) == 1:  # počítají se různí výrobci, ne kroky
            chyby.append("overeni má jen výrobce, který je i u anotace (ZADANI 4.5)")
    return chyby


def vyrobce(k: dict, krok: dict) -> str:
    return k["poskytovatele"][krok["poskytovatel"]]["vyrobce"]


def dostupne(k: dict, role: str, env=os.environ) -> list[dict]:
    """Kroky role, jejichž secret (a případná adresa) je nastaven – v pořadí z konfigurace."""
    res = []
    for s in k["role"].get(role, []):
        p = k["poskytovatele"][s["poskytovatel"]]
        if env.get(p["secret"]) and (not p.get("url_env") or env.get(p["url_env"])):
            res.append(s)
    return res


def _json_z_textu(text: str) -> dict:
    """Vytáhne JSON objekt z odpovědi (model může přidat ```json ohraničení)."""
    t = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    if m:
        t = m.group(1).strip()
    try:
        d = json.loads(t)
    except json.JSONDecodeError:
        i, j = t.find("{"), t.rfind("}")
        if i < 0 or j <= i:
            raise AIChyba("odpověď není JSON")
        try:
            d = json.loads(t[i:j + 1])
        except json.JSONDecodeError as e:
            raise AIChyba(f"odpověď není JSON: {e}")
    if not isinstance(d, dict):
        raise AIChyba("odpověď není JSON objekt")
    return d


_TYPY = {"string": str, "number": (int, float), "integer": int, "boolean": bool, "array": list, "object": dict}


def zkontroluj_schema(d, schema: dict, cesta: str = "$") -> list[str]:
    """Minimální validace (type, required, properties, items, enum) – bez závislostí navíc."""
    chyby = []
    t = schema.get("type")
    if t:
        ok = isinstance(d, _TYPY[t]) and not (t in ("number", "integer") and isinstance(d, bool))
        if not ok:
            return [f"{cesta}: čekán typ {t}"]
    if "enum" in schema and d not in schema["enum"]:
        chyby.append(f"{cesta}: hodnota mimo výčet")
    if isinstance(d, dict):
        for r in schema.get("required", []):
            if r not in d:
                chyby.append(f"{cesta}: chybí {r}")
        for n, s in schema.get("properties", {}).items():
            if n in d:
                chyby += zkontroluj_schema(d[n], s, f"{cesta}.{n}")
    if isinstance(d, list) and "items" in schema:
        for i, x in enumerate(d):
            chyby += zkontroluj_schema(x, schema["items"], f"{cesta}[{i}]")
    return chyby


def _mezery(s: str) -> str:
    return " ".join(s.split())


def overit_citace(citace: str, zdroj: str) -> bool:
    """Citace musí doslova (po sjednocení mezer) existovat ve zdroji. Stejně pro všechny poskytovatele."""
    return bool(citace.strip()) and _mezery(citace) in _mezery(zdroj)


class Brana:
    """Volání modelů s pořadím, přeskakováním a stropem počtu volání na běh."""

    def __init__(self, konfig: dict | None = None, env=None, adaptery: dict[str, Callable] | None = None):
        self.k = konfig or nacti_konfig()
        self.env = os.environ if env is None else env
        if adaptery is None:
            from .adaptery import ADAPTERY
            adaptery = ADAPTERY
        self.adaptery = adaptery
        self.volani = 0

    def zeptej_se(self, role: str, prompt: str, schema: dict, vyloucit_vyrobce: str | None = None) -> Vysledek | None:
        """Zkouší dostupné poskytovatele v pořadí; `None` = žádný nedostupný (krok se přeskočí).
        `vyloucit_vyrobce`: pro ověření výrobce, který výstup navrhl."""
        poslední = None
        for s in dostupne(self.k, role, self.env):
            if vyloucit_vyrobce and vyrobce(self.k, s) == vyloucit_vyrobce:
                continue
            if self.volani >= self.k.get("max_volani_za_beh", 50):
                raise StropVyčerpán("dosažen strop počtu volání AI za běh")
            self.volani += 1
            try:
                text = self.adaptery[s["poskytovatel"]](prompt, s["model"], self.env, self.k)
                d = _json_z_textu(text)
                chyby = zkontroluj_schema(d, schema)
                if chyby:
                    raise AIChyba("; ".join(chyby[:5]))
                return Vysledek(d, s["poskytovatel"], s["model"])
            except AIChyba as e:
                poslední = e  # další poskytovatel v pořadí
        if poslední:
            raise poslední
        return None
