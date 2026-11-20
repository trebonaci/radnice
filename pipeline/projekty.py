"""Projektové karty: ručně spravované `data/projekty/*.yaml` + automatické vazby → `data/projekty.json`.

Projekt (soubor YAML) určuje jen identitu akce: název, popis, ORG a názvy rozpočtových položek a vzory
(`vazby.hledat`, regulární výrazy bez ohledu na velikost písmen), podle kterých se k němu najdou
zakázky (E-ZAK), smlouvy (registr) a usnesení. Všechno ostatní dopočítá kód z `data/`:

- rozpočet: položky RO s ORG projektu („doloženo“) nebo s názvem položky z `rozpocet.nazvy` („naše propojení“),
- schválený rozpočet roku: položky `data/rozpocet.json` s názvem z `rozpocet.schvaleny` („naše propojení“,
  rozpočet ORG neuvádí),
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


NAZEV_ROLE = {"stavba": "smlouva o dílo", "technicky_dozor": "technický dozor", "bozp": "BOZP",
              "vybaveni": "vybavení", "administrace": "administrace výběrového řízení"}


def druh_projektu(text: str) -> str:
    """Stupeň projektové dokumentace z názvu smlouvy nebo zakázky."""
    t = text or ""
    studie = re.search(r"studi", t, re.I)
    provadeci = re.search(r"provedení stavby|\bDPS\b|prováděc", t)
    povoleni = re.search(r"\bDSP\b|\bDUR\b|stavební\w* povolení|společné\w* povolení|povolení stavby|"
                         r"stavební\w* řízení", t, re.I)
    if studie:
        return "architektonická studie"
    if provadeci and povoleni:
        return "projekt pro stavební řízení a prováděcí"
    if provadeci:
        return "projekt prováděcí"
    if povoleni:
        return "projekt pro stavební řízení"
    return "projektová dokumentace"


def kratky_popis(role_: str, text: str, dodatek: int | None = None) -> str:
    """Krátký popis smlouvy pro historii akce (systémový název je až v detailu)."""
    co = druh_projektu(text) if role_ == "projekt" else NAZEV_ROLE.get(role_, role_)
    return f"dodatek {dodatek} ({co})" if dodatek else co


def kratce_usneseni(u: dict) -> str:
    """Krátký popis usnesení v historii akce: co orgán schválil, bez opakování názvu akce."""
    t = " ".join((u.get("text") or "").split())
    if u.get("vysledek_hlasovani") != "prijato":
        return "návrh nepřijat"
    m = re.search(r"Dodatku č\.\s*(\d+)", t)
    if m:
        return f"schválení dodatku {m[1]}"
    if re.search(r"nejvýhodnější nabídk|výběr\w* (dodavatele|zhotovitele)|pořadí nabídek", t):
        return "výběr dodavatele"
    m = re.search(r"rozpočtového opatření č\.\s*(\d+)", t)
    if m:
        return f"rozpočtové opatření č. {m[1]}"
    return u.get("tema") or ""


def dni_mezi(od: str | None, do: str | None) -> int | None:
    from datetime import date
    try:
        return (date.fromisoformat(do[:10]) - date.fromisoformat(od[:10])).days
    except (TypeError, ValueError):
        return None


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


def _smluvni(castky: list[dict], druh: str = "smluvni") -> list[dict]:
    return [{"hodnota": c["hodnota"], "s_dph": c.get("s_dph"), "druh": c.get("druh", "smluvni"),
             "mena": c.get("mena", "CZK"), "jednotka": c.get("jednotka", "Kč")}
            for c in castky if c.get("druh", "smluvni") == druh]


def sestav_projekt(p: dict, data: dict) -> dict:
    datum_jednani = {j["id"]: j["datum"] for j in data["jednani"]}
    usneseni = {u["id"]: u for u in data["usneseni"]}
    url_dokumentu = {j["dokument"]["dokument_id"]: j["dokument"]["url"] for j in data["jednani"] if j.get("dokument")}

    def odkaz_zapisu(citace: dict | None) -> str | None:
        """Odkaz na zápis (PDF) se stranou, kde je usnesení – „#page=N“ otevře prohlížeč na té straně."""
        url = url_dokumentu.get((citace or {}).get("dokument_id"))
        strany = (citace or {}).get("strany") or []
        return f"{url}#page={strany[0]}" if url and strany else url
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
                         "kategorie": "rozpočet",
                         "kratce": ("navýšení" if r["zmena"] > 0 else "snížení") + f" (opatření č. {r['cislo_ro']})",
                         "zmena": r["zmena"], "polozka": r["nazev"], "zdroj_id": r["id"], "jistota": jistota,
                         "usneseni_cislo": r.get("usneseni_cislo"), "url": odkaz_zapisu(r.get("citace"))})
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
                         "nabidkova": _smluvni(v["castky"], "nabidkova"),
                         "zaplaceno": [{"obdobi": k["obdobi"], "hodnota": k["hodnota"], "s_dph": k.get("s_dph")}
                                       for k in v["castky"] if k.get("druh") == "zaplaceno"]}
                        for v in c["vitezove"]]
            casti.append({"nazev": c["nazev"], "stav": c["stav"], "pocet_nabidek": c["pocet_nabidek"],
                          "datum_uverejneni": c["datum_uverejneni"],
                          "datum_uzavreni_smlouvy": c["datum_uzavreni_smlouvy"], "vitezove": vitezove,
                          "registr_smluv": c.get("registr_smluv", [])})
            if c["datum_uverejneni"] or c.get("lhuta_nabidek"):
                # Délka výběrového řízení (#136): od zveřejnění do podpisu smlouvy. Malé zakázky E-ZAK často
                # zveřejní až po skončení soutěže (uveřejnění po lhůtě pro nabídky) – začátek pak neznáme
                # a uvádí se jen doba od konce lhůty pro nabídky do smlouvy.
                lhuta_konec, smlouva_ = c.get("lhuta_nabidek"), c.get("datum_uzavreni_smlouvy")
                zacatek = c["datum_uverejneni"]
                if zacatek and lhuta_konec and dni_mezi(zacatek, lhuta_konec) < 0:
                    zacatek = None
                lhuta = dni_mezi(zacatek, lhuta_konec) if zacatek else None
                rizeni = dni_mezi(zacatek, smlouva_) if zacatek else None
                po_nabidkach = dni_mezi(lhuta_konec, smlouva_)
                datum_soutez = zacatek or lhuta_konec
                predmet = "stavba" if r_ == "stavba" else kratky_popis(r_, z["nazev"])
                n = c.get("pocet_nabidek")
                nabidky = (f"{n} nabídka" if n == 1 else f"{n} nabídky" if 2 <= n <= 4 else f"{n} nabídek") if n else None
                if rizeni is not None:
                    doba = f"od vyhlášení do smlouvy {rizeni} dní" + (f" (lhůta pro nabídky {lhuta} dní)" if lhuta else "")
                elif lhuta is not None:
                    doba = f"lhůta pro nabídky {lhuta} dní, smlouva zatím není"
                elif po_nabidkach is not None:
                    doba = f"smlouva {po_nabidkach} dní po podání nabídek (vyhlášení zveřejněno až dodatečně)"
                else:
                    doba = None
                udalosti.append({"datum": datum_soutez, "typ": "soutez", "text": f"Soutěž: {z['nazev']}",
                                 "kategorie": "výběrové řízení",
                                 "kratce": ", ".join(x for x in [predmet, doba, nabidky] if x),
                                 "lhuta_dni": lhuta, "rizeni_dni": rizeni, "po_nabidkach_dni": po_nabidkach,
                                 "pocet_nabidek": n, "url": z["url"],
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
                         "kategorie": "smlouva", "kratce": kratky_popis(r_, s["predmet"], int(m[1]) if m else None),
                         "text": s["predmet"], "role": r_, "zdroj_id": s["id"], "jistota": jistota, "url": s["url"]})

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
                             "kategorie": "rada" if u["id"].startswith("rm-") else "zastupitelstvo",
                             "kratce": kratce_usneseni(u),
                             "text_ai": u.get("tema_ai"), "overeni": u.get("overeni"),
                             "usneseni_cislo": u["cislo"], "url": odkaz_zapisu(u.get("citace")),
                             "zdroj_id": u["id"], "jistota": jistota})

    schvaleny_nazvy = set((p.get("rozpocet") or {}).get("schvaleny") or [])
    schvaleny = [{"id": r["id"], "rok": r["rok"], "nazev": r["nazev"], "trida": r["trida"], "castka": r["castka"],
                  "po_zmenach": r.get("po_zmenach"), "zmeny_ro": r.get("zmeny_ro", []), "nova": False,
                  "jistota": "nase_propojeni"}
                 for r in data.get("rozpocet", []) if r["nazev"] in schvaleny_nazvy]
    # položky přidané rozpočtovým opatřením během roku (ve schváleném rozpočtu nejsou), např. dotace KIF
    # u přístavby tělocvičen – podle názvu z přehledu RO (#138)
    from pipeline.rozpocet_zmeny import _klic, klic_polozky, normalizuj_nazev, posledni_stav
    v_rozpoctu = {(r["rok"],) + klic_polozky(r["orj"], r["oddil"], "KV" if r["trida"] == "kapitalove" else "BV", r["nazev"])
                  for r in data.get("rozpocet", [])}
    hledane = {normalizuj_nazev(n) for n in schvaleny_nazvy}
    for k, r in posledni_stav(data.get("rozpocet_zmeny", [])).items():
        if k not in v_rozpoctu and k[-1] in hledane:
            schvaleny.append({"id": r["id"], "rok": r["rok"], "nazev": r["ucel"],
                              "trida": "kapitalove" if r["druh_zkratka"] == "KV" else "bezne",
                              "castka": {"hodnota": 0.0, "mena": "CZK", "jednotka": "Kč", "s_dph": None, "druh": "rozpocet"},
                              "po_zmenach": {"hodnota": float(r["po_zmene"]), "mena": "CZK", "jednotka": "Kč", "s_dph": None,
                                             "druh": "rozpocet_upraveny", "po_ro": r["cislo_ro"], "zdroj_id": r["id"]},
                              "zmeny_ro": [x["cislo_ro"] for x in data.get("rozpocet_zmeny", []) if _klic(x) == k],
                              "nova": True, "jistota": "nase_propojeni"})

    # Dokončení stavby (#136): kolaudace / předání není v žádném strojově čteném zdroji, proto ho zapisuje
    # člověk do YAML s dokladem ({datum, popis, url}). Doplacení = E-ZAK „ukončeno plnění“ u zakázky na stavbu
    # (zadavatel tím uzavírá smlouvu a zveřejňuje skutečně uhrazenou cenu) – jiná událost než dokončení.
    dokonceni = dict(p["dokonceni"]) if p.get("dokonceni") else None
    if dokonceni:
        dokonceni["datum"] = str(dokonceni["datum"])     # YAML bez uvozovek dá datetime.date
        udalosti.append({"datum": str(dokonceni["datum"]), "typ": "dokonceni", "kategorie": "dokončení",
                         "kratce": dokonceni.get("popis") or "stavba dokončena", "text": dokonceni.get("popis") or "",
                         "url": dokonceni.get("url"), "zdroj_id": None, "jistota": "dolozeno"})
    stavby_ = [z for z in zakazky if z["role"] == "stavba"]
    doplaceno = bool(stavby_) and all(c["stav"] == "ukončeno plnění" for z in stavby_ for c in z["casti"])

    udalosti.sort(key=lambda e: (e["datum"] or "", e["typ"]))
    rozpocet = sorted(polozky.values(), key=lambda x: (not x["kapitalova"], x["nazev"]))
    return {
        "id": p["id"], "nazev": p["nazev"], "popis": p.get("popis"), "oblast": p.get("oblast"),
        "druh": p.get("druh"), "vlastnik_subjekt_id": p.get("vlastnik_subjekt_id"),
        "faze": "dokonceno" if dokonceni else faze(zakazky, smlouvy),
        "faze_jistota": "dolozeno" if dokonceni else "nase_propojeni",
        "dokonceni": dokonceni,
        "doplaceno": doplaceno,
        "rozpocet": rozpocet,
        "schvaleny_rozpocet": schvaleny,
        "casti": (casti := casti_akce(zakazky, smlouvy, dodatky_jen_termin(data["usneseni"]))),
        "souhrn": souhrn(rozpocet, casti) | {"schvaleny": souhrn_schvaleny(schvaleny)},
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
    return {"rozpocet": rozpocet_souhrn, "smluvni_bez_dph": smluvni, "smluvni_s_dph": smluvni_s,
            "skladba_s_dph": skladba(casti)}


SKUPINY = [("stavba", "Stavba", ("stavba",)),
           ("priprava", "Projekt a výběrové řízení", ("projekt", "administrace")),
           ("dozor", "Technický dozor a BOZP", ("technicky_dozor", "bozp")),
           ("vybaveni", "Vybavení", ("vybaveni",))]


def skladba(casti: list[dict]) -> list[dict]:
    """Cena akce po skupinách (#136), s DPH po dodatcích (druh smluvni). Skupina bez známé ceny všech částí
    má `castka` null a seznam chybějících rolí; skupiny se sčítají až na kartě, jen když jsou všechny známé."""
    vysledek = []
    for klic, nazev, role_ in SKUPINY:
        cc = [c for c in casti if c["role"] in role_]
        if not cc:
            continue
        nezname = [c["role"] for c in cc if c.get("cena_po_dodatcich_s_dph") is None]
        vysledek.append({"skupina": klic, "nazev": nazev, "casti": len(cc),
                         "castka": None if nezname else sum(_halere(c["cena_po_dodatcich_s_dph"]) for c in cc) / 100,
                         "nezname": nezname, "druh": "smluvni", "s_dph": True})
    return vysledek


def souhrn_schvaleny(schvaleny: list[dict]) -> list[dict]:
    """Schválený rozpočet akce po letech (druh rozpocet, jeden rok = jeden součet; s upraveným se nesčítá)."""
    vysledek = []
    for rok in sorted({s["rok"] for s in schvaleny}):
        roku = [s for s in schvaleny if s["rok"] == rok]
        inv = sum(_halere(s["castka"]["hodnota"]) for s in roku if s["trida"] == "kapitalove")
        neinv = sum(_halere(s["castka"]["hodnota"]) for s in roku if s["trida"] == "bezne")
        # po změnách (přehled RO): položka bez změny zůstává na schválené částce
        po = [_halere((s.get("po_zmenach") or {}).get("hodnota", s["castka"]["hodnota"])) for s in roku]
        po_inv = sum(v for s, v in zip(roku, po) if s["trida"] == "kapitalove")
        vysledek.append({"rok": rok, "celkem": (inv + neinv) / 100, "investicni": inv / 100, "neinvesticni": neinv / 100,
                         "druh": "rozpocet", "s_dph": None, "polozek": len(roku), "jistota": "nase_propojeni",
                         "po_zmenach": {"celkem": sum(po) / 100, "investicni": po_inv / 100,
                                        "neinvesticni": (sum(po) - po_inv) / 100, "druh": "rozpocet_upraveny",
                                        "s_dph": None,
                                        "zmeneno": any(s.get("po_zmenach") for s in roku)}})
    return vysledek


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
                # Původní cena (#136): smluvní cena v E-ZAK se po dodatcích přepisuje („Cena po dodatku č. 5“),
                # proto přednost má podepsaná smlouva z registru, pak nabídková cena vítěze z E-ZAK a teprve
                # nakonec smluvní cena z E-ZAK (jen bez dodatků, jinak by se dodatky započetly dvakrát).
                ezak = {"zdroj_id": z["id"], "url": z["url"]}
                kandidati = []
                if g["puvodni"]:
                    kandidati.append((_bez_dph(g["puvodni"]["castky"]), _s_dph(g["puvodni"]["castky"]),
                                      {"zdroj_id": g["puvodni"]["id"], "url": g["puvodni"]["url"]}, "registr"))
                kandidati.append((_bez_dph(v.get("nabidkova", [])), _s_dph(v.get("nabidkova", [])), ezak, "nabidka"))
                kandidati.append((_bez_dph(v["smluvni"]), _s_dph(v["smluvni"]), ezak, "smluvni_ezak"))
                cena = cena_s = zdroj = zdroj_s = druh_zdroje = druh_s = None
                for bez, s_, zdr, druh_ in kandidati:      # každý základ DPH z prvního zdroje, který ho má
                    if cena is None and bez is not None:
                        cena, zdroj, druh_zdroje = bez, zdr, druh_
                    if cena_s is None and s_ is not None:
                        cena_s, zdroj_s, druh_s = s_, zdr, druh_
                # původ se sleduje pro každý základ DPH zvlášť (bez DPH z nabídky, s DPH ze smluvní ceny po dodatcích…)
                po_dodatcich_ezak = [z_ for z_, d_ in (("bez_dph", druh_zdroje), ("s_dph", druh_s))
                                     if d_ == "smluvni_ezak" and g["dodatky"]]
                druh_zdroje = druh_zdroje or druh_s
                zdroj = zdroj or zdroj_s or ezak
                if zdroj_s == zdroj:
                    zdroj_s = None
                ezak_akt = {"bez_dph": _bez_dph(v["smluvni"]), "s_dph": _s_dph(v["smluvni"])}
                nabidka = {"bez_dph": _bez_dph(v.get("nabidkova", [])), "s_dph": _s_dph(v.get("nabidkova", []))}
                casti.append({"role": z["role"], "dodavatel": {"nazev": v["nazev"],
                                                               "jmeno_podnikatele": v.get("jmeno_podnikatele")},
                              "puvodni": {"bez_dph": cena, "s_dph": cena_s, **zdroj, "zdroj_druh": druh_zdroje,
                                          # smluvní cena E-ZAK u smlouvy s dodatky může už dodatky obsahovat
                                          "muze_obsahovat_dodatky": bool(po_dodatcich_ezak),
                                          "zaklady_z_ezak_po_dodatcich": po_dodatcich_ezak,
                                          **({"zdroj_s_dph": zdroj_s} if zdroj_s else {})},
                              "vysoutezena": nabidka if any(x is not None for x in nabidka.values()) else None,
                              "ezak_smluvni": ezak_akt, "ezak_url": z["url"],
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
        pu = c["puvodni"]
        if pu and pu.get("s_dph_dopocteno") and "bez_dph" in pu.get("zaklady_z_ezak_po_dodatcich", []):
            pu["zaklady_z_ezak_po_dodatcich"] = pu["zaklady_z_ezak_po_dodatcich"] + ["s_dph"]   # dopočet dědí původ
        cisla = {d["cislo"] for d in c["dodatky"]}
        c["chybi_dodatky"] = sorted(set(range(1, max(cisla) + 1)) - cisla) if cisla else []
        # dodatek bez částky v registru = změna ceny neznámá (kromě dodatku jen o termínu podle usnesení)
        c["obsahuje_dopocet_dph"] = any(x and x.get("s_dph_dopocteno") for x in [c["puvodni"]] + c["dodatky"])
        for klic, pole in (("cena_po_dodatcich", "bez_dph"), ("cena_po_dodatcich_s_dph", "s_dph")):
            zaklad = (c["puvodni"][pole] if c["puvodni"]
                      and pole not in c["puvodni"].get("zaklady_z_ezak_po_dodatcich", []) else None)
            znam = all(d[pole] is not None for d in c["dodatky"])
            c[klic] = ((_halere(zaklad) + sum(_halere(d[pole]) for d in c["dodatky"])) / 100
                       if zaklad is not None and not c["chybi_dodatky"] and znam else None)
        # kontrola: E-ZAK uvádí smluvní cenu po dodatcích – shoduje se s naším součtem?
        ea = c.get("ezak_smluvni") or {}
        porovnani = [(ea.get(z), c[k]) for z, k in (("bez_dph", "cena_po_dodatcich"), ("s_dph", "cena_po_dodatcich_s_dph"))
                     if ea.get(z) is not None and c[k] is not None]
        c["souhlas_ezak"] = (None if not c["dodatky"] or not porovnani
                             else all(abs(_halere(a) - _halere(b)) <= 100 for a, b in porovnani))
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
        from pipeline.rozpocet_zmeny import normalizuj_nazev
        roky = {r["rok"] for r in data.get("rozpocet", [])}
        nazvy_roku = ({normalizuj_nazev(r["nazev"]) for r in data.get("rozpocet", [])}
                      | {normalizuj_nazev(r["ucel"]) for r in data.get("rozpocet_zmeny", [])})
        for nazev in (p.get("rozpocet") or {}).get("schvaleny") or []:
            if roky and normalizuj_nazev(nazev) not in nazvy_roku:
                chyby.append(f"projekt {p['id']}: položka schváleného rozpočtu {nazev!r} v rozpočtu není")
        vysledek.append(sestav_projekt(p, data))
    return vysledek, chyby
