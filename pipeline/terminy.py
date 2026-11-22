"""Termín dokončení stavby podle smlouvy (#205): `raw/smlouvy/terminy.json` → `data/terminy.json`.

Z úryvků textu smluv (stažených `pipeline/zdroje/prilohy_smluv.py`) čte kód – ne AI – termín dokončení díla:
- `druh = "datum"`: pevné datum („termín dokončení díla: 30. 9. 2026“, „dokončit dílo nejpozději do 15.12.2026“),
- `druh = "lhuta"`: lhůta bez data („do 120 kalendářních dnů od předání staveniště“) – datum nevíme.
`citace` je doslovný výňatek z úryvku (kontroluje se, že v něm je), `strana` je strana PDF.
Ze smlouvy se bere první nalezený termín (obvykle článek o době plnění); u dodatku ten, který mění termín.
"""
from __future__ import annotations

import re
from datetime import date

DATUM = r"(\d{1,2})\.\s?(\d{1,2})\.\s?(20\d{2})"
KLIC = (r"(?:term[ií]n\w*\s+(?:dokon[čc]en\w*|p[řr]ed[aá]n[ií]\w*)(?:\s+(?:d[ií]la|stavby|prac[ií]|v[šs]ech\s+prac[ií]))?"
        r"|dokon[čc]it\s+(?:d[ií]lo|stavbu)|p[řr]edat\s+(?:d[ií]lo|stavbu)|dokon[čc]en[ií]\s+(?:d[ií]la|stavby))")
# mezi klíčovým slovem a datem nesmí být jiný termín (zahájení) ani konec věty
MEZI = r"(?:(?!zah[aá]jen|\.\s+[A-ZČŘŠŽ])[^;]){0,90}?"
RE_DATUM = re.compile(KLIC + MEZI + DATUM, re.I)
RE_LHUTA = re.compile(KLIC + MEZI + r"(\d{1,4})\s+(?:kalend[aá][řr]n[ií]ch\s+|pracovn[ií]ch\s+)?(?:dn[ůuí]|t[ýy]dn[ůu]|m[ěe]s[ií]c[ůu])"
                      r"[^.;]{0,80}", re.I)


def _datum(d: str, m: str, r: str) -> str | None:
    try:
        return date(int(r), int(m), int(d)).isoformat()
    except ValueError:
        return None


def z_uryvku(text: str) -> dict | None:
    """První termín dokončení v úryvku: {druh, datum, citace} nebo None."""
    m = RE_DATUM.search(text)
    if m:
        dt = _datum(*m.groups()[-3:])
        if dt:
            return {"druh": "datum", "datum": dt, "citace": m.group(0)}
    m = RE_LHUTA.search(text)
    if m:
        return {"druh": "lhuta", "datum": None, "citace": m.group(0).strip()}
    return None


def sestav(raw: dict) -> tuple[list[dict], list[str]]:
    vysledek, chyby = [], []
    for zid, zaznam in sorted(raw.items()):
        nalez = None
        for soubor in zaznam.get("soubory", []):
            for u in soubor.get("uryvky", []):
                t = z_uryvku(u["text"])
                if t and (nalez is None or (nalez["druh"] == "lhuta" and t["druh"] == "datum")):
                    nalez = t | {"strana": u["strana"], "url": soubor["url"], "uryvek": u["text"]}
            if nalez and nalez["druh"] == "datum":
                break
        if not nalez:
            continue
        if nalez["citace"] not in nalez.pop("uryvek"):
            chyby.append(f"{zid}: citace termínu není v úryvku")
            continue
        strana = nalez["strana"]
        vysledek.append({"zdroj_id": zid, "druh": nalez["druh"], "datum": nalez["datum"], "citace": nalez["citace"],
                         "strana": strana, "url": f"{nalez['url']}#page={strana}", "smlouva_url": zaznam.get("url"),
                         "jistota": "dolozeno"})
    return vysledek, chyby


def pro_kartu(k: dict, terminy: dict) -> dict | None:
    """Platný termín dokončení stavby karty: z posledního dodatku, který termín uvádí, jinak z původní smlouvy."""
    st = next((c for c in k.get("casti", []) if c.get("role") == "stavba"), None)
    if not st:
        return None
    kandidati = [(d.get("datum") or "", "dodatek", d) for d in st.get("dodatky") or []]
    kandidati.sort(key=lambda x: x[0], reverse=True)
    kandidati.append(("", "smlouva", st.get("puvodni") or {}))
    for _, odkud, d in kandidati:
        t = terminy.get(d.get("zdroj_id"))
        if t and (t["druh"] == "datum" or odkud == "smlouva"):
            cislo = d.get("cislo")
            return t | {"podle": f"dodatek č. {cislo}" if odkud == "dodatek" and cislo else odkud}
    return None
