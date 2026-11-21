"""Pracovní zásobník projektů (#172): `data/zasobnik.yaml` + doklady z `data/` → `data/zasobnik.json`.

Model (rozhodnutí Ondřeje 21. 11. 2026): námět (aktivita SPRM) → zásobník (konkrétní projekt) →
rozpočet (ORG) → realizace → dokončení. Zásobník NENÍ dokument schválený městem, je to pracovní přehled.

Záznamy výstupu (`typ`):
- `polozka`  – projekt ze `data/zasobnik.yaml`. Doklady = smlouvy a zakázky na studii nebo projektovou
  dokumentaci podle vzorů `vazby.hledat` (naše propojení), které nejsou v žádné kartě investice.
  Z nich kód odvodí nositele (zadavatele) a nejvyšší zadaný stupeň připravenosti (doloženo smlouvou nebo
  zakázkou; říká, že práce byla zadána, ne že je hotová).
- `kandidat` – smlouva nebo zakázka na přípravu od roku 2023, která není v kartě ani v položce zásobníku
  (podklad pro doplnění zásobníku, nic se z něj nevyvozuje).
- `namet`    – aktivita Strategického plánu se stavem „Plánováno“ v evidenci, ke které není karta ani položka.

Částky se nesčítají ani neodhadují: odhad nákladů je jen ten, který je ručně opsaný ze zdroje.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

import yaml

from pipeline import projekty as modul_projekty

# Stupně připravenosti (pořadí = vyšší je dál). Doklad = zadaná zakázka nebo uzavřená smlouva.
STUPNE = [
    ("zamer", "záměr"),
    ("studie", "studie zadána"),
    ("projekt", "projektová dokumentace zadána"),
    ("projekt_povoleni", "projekt pro povolení stavby zadán"),
    ("projekt_provadeci", "prováděcí projekt zadán"),
]
PORADI = {k: i for i, (k, _) in enumerate(STUPNE)}
NAZEV_STUPNE = dict(STUPNE)

# Příprava stavby: studie, projekt, předprojektová příprava. DPS = dokumentace pro provedení stavby, ale také
# dům s pečovatelskou službou („DPS 1“, „DPS III“) – ten se vylučuje.
RE_PRIPRAVA = re.compile(
    r"projektov\w* dok|projektové dokum|drojektov|\(PD\)|zpracování PD|zhotov\w*\.? ?PD|\bPD\b|studi|"
    r"předprojektov|\bDSP\b|\bDZS\b|\bDUR\b|\bDPS\b(?!\s*(?:[0-9]|I\b|II\b|III\b|IA\b|IC\b))", re.I)
RE_DPS_DUM = re.compile(r"\bDPS\s*(?:[0-9]|I\b|II\b|III\b|IA\b|IC\b)")
RE_NE_PRIPRAVA = re.compile(r"havarijní|lázeňských procedur|rehabilitační pobyt|kybernetick", re.I)
KANDIDATI_OD = "2023-01-01"
OBLASTI = {"doprava", "voda_odpady", "sport", "skolstvi", "socialni", "bydleni", "kultura", "lazne", "zelen", "jine"}


def je_priprava(text: str) -> bool:
    t = " ".join((text or "").split())
    return bool(RE_PRIPRAVA.search(t)) and not RE_NE_PRIPRAVA.search(t)


def stupen(text: str) -> str:
    # „DPS IA“, „DPS 1“ = dům s pečovatelskou službou, ne dokumentace pro provedení stavby
    druh = modul_projekty.druh_projektu(RE_DPS_DUM.sub("dům s pečovatelskou službou", text))
    return {"architektonická studie": "studie", "projekt prováděcí": "projekt_provadeci",
            "projekt pro stavební řízení a prováděcí": "projekt_provadeci",
            "projekt pro stavební řízení": "projekt_povoleni"}.get(druh, "projekt")


def nacti(koren: Path) -> list[dict]:
    cesta = koren / "data" / "zasobnik.yaml"
    if not cesta.exists():
        return []
    return (yaml.safe_load(cesta.read_text(encoding="utf-8")) or {}).get("polozky") or []


def _doklady(data: dict) -> list[dict]:
    """Smlouvy a zakázky na přípravu stavby, sjednocené do jednoho tvaru."""
    vysledek = []
    for z in data.get("zakazky", []):
        # zakázka dokládá zadání jen s vybraným dodavatelem (zrušená nebo běžící soutěž ne)
        if je_priprava(z["nazev"]) and _zadano(z):
            vysledek.append({"typ": "zakazka", "id": z["id"], "text": " ".join(html.unescape(z["nazev"]).split()),
                             "datum": z.get("datum_zahajeni"), "ico": z.get("subjekt_ico"), "url": z.get("url")})
    for s in data.get("smlouvy", []):
        if je_priprava(s.get("predmet")):
            vysledek.append({"typ": "smlouva", "id": s["id"], "text": " ".join(html.unescape(s["predmet"]).split()),
                             "datum": s.get("datum_uzavreni"), "ico": s.get("subjekt_ico"), "url": s.get("url")})
    return vysledek


def _zadano(z: dict) -> bool:
    return z.get("stav") != "zrušen" and any(c.get("vitezove") for c in z.get("casti", []))


def _v_kartach(projekty: list[dict]) -> set[str]:
    return {x["id"] for k in projekty for x in k.get("zakazky", []) + k.get("smlouvy", [])}


def _stavby(polozka: dict, data: dict, v_kartach: set[str]) -> list[dict]:
    """Zakázky na stavbu podle vzorů položky, které nejsou v žádné kartě."""
    return [{"id": z["id"], "nazev": " ".join(z["nazev"].split()), "datum": z.get("datum_zahajeni"),
             "stav": z.get("stav"), "url": z.get("url")} for z in data.get("zakazky", [])
            if z["id"] not in v_kartach and not je_priprava(z["nazev"])
            and modul_projekty.role(z["nazev"]) == "stavba" and modul_projekty._odpovida(z["nazev"], polozka)]


def sestav_polozku(p: dict, doklady: list[dict], data: dict, v_kartach: set[str], subjekty: dict) -> dict:
    moje = sorted((d for d in doklady if d["id"] not in v_kartach and modul_projekty._odpovida(d["text"], p)),
                  key=lambda d: (d["datum"] or "", d["id"]))
    pripravenost = {"stupen": "zamer", "nazev": NAZEV_STUPNE["zamer"], "doklad": None,
                    "jistota": "dolozeno" if p.get("zdroj") else "nevime"}
    for d in moje:
        st = stupen(d["text"])
        if PORADI[st] >= PORADI[pripravenost["stupen"]]:
            pripravenost = {"stupen": st, "nazev": NAZEV_STUPNE[st], "doklad": d, "jistota": "dolozeno"}
    nositele = list(dict.fromkeys(d["ico"] for d in moje if d["ico"]))
    return {
        "typ": "polozka", "id": p["id"], "nazev": p["nazev"], "popis": p.get("popis"), "oblast": p.get("oblast"),
        "nositele": [{"ico": i, "nazev": subjekty.get(i, i)} for i in nositele],
        "nositel_jistota": "nase_propojeni" if nositele else "nevime",
        "pripravenost": pripravenost,
        "doklady": [d | {"stupen": stupen(d["text"]), "jistota": "nase_propojeni"} for d in moje],
        "prvni_doklad": moje[0]["datum"] if moje else None,
        "odhad": _odhad(p.get("odhad")),
        "zdroj": p.get("zdroj"),
        "stavby": (stavby := _stavby(p, data, v_kartach)),
        "faze": _faze(moje, stavby),
    }


def _faze(doklady: list[dict], stavby: list[dict]) -> str:
    """`realizovano` = po poslední přípravě (bez dodatků) byla zadána stavba a je ukončené plnění (E-ZAK);
    `stavba` = po přípravě běží zakázka na stavbu → čas založit kartu; jinak `zasobnik`."""
    priprava = [d["datum"] or "" for d in doklady if not modul_projekty.RE_DODATEK.search(d["text"])]
    posledni = max(priprava) if priprava else ""
    po = [z for z in stavby if (z["datum"] or "") >= posledni]
    if any(z["stav"] == "ukončeno plnění" for z in po):
        return "realizovano"
    return "stavba" if po else "zasobnik"


def _odhad(o: dict | None) -> dict | None:
    if not o:
        return None
    return {"hodnota": float(o["hodnota"]), "mena": "CZK", "jednotka": "Kč", "s_dph": o.get("s_dph"),
            "druh": "odhad", "url": o.get("url"), "citace": o.get("citace"), "jistota": "dolozeno"}


def zkontroluj(polozky: list[dict], aktivity: dict) -> list[str]:
    chyby, ids = [], set()
    for p in polozky:
        pid = p.get("id")
        for pole in ("id", "nazev", "oblast"):
            if not p.get(pole):
                chyby.append(f"zásobník {pid!r}: chybí pole {pole}")
        if pid in ids:
            chyby.append(f"zásobník {pid}: duplicitní id")
        ids.add(pid)
        if p.get("oblast") and p["oblast"] not in OBLASTI:
            chyby.append(f"zásobník {pid}: neznámá oblast {p['oblast']!r}")
        hledat = (p.get("vazby") or {}).get("hledat") or []
        if not hledat and not (p.get("zdroj") or {}).get("url"):
            chyby.append(f"zásobník {pid}: položka bez vazeb musí mít zdroj s url (jen reálné nápady)")
        for vzor in hledat + ((p.get("vazby") or {}).get("vyloucit") or []):
            try:
                re.compile(vzor)
            except re.error as e:
                chyby.append(f"zásobník {pid}: chybný vzor {vzor!r}: {e}")
        o = p.get("odhad")
        if o and (o.get("hodnota") is None or not o.get("url") or "s_dph" not in o):
            chyby.append(f"zásobník {pid}: odhad potřebuje hodnotu, s_dph a url zdroje")
        for i in p.get("sprm") or []:
            if aktivity and int(i) not in aktivity:
                chyby.append(f"zásobník {pid}: aktivita SPRM {i} v evidenci není")
    return chyby


def nacti_subjekty(koren: Path) -> dict:
    cesta = koren / "config" / "subjekty.yaml"
    if not cesta.exists():
        return {}
    return {str(s["ico"]): s["nazev"] for s in yaml.safe_load(cesta.read_text(encoding="utf-8")) or []}


def sestav(koren: Path, data: dict, projekty: list[dict]) -> tuple[list[dict], list[str]]:
    aktivity, pravidla = modul_projekty.nacti_sprm(koren)
    rucni = nacti(koren)
    chyby = zkontroluj(rucni, aktivity)
    if chyby:
        return [], chyby
    subjekty = nacti_subjekty(koren)
    doklady = _doklady(data)
    v_kartach = _v_kartach(projekty)
    vysledek = []
    for p in rucni:
        z = sestav_polozku(p, doklady, data, v_kartach, subjekty)
        z["sprm"] = modul_projekty.prirad_sprm(z, p, aktivity, pravidla)
        vysledek.append(z)
    pouzite = v_kartach | {d["id"] for z in vysledek for d in z["doklady"]}
    for d in sorted(doklady, key=lambda d: (d["datum"] or "", d["id"]), reverse=True):
        if d["id"] in pouzite or (d["datum"] or "") < KANDIDATI_OD:
            continue
        vysledek.append({"typ": "kandidat", "id": f"kandidat-{d['id']}", "nazev": d["text"],
                         "nositele": [{"ico": d["ico"], "nazev": subjekty.get(d["ico"], d["ico"])}] if d["ico"] else [],
                         "doklad": d, "stupen": stupen(d["text"]), "jistota": "nase_propojeni"})
    v_pouziti = {s["id"] for k in projekty for s in k.get("sprm", [])} | \
                {s["id"] for z in vysledek if z["typ"] == "polozka" for s in z["sprm"]}
    for i, a in sorted(aktivity.items()):
        if a.get("stav") == "Plánováno" and i not in v_pouziti:
            vysledek.append({"typ": "namet", "id": f"sprm-{i}", "nazev": " ".join(a["aktivita"].split()),
                             "osa": a.get("osa_nazev"), "opatreni": a.get("opatreni"),
                             "stav_v_evidenci": a.get("stav"), "komentar": a.get("komentar") or None,
                             "faze": "namet", "jistota": "dolozeno",
                             "zdroj": "https://trebonaci.cz/wp-json/trebonaci/v1/projekty"})
    return vysledek, chyby
