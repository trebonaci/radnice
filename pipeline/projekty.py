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
    ("projekt", r"projektov\w* dokumentac|vypracování projekt|projekt\w* interiér|zpracování PD|\bDZS\b|\bDPS\b"),
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
            vitezove = [{"nazev": v["nazev"], "jmeno_podnikatele": v.get("jmeno_podnikatele"), "smluvni": _smluvni(v["castky"]),
                         "zaplaceno": [{"obdobi": k["obdobi"], "hodnota": k["hodnota"], "s_dph": k.get("s_dph")}
                                       for k in v["castky"] if k.get("druh") == "zaplaceno"]}
                        for v in c["vitezove"]]
            casti.append({"nazev": c["nazev"], "stav": c["stav"], "pocet_nabidek": c["pocet_nabidek"],
                          "datum_uverejneni": c["datum_uverejneni"],
                          "datum_uzavreni_smlouvy": c["datum_uzavreni_smlouvy"], "vitezove": vitezove,
                          "registr_smluv": c.get("registr_smluv", [])})
            if c["datum_uverejneni"]:
                udalosti.append({"datum": c["datum_uverejneni"], "typ": "soutez", "text": f"Soutěž: {z['nazev']}",
                                 "role": r_, "zdroj_id": z["id"], "jistota": "nase_propojeni"})
        zakazky.append({"id": z["id"], "nazev": z["nazev"], "role": r_, "stav": z["stav"],
                        "url": z["url"], "casti": casti, "jistota": "nase_propojeni"})

    # smlouvy (registr)
    smlouvy = []
    shodne = [s for s in data["smlouvy"] if _odpovida(s["predmet"], p)]
    navazane = {s["navazuje_na"] for s in shodne if s.get("navazuje_na")}
    shodne_id = {s["id"] for s in shodne}
    # původní smlouvy, na které dodatky odkazují v registru (`navazanyZaznam`) = doložená vazba
    puvodni = [s for s in data["smlouvy"] if s["id_smlouvy"] in navazane and s["id"] not in shodne_id]
    vybrane_id = shodne_id | {s["id"] for s in puvodni}
    vybrane_smlouvy = {s["id_smlouvy"] for s in shodne + puvodni if s.get("id_smlouvy")}
    # další dodatky odkazující na vybrané původní smlouvy (i s obecným předmětem) – jinak by řada dodatků byla neúplná
    dalsi = [s for s in data["smlouvy"] if s["id"] not in vybrane_id and s.get("navazuje_na") in vybrane_smlouvy]
    for s, jistota in ([(x, "nase_propojeni") for x in shodne] + [(x, "dolozeno") for x in puvodni]
                       + [(x, "dolozeno") for x in dalsi]):
        r_ = role(s["predmet"])
        m = RE_DODATEK.search(s["predmet"] or "")
        smlouvy.append({"id": s["id"], "id_smlouvy": s["id_smlouvy"], "navazuje_na": s.get("navazuje_na"),
                        "cislo_smlouvy": s.get("cislo_smlouvy"),
                        "predmet": s["predmet"], "role": r_,
                        "dodatek_cislo": int(m[1]) if m else None, "datum_uzavreni": s["datum_uzavreni"],
                        "strany": [{"nazev": x["nazev"], "jmeno_podnikatele": x.get("jmeno_podnikatele")}
                                   for x in s["strany"]],
                        "castky": _smluvni(s["castky"]), "cena_neuvedena": s.get("cena_neuvedena"),
                        "url": s["url"], "evidencni_cislo_zakazky": s.get("evidencni_cislo_zakazky"),
                        "jistota": jistota})
        udalosti.append({"datum": s["datum_uzavreni"], "typ": "dodatek" if m else "smlouva",
                         "text": s["predmet"], "role": r_, "zdroj_id": s["id"], "jistota": jistota})

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
    rozpocet = sorted(polozky.values(), key=lambda x: (not x["kapitalova"], x["nazev"]))
    return {
        "id": p["id"], "nazev": p["nazev"], "popis": p.get("popis"), "oblast": p.get("oblast"),
        "druh": p.get("druh"), "vlastnik_subjekt_id": p.get("vlastnik_subjekt_id"),
        "faze": faze(zakazky, smlouvy), "faze_jistota": "nase_propojeni",
        "rozpocet": rozpocet,
        "casti": (casti := casti_akce(zakazky, smlouvy, dodatky_jen_termin(data["usneseni"]))),
        "souhrn": souhrn(rozpocet, casti),
        "zakazky": sorted(zakazky, key=lambda z: z["id"]),
        "smlouvy": sorted(smlouvy, key=lambda s: (s["datum_uzavreni"] or "", s["id"])),
        "usneseni": sorted(vazane, key=lambda u: (u["datum"] or "", u["id"])),
        # nejvyšší známé číslo dodatku podle role (starší dodatky nemusí být v datech)
        "posledni_dodatek": {r_: max(s["dodatek_cislo"] for s in smlouvy if s["role"] == r_ and s["dodatek_cislo"])
                             for r_ in sorted({s["role"] for s in smlouvy if s["dodatek_cislo"]})},
        "udalosti": udalosti,
        "posledni_udalost": udalosti[-1] if udalosti else None,
    }


def _halere(v: float) -> int:
    return round(v * 100)


def souhrn(rozpocet: list[dict], casti: list[dict]) -> dict:
    """Kolik stojí celá akce – dva součty, každý jen v rámci jednoho druhu částky (nikdy mezi sebou):

    - `rozpocet`: stav všech položek akce po posledním RO, investiční i neinvestiční (druh rozpocet_upraveny),
    - `smluvni_bez_dph`: `celkem` = původní smluvní ceny všech částí (`casti_akce`) bez DPH v Kč;
      `po_dodatcich` = součet cen po dodatcích, jen když ji známe u všech částí (jinak null, chybějící v `neuplne`).
    """
    inv = [p for p in rozpocet if p["kapitalova"] and p["po_poslednim_ro"] is not None]
    neinv = [p for p in rozpocet if not p["kapitalova"] and p["po_poslednim_ro"] is not None]
    r = {"investicni": sum(_halere(p["po_poslednim_ro"]) for p in inv),
         "neinvesticni": sum(_halere(p["po_poslednim_ro"]) for p in neinv)}
    if inv + neinv:
        rozpocet_souhrn = {"celkem": (r["investicni"] + r["neinvesticni"]) / 100, "investicni": r["investicni"] / 100,
                           "neinvesticni": r["neinvesticni"] / 100, "druh": "rozpocet_upraveny", "s_dph": None,
                           "polozek": len(inv) + len(neinv),
                           "jistota": "dolozeno" if all(p["jistota"] == "dolozeno" for p in inv + neinv)
                           else "nase_propojeni"}
    else:
        rozpocet_souhrn = {"celkem": None, "investicni": None, "neinvesticni": None, "druh": "rozpocet_upraveny",
                           "s_dph": None, "polozek": 0, "jistota": "nevime"}

    znamo = [c for c in casti if c["puvodni"] and c["puvodni"]["bez_dph"] is not None]
    po = [c for c in casti if c["cena_po_dodatcich"] is not None]
    smluvni = {"celkem": sum(_halere(c["puvodni"]["bez_dph"]) for c in znamo) / 100 if znamo else None,
               "druh": "smluvni", "s_dph": False, "mena": "CZK",
               "po_dodatcich": sum(_halere(c["cena_po_dodatcich"]) for c in po) / 100
               if po and len(po) == len(casti) else None,
               "neuplne": [c["role"] for c in casti if c["cena_po_dodatcich"] is None],
               "jistota": "nase_propojeni"}
    # totéž s DPH – rozpočet města počítá s cenou včetně DPH, proto karta ukazuje přednostně tento základ
    znamo_s = [c for c in casti if c["puvodni"] and c["puvodni"].get("s_dph") is not None]
    po_s = [c for c in casti if c.get("cena_po_dodatcich_s_dph") is not None]
    smluvni_s = {"celkem": sum(_halere(c["puvodni"]["s_dph"]) for c in znamo_s) / 100 if znamo_s else None,
                 "druh": "smluvni", "s_dph": True, "mena": "CZK",
                 "po_dodatcich": sum(_halere(c["cena_po_dodatcich_s_dph"]) for c in po_s) / 100
                 if po_s and len(po_s) == len(casti) else None,
                 "neuplne": [c["role"] for c in casti if c.get("cena_po_dodatcich_s_dph") is None],
                 "jistota": "nase_propojeni"}
    return {"rozpocet": rozpocet_souhrn, "smluvni_bez_dph": smluvni, "smluvni_s_dph": smluvni_s}


def _bez_dph(castky: list[dict]) -> float | None:
    kc = [x for x in castky if x["s_dph"] is False and x.get("mena", "CZK") == "CZK"]
    return kc[0]["hodnota"] if kc else None


def _s_dph(castky: list[dict]) -> float | None:
    kc = [x for x in castky if x["s_dph"] is True and x.get("mena", "CZK") == "CZK"]
    return kc[0]["hodnota"] if kc else None


RE_DODATEK_TERMIN = re.compile(
    r"Dodatku č\.\s*(\d+) ke smlouvě o dílo č\.\s*([\d/]+).{0,400}?jehož předmětem je změna termínu dokončení díla(?![^.]*cen)")


def dodatky_jen_termin(usneseni: list[dict]) -> dict[str, str]:
    """Číslo dodatku v registru (`<číslo SOD>/<N>`) → id usnesení, podle kterého dodatek mění jen termín.

    Doklad ze zdroje: přijaté usnesení „uzavření Dodatku č. N ke smlouvě o dílo č. X …, jehož předmětem
    je změna termínu dokončení díla“ (bez zmínky o ceně). Takový dodatek cenu nemění, i když v registru
    částku nemá.
    """
    vysledek = {}
    for u in usneseni:
        if u.get("vysledek_hlasovani") != "prijato":
            continue
        for m in RE_DODATEK_TERMIN.finditer(" ".join((u.get("text") or "").split())):
            vysledek[f"{m[2]}/{m[1]}"] = u["id"]
    return vysledek


SAZBY_DPH = (1.0, 1.10, 1.12, 1.15, 1.21)
SAZBA_VYCHOZI = 1.21


def sazba_dph(polozky: list[dict]) -> float | None:
    """Sazba DPH (koeficient) z položek téže smlouvy, které mají cenu bez i s DPH: poměr s/bez zaokrouhlený
    na zákonnou sazbu. Neplátce DPH (stejná částka) = 1.0. Bez takové položky None."""
    for x in polozky:
        b, sd = (x or {}).get("bez_dph"), (x or {}).get("s_dph")
        if b and sd and not (x or {}).get("s_dph_dopocteno"):
            pomer = sd / b
            for k in SAZBY_DPH:
                if abs(pomer - k) < 0.005:
                    return k
    return None


def doplnit_dph(c: dict) -> None:
    """Kde smlouva nebo dodatek uvádí jen cenu bez DPH, dopočítá cenu s DPH (Ondřej 20. 11. 2026, #115):
    sazbou z jiné položky téže smlouvy (i neplátce = 0 %), jinak základní sazbou 21 %. Dopočtená částka má
    `s_dph_dopocteno: true` a `sazba_dph` (%); ve zdroji ji nehledat."""
    polozky = [c["puvodni"]] + c["dodatky"]
    zjistena = sazba_dph(polozky)
    k = zjistena or SAZBA_VYCHOZI
    for x in polozky:
        if x and x.get("s_dph") is None and x.get("bez_dph") is not None:
            x["s_dph"] = round(_halere(x["bez_dph"]) * k) / 100
            x["s_dph_dopocteno"] = True
            x["sazba_dph"] = round((k - 1) * 100)
            x["sazba_dph_zdroj"] = "jina_polozka_smlouvy" if zjistena else "zakladni_sazba"


def casti_akce(zakazky: list[dict], smlouvy: list[dict], jen_termin: dict[str, str] | None = None) -> list[dict]:
    """Části akce (stavba, projekt, dozor, BOZP, vybavení…): původní smlouva + její dodatky.

    - Dodatek patří k původní smlouvě přes `navazuje_na` z registru (doloženo); bez něj tvoří vlastní skupinu.
    - Původní cena: smluvní cena vítěze z E-ZAK, jinak z registru. Zakázka E-ZAK se se skupinou smluv spojí
      přes odkaz do registru (doloženo), jinak jen když je v akci jediná zakázka i jediná skupina dané role.
    - Částka u dodatku v registru je **změna ceny** (ověřeno na dodatku č. 1 smlouvy s koordinátorem BOZP
      přístavby tělocvičen: 138 900 + 7 750 = 146 650 Kč bez DPH, 20. 11. 2026). Dodatek bez částky
      nemá známou změnu ceny – cena po dodatcích pak zůstává neznámá.
    - `cena_po_dodatcich` (bez DPH) počítá kód jen při známé původní ceně a úplné řadě dodatků 1..N.
    """
    skupiny: dict[str, dict] = {}
    for sm in smlouvy:
        klic = (sm["navazuje_na"] if sm["dodatek_cislo"] and sm.get("navazuje_na") else sm["id_smlouvy"]) or sm["id"]
        g = skupiny.setdefault(klic, {"puvodni": None, "dodatky": [], "role": sm["role"]})
        if sm["dodatek_cislo"]:
            g["dodatky"].append(sm)
        else:
            g["puvodni"] = sm
            g["role"] = sm["role"]

    def dodavatel(strany):
        return {"nazev": ", ".join(x["nazev"] for x in strany),
                "jmeno_podnikatele": ", ".join(x["jmeno_podnikatele"] for x in strany if x["jmeno_podnikatele"]) or None}

    casti = []
    volne = dict(skupiny)
    for z in zakazky:
        for c in z["casti"]:
            for v in c["vitezove"]:
                odkazy = set(c.get("registr_smluv") or [])
                klic = next((k for k, g in volne.items() if g["puvodni"] and g["puvodni"]["url"] in odkazy), None)
                if not klic:   # shoda podle evidenčního čísla zakázky (doloženo)
                    cislo = z["id"].removeprefix("ezak-")
                    klic = next((k for k, g in volne.items()
                                 if g["puvodni"] and g["puvodni"].get("evidencni_cislo_zakazky") == cislo), None)
                jistota = "dolozeno" if klic else None
                if not klic:   # stejná role a stejný dodavatel, jinak jediná zakázka i skupina dané role
                    jmeno = v.get("jmeno_podnikatele") or v["nazev"]
                    stejne = [k for k, g in volne.items() if g["role"] == z["role"]]
                    dodavatel_ = [k for k in stejne if any(
                        jmeno in (x["jmeno_podnikatele"] or x["nazev"])
                        for x in (volne[k]["puvodni"] or (volne[k]["dodatky"] or [{}])[0]).get("strany", []))]
                    if len(dodavatel_) == 1:
                        klic, jistota = dodavatel_[0], "nase_propojeni"
                    elif (len(stejne) == 1 and sum(1 for x in zakazky if x["role"] == z["role"]) == 1
                          and not any((x["jmeno_podnikatele"] or x["nazev"]) not in ("", "fyzická osoba")
                                      for x in (volne[stejne[0]]["puvodni"] or (volne[stejne[0]]["dodatky"] or [{}])[0])
                                      .get("strany", []))):
                        # jen když skupina nemá známého jiného dodavatele (např. jen anonymní strany)
                        klic, jistota = stejne[0], "nase_propojeni"
                g = volne.pop(klic) if klic else {"puvodni": None, "dodatky": []}
                cena, cena_s, zdroj = _bez_dph(v["smluvni"]), _s_dph(v["smluvni"]), {"zdroj_id": z["id"], "url": z["url"]}
                zdroj_s = None
                if g["puvodni"]:
                    reg = {"zdroj_id": g["puvodni"]["id"], "url": g["puvodni"]["url"]}
                    reg_bez, reg_s = _bez_dph(g["puvodni"]["castky"]), _s_dph(g["puvodni"]["castky"])
                    # každý základ DPH se doplňuje z registru zvlášť; druhý známý údaj se nepřepisuje
                    if cena is None and reg_bez is not None:
                        cena, zdroj = reg_bez, reg
                        if cena_s is not None:
                            zdroj_s = {"zdroj_id": z["id"], "url": z["url"]}
                    if cena_s is None and reg_s is not None:
                        cena_s = reg_s
                        if cena is not None and zdroj is not reg:
                            zdroj_s = reg
                casti.append({"role": z["role"], "dodavatel": {"nazev": v["nazev"],
                                                               "jmeno_podnikatele": v.get("jmeno_podnikatele")},
                              "puvodni": {"bez_dph": cena, "s_dph": cena_s, **zdroj,
                                          **({"zdroj_s_dph": zdroj_s} if zdroj_s else {})},
                              "dodatky_smlouvy": g["dodatky"], "vazba_dodatku": jistota})
    for g in volne.values():
        p_ = g["puvodni"]
        strany = (p_ or (g["dodatky"] or [{}])[0]).get("strany", [])
        casti.append({"role": g["role"], "dodavatel": dodavatel(strany),
                      "puvodni": {"bez_dph": _bez_dph(p_["castky"]), "s_dph": _s_dph(p_["castky"]),
                                  "zdroj_id": p_["id"], "url": p_["url"]}
                      if p_ else None,
                      "dodatky_smlouvy": g["dodatky"], "vazba_dodatku": "dolozeno" if p_ else None})
    for c in casti:
        dodatky = sorted(c.pop("dodatky_smlouvy"), key=lambda d: d["dodatek_cislo"])
        c["dodatky"] = []
        for d in dodatky:
            termin = (jen_termin or {}).get(d.get("cislo_smlouvy") or "") if not d["castky"] else None
            c["dodatky"].append({"cislo": d["dodatek_cislo"], "bez_dph": 0.0 if termin else _bez_dph(d["castky"]),
                                 "s_dph": 0.0 if termin else _s_dph(d["castky"]),
                                 "jen_termin": termin is not None, "doklad_usneseni": termin,
                                 "bez_castky": not d["castky"], "datum": d["datum_uzavreni"], "zdroj_id": d["id"],
                                 "url": d["url"]})
        doplnit_dph(c)
        cisla = {d["cislo"] for d in c["dodatky"]}
        c["chybi_dodatky"] = sorted(set(range(1, max(cisla) + 1)) - cisla) if cisla else []
        # dodatek bez částky v registru = změna ceny neznámá (kromě dodatku jen o termínu podle usnesení)
        c["obsahuje_dopocet_dph"] = any(x and x.get("s_dph_dopocteno") for x in [c["puvodni"]] + c["dodatky"])
        for klic, pole in (("cena_po_dodatcich", "bez_dph"), ("cena_po_dodatcich_s_dph", "s_dph")):
            zaklad = c["puvodni"][pole] if c["puvodni"] else None
            znam = all(d[pole] is not None for d in c["dodatky"])
            c[klic] = ((_halere(zaklad) + sum(_halere(d[pole]) for d in c["dodatky"])) / 100
                       if zaklad is not None and not c["chybi_dodatky"] and znam else None)
        c["dodatky_bez_dph"] = (sum(_halere(d["bez_dph"]) for d in c["dodatky"] if d["bez_dph"] is not None) / 100
                                if any(d["bez_dph"] is not None for d in c["dodatky"]) else None)
    poradi = ["stavba", "projekt", "technicky_dozor", "bozp", "vybaveni", "administrace"]
    return sorted(casti, key=lambda c: poradi.index(c["role"]) if c["role"] in poradi else 99)


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
