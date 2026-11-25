"""Sestavení statického webu radnice.trebonaci.cz (#191) → `_site/index.html`.

    python -m web.build [--vystup _site] [--nahled]

Šablona `web/site/sablona.html` + data z `data/*.json` (vložená do stránky, žádný server ani databáze).
Zveřejnění (rozhodnutí Ondřeje 22. 11. 2026): vzhled a typy obsahu schvaluje Ondřej (větev `verejne`),
denní data z ověřené pipeline jdou ven automaticky. `--nahled` označí stránku jako neschválený náhled."""
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import date
from pathlib import Path

from web.zpravy import zpravy_pro_web

KOREN = Path(__file__).resolve().parent.parent
SABLONA = KOREN / "web" / "site" / "sablona.html"


def _json(nazev: str):
    cesta = KOREN / "data" / f"{nazev}.json"
    return json.loads(cesta.read_text(encoding="utf-8")) if cesta.exists() else []


def _vloz(hodnota) -> str:
    return json.dumps(hodnota, ensure_ascii=False).replace("</", "<\\/")


def _datum(beh: dict) -> str:
    d = (beh or {}).get("zacatek", "")[:10]
    if not d:
        return ""
    r, m, den = d.split("-")
    return f"{int(den)}. {int(m)}. {r}"


def usneseni_pro_web(usneseni: list[dict], jednani: list[dict]) -> list[dict]:
    """Výběr polí usnesení pro stránku #usneseni (#198): nic se nepočítá, jen se vybírá a doplní odkaz na stranu zápisu."""
    j = {x["id"]: x for x in jednani}
    vysledek = []
    for u in usneseni:
        jd = j.get(u["jednani_id"], {})
        url = (jd.get("dokument") or {}).get("url")
        strany = (u.get("citace") or {}).get("strany") or []
        po = u.get("pro_obcany") or {}
        vysledek.append({
            "id": u["id"], "cislo": u.get("cislo"), "jednani_id": u["jednani_id"], "datum": jd.get("datum"),
            "organ": jd.get("organ"), "jednani_cislo": jd.get("cislo"), "bod": u.get("bod"),
            "vysledek": u.get("vysledek_hlasovani"), "tema": u.get("tema"), "tema_ai": u.get("tema_ai"),
            "shrnuti": po.get("text") or u.get("shrnuti"),
            "shrnuti_ai": bool(u.get("pro_obcany_ai") if po.get("text") else u.get("shrnuti_ai")),
            "kategorie": u.get("kategorie") or ["ostatni"], "okruh": u.get("okruh"), "okruhy": u.get("okruhy") or [],
            "strana": strany[0] if strany else None,
            "url": f"{url}#page={strany[0]}" if url and strany else url, "zapis": url,
        })
    vysledek.sort(key=lambda x: (x["datum"] or "", x["organ"] or "", x["cislo"] or ""), reverse=True)
    return vysledek


def zpravy_stranky(zpravy: list[dict], okruhy: list[dict], beh: dict) -> dict:
    """Zprávy a KPI pro „Co se děje“; 30 dní se počítá k datu posledního běhu (bez běhu k nejnovější zprávě)."""
    den = (beh or {}).get("zacatek", "")[:10] or max((z["datum"] for z in zpravy), default=date.today().isoformat())
    return zpravy_pro_web(zpravy, [o["id"] for o in okruhy], date.fromisoformat(den))
def kpi_investic(projekty: list, investice: dict | None) -> dict:
    """KPI stránky Investice a opravy: jen čísla z dat (počty podle fáze, cena podle smluv s DPH
    u probíhajících akcí, investice v rozpočtu po změnách bez rezervy). Nic se neodhaduje."""
    pocty = {f: 0 for f in ("probiha", "soutezi_se", "pripravuje_se", "dokonceno")}
    for p in projekty:
        if p.get("faze") in pocty:
            pocty[p["faze"]] += 1
    pocty["celkem"] = len(projekty)
    cena, s_cenou, neuplnych, akci = 0.0, 0, 0, 0
    for p in projekty:
        if p.get("faze") != "probiha":
            continue
        akci += 1
        c = (p.get("souhrn") or {}).get("celkova_cena_s_dph") or {}
        if c.get("castka") is None:
            continue
        cena += c["castka"]
        s_cenou += 1
        neuplnych += 1 if c.get("neuplne") else 0
    inv = investice or {}
    return {
        "pocty": pocty,
        "cena_probihajicich": {"castka": round(cena, 2), "akci": akci, "akci_s_cenou": s_cenou,
                               "neuplnych": neuplnych, "druh": "smluvni", "s_dph": True},
        "rozpocet": {"castka": inv.get("bez_rezervy_po_zmenach"), "rok": inv.get("rok"),
                     "druh": "rozpocet_upraveny", "s_dph": None},
    }


def sestav(nahled: bool = False) -> str:
    beh = json.loads((KOREN / "data" / "beh.json").read_text(encoding="utf-8")) if (KOREN / "data" / "beh.json").exists() else {}
    datum = _datum(beh)
    investice = _json("investice")
    stitek = (f"Náhled · data k {datum} · neschváleno ke zveřejnění" if nahled
              else f"Data aktualizována {datum}" if datum else "Data z veřejných zdrojů")
    nahrady = {
        "__DATA__": _vloz(_json("projekty")),
        "__MAPA__": _vloz(_json("mapa")),
        "__GISCSS__": (SABLONA.parent / "mapa.css").read_text(encoding="utf-8"),
        "__GISJS__": (SABLONA.parent / "mapa.js").read_text(encoding="utf-8"),
        "__ZASOBNIK__": _vloz(_json("zasobnik")),
        "__MISTA__": _vloz(_json("mista")),
        "__ZMENY__": _vloz(_json("zmeny")),
        "__OKRUHY__": _vloz(_json("okruhy")),
        "__ZPRAVY__": _vloz(zpravy_stranky(_json("zpravy"), _json("okruhy"), beh)),
        "__HARMONOGRAM__": _vloz(_json("harmonogram")),
        "__UKAZATELE__": _vloz(_json("ukazatele")),
        "__USNESENI__": _vloz(usneseni_pro_web(_json("usneseni"), _json("jednani"))),
        "__INVESTICE__": _vloz((investice or [None])[-1]),
        "__KPI__": _vloz(kpi_investic(_json("projekty") or [], (investice or [None])[-1])),
        "__STITEK__": stitek,
        "__DATUM__": datum,
    }
    html = SABLONA.read_text(encoding="utf-8")
    for klic, hodnota in nahrady.items():
        html = html.replace(klic, hodnota)
    zbyle = sorted(set(re.findall(r"__[A-Z]+__", html)))
    if zbyle:
        raise ValueError(f"nenahrazené značky v šabloně: {zbyle}")
    return html


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("--vystup", default="_site")
    a.add_argument("--nahled", action="store_true")
    args = a.parse_args()
    cil = Path(args.vystup)
    cil.mkdir(parents=True, exist_ok=True)
    (cil / "index.html").write_text(sestav(args.nahled), encoding="utf-8")
    # obrázky šablony (logo Třeboňáků)
    shutil.copytree(SABLONA.parent / "obr", cil / "obr", dirs_exist_ok=True)
    # písmo Inter (licence OFL) – z vlastního webu, ne z Google Fonts
    shutil.copytree(SABLONA.parent / "fonts", cil / "fonts", dirs_exist_ok=True)
    # knihovna mapy Leaflet (#208) – z vlastního webu, ne z CDN
    shutil.copytree(SABLONA.parent / "leaflet", cil / "leaflet", dirs_exist_ok=True)
    # Datové JSON pro modul /radnice/ na trebonaci.cz (#177): servírované z Cloudflare,
    # načítané napříč doménami (CORS níže), aktualizuje je denní běh pipeline automaticky.
    data_cil = cil / "data"
    data_cil.mkdir(exist_ok=True)
    for nazev in ("prehled", "ukazatele", "beh"):
        zdroj = KOREN / "data" / f"{nazev}.json"
        if zdroj.exists():
            shutil.copyfile(zdroj, data_cil / f"{nazev}.json")
    # Cloudflare Pages: bez indexování náhledů, základní bezpečnostní hlavičky;
    # /data/* je veřejné JSON pro cizí doménu (trebonaci.cz), proto CORS a bez indexace.
    (cil / "_headers").write_text(
        "/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n"
        + ("  X-Robots-Tag: noindex\n" if args.nahled else "")
        + "\n/data/*\n  Access-Control-Allow-Origin: *\n  X-Robots-Tag: noindex\n",
        encoding="utf-8")
    print(cil / "index.html")


if __name__ == "__main__":
    main()
