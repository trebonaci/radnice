"""Smlouvy z Registru smluv (`raw/smlouvy/<RRRR>-<MM>.json`) → záznamy `smlouva` (DATOVY_MODEL.md).

Bez AI, údaje se opisují. Pravidla:
- Neplatné záznamy (`platnyZaznam` ≠ 1) se vynechají; ze záznamů téže smlouvy (`idSmlouvy`) platí
  nejnověji zveřejněná verze.
- Smluvní strana bez IČO nebo s názvem bez právní formy je (podnikající) fyzická osoba → „fyzická osoba“,
  bez IČO a adresy. Adresy se nezveřejňují vůbec, `schvalil` (jméno úředníka) také ne.
- Částky: `hodnotaBezDph` (s_dph false), `hodnotaVcetneDph` (s_dph true), cizí měna zvlášť; druh `smluvni`;
  nic se nesčítá. „Cena neuvedena“ = prázdné částky + příznak.
- Jména osob s titulem v předmětu smlouvy maskuje sestavení (`pipeline/sestav.py`).
"""
from __future__ import annotations

import json
import html
import re
from pathlib import Path

from pipeline.zakazky import je_pravnicka
from pipeline.zdroje.registr_smluv import sledovana_ico


def _seznam(v) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _cislo(v) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


# výpůjčka, nájem, pacht nebo dar: fyzická osoba užívá nebo dává majetek, není dodavatelem města (#93)
RE_NE_DODAVKA = re.compile(r"výpůjč|nájem|nájm|pacht|daru|darovac", re.I)
# jméno osoby: 2–4 slova s velkým počátečním písmenem, volitelně „nar. RRRR“; organizace (čísla, zkratky,
# čárky) se po slovech nemaskují, jinak by zmizela i věcná slova předmětu (místa, názvy)
RE_JMENO_OSOBY = re.compile(r"(?:[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:-[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)?\s+){1,3}"
                            r"[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:\s*,?\s*nar\.\s*\d{4})?")


# předmět o veřejné kulturní akci: jména umělců (autor, režie, účinkující) se neskrývají (#131),
# fyzické osoby jako smluvní strany ano (`_skryj_fo`)
RE_KULTURNI_AKCE = re.compile(r"koncert|představení|uměleck\w* výkon|vystoupení|divadeln", re.I)


def je_kulturni_akce(predmet: str | None) -> bool:
    return bool(predmet and RE_KULTURNI_AKCE.search(predmet))


def strana(s: dict, znama: frozenset[str] = frozenset(), predmet: str | None = None) -> dict:
    """`znama` = IČO sledovaných právnických osob (config/subjekty.yaml): ty se nikdy neanonymizují.
    `predmet` smlouvy: u výpůjčky, nájmu, pachtu a daru se ani podnikající fyzická osoba neuvádí jménem."""
    nazev, ico = (s.get("nazev") or "").strip(), (s.get("ico") or "").strip() or None
    # „identifikace: PO“ z registru platí (spolky, ústavy bez právní formy v názvu); „FO“ registr uvádí
    # i u některých s.r.o., proto jinak rozhoduje IČO a právní forma v názvu
    identifikace = s.get("identifikace")
    fyzicka = ico not in znama and identifikace != "PO" and (not ico or not je_pravnicka(nazev))
    if fyzicka:
        # podnikající fyzická osoba (má IČO), která je příjemcem plnění (dodavatel), se uvádí jménem ze zdroje,
        # bez IČO a adresy (#93); ostatní fyzické osoby (nájemci, dárci, bez IČO) zůstávají anonymní
        prijemce = s.get("prijemce") == "1"
        return {"nazev": "fyzická osoba", "ico": None, "fyzicka_osoba": True, "prijemce": prijemce,
                "jmeno_podnikatele": nazev if ico and nazev and prijemce
                and not RE_NE_DODAVKA.search(predmet or "") else None}
    return {"nazev": nazev, "ico": ico, "fyzicka_osoba": False, "prijemce": s.get("prijemce") == "1",
            "jmeno_podnikatele": None}


def castky(sml: dict, zdroj: str, misto: str) -> list[dict]:
    """Citace = doslovný zlomek uloženého JSON (`raw/smlouvy/<soubor>`), ověřuje `zkontroluj`;
    umístění (soubor, ID verze) je v `poznamka`."""
    vysledek = []
    for pole, s_dph in (("hodnotaBezDph", False), ("hodnotaVcetneDph", True)):
        h = _cislo(sml.get(pole))
        if h is not None:
            vysledek.append({"hodnota": h, "mena": "CZK", "jednotka": "Kč", "s_dph": s_dph, "druh": "smluvni",
                             "obdobi": None, "k_datu": None, "citace": f'"{pole}": {json.dumps(sml[pole], ensure_ascii=False)}',
                             "poznamka": f"{zdroj}; {misto}"})
    cm = sml.get("ciziMena")
    if isinstance(cm, dict) and _cislo(cm.get("hodnota")) is not None:
        vysledek.append({"hodnota": _cislo(cm["hodnota"]), "mena": cm.get("mena"), "jednotka": cm.get("mena"),
                         "s_dph": None, "druh": "smluvni", "obdobi": None, "k_datu": None,
                         "citace": f'"hodnota": {json.dumps(cm["hodnota"], ensure_ascii=False)}',
                         "poznamka": f"{zdroj}; {misto}; cizí měna, DPH registr neuvádí"})
    return vysledek


def _skryj_fo(predmet, strany: list[dict], znama: frozenset[str]):
    """Z předmětu odstraní jméno, IČO a adresu smluvních stran, které jsou fyzickými osobami."""
    if not predmet:
        return predmet
    puvodni = predmet
    for s in strany:
        if strana(s, znama, puvodni)["fyzicka_osoba"]:
            nazev = (s.get("nazev") or "").strip()
            for hodnota in (s.get("adresa"), nazev, s.get("ico")):
                h = (hodnota or "").strip()
                if len(h) >= 3:
                    predmet = predmet.replace(h, "[jméno]" if h == nazev else "[údaj]")
            if strana(s, znama, puvodni)["jmeno_podnikatele"] is None and RE_JMENO_OSOBY.fullmatch(nazev):
                # předmět často uvádí jen část jména (např. „p. Příjmení“) → maskovat i jednotlivá slova jména
                for slovo in re.findall(r"[^\W\d_]{4,}", nazev):
                    if slovo[0].isupper():
                        predmet = re.sub(rf"(?<!\w){re.escape(slovo)}(?!\w)", "[jméno]", predmet, flags=re.IGNORECASE)
    return predmet


def prevod(z: dict, zdroj: str, znama: frozenset[str] = frozenset()) -> dict:
    sml = z.get("smlouva", {})
    ident = z.get("identifikator", {})
    subj = sml.get("subjekt", {})
    return {
        "id": f"rs-{ident.get('idVerze')}",
        "id_smlouvy": ident.get("idSmlouvy"),
        "id_verze": ident.get("idVerze"),
        # zveřejnit může i fyzická osoba (sledovaná organizace je pak smluvní stranou) → stejná anonymizace
        "subjekt_ico": strana(subj, znama)["ico"],
        "subjekt_nazev": strana(subj, znama)["nazev"],
        "strany": [strana(s, znama, sml.get("predmet")) for s in _seznam(sml.get("smluvniStrana"))],
        # registr občas vrací HTML entity („&quot;“) – převést na znaky
        "predmet": _skryj_fo(html.unescape(sml["predmet"]) if sml.get("predmet") else sml.get("predmet"),
                             _seznam(sml.get("smluvniStrana")), znama),
        "datum_uzavreni": sml.get("datumUzavreni"),
        "datum_zverejneni": (z.get("casZverejneni") or "")[:10] or None,
        "cislo_smlouvy": sml.get("cisloSmlouvy"),
        "castky": castky(sml, zdroj, f"záznam idVerze {ident.get('idVerze')}"),
        "cena_neuvedena": sml.get("cenaNeuvedena") in ("1", "true"),
        "navazuje_na": sml.get("navazanyZaznam") or z.get("navazanyZaznam"),
        "evidencni_cislo_zakazky": sml.get("evidencniCisloZakazky"),
        "url": z.get("odkaz"),
        "zdroj": zdroj,
    }


def nacti_smlouvy(koren: Path) -> list[dict]:
    """Platné smlouvy sledovaných subjektů (jedna verze na smlouvu). Řazeno od nejnovějších."""
    adresar = koren / "raw" / "smlouvy"
    znama = frozenset(sledovana_ico(koren))
    posledni: dict[str, tuple[str, dict, str]] = {}
    if adresar.exists():
        for soubor in sorted(adresar.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9].json")):
            for z in json.loads(soubor.read_text(encoding="utf-8")):
                ident = z.get("identifikator", {})
                klic = ident.get("idSmlouvy")
                if not klic:
                    continue
                poradi = (z.get("casZverejneni") or "") + str(ident.get("idVerze", "")).zfill(12)
                if klic not in posledni or poradi > posledni[klic][0]:
                    posledni[klic] = (poradi, z, soubor.name)
    def sleduje(z: dict) -> bool:          # nejnovější verze už sledovaný subjekt nemusí obsahovat
        sml = z.get("smlouva", {})
        ica = {sml.get("subjekt", {}).get("ico")} | {s.get("ico") for s in _seznam(sml.get("smluvniStrana"))}
        return bool(ica & znama)
    vysledek = [prevod(z, zdroj, znama) for _, z, zdroj in posledni.values()
                if str(z.get("platnyZaznam")) == "1" and sleduje(z)]
    return sorted(vysledek, key=lambda s: (s["datum_zverejneni"] or "", s["id"]), reverse=True)


def zkontroluj(smlouvy: list[dict], koren: Path | None = None) -> list[str]:
    chyby = []
    texty: dict[str, str] = {}
    for s in smlouvy:
        for st in s["strany"]:
            if st["fyzicka_osoba"] and (st["ico"] or st["nazev"] != "fyzická osoba"):
                chyby.append(f"smlouvy: {s['id']}: fyzická osoba není anonymizovaná")
        for k in s["castky"]:
            if k["druh"] != "smluvni" or (k["mena"] == "CZK" and k["s_dph"] not in (True, False)):
                chyby.append(f"smlouvy: {s['id']}: částka bez druhu nebo DPH")
            if not k.get("citace") or not k.get("poznamka"):
                chyby.append(f"smlouvy: {s['id']}: částka bez citace nebo umístění")
            elif koren is not None:
                if s["zdroj"] not in texty:
                    cesta = koren / "raw" / "smlouvy" / s["zdroj"]
                    texty[s["zdroj"]] = cesta.read_text(encoding="utf-8") if cesta.exists() else ""
                if k["citace"] not in texty[s["zdroj"]]:
                    chyby.append(f"smlouvy: {s['id']}: citace částky není ve zdroji {s['zdroj']}")
    return chyby
