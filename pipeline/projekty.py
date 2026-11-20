"""Projektové karty: ručně spravované `data/projekty/*.yaml` + automatické vazby → `data/projekty.json`.

Projekt (soubor YAML) určuje jen identitu akce: název, popis, ORG a názvy rozpočtových položek a vzory
(`vazby.hledat`, regulární výrazy bez ohledu na velikost písmen), podle kterých se k němu najdou
zakázky (E-ZAK), smlouvy (registr) a usnesení. Všechno ostatní dopočítá kód z `data/`:

- rozpočet: položky RO s ORG projektu („doloženo“) nebo s názvem položky z `rozpocet.nazvy` („naše propojení“),
- zakázky, smlouvy, usnesení podle vzorů v názvu / předmětu / textu („naše propojení“); usnesení, z něhož
  pochází RO projektu, je „doloženo“,
- role části (projekt, stavba, technický dozor, BOZP, vybavení, dodatek) podle názvu,
- časová osa a fáze (návrh z dokladů, ne úřední stav).

Částky se nesčítají: karta ukazuje každou s druhem a údajem o DPH tak, jak je ve zdroji.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROLE = [  # pořadí = priorita; dodatek je zvlášť (dodatek_cislo) a patří k roli smlouvy, kterou mění
    ("technicky_dozor", r"technick\w* dozor"),
    ("bozp", r"koordinátor\w* BOZP"),
    ("projekt", r"projektov\w* dokumentac|zpracování PD|\bDZS\b|\bDPS\b"),
    ("vybaveni", r"vybavení|dodávka|posilovn|televiz"),
    ("administrace", r"administrac\w* (?:veřejné )?zakázk|zadávacího řízení"),
]
RE_DODATEK = re.compile(r"dodat\w*\s+č\.\s*(\d+)", re.I)


def role(text: str) -> str:
    for nazev, vzor in ROLE:
        if re.search(vzor, text or "", re.I):
            return nazev
    return "stavba"


def nacti_projekty(koren: Path) -> list[dict]:
    adresar = koren / "data" / "projekty"
    return [yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted(adresar.glob("*.yaml"))] \
        if adresar.exists() else []


def _odpovida(text: str, projekt: dict) -> bool:
    v = projekt.get("vazby") or {}
    if not text:
        return False
    text = " ".join(text.split())
    if any(re.search(x, text, re.I) for x in v.get("vyloucit") or []):
        return False
    return any(re.search(x, text, re.I) for x in v.get("hledat") or [])


def _smluvni(castky: list[dict]) -> list[dict]:
    return [{"hodnota": c["hodnota"], "s_dph": c.get("s_dph"), "druh": c.get("druh", "smluvni"),
             "mena": c.get("mena", "CZK"), "jednotka": c.get("jednotka", "Kč")}
            for c in castky if c.get("druh", "smluvni") == "smluvni"]


def sestav_projekt(p: dict, data: dict) -> dict:
    datum_jednani = {j["id"]: j["datum"] for j in data["jednani"]}
    usneseni = {u["id"]: u for u in data["usneseni"]}
    orgy = set((p.get("rozpocet") or {}).get("org") or [])
    nazvy = set((p.get("rozpocet") or {}).get("nazvy") or [])
    udalosti = []

    # rozpočet: položky RO (jen přijatá usnesení)
    polozky: dict[tuple, dict] = {}
    usneseni_ro: dict[str, str] = {}
    for r in data["rozpoctova_opatreni"]:
        if r["vysledek_hlasovani"] != "prijato" or r["strana"] != "vydaje":
            continue
        if r["org"] in orgy:
            jistota = "dolozeno"
        elif r["nazev"] in nazvy:
            jistota = "nase_propojeni"
        else:
            continue
        if usneseni_ro.get(r["usneseni_id"]) != "dolozeno":
            usneseni_ro[r["usneseni_id"]] = jistota
        klic = (r["org"], r["nazev"])
        pol = polozky.setdefault(klic, {"org": r["org"], "nazev": r["nazev"], "polozka": r["polozka"],
                                        "kapitalova": r["polozka"].startswith("6"), "jistota": jistota,
                                        "zmeny": []})
        datum = datum_jednani.get(r["jednani_id"])
        pol["zmeny"].append({"datum": datum, "cislo_ro": r["cislo_ro"], "organ": r["organ"], "zmena": r["zmena"],
                             "rozpocet": r["rozpocet"], "usneseni_id": r["usneseni_id"], "ro_id": r["id"]})
        udalosti.append({"datum": datum, "typ": "rozpocet", "text": f"Rozpočtové opatření č. {r['cislo_ro']}",
                         "zmena": r["zmena"], "polozka": r["nazev"], "zdroj_id": r["id"], "jistota": jistota})
    for pol in polozky.values():
        pol["zmeny"].sort(key=lambda z: (z["datum"] or "", z["cislo_ro"]))
        posledni = next((z["rozpocet"] for z in reversed(pol["zmeny"]) if z["rozpocet"]), None)
        pol["schvaleny"] = posledni["schvaleny"] if posledni else None
        pol["po_poslednim_ro"] = posledni["po_ro"] if posledni else None

    # zakázky (E-ZAK)
    zakazky = []
    for z in data["zakazky"]:
        if not _odpovida(z["nazev"], p):
            continue
        r_ = role(z["nazev"])
        casti = []
        for c in z["casti"]:
            vitezove = [{"nazev": v["nazev"], "smluvni": _smluvni(v["castky"]),
                         "zaplaceno": [{"obdobi": k["obdobi"], "hodnota": k["hodnota"], "s_dph": k.get("s_dph")}
                                       for k in v["castky"] if k.get("druh") == "zaplaceno"]}
                        for v in c["vitezove"]]
            casti.append({"nazev": c["nazev"], "stav": c["stav"], "pocet_nabidek": c["pocet_nabidek"],
                          "datum_uverejneni": c["datum_uverejneni"],
                          "datum_uzavreni_smlouvy": c["datum_uzavreni_smlouvy"], "vitezove": vitezove})
            if c["datum_uverejneni"]:
                udalosti.append({"datum": c["datum_uverejneni"], "typ": "soutez", "text": f"Soutěž: {z['nazev']}",
                                 "role": r_, "zdroj_id": z["id"], "jistota": "nase_propojeni"})
        zakazky.append({"id": z["id"], "nazev": z["nazev"], "role": r_, "stav": z["stav"],
                        "url": z["url"], "casti": casti, "jistota": "nase_propojeni"})

    # smlouvy (registr)
    smlouvy = []
    for s in data["smlouvy"]:
        if not _odpovida(s["predmet"], p):
            continue
        r_ = role(s["predmet"])
        m = RE_DODATEK.search(s["predmet"] or "")
        smlouvy.append({"id": s["id"], "predmet": s["predmet"], "role": r_,
                        "dodatek_cislo": int(m[1]) if m else None, "datum_uzavreni": s["datum_uzavreni"],
                        "strany": [x["nazev"] for x in s["strany"]], "castky": _smluvni(s["castky"]),
                        "url": s["url"], "jistota": "nase_propojeni"})
        udalosti.append({"datum": s["datum_uzavreni"], "typ": "dodatek" if m else "smlouva",
                         "text": s["predmet"], "role": r_, "zdroj_id": s["id"], "jistota": "nase_propojeni"})

    # usnesení
    vazane = []
    for u in data["usneseni"]:
        if u["id"] in usneseni_ro:
            jistota = usneseni_ro[u["id"]]
        elif _odpovida(u["text"], p):
            jistota = "nase_propojeni"
        else:
            continue
        vazane.append({"id": u["id"], "cislo": u["cislo"], "datum": datum_jednani.get(u["jednani_id"]),
                       "tema": u["tema"], "tema_ai": u.get("tema_ai"), "shrnuti": u["shrnuti"],
                       "shrnuti_ai": u.get("shrnuti_ai"), "citace": u.get("citace"), "overeni": u.get("overeni"),
                       "vysledek_hlasovani": u["vysledek_hlasovani"], "jistota": jistota})
        if u["id"] not in usneseni_ro:
            udalosti.append({"datum": datum_jednani.get(u["jednani_id"]), "typ": "usneseni", "text": u["tema"],
                             "text_ai": u.get("tema_ai"), "overeni": u.get("overeni"),
                             "zdroj_id": u["id"], "jistota": jistota})

    udalosti.sort(key=lambda e: (e["datum"] or "", e["typ"]))
    return {
        "id": p["id"], "nazev": p["nazev"], "popis": p.get("popis"), "oblast": p.get("oblast"),
        "druh": p.get("druh"), "vlastnik_subjekt_id": p.get("vlastnik_subjekt_id"),
        "faze": faze(zakazky, smlouvy), "faze_jistota": "nase_propojeni",
        "rozpocet": sorted(polozky.values(), key=lambda x: (not x["kapitalova"], x["nazev"])),
        "zakazky": sorted(zakazky, key=lambda z: z["id"]),
        "smlouvy": sorted(smlouvy, key=lambda s: (s["datum_uzavreni"] or "", s["id"])),
        "usneseni": sorted(vazane, key=lambda u: (u["datum"] or "", u["id"])),
        # nejvyšší známé číslo dodatku podle role (starší dodatky nemusí být v datech)
        "posledni_dodatek": {r_: max(s["dodatek_cislo"] for s in smlouvy if s["role"] == r_ and s["dodatek_cislo"])
                             for r_ in sorted({s["role"] for s in smlouvy if s["dodatek_cislo"]})},
        "udalosti": udalosti,
        "posledni_udalost": udalosti[-1] if udalosti else None,
    }


def faze(zakazky: list[dict], smlouvy: list[dict]) -> str:
    """Návrh fáze z dokladů (ne úřední stav): podle hlavní zakázky na stavbu."""
    stavby = [z for z in zakazky if z["role"] == "stavba"]
    def _hotovo(z: dict) -> bool:  # u vícečástečné zakázky musí být ukončeny všechny části
        stavy = [c["stav"] for c in z["casti"]] if z["stav"] is None and z["casti"] else [z["stav"]]
        return all(st == "ukončeno plnění" for st in stavy)

    if any(_hotovo(z) for z in stavby):
        return "dokonceno"
    if any(v for z in stavby for c in z["casti"] for v in c["vitezove"]) or \
            any(s["role"] == "stavba" for s in smlouvy):
        return "probiha"
    if stavby:
        return "soutezi_se"
    return "pripravuje_se"


def sestav(koren: Path, data: dict) -> tuple[list[dict], list[str]]:
    chyby, vysledek, ids = [], [], set()
    for p in nacti_projekty(koren):
        for pole in ("id", "nazev", "vazby"):
            if not p.get(pole):
                chyby.append(f"projekt {p.get('id')!r}: chybí pole {pole}")
        if p.get("id") in ids:
            chyby.append(f"projekt {p['id']}: duplicitní id")
        ids.add(p.get("id"))
        if chyby:
            continue
        for vzor in (p["vazby"].get("hledat") or []) + (p["vazby"].get("vyloucit") or []):
            try:
                re.compile(vzor)
            except re.error as e:
                chyby.append(f"projekt {p['id']}: chybný vzor {vzor!r}: {e}")
        vysledek.append(sestav_projekt(p, data))
    return vysledek, chyby
