"""Sestaví data/ z rozloženého zápisu (pipeline/zapisy.py) a AI anotací (anotace/*.yaml).

Kontroly (selhání = nenulový návratový kód):
- každá citace doslova (po sjednocení mezer) existuje ve zdroji;
  citace usnesení musí být uvnitř textu daného usnesení;
- každá částka se jako číslo vyskytuje ve své citaci;
- anotace neodkazuje na neexistující usnesení a každé usnesení má anotaci;
- součet hlasů nepřesahuje počet přítomných na začátku jednání;
- citace neobsahují řetězce určené k anonymizaci.

Spuštění: python -m pipeline.sestav
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

from pipeline.zapisy import normalizuj, rozloz

KOREN = Path(__file__).resolve().parent.parent
ANONYM = "[fyzická osoba]"
RE_CISLO = re.compile(r"\d{1,3}(?:[ .]\d{3})+(?:,\d+)?|\d+(?:,\d+)?")


def cisla_v_textu(text: str) -> list[float]:
    """Najde čísla v českém zápisu (223.850,00 / 25.000 / 2 100 / 16,34)."""
    vysledek = []
    for m in RE_CISLO.finditer(text):
        s = m.group(0).replace(" ", "").replace(".", "").replace(",", ".")
        try:
            vysledek.append(float(s))
        except ValueError:
            pass
    return vysledek


def _polozky(retezce: list) -> list[tuple[str, str]]:
    """Položka anonymizace je řetězec (nahradí se [fyzická osoba]) nebo {retezec, nahrada}."""
    return [(r, ANONYM) if isinstance(r, str) else (r["retezec"], r["nahrada"]) for r in retezce]


def anonymizuj(text: str, retezce: list) -> str:
    for r, nahrada in _polozky(retezce):
        text = text.replace(r, nahrada)
    return text


def zpracuj_jednani(jednani_id: str, manifest: dict, chyby: list[str]) -> tuple[dict, list, list]:
    adresar = KOREN / "raw" / "texty" / jednani_id
    rozlozeno = rozloz(jednani_id, adresar)
    anot = yaml.safe_load((KOREN / "anotace" / f"{jednani_id}.yaml").read_text(encoding="utf-8"))
    dokument = normalizuj(" ".join(p.read_text(encoding="utf-8") for p in sorted(adresar.glob("strana-*.txt"))))
    dok = manifest[jednani_id]

    def over(citace: str, kde: str, kontext: str) -> bool:
        if normalizuj(citace) not in normalizuj(kde):
            chyby.append(f"{jednani_id}: citace nenalezena ({kontext}): {citace!r}")
            return False
        return True

    meta = anot["jednani"]
    over(meta["citace"], dokument, "jednani")
    for z in meta.get("pritomnost_zmeny", []):
        over(z["citace"], dokument, "pritomnost")

    usn_ids = {u["id"] for u in rozlozeno["usneseni"]}
    for klic in anot["usneseni"]:
        if klic not in usn_ids:
            chyby.append(f"{jednani_id}: anotace pro neexistující usnesení {klic}")

    usneseni_out = []
    for u in rozlozeno["usneseni"]:
        a = anot["usneseni"].get(u["id"])
        if a is None:
            chyby.append(f"{jednani_id}: usnesení {u['id']} nemá anotaci")
            continue
        anon = a.get("anonymizace", [])
        ok = over(a["citace"], u["text"], u["id"])
        for c in a.get("castky", []):
            ok &= over(c["citace"], dokument, f"{u['id']} castka")
            if not any(abs(x - float(c["hodnota"])) < 0.005 for x in cisla_v_textu(c["citace"])):
                chyby.append(f"{jednani_id}: {u['id']} částka {c['hodnota']} není v citaci {c['citace']!r}")
                ok = False
        for p in a.get("parcely", []):
            ok &= over(p["citace"], dokument, f"{u['id']} parcela")
        for cit in [a["citace"]] + [c["citace"] for c in a.get("castky", [])] + [p["citace"] for p in a.get("parcely", [])]:
            for r, _ in _polozky(anon):
                if r in cit:
                    chyby.append(f"{jednani_id}: {u['id']} citace obsahuje anonymizovaný údaj {r!r}")
                    ok = False
        for r, _ in _polozky(anon):
            if r not in normalizuj(u["text"]) and r not in u["text"]:
                chyby.append(f"{jednani_id}: {u['id']} řetězec k anonymizaci nenalezen: {r!r}")
        usneseni_out.append({
            "id": u["id"],
            "cislo": u["cislo"],
            "jednani_id": jednani_id,
            "bod": u["bod"],
            "vysledek": u["vysledek"],
            "text": anonymizuj(u["text"], anon),
            "text_anonymizovan": bool(anon),
            "tema": a["tema"],
            "tema_ai": True,
            "kategorie": a["kategorie"],
            "kategorie_ai": True,
            "shrnuti": a["shrnuti"],
            "shrnuti_ai": True,
            "citace": {"dokument_id": dok["dokument_id"], "strany": u["strany"], "text": a["citace"]},
            "castky": [{**c, "mena": "CZK"} for c in a.get("castky", [])],
            "parcely": a.get("parcely", []),
            "poznamka": a.get("poznamka"),
            "otazky": a.get("otazky", []),
            "overeni": "overeno_kodem" if ok else "navrh",
        })

    hlasovani_out = []
    for h in rozlozeno["hlasovani"]:
        soucet = h["pro"] + h["proti"] + h["zdrzel"]
        if soucet > meta["pritomno"]:
            chyby.append(f"{jednani_id}: hlasování {h['zdroj_radek']} má víc hlasů ({soucet}) než přítomných")
        hlasovani_out.append({k: v for k, v in h.items() if k != "zdroj_radek"} | {"hlasu_celkem": soucet})

    body = rozlozeno["body"]
    for b in body:
        upr = (anot.get("body") or {}).get(b["cislo"]) or {}
        if "nazev" in upr:
            b["nazev"] = upr["nazev"]
            b["nazev_anonymizovan"] = True
        anon = upr.get("anonymizace", [])
        if b["text"]:
            for r, _ in _polozky(anon):
                if r not in b["text"]:
                    chyby.append(f"{jednani_id}: bod {b['cislo']} řetězec k anonymizaci nenalezen: {r!r}")
            b["text"] = anonymizuj(b["text"], anon)
        b["text_anonymizovan"] = bool(anon)

    jednani_out = {
        "id": jednani_id,
        "organ": meta["organ"],
        "druh": meta.get("druh", "radne"),
        "cislo": meta["cislo"],
        "datum": meta["datum"],
        "obdobi": meta["obdobi"],
        "pritomno_na_zacatku": meta["pritomno"],
        "clenu": meta["clenu"],
        "pritomnost_zmeny": [{k: v for k, v in z.items() if k != "citace"} for z in meta.get("pritomnost_zmeny", [])],
        "dokument": {k: dok[k] for k in ("dokument_id", "url", "stranka_zdroje", "vyveseno", "sha256", "pocet_stran")},
        "body": body,
        "upozorneni_parseru": rozlozeno["upozorneni"],
    }
    return jednani_out, usneseni_out, hlasovani_out


def main() -> int:
    manifest = {d["jednani_id"]: d for d in json.loads((KOREN / "raw" / "manifest.json").read_text(encoding="utf-8"))}
    chyby: list[str] = []
    jednani, usneseni, hlasovani = [], [], []
    for jednani_id in sorted(manifest):
        if not (KOREN / "anotace" / f"{jednani_id}.yaml").exists():
            continue
        j, u, h = zpracuj_jednani(jednani_id, manifest, chyby)
        jednani.append(j)
        usneseni += u
        hlasovani += h
    data = KOREN / "data"
    data.mkdir(exist_ok=True)
    for nazev, obsah in (("jednani", jednani), ("usneseni", usneseni), ("hlasovani", hlasovani)):
        (data / f"{nazev}.json").write_text(json.dumps(obsah, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"jednání {len(jednani)}, usnesení {len(usneseni)}, hlasování {len(hlasovani)}")
    for c in chyby:
        print("CHYBA:", c, file=sys.stderr)
    return 1 if chyby else 0


if __name__ == "__main__":
    sys.exit(main())
