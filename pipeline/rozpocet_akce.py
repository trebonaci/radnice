"""Schválený rozpočet města po akcích → `data/rozpocet.json` (#129, krok 2).

Zdroj: `raw/rozpocet/<rok>/rozpocet/strana-N.txt` (pdftotext -layout z PDF „Rozpočet města Třeboně na rok
RRRR“, stahuje `pipeline/zdroje/rozpocet_mesta.py`). Bez AI, čísla se opisují:

- čteme jen výdaje: třída 5 (běžné) a 6 (kapitálové), oddíly „souhrnný přehled dle ORJ“ se přeskakují,
- řádek = [třída] [ORJ] [oddíl] Popis + 1–4 čísla (schválený 2025 a upravený 2025 v tis. Kč, skutečnost
  2025 v Kč, rozpočet 2026 v Kč); bere se poslední číslo = schválený rozpočet roku dokumentu v Kč,
- ORJ a oddíl platí, dokud je nepřepíše další řádek; popis zalomený na více řádků se spojí,
- kontrola: součet položek = řádek „… celkem“ u oddílu, ORJ i třídy (jinak chyba, data se nemění).

Rozpočet číslo ORG neuvádí, proto se na karty investic napojuje podle názvu položky (naše propojení).
DPH dokument neuvádí (`s_dph: null`).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pipeline.rozpocet import na_halere

N = r"-?\d{1,3}(?: \d{3})*,\d{2}"
RE_CISLA = re.compile(rf"(?P<cisla>(?:\s+{N}){{1,4}})\s*$")
RE_TRIDA = re.compile(r"^\s*(?P<trida>[1-8])\s+(?P<nazev>\S.*?)\s*$")
RE_POLOZKA = re.compile(r"^\s*(?:(?P<trida>[56])\s+)?(?:(?P<orj>\d{3})\s+)?(?:(?P<od>\d{1,2})\s+)?(?P<popis>\S.*?)\s*$")
RE_CELKEM_OD = re.compile(r"^\s*(?P<od>\d{1,2})\s+(?P<nazev>.*?)\s*celkem$")
RE_CELKEM_ORJ = re.compile(r"^\s*ORJ\s+(?P<orj>\d{3})\s+(?P<nazev>.*?)(?:\s*celkem)?$", re.I)   # „celkem“ občas chybí
RE_CELKEM_TRIDA = re.compile(r"^(?P<trida>[56])\s+.*celkem$")
HLAVICKA = ("Schválený rozpočet", "OD/", "Třída ORJ", "Pol ", "tis. Kč", "VÝDAJE", "PŘÍJMY")
TRIDY = {"5": "bezne", "6": "kapitalove"}


def _kc(halere: int) -> float:
    return halere / 100


def _cisla(s: str) -> list[int]:
    return [na_halere(c) for c in re.findall(N, s)]


def polozky(strany: list[str], rok: int, dokument: str) -> tuple[list[dict], list[str]]:
    """`strany` = texty stran v pořadí. Vrací (položky, chyby)."""
    vysledek: list[dict] = []
    chyby: list[str] = []
    trida = orj = od = None
    aktivni = False
    soucty = {"od": 0, "orj": 0, "trida": 0}
    cekajici: list[str] = []          # řádky popisu bez čísel (zalomený název)
    posledni = None                   # položka, ke které může patřit pokračování popisu
    for cislo_strany, text in enumerate(strany, start=1):
        for radek in text.splitlines():
            obsah = radek.strip()
            if not obsah or obsah.startswith(HLAVICKA) or obsah.startswith("Schválený rozpočet města") \
                    or re.fullmatch(r"\d+/\d+", obsah) or obsah in ("Třída ORJ OD", "Pol"):
                continue
            m_cisla = RE_CISLA.search(radek)
            hlava = radek[:m_cisla.start()] if m_cisla else radek
            # nadpis třídy („5 Běžné výdaje“, „6 Kapitálové výdaje – souhrnný přehled…“)
            if not m_cisla:
                mt = RE_TRIDA.match(radek)
                if mt and ("výdaje" in mt["nazev"].lower() or "příjmy" in mt["nazev"].lower()
                           or mt["nazev"] == "Financování"):
                    aktivni = mt["trida"] in TRIDY and "souhrnný" not in mt["nazev"].lower()
                    trida, orj, od, cekajici, posledni = mt["trida"], None, None, [], None
                    continue
                if obsah in ("Financování",) or "souhrnný přehled" in obsah.lower():
                    aktivni = False
                    continue
                if aktivni:
                    if posledni is not None and posledni.get("_ceka_pokracovani"):
                        posledni["nazev"] += " " + obsah
                        posledni["citace"]["text"] += " " + obsah
                        posledni["_ceka_pokracovani"] = False
                    else:
                        cekajici.append(obsah)
                continue
            if not aktivni:
                continue
            hodnoty = _cisla(m_cisla["cisla"])
            castka = hodnoty[-1]
            hlava_s = hlava.strip()
            mp = RE_POLOZKA.match(hlava) if hlava_s else None
            # součet oddílu bez slova „celkem“ („10 Zemědělství…“): oddíl stejný jako u předchozích položek
            soucet_oddilu = bool(mp and mp["od"] and not mp["orj"] and not mp["trida"] and od is not None
                                 and int(mp["od"]) == od and len(hodnoty) == 1)
            if hlava_s.endswith("celkem") or soucet_oddilu or RE_CELKEM_ORJ.match(hlava_s):
                if (mo := RE_CELKEM_ORJ.match(hlava_s)):
                    if mo["orj"] != orj or soucty["orj"] != castka:
                        chyby.append(f"rozpočet {rok}: ORJ {mo['orj']} třída {trida}: součet položek "
                                     f"{_kc(soucty['orj'])} ≠ celkem {_kc(castka)} (strana {cislo_strany})")
                    soucty["orj"] = 0
                elif (mt := RE_CELKEM_TRIDA.match(hlava_s)):
                    if soucty["trida"] != castka:
                        chyby.append(f"rozpočet {rok}: třída {trida}: součet položek {_kc(soucty['trida'])} "
                                     f"≠ celkem {_kc(castka)} (strana {cislo_strany})")
                    soucty["trida"] = 0
                elif (md := RE_CELKEM_OD.match(hlava_s)) or soucet_oddilu:
                    md = md or mp
                    if int(md["od"]) != od or soucty["od"] != castka:
                        chyby.append(f"rozpočet {rok}: ORJ {orj} oddíl {md['od']}: součet položek "
                                     f"{_kc(soucty['od'])} ≠ celkem {_kc(castka)} (strana {cislo_strany})")
                    soucty["od"] = 0
                else:
                    chyby.append(f"rozpočet {rok}: nerozpoznaný součtový řádek „{hlava_s}“ (strana {cislo_strany})")
                cekajici, posledni = [], None
                continue
            if mp and mp["trida"] and mp["trida"] != trida:
                chyby.append(f"rozpočet {rok}: řádek třídy {mp['trida']} v oddílu třídy {trida} (strana {cislo_strany})")
            if mp and mp["orj"]:
                orj = mp["orj"]
            if mp and mp["od"]:
                od = int(mp["od"])
            popis = mp["popis"] if mp else ""
            pokracovani = not popis            # čísla bez popisu: název je zalomený kolem řádku s čísly
            nazev = " ".join(cekajici + ([popis] if popis else []))
            if not nazev or orj is None or od is None:
                chyby.append(f"rozpočet {rok}: řádek bez názvu, ORJ nebo oddílu „{obsah}“ (strana {cislo_strany})")
                cekajici, posledni = [], None
                continue
            poradi = sum(1 for p in vysledek if p["trida"] == TRIDY[trida] and p["orj"] == orj and p["oddil"] == od) + 1
            posledni = {
                "id": f"rozpocet-{rok}-{trida}-{orj}-{od:02d}-{poradi:02d}",
                "rok": rok,
                "trida": TRIDY[trida],
                "orj": orj,
                "oddil": od,
                "nazev": nazev,
                "castka": {"hodnota": _kc(castka), "mena": "CZK", "jednotka": "Kč", "s_dph": None,
                           "druh": "rozpocet", "obdobi": str(rok), "k_datu": None,
                           "citace": re.findall(N, m_cisla["cisla"])[-1],     # doslovný poslední sloupec
                           "poznamka": f"{dokument}, strana {cislo_strany}; DPH dokument neuvádí"},
                "rozpocet_2025_upraveny_tis": _kc(hodnoty[1]) if len(hodnoty) == 4 else None,
                "citace": {"dokument": dokument, "strana": cislo_strany, "text": " ".join(cekajici + [obsah])},
                "_ceka_pokracovani": pokracovani,
            }
            vysledek.append(posledni)
            for k in soucty:
                soucty[k] += castka
            cekajici = []
    for p in vysledek:
        p.pop("_ceka_pokracovani", None)
    if not vysledek:
        chyby.append(f"rozpočet {rok}: žádné položky výdajů")
    return vysledek, chyby


def nacti(koren: Path) -> tuple[list[dict], list[str]]:
    """Všechny roky v `raw/rozpocet/<rok>/rozpocet/`."""
    manifest_cesta = koren / "raw" / "rozpocet" / "manifest.json"
    if not manifest_cesta.exists():
        return [], []
    manifest = json.loads(manifest_cesta.read_text(encoding="utf-8"))
    vse, chyby = [], []
    for klic, zaznam in sorted(manifest.items()):
        rok, druh = klic.split("/")
        if druh != "rozpocet":
            continue
        adresar = koren / "raw" / "rozpocet" / rok / druh
        soubory = sorted(adresar.glob("strana-*.txt"), key=lambda p: int(p.stem.split("-")[1]))
        strany = [p.read_text(encoding="utf-8") for p in soubory]
        if len(strany) != zaznam.get("stran"):
            chyby.append(f"rozpočet {rok}: počet stran {len(strany)} ≠ manifest {zaznam.get('stran')}")
        p, ch = polozky(strany, int(rok), zaznam.get("url", ""))
        vse += p
        chyby += ch
    return vse, chyby


def zkontroluj(zaznamy: list[dict], koren: Path) -> list[str]:
    """Citace řádku je doslova (po sjednocení mezer) na uvedené straně zdroje."""
    chyby = []
    cache: dict[Path, str] = {}
    for z in zaznamy:
        cesta = koren / "raw" / "rozpocet" / str(z["rok"]) / "rozpocet" / f"strana-{z['citace']['strana']}.txt"
        if cesta not in cache:
            cache[cesta] = " ".join(cesta.read_text(encoding="utf-8").split()) if cesta.exists() else ""
        zdroj = cache[cesta]
        casti = z["citace"]["text"].split(" ")
        if " ".join(casti) not in zdroj and not all(c in zdroj for c in casti):
            chyby.append(f"{z['id']}: citace není ve zdroji")
        if z["castka"]["citace"] not in zdroj:
            chyby.append(f"{z['id']}: citace částky není ve zdroji")
    return chyby
