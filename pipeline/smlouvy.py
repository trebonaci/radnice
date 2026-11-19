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


def strana(s: dict, znama: frozenset[str] = frozenset()) -> dict:
    """`znama` = IČO sledovaných právnických osob (config/subjekty.yaml): ty se nikdy neanonymizují."""
    nazev, ico = (s.get("nazev") or "").strip(), (s.get("ico") or "").strip() or None
    if not ico or (ico not in znama and not je_pravnicka(nazev)):
        return {"nazev": "fyzická osoba", "ico": None, "fyzicka_osoba": True, "prijemce": s.get("prijemce") == "1"}
    return {"nazev": nazev, "ico": ico, "fyzicka_osoba": False, "prijemce": s.get("prijemce") == "1"}


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
    for s in strany:
        if strana(s, znama)["fyzicka_osoba"]:
            nazev = (s.get("nazev") or "").strip()
            for hodnota in (s.get("adresa"), nazev, s.get("ico")):
                h = (hodnota or "").strip()
                if len(h) >= 3:
                    predmet = predmet.replace(h, "[jméno]" if h == nazev else "[údaj]")
    return predmet


def prevod(z: dict, zdroj: str, znama: frozenset[str] = frozenset()) -> dict:
    sml = z.get("smlouva", {})
    ident = z.get("identifikator", {})
    subj = sml.get("subjekt", {})
    return {
        "id": f"rs-{ident.get('idVerze')}",
        "id_smlouvy": ident.get("idSmlouvy"),
        "id_verze": ident.get("idVerze"),
        "subjekt_ico": subj.get("ico"),
        "subjekt_nazev": subj.get("nazev"),
        "strany": [strana(s, znama) for s in _seznam(sml.get("smluvniStrana"))],
        "predmet": _skryj_fo(sml.get("predmet"), _seznam(sml.get("smluvniStrana")), znama),
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
    vysledek = [prevod(z, zdroj, znama) for _, z, zdroj in posledni.values() if str(z.get("platnyZaznam")) == "1"]
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
