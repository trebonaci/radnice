"""Přehled dění na radnici pro web (#187) → `data/prehled.json`.

Podle designových pravidel Ondřeje (docs/DESIGN-PREHLED-RADNICE.md): každá položka má typ, stav jako textový
štítek, věcný titulek, krátké shrnutí, datum události, odkaz na primární zdroj (konkrétně pojmenovaný, PDF
označené) a případně doložený další krok. Návrh se nesmí tvářit jako rozhodnutí.

Položky:
- změny pro občany z přijatých usnesení (`data/zmeny.json`) – stav „rozhodnuto“,
- karty investic – stav podle fáze z dokladů (plánuje se / soutěží se / realizuje se / dokončeno),
- položky pracovního zásobníku – stav „plánuje se“ (doklad: smlouva nebo zakázka na přípravu).
Řazení: nejnovější událost nahoře; datum události se nemění datem aktualizace přehledu.
"""
from __future__ import annotations

STAVY = {
    "rozhodnuto": {"nazev": "Rozhodnuto", "popis": "Rada nebo zastupitelstvo usnesení přijalo."},
    "vzato_na_vedomi": {"nazev": "Vzato na vědomí", "popis": "Rada nebo zastupitelstvo informaci jen vzalo na vědomí, o věci nerozhodovalo."},
    "navrzeno": {"nazev": "Navrženo", "popis": "Návrh je předložený, o něm se zatím nerozhodlo."},
    "projednava_se": {"nazev": "Projednává se", "popis": "Věc je na programu jednání nebo běží výběrové řízení."},
    "planuje_se": {"nazev": "Plánuje se", "popis": "Město má peníze v rozpočtu nebo zadalo přípravu (studii, projekt)."},
    "realizuje_se": {"nazev": "Realizuje se", "popis": "Smlouva je uzavřená, práce probíhají."},
    "dokonceno": {"nazev": "Dokončeno", "popis": "Stavba je předaná nebo zaplacená."},
}
FAZE_NA_STAV = {"pripravuje_se": "planuje_se", "soutezi_se": "projednava_se", "probiha": "realizuje_se",
                "dokonceno": "dokonceno"}
ORGAN = {"rada": "Rada města", "zastupitelstvo": "Zastupitelstvo města"}
OBLASTI = {"sport": "Sport", "kultura": "Kultura a památky", "socialni": "Sociální služby", "skolstvi": "Školy a školky",
           "doprava": "Doprava a ulice", "voda_odpady": "Voda a odpady", "bydleni": "Bydlení", "zelen": "Zeleň",
           "lazne": "Lázně", "komunity_spolky": "Komunitní život a spolky", "verejna_sprava": "Úřad a samospráva",
           "jine": "Ostatní", "ostatni": "Ostatní", None: "Ostatní"}
DRUH_ZDROJE = {"smlouva": "Registr smluv", "dodatek": "Registr smluv", "soutez": "Veřejná zakázka (E-ZAK)",
               "usneseni": None, "rozpocet": None}


def _datum_cz(d: str | None) -> str:
    if not d:
        return ""
    r, m, den = d[:10].split("-")
    return f"{int(den)}. {int(m)}. {r}"


def _zdroj_zapisu(url: str | None, organ: str | None, datum: str | None) -> dict | None:
    if not url:
        return None
    strana = url.split("#page=")[1] if "#page=" in url else None
    nazev = f"Zápis z jednání {'rady' if organ == 'rada' else 'zastupitelstva'} města, {_datum_cz(datum)}"
    return {"nazev": nazev, "url": url, "druh": "zápis", "pdf": True, "strana": int(strana) if strana else None,
            "datum": datum}


def _zdroj_udalosti(u: dict) -> dict | None:
    if not u or not u.get("url"):
        return None
    if u["typ"] in ("usneseni", "rozpocet"):
        organ = "zastupitelstvo" if (u.get("usneseni_cislo") or "").startswith("ZM") else "rada"
        z = _zdroj_zapisu(u["url"], organ, u["datum"])
        return z | {"nazev": f"{z['nazev']} – {u['usneseni_cislo']}"} if u.get("usneseni_cislo") else z
    druh = DRUH_ZDROJE.get(u["typ"]) or "Zdroj"
    return {"nazev": f"{druh}: {u.get('kratce') or u.get('text')}, {_datum_cz(u['datum'])}", "url": u["url"],
            "druh": druh, "pdf": u["url"].lower().split("#")[0].endswith(".pdf"), "strana": None, "datum": u["datum"]}


def ze_zmen(zmeny: list[dict]) -> list[dict]:
    vysledek = []
    for z in zmeny:
        zdroj = _zdroj_zapisu(z.get("url"), z.get("organ"), z.get("datum"))
        if zdroj and z.get("usneseni_cislo"):
            zdroj["nazev"] += f" – usnesení {z['usneseni_cislo']}"
        vysledek.append({
            "id": z["id"], "druh": "zmena", "typ": ORGAN.get(z.get("organ"), "Radnice"),
            "oblast": z.get("oblast"), "oblast_nazev": OBLASTI.get(z.get("oblast"), "Ostatní"),
            "stav": "vzato_na_vedomi" if z.get("ukony") == ["bere_na_vedomi"] else "rozhodnuto",
            "titulek": z.get("kdo") or "Změna pro občany", "shrnuti": z["text"],
            "datum": z.get("datum"), "zdroj": zdroj,
            "dalsi_krok": f"Platí od {_datum_cz(z['plati_od'])}." if z.get("plati_od") else None,
            "text_ai": bool(z.get("pro_obcany_ai")), "misto_id": z.get("misto_id"),
        })
    return vysledek


def z_investic(projekty: list[dict]) -> list[dict]:
    vysledek = []
    for p in projekty:
        posledni = p.get("posledni_udalost") or {}
        stav = FAZE_NA_STAV.get(p.get("faze"), "planuje_se")
        vysledek.append({
            "id": f"investice-{p['id']}", "druh": "investice", "typ": "Investice",
            "oblast": p.get("oblast"), "oblast_nazev": OBLASTI.get(p.get("oblast"), "Ostatní"),
            "stav": stav, "stav_jistota": p.get("faze_jistota"), "titulek": p["nazev"],
            "shrnuti": p.get("popis") or "",
            "posledni_udalost": posledni.get("kratce") or posledni.get("text"),
            "datum": posledni.get("datum"), "zdroj": _zdroj_udalosti(posledni), "dalsi_krok": None,
            "karta_id": p["id"], "text_ai": bool(posledni.get("text_ai")),
        })
    return vysledek


def ze_zasobniku(zasobnik: list[dict]) -> list[dict]:
    vysledek = []
    for z in zasobnik:
        if z["typ"] != "polozka" or z.get("faze") not in ("zasobnik", "stavba") or not z.get("doklady"):
            continue
        d = z["pripravenost"]["doklad"] or z["doklady"][-1]
        nositel = ", ".join(n["nazev"] for n in z.get("nositele", []) if n["ico"] != "00247618")
        shrnuti = f"Připravuje se: {z['pripravenost']['nazev']}" + (f" (zadavatel {nositel})" if nositel else "") + "."
        druh = "Registr smluv" if d["typ"] == "smlouva" else "Veřejná zakázka (E-ZAK)"
        vysledek.append({
            "id": f"zasobnik-{z['id']}", "druh": "zasobnik", "typ": "Příprava investice",
            "oblast": z.get("oblast"), "oblast_nazev": OBLASTI.get(z.get("oblast"), "Ostatní"),
            "stav": "planuje_se", "titulek": z["nazev"], "shrnuti": shrnuti,
            "datum": d.get("datum"),
            "zdroj": {"nazev": f"{druh}: {d['text']}, {_datum_cz(d.get('datum'))}", "url": d.get("url"), "druh": druh,
                      "pdf": False, "strana": None, "datum": d.get("datum")} if d.get("url") else None,
            "dalsi_krok": None, "text_ai": False,
        })
    return vysledek


def sestav(zmeny: list[dict], projekty: list[dict], zasobnik: list[dict]) -> list[dict]:
    zaznamy = ze_zmen(zmeny) + z_investic(projekty) + ze_zasobniku(zasobnik)
    # bez primárního zdroje se položka nezveřejňuje jako ověřený fakt (pravidlo 1)
    zaznamy = [z for z in zaznamy if z["zdroj"] and z["zdroj"].get("url") and z["datum"]]
    for z in zaznamy:
        z["stav_nazev"], z["stav_popis"] = STAVY[z["stav"]]["nazev"], STAVY[z["stav"]]["popis"]
    return sorted(zaznamy, key=lambda z: (z["datum"], z["id"]), reverse=True)
