"""Veřejné zakázky z exportů E-ZAK (`raw/ezak/<ico>/<rok>-<pololetí>.xml`) → záznamy `zakazka` (DATOVY_MODEL.md).

Bez AI: údaje se jen opisují z XML. Pravidla:
- Zakázka se může objevit ve více ročních exportech; platí stav z nejnovějšího roku.
- Fyzické osoby (subjekt s `bydliste`, ne `misto_podnikani` / `zeme_sidla`) se nezveřejňují:
  místo názvu „fyzická osoba“, bez IČO.
- Částky mají `druh` a `s_dph`, nesčítají se: smluvní cena (`smluvni`) a plnění za rok (`zaplaceno`).
  Nabídkové ceny uchazečů se neukládají, jen počet nabídek.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "{urn:cz:isvz:mmr:schemas:vz-z-profilu-zadavatele:v100}"
# Název právnické osoby poznáme podle právní formy NA KONCI názvu nebo podle typu instituce NA ZAČÁTKU.
# Kdo ani jedno nemá, je nejspíš podnikající fyzická osoba → anonymizovat (ZADANI: podnikatele – fyzické
# osoby vždy anonymizovat). Slovo jako „správa“ uprostřed obchodního jména nestačí (Codex P1, #74).
RE_PRAVNI_FORMA = re.compile(
    r"(?:s\.\s?r\.\s?o\.?|spol\.\s?s\s?r\.\s?o\.?|a\.\s?s\.?|v\.\s?o\.\s?s\.?|k\.\s?s\.?|z\.\s?s\.?|z\.\s?ú\.?|"
    r"o\.\s?p\.\s?s\.?|s\.\s?p\.?|družstvo|příspěvková organizace|státní podnik|gmbh|ltd\.?|sp\.\s?z\s?o\.\s?o\.?)\s*$",
    re.IGNORECASE)
RE_INSTITUCE = re.compile(r"^(?:město|obec|městys|statutární město|kraj|ministerstvo|správa|úřad|státní|česká republika)\b",
                          re.IGNORECASE)


RE_ODSTEPNY = re.compile(r"(?:a\.\s?s\.?|s\.\s?r\.\s?o\.?)\s*,\s*(?:odštěpný závod|organizační složka)", re.IGNORECASE)


# Školy, ústavy, spolky a další organizace bez právní formy na konci názvu (ostrý běh 20. 11. 2026:
# „Základní škola Třeboň, Sokolská 296“, „Hasičský záchranný sbor Jihočeského kraje“…).
RE_ORGANIZACE = re.compile(
    r"\b(?:mateřská|základní|střední|vyšší odborná|vysoká|umělecká|hudební)\s+škola\b|\bgymnázium\b|"
    r"zapsaný spolek|^spolek\b|\bdružstvo\b|státní podnik|\bv\.\s?v\.\s?i\.|\bústav\b|záchranný sbor|"
    r"^národní\b|\bministerstvo\b|ředitelství|\bknihovna\b|\bmuzeum\b|\bnemocnice\b|příspěvková organizace|"
    r"obecně prospěšná|\bnadace\b|nadační fond|\bfarnost\b|\bsvaz\b|\buniverzita\b", re.IGNORECASE)


def je_pravnicka(nazev: str) -> bool:
    nazev = nazev.strip().rstrip(",")
    return bool(RE_PRAVNI_FORMA.search(nazev) or RE_INSTITUCE.search(nazev) or RE_ODSTEPNY.search(nazev)
                or RE_ORGANIZACE.search(nazev))


DRUHY = {"stavební práce": "stavebni", "dodávky": "dodavky", "služby": "sluzby"}
ZAKLAD_URL = "https://zakazky.mesto-trebon.cz/contract_display_{cislo}.html"


def _t(e: ET.Element | None, cesta: str) -> str | None:
    if e is None:
        return None
    v = e.findtext("/".join(f"{NS}{c}" for c in cesta.split("/")))
    return v.strip() if v and v.strip() else None


def _datum(v: str | None) -> str | None:
    return v[:10] if v else None


def _cislo(v: str | None) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _castka(e: ET.Element, tag: str, s_dph, druh, zdroj, misto, obdobi=None) -> dict | None:
    """Částka z prvku `tag`; citace = doslovný prvek XML, poznámka = umístění (soubor, zakázka, část, dodavatel)."""
    raw = _t(e, tag)
    hodnota = _cislo(raw)
    if hodnota is None:
        return None
    return {"hodnota": hodnota, "mena": "CZK", "jednotka": "Kč", "s_dph": s_dph, "druh": druh,
            "obdobi": obdobi, "k_datu": None, "citace": f"<{tag}>{raw}</{tag}>",
            "poznamka": f"{zdroj}; {misto}"}


def subjekt(e: ET.Element | None) -> dict:
    """Dodavatel/účastník. Fyzická osoba (má `bydliste`) se anonymizuje."""
    if e is None:
        return {"nazev": None, "ico": None, "fyzicka_osoba": None}
    nazev = _t(e, "nazev_subjektu") or ""
    fo = (e.find(f"{NS}bydliste") is not None and e.find(f"{NS}misto_podnikani") is None
          and e.find(f"{NS}zeme_sidla") is None) or not je_pravnicka(nazev)
    if fo:
        return {"nazev": "fyzická osoba", "ico": None, "fyzicka_osoba": True}
    return {"nazev": nazev, "ico": _t(e, "ico"), "fyzicka_osoba": False}


def _cast(c: ET.Element, zdroj: str, zid: str | None = None) -> dict:
    p = c.find(f"{NS}zadavaci_postup_casti")
    lhuta = None
    for l in (p.findall(f"{NS}lhuty_zadavaciho_postupu/{NS}lhuta") if p is not None else []):
        if (_t(l, "druh_lhuty") or "").startswith("lhůta podání nabídek") or _t(l, "druh_lhuty") == "lhůta podání nabídky":
            lhuta = _t(l, "datum_konce_lhuty")
    vitezove = []
    for v in (p.findall(f"{NS}vybrani_dodavatele/{NS}vybrany_dodavatel") if p is not None else []):
        misto = f"zakázka {zid}, část {_t(c, 'id_objektu')}, dodavatel č. {len(vitezove) + 1}"
        castky = [x for x in (
            _castka(v, "smluvni_cena_s_DPH", True, "smluvni", zdroj, misto),
            _castka(v, "smluvni_cena_bez_DPH", False, "smluvni", zdroj, misto),
        ) if x]
        for pl in v.findall(f"{NS}plneni_dodavateli/{NS}plneni"):
            rok = _t(pl, "rok_smlouvy")
            castky += [x for x in (
                _castka(pl, "cena_za_rok_s_dph", True, "zaplaceno", zdroj, misto, rok),
                _castka(pl, "cena_za_rok_bez_dph", False, "zaplaceno", zdroj, misto, rok),
            ) if x]
        vitezove.append({**subjekt(v.find(f"{NS}subjekt")), "smlouva_uzavrena": _t(v, "uzavrena_smlouva_nebo_rd") == "1",
                         "castky": castky})
    ucastnici = p.findall(f"{NS}ucastnici/{NS}ucastnik") if p is not None else []
    registr = []
    for m in (p.findall(f"{NS}dokumenty/{NS}dokument/{NS}metadata_smlouvy_nebo_rd") if p is not None else []):
        url = _t(m, "url_v_registru_smluv")
        if url and url not in registr:
            registr.append(url)
    return {
        "id": _t(c, "id_objektu"),
        "nazev": _t(c, "nazev_casti_vz"),
        "stav": _t(p, "stav_zadavaciho_postupu"),
        "druh_rizeni": _t(p, "druh_zadavaciho_postupu"),
        "datum_uverejneni": _datum(_t(p, "datum_uverejneni")),
        "lhuta_nabidek": _datum(lhuta),
        "datum_uzavreni_smlouvy": _datum(_t(p, "datum_uzavreni_smlouvy")),
        "datum_zruseni": _datum(_t(p, "datum_zruseni_rizeni")),
        "pocet_nabidek": len(ucastnici),
        "vitezove": vitezove,
        "registr_smluv": registr,
    }


def rozloz_soubor(cesta: Path, ico: str, rel: str) -> list[dict]:
    koren = ET.parse(cesta).getroot()
    vysledek = []
    for z in koren.findall(f"{NS}zakazka"):
        zid = _t(z, "id_objektu")
        cislo = zid.split("-")[-1] if zid else None
        casti = [_cast(c, rel, zid) for c in z.findall(f"{NS}casti_vz/{NS}cast_zakazky")]
        vysledek.append({
            "id": f"ezak-{zid}",
            "subjekt_ico": ico,
            "nazev": _t(z, "nazev_vz"),
            "druh": DRUHY.get(_t(z, "druh_vz") or "", "jine"),
            "rezim": _t(z, "rezim_vz"),
            "predmet": _t(z, "predmet_vz"),
            "cpv": _t(z, "hlavni_cpv"),
            "stav": casti[0]["stav"] if len(casti) == 1 else None,
            "datum_zahajeni": min((c["datum_uverejneni"] for c in casti if c["datum_uverejneni"]), default=None),
            "casti": casti,
            "url": ZAKLAD_URL.format(cislo=cislo) if cislo else None,
            "zdroj": rel,
        })
    return vysledek


def nacti_zakazky(koren: Path) -> list[dict]:
    """Všechny zakázky; ze starších ročních exportů přepíše stav novější. Řazeno od nejnovějších."""
    adresar = koren / "raw" / "ezak"
    zakazky: dict[str, dict] = {}
    if adresar.exists():
        for soubor in sorted(adresar.glob("*/*.xml"), key=lambda p: (p.stem, p.parent.name)):
            rel = f"{soubor.parent.name}/{soubor.name}"
            for z in rozloz_soubor(soubor, soubor.parent.name, rel):
                zakazky[z["id"]] = z
    return sorted(zakazky.values(), key=lambda z: (z["datum_zahajeni"] or "", z["id"]), reverse=True)


def zkontroluj(zakazky: list[dict], koren: Path | None = None) -> list[str]:
    """Kontrola anonymizace, druhu a DPH částek; s `koren` i doslovná shoda citace se zdrojovým XML."""
    chyby = []
    texty: dict[str, str] = {}
    for z in zakazky:
        for c in z["casti"]:
            for v in c["vitezove"]:
                if v["fyzicka_osoba"] and (v["ico"] or v["nazev"] != "fyzická osoba"):
                    chyby.append(f"zakazky: {z['id']}: fyzická osoba není anonymizovaná")
                for k in v["castky"]:
                    if k["druh"] not in ("smluvni", "zaplaceno") or k["s_dph"] not in (True, False):
                        chyby.append(f"zakazky: {z['id']}: částka bez druhu nebo DPH")
                    if not k.get("citace") or not k.get("poznamka"):
                        chyby.append(f"zakazky: {z['id']}: částka bez citace nebo umístění")
                    elif koren is not None:
                        if z["zdroj"] not in texty:
                            f = koren / "raw" / "ezak" / z["zdroj"]
                            texty[z["zdroj"]] = f.read_text(encoding="utf-8") if f.exists() else ""
                        if k["citace"] not in texty[z["zdroj"]]:
                            chyby.append(f"zakazky: {z['id']}: citace částky není ve zdroji")
    return chyby
