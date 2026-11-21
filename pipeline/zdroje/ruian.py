"""Geometrie ulic a budov Třeboně z RÚIAN (#180) → `raw/ruian/`.

Zdroj: výměnný formát RÚIAN (VFR) ČÚZK, soubor obce „kompletní sada s grafikou“ (OB_<kód>_UKSH), měsíční
stav k poslednímu dni předchozího měsíce, `https://vdp.cuzk.gov.cz/vymenny_format/soucasna/<RRRRMMDD>_OB_<kód>_UKSH.xml.zip`.
Ukládá se jen výtah potřebný pro mapu, souřadnice převedené z S-JTSK (EPSG:5514) do WGS84:
- `ulice.json`: kód, název, definiční čára ulice (seznam linií [[délka, šířka], …]),
- `budovy.json`: stavební objekty s číslem popisným/evidenčním: kód, část obce, čísla, definiční bod,
- `adresy.json`: adresní místa: kód, ulice, číslo domovní a orientační, kód stavebního objektu, bod.
Kontrola před zápisem: aspoň `MIN_ULIC` ulic a `MIN_ADRES` adres; při chybě zůstanou předchozí data.
Z prostředí Clauda server ČÚZK nejde – stahuje běh v Actions.
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET

from pipeline.zdroje.zapisy_mesta import ChybaZdroje, ziskej_url

KOD_OBCE = "547336"          # Třeboň (ověřit při prvním stažení: název obce v souboru)
NAZEV_OBCE = "Třeboň"
ZAKLAD = "https://vdp.cuzk.gov.cz/vymenny_format/soucasna/"
MIN_ULIC = 50
MIN_ADRES = 1000
GML_ID = "{http://www.opengis.net/gml/3.2}id"


def url(den: date, kod: str = KOD_OBCE) -> str:
    return f"{ZAKLAD}{den:%Y%m%d}_OB_{kod}_UKSH.xml.zip"


def kandidati_dnu(dnes: date) -> list[date]:
    """Poslední den předchozího a předpředchozího měsíce (soubor vychází v prvních dnech měsíce)."""
    prvni = dnes.replace(day=1)
    minuly = prvni - timedelta(days=1)
    return [minuly, minuly.replace(day=1) - timedelta(days=1)]


def _ln(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _dite(el, nazev):
    for d in el:
        if _ln(d.tag) == nazev:
            return d
    return None


def _text(el, *cesta):
    for nazev in cesta:
        if el is None:
            return None
        el = _dite(el, nazev)
    return el.text.strip() if el is not None and el.text else None


def _potomci(el, nazev):
    return [d for d in el.iter() if _ln(d.tag) == nazev]


def _souradnice(el) -> list[list[tuple[float, float]]]:
    """Linie (posList) nebo body (pos) v S-JTSK pod prvkem."""
    linie = []
    for p in _potomci(el, "posList") + _potomci(el, "pos"):
        cisla = [float(x) for x in (p.text or "").split()]
        linie.append([(cisla[i], cisla[i + 1]) for i in range(0, len(cisla) - 1, 2)])
    return [l for l in linie if l]


def _prevod():
    from pyproj import Transformer
    t = Transformer.from_crs("EPSG:5514", "EPSG:4326", always_xy=True)

    def wgs(xy):
        lon, lat = t.transform(xy[0], xy[1])
        return [round(lon, 6), round(lat, 6)]
    return wgs


def rozloz(soubor, wgs=None) -> dict:
    """Projde VFR (proudově) a vrátí výtah: obec, ulice, části obce, budovy, adresy."""
    wgs = wgs or _prevod()
    obec, ulice, casti, budovy, adresy = None, [], {}, [], []
    for _, el in ET.iterparse(soubor, events=("end",)):
        if GML_ID not in el.attrib:
            continue
        druh = _ln(el.tag)
        if druh == "Obec":
            obec = {"kod": _text(el, "Kod"), "nazev": _text(el, "Nazev")}
        elif druh == "CastObce":
            casti[_text(el, "Kod")] = _text(el, "Nazev")
        elif druh == "Ulice":
            geom = _dite(el, "Geometrie")
            cara = _dite(geom, "DefinicniCara") if geom is not None else None
            linie = [[wgs(b) for b in l] for l in _souradnice(cara)] if cara is not None else []
            ulice.append({"kod": _text(el, "Kod"), "nazev": _text(el, "Nazev"), "linie": [l for l in linie if len(l) > 1]})
        elif druh == "StavebniObjekt":
            cisla = [c.text.strip() for c in _potomci(el, "CisloDomovni") if c.text]
            geom = _dite(el, "Geometrie")
            bod = _dite(geom, "DefinicniBod") if geom is not None else None
            body = _souradnice(bod) if bod is not None else []
            if cisla and body:
                budovy.append({"kod": _text(el, "Kod"), "cast_obce_kod": _text(el, "CastObce", "Kod"),
                               "typ_cisla": _text(el, "TypStavebnihoObjektuKod"), "cisla": cisla, "bod": wgs(body[0][0])})
        elif druh == "AdresniMisto":
            geom = _dite(el, "Geometrie")
            bod = _dite(geom, "DefinicniBod") if geom is not None else None
            body = _souradnice(bod) if bod is not None else []
            if body:
                adresy.append({"kod": _text(el, "Kod"), "ulice_kod": _text(el, "Ulice", "Kod"),
                               "cislo_domovni": _text(el, "CisloDomovni"), "cislo_orientacni": _text(el, "CisloOrientacni"),
                               "pismeno": _text(el, "CisloOrientacniPismeno"), "so_kod": _text(el, "StavebniObjekt", "Kod"),
                               "bod": wgs(body[0][0])})
        el.clear()
    nazvy_ulic = {u["kod"]: u["nazev"] for u in ulice}
    for b in budovy:
        b["cast_obce"] = casti.get(b.pop("cast_obce_kod"))
    for a in adresy:
        a["ulice"] = nazvy_ulic.get(a.pop("ulice_kod"))
    return {"obec": obec, "ulice": sorted(ulice, key=lambda u: u["nazev"] or ""),
            "budovy": sorted(budovy, key=lambda b: b["kod"] or ""), "adresy": sorted(adresy, key=lambda a: a["kod"] or "")}


def zkontroluj(vytah: dict) -> list[str]:
    chyby = []
    if not vytah["obec"] or vytah["obec"].get("nazev") != NAZEV_OBCE:
        chyby.append(f"RÚIAN: soubor není za obec {NAZEV_OBCE} ({vytah['obec']})")
    if len(vytah["ulice"]) < MIN_ULIC:
        chyby.append(f"RÚIAN: jen {len(vytah['ulice'])} ulic")
    if sum(1 for u in vytah["ulice"] if u["linie"]) < MIN_ULIC:
        chyby.append("RÚIAN: ulice bez definičních čar")
    if len(vytah["adresy"]) < MIN_ADRES:
        chyby.append(f"RÚIAN: jen {len(vytah['adresy'])} adres")
    for b in vytah["adresy"][:50] + vytah["budovy"][:50]:
        lon, lat = b["bod"]
        if not (14.5 < lon < 15.0 and 48.8 < lat < 49.2):
            chyby.append(f"RÚIAN: bod mimo Třeboňsko {b['bod']} – chybný převod souřadnic")
            break
    return chyby


def stahni(koren: Path, ziskej=ziskej_url, dnes: date | None = None) -> list[str]:
    dnes = dnes or date.today()
    adresar = koren / "raw" / "ruian"
    manifest_cesta = adresar / "manifest.json"
    manifest = json.loads(manifest_cesta.read_text(encoding="utf-8")) if manifest_cesta.exists() else {}
    posledni = None
    for den in kandidati_dnu(dnes):
        if manifest.get("k_datu") == den.isoformat():
            return []
        try:
            obsah = ziskej(url(den))
            posledni = (den, obsah)
            break
        except (ChybaZdroje, OSError) as e:
            chyba = e
    if posledni is None:
        return [f"RÚIAN: soubor nenalezen ({chyba}) – ponechána předchozí data"]
    den, obsah = posledni
    try:
        with zipfile.ZipFile(io.BytesIO(obsah)) as z:
            jmeno = next(n for n in z.namelist() if n.endswith(".xml"))
            with z.open(jmeno) as f:
                vytah = rozloz(f)
    except (zipfile.BadZipFile, StopIteration, ET.ParseError, ValueError) as e:
        return [f"RÚIAN: nelze přečíst ({e}) – ponechána předchozí data"]
    chyby = zkontroluj(vytah)
    if chyby:
        return [c + " – ponechána předchozí data" for c in chyby]
    adresar.mkdir(parents=True, exist_ok=True)
    for nazev in ("ulice", "budovy", "adresy"):
        docasny = adresar / f"{nazev}.json.nove"
        docasny.write_text(json.dumps(vytah[nazev], ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        docasny.replace(adresar / f"{nazev}.json")
    manifest = {"url": url(den), "k_datu": den.isoformat(), "sha256": hashlib.sha256(obsah).hexdigest(),
                "obec": vytah["obec"], "ulic": len(vytah["ulice"]), "budov": len(vytah["budovy"]),
                "adres": len(vytah["adresy"]), "stazeno": dnes.isoformat(),
                "souradnice": "WGS84 (EPSG:4326), převod z S-JTSK (EPSG:5514) knihovnou pyproj"}
    manifest_cesta.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return []


if __name__ == "__main__":
    upozorneni = stahni(Path(__file__).resolve().parents[2])
    for u in upozorneni:
        print(u, file=sys.stderr)
    sys.exit(1 if upozorneni else 0)
