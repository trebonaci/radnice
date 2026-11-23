"""Harmonogram investic a dlouhodobých projektů (#194) → `data/harmonogram.json`.

Řádek harmonogramu = karta investice, položka zásobníku nebo dlouhodobý neinvestiční projekt (`data/aktivity.yaml`).
Úseky (fáze) odvozuje kód jen z datovaných dokladů:

- `priprava` – od prvního dokladu před výběrem dodavatele stavby (smlouva na projekt, usnesení, rozpočet)
  do začátku výběru dodavatele stavby (nebo do smlouvy na stavbu),
- `soutez`   – od zahájení zakázky na stavbu (E-ZAK) do smlouvy o dílo,
- `stavba`   – od smlouvy o dílo; u dokončené akce do posledního dokladu ke stavbě (dodatek, smlouva) –
  skutečné předání stavby v datech není, proto `konec_jistota = "posledni_doklad"`,
- `prubeh`   – dlouhodobý neinvestiční projekt: od prvního doloženého milníku (usnesení).

Otevřený úsek (`otevreno`, `do = None`) web kreslí do dnešního dne (data tak nezávisí na dni sestavení). Data úseků jsou data dokladů, ne plánované termíny města.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

OBLASTI = {"doprava", "voda_odpady", "sport", "skolstvi", "socialni", "bydleni", "kultura", "lazne", "zelen",
           "uzemni_plan", "komunity_spolky", "jine"}
NAZEV_FAZE = {"priprava": "příprava", "soutez": "výběr dodavatele", "stavba": "stavba", "prubeh": "probíhá"}


def _usek(faze: str, od: str | None, do: str | None, **navic) -> dict | None:
    if not od:
        return None
    otevreno = do is None
    if do is not None and do < od:
        do = od
    return {"faze": faze, "nazev": NAZEV_FAZE[faze], "od": od, "do": do, "otevreno": otevreno, **navic}


def karta(k: dict, zakazky: dict) -> dict | None:
    ud = sorted((e for e in k.get("udalosti", []) if e.get("datum")), key=lambda e: e["datum"])
    if not ud:
        return None
    sml = [e for e in ud if e["typ"] == "smlouva" and e.get("role") == "stavba"]
    sout = [e for e in ud if e["typ"] == "soutez" and e.get("role") == "stavba" and not e.get("zruseno")]
    zacatek_stavby = sml[0]["datum"] if sml else None

    def zacatek_souteze(e: dict) -> str:
        z = zakazky.get(e.get("zdroj_id")) or {}
        return min(d for d in (e["datum"], z.get("datum_zahajeni")) if d)

    # soutěž, ze které vzešla smlouva: poslední zahájená do smlouvy (vyhlášení bývá zveřejněno až dodatečně)
    kandidati = [zacatek_souteze(e) for e in sout]
    pred_smlouvou = [d for d in kandidati if not zacatek_stavby or d <= zacatek_stavby]
    zac_sout = max(pred_smlouvou) if pred_smlouvou else None
    hranice = zac_sout or zacatek_stavby
    priprava = [e for e in ud if e.get("role") != "stavba" and (hranice is None or e["datum"] < hranice)]
    useky = []
    if priprava:
        useky.append(_usek("priprava", priprava[0]["datum"], hranice, url=priprava[0].get("url"),
                           jistota="nase_propojeni"))
    if zac_sout:
        e = next(x for x in sout if zacatek_souteze(x) == zac_sout)
        useky.append(_usek("soutez", zac_sout, zacatek_stavby, url=e.get("url"), jistota="dolozeno"))
    if zacatek_stavby:
        konec, konec_jistota = None, None
        if k.get("faze") == "dokonceno":
            if k.get("dokonceni") and k["dokonceni"].get("datum"):
                konec, konec_jistota = str(k["dokonceni"]["datum"]), "dolozeno"
            elif k.get("ukonceni_plneni"):
                konec, konec_jistota = k["ukonceni_plneni"]["datum"], "ukonceni_plneni"
            else:
                konec = max(e["datum"] for e in ud if e.get("role") == "stavba")
                konec_jistota = "posledni_doklad"
        useky.append(_usek("stavba", zacatek_stavby, konec, url=sml[0].get("url"), jistota="dolozeno",
                           konec_jistota=konec_jistota))
    milniky = [{"datum": e["datum"], "typ": e["typ"], "text": e.get("kratce") or e.get("text"), "url": e.get("url")}
               for e in ud if e["typ"] in ("dodatek", "usneseni") or (e["typ"] == "soutez" and e.get("zruseno"))]
    return {"typ": "investice", "id": k["id"], "nazev": k["nazev"], "oblast": k.get("oblast"), "faze": k.get("faze"),
            "faze_jistota": k.get("faze_jistota"), "useky": [u for u in useky if u], "milniky": milniky,
            "odkaz": f"#{k['id']}"}


def polozka_zasobniku(z: dict) -> dict | None:
    dokl = [d for d in z.get("doklady", []) if d.get("datum")]
    if not dokl or z.get("faze") == "realizovano":
        return None
    prvni = min(d["datum"] for d in dokl)
    return {"typ": "zasobnik", "id": z["id"], "nazev": z["nazev"], "oblast": z.get("oblast"), "faze": z.get("faze"),
            "faze_jistota": "nase_propojeni",
            "useky": [_usek("priprava", prvni, None, jistota="nase_propojeni",
                            url=next(d.get("url") for d in dokl if d["datum"] == prvni))],
            "milniky": [{"datum": d["datum"], "typ": d["typ"], "text": d["text"], "url": d.get("url")} for d in dokl],
            "odkaz": "#zasobnik"}


# ---------- dlouhodobé neinvestiční projekty ----------

def nacti_aktivity(koren: Path) -> list[dict]:
    cesta = koren / "data" / "aktivity.yaml"
    if not cesta.exists():
        return []
    return (yaml.safe_load(cesta.read_text(encoding="utf-8")) or {}).get("aktivity") or []


def zkontroluj(aktivity: list[dict]) -> list[str]:
    chyby, ids = [], set()
    for a in aktivity:
        aid = a.get("id")
        for pole in ("id", "nazev", "oblast"):
            if not a.get(pole):
                chyby.append(f"aktivita {aid!r}: chybí pole {pole}")
        if aid in ids:
            chyby.append(f"aktivita {aid}: duplicitní id")
        ids.add(aid)
        if a.get("oblast") and a["oblast"] not in OBLASTI:
            chyby.append(f"aktivita {aid}: neznámá oblast {a['oblast']!r}")
        hledat = (a.get("vazby") or {}).get("hledat") or []
        if not hledat:
            chyby.append(f"aktivita {aid}: chybí vazby.hledat (milníky z usnesení)")
        for vzor in hledat:
            try:
                re.compile(vzor)
            except re.error as e:
                chyby.append(f"aktivita {aid}: chybný vzor {vzor!r}: {e}")
        k = a.get("ukonceno")
        if k and (not k.get("datum") or not k.get("url")):
            chyby.append(f"aktivita {aid}: ukonceno potřebuje datum a url zdroje")
    return chyby


def _url_usneseni(u: dict, url_dokumentu: dict) -> str | None:
    c = u.get("citace") or {}
    url = url_dokumentu.get(c.get("dokument_id"))
    strany = c.get("strany") or []
    return f"{url}#page={strany[0]}" if url and strany else url


def aktivita(a: dict, usneseni: list[dict], jednani: dict, url_dokumentu: dict) -> dict:
    vzory = [re.compile(v) for v in a["vazby"]["hledat"]]
    milniky = []
    for u in usneseni:
        text = " ".join((u.get("text") or "").split())
        if u.get("vysledek_hlasovani") != "prijato" or not any(v.search(text) for v in vzory):
            continue
        j = jednani.get(u["jednani_id"], {})
        po = u.get("pro_obcany") or {}
        milniky.append({"datum": j.get("datum"), "typ": "usneseni", "organ": j.get("organ"), "cislo": u.get("cislo"),
                        "text": po.get("text") or u.get("shrnuti"),
                        "text_ai": bool(u.get("pro_obcany_ai") if po.get("text") else u.get("shrnuti_ai")),
                        "url": _url_usneseni(u, url_dokumentu), "jistota": "nase_propojeni"})
    milniky.sort(key=lambda m: (m["datum"] or "", m["cislo"] or ""))
    konec = (a.get("ukonceno") or {}).get("datum")
    datovane = [m for m in milniky if m["datum"]]
    useky = [_usek("prubeh", datovane[0]["datum"], str(konec) if konec else None, jistota="nase_propojeni",
                   url=datovane[0]["url"], zacatek_pred_daty=bool(a.get("zacatek_pred_daty")))] if datovane else []
    return {"typ": "aktivita", "id": a["id"], "nazev": a["nazev"], "popis": a.get("popis"), "oblast": a["oblast"],
            "faze": "dokonceno" if konec else "probiha", "faze_jistota": "nase_propojeni",
            "useky": [u for u in useky if u], "milniky": milniky, "odkaz": None, "zdroj": a.get("zdroj")}


def sestav(koren: Path, data: dict, projekty: list[dict], zasobnik: list[dict]) -> tuple[list[dict], list[str]]:
    rucni = nacti_aktivity(koren)
    chyby = zkontroluj(rucni)
    if chyby:
        return [], chyby
    zakazky = {z["id"]: z for z in data.get("zakazky", [])}
    jednani = {j["id"]: j for j in data.get("jednani", [])}
    url_dokumentu = {j["dokument"]["dokument_id"]: j["dokument"]["url"] for j in data.get("jednani", []) if j.get("dokument")}
    radky = [r for r in (karta(k, zakazky) for k in projekty) if r and r["useky"]]
    radky += [r for r in (polozka_zasobniku(z) for z in zasobnik if z["typ"] == "polozka") if r]
    radky += [aktivita(a, data.get("usneseni", []), jednani, url_dokumentu) for a in rucni]
    radky.sort(key=lambda r: ({"aktivita": 0, "investice": 1, "zasobnik": 2}[r["typ"]],
                              min((u["od"] for u in r["useky"]), default="9999")))
    return radky, chyby
