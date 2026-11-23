"""Doložené ukončení plnění stavební smlouvy (#207) z `raw/ezak/plneni.json` → `projekty[].ukonceni_plneni`.

Datum se čte kódem z doslovné věty „Plnění smlouvy ukončeno DD.MM.RRRR“ ze stránky zakázky v E-ZAK. Karta ho dostane,
jen když mají datum všechny její stavební zakázky ve stavu „ukončeno plnění“; platí nejpozdější. Jde o ukončení
plnění smlouvy (doloženo), ne o kolaudaci ani předání stavby veřejnosti.
"""
from __future__ import annotations

import re
from datetime import date

RE_DATUM = re.compile(r"Plnění smlouvy ukončeno (\d{2})\.(\d{2})\.(\d{4})$")


def datum(citace: str) -> str | None:
    m = RE_DATUM.search(citace)
    if not m:
        return None
    try:
        return date(int(m[3]), int(m[2]), int(m[1])).isoformat()
    except ValueError:
        return None


def pro_kartu(k: dict, plneni: dict) -> dict | None:
    stavby = [z for z in k.get("zakazky", []) if z.get("role") == "stavba"
              and any(c.get("stav") == "ukončeno plnění" for c in z.get("casti", []))]
    nalezy = []
    for z in stavby:
        zaznam = plneni.get(z["id"]) or {}
        dolozene = [(datum(c), c) for c in zaznam.get("citace", []) if datum(c)]
        if not dolozene:
            return None
        dt, cit = max(dolozene)
        nalezy.append({"datum": dt, "citace": cit, "url": zaznam["url"], "zakazka_id": z["id"], "jistota": "dolozeno"})
    return max(nalezy, key=lambda x: x["datum"]) if nalezy else None
