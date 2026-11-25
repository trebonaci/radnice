"""Zprávy pro stránku „Co se děje“ (#243) → `data/zpravy.json`.

Zpráva = jedna událost z jednoho veřejného dokumentu (zadání: docs/navrhy/2026-11-23/README.md, oddíl
„Co se děje: druhy zpráv“). Druhy: usnesení, změna pro občany, výběrové řízení, smlouva, dodatek, rozpočtové opatření.

Pravidla proti opakování:
1. dodatek a usnesení, které ho schválilo, jsou jedna zpráva (druh `dodatek`, dva zdroje),
2. změna pro občany nahrazuje usnesení, ze kterého vznikla,
3. víc zpráv k jedné akci (karta projektu) ve stejný den dostane společnou `skupina` (stránka je seskupí),
4. smlouva a dodatek pod 500 000 Kč bez vazby na kartu projektu nebo zásobník se nevypisují.

Částky se jen opisují ze zdroje (bez součtů). Bez AI: texty jsou šablony z polí zdroje; shrnutí usnesení je
shrnutí z anotace a nese příznak `shrnuti_ai`.
"""
from __future__ import annotations

import re

from pipeline import okruhy as modul_okruhy

PRAH = 500_000.0
DRUHY = ("usneseni", "zmena", "vyberove_rizeni", "smlouva", "dodatek", "rozpoctove_opatreni")
PROCEDURALNI = re.compile(
    r"program\w* jednání|ověřovatel|zapisovatel|návrhov\w* komis|volba \w*\s*komis|volba členů \w*\s*komis", re.I)
RE_DODATEK = re.compile(r"dodat\w*", re.I)
RE_DODATEK_USN = re.compile(r"Dodatku č\.\s*(\d+)\s+ke\s+smlouvě[^.]{0,80}?č\.\s*([\d/]+)")
RE_RO = re.compile(r"^Rozpočtov\w+ opatření", re.I)
MESICE_ORGAN = {"rada": "Rada města", "zastupitelstvo": "Zastupitelstvo města"}


def _datum_cz(d: str) -> str:
    r, m, den = d[:10].split("-")
    return f"{int(den)}. {int(m)}. {r}"


def _organ(usn: dict) -> str:
    return "zastupitelstvo" if (usn.get("cislo") or "").startswith("ZM") else "rada"


def _zdroj_zapisu(usn: dict, jednani: dict[str, dict]) -> dict:
    j = jednani.get(usn["jednani_id"]) or {}
    url = (j.get("dokument") or {}).get("url")
    strany = (usn.get("citace") or {}).get("strany") or []
    if url and strany:
        url = f"{url}#page={strany[0]}"
    organ = "rady" if _organ(usn) == "rada" else "zastupitelstva"
    return {"nazev": f"Zápis z jednání {organ} města, {_datum_cz(j.get('datum') or '')} – usnesení {usn['cislo']}",
            "url": url}


def _castka(c: dict | None, druh: str | None = None) -> dict | None:
    if not c or c.get("hodnota") is None:
        return None
    return {"hodnota": c["hodnota"], "druh": druh or c.get("druh"), "s_dph": c.get("s_dph")}


def _vyber_castku(castky: list[dict], druh: str | None = None) -> dict | None:
    """Částka ke zprávě: smluvní cena s DPH, jinak první uvedená. Opisuje, nepočítá."""
    smluvni = [c for c in castky if c.get("druh") == "smluvni" and c.get("mena", "CZK") == "CZK"]
    s_dph = [c for c in smluvni if c.get("s_dph") is True]
    bez_dph = [c for c in smluvni if c.get("s_dph") is False]
    # zdroj uvádí stejnou cenu s DPH i bez (dodavatel neplátce DPH): vezmeme variantu bez DPH –
    # shoduje se s registrem smluv a se smlouvou pak nevznikne zdánlivý rozpor dvou cen (#282)
    if s_dph and bez_dph and s_dph[0].get("hodnota") == bez_dph[0].get("hodnota"):
        return _castka(bez_dph[0], druh)
    return _castka((s_dph or smluvni or [None])[0], druh)


def _dodavatel(strany: list[dict]) -> tuple[str | None, str | None]:
    """(název, jméno podnikatele). Fyzická osoba: název „fyzická osoba“, jméno jen u podnikatele (#93, pole
    `jmeno_podnikatele` se ve výstupu nekontroluje jako osobní údaj); do textu zprávy jméno nejde."""
    vyber = [s for s in strany if s.get("prijemce")] or strany
    if not vyber:
        return None, None
    s = vyber[0]
    if s.get("fyzicka_osoba"):
        return "podnikající fyzická osoba" if s.get("jmeno_podnikatele") else "fyzická osoba", s.get("jmeno_podnikatele")
    return s.get("nazev"), None


def _jmeno_podnikatele(strany: list[dict]) -> dict:
    jmeno = _dodavatel(strany)[1]
    return {"jmeno_podnikatele": jmeno} if jmeno else {}


def _hodnota_pro_prah(castky: list[dict]) -> float:
    return max((abs(c["hodnota"]) for c in castky if c.get("hodnota") is not None and c.get("mena", "CZK") == "CZK"),
               default=0.0)


def _je_dodatek(sm: dict) -> bool:
    return bool(sm.get("navazuje_na")) and bool(RE_DODATEK.search(sm.get("predmet") or ""))


def _urci_okruh(cfg: dict, nazev: str | None, karta_okruh: str | None, zalozni: str | None = None) -> str:
    """Okruh: karta projektu / zásobník, jinak vzor v názvu (config/okruhy.yaml), jinak záložní nebo Rozvoj a správa."""
    if karta_okruh:
        return karta_okruh
    okruh, podle = modul_okruhy.pro_polozku(cfg, {"nazev": nazev}, "nazev")
    if podle == "bez tématu" and zalozni:
        return zalozni
    return okruh


OKRUH_FIRMY = "spolecnosti"  # okruh „Městské společnosti" (config/okruhy.yaml); hlídá test SLT→spolecnosti


def sestav(vystup: dict, cfg: dict, subjekty: dict[str, str] | None = None,
           firmy: set[str] | None = None) -> list[dict]:
    """Zprávy ze sestavených výstupů (po označení okruhů). Nejnovější nahoře.
    `firmy`: IČO městských obchodních společností – jejich zakázky/smlouvy bez věcného okruhu jdou do Městských společností."""
    firmy = firmy or set()

    def okruh_firmy(ico) -> str | None:
        return OKRUH_FIRMY if str(ico or "") in firmy else None

    jednani = {j["id"]: j for j in vystup.get("jednani") or []}
    usneseni = {u["id"]: u for u in vystup.get("usneseni") or []}
    karty = {k["id"]: k for k in vystup.get("projekty") or []}
    # vazby dokladů na kartu projektu / zásobník
    karta_smlouvy, karta_zakazky, karta_usneseni = {}, {}, {}
    for k in karty.values():
        for s in k.get("smlouvy") or []:
            karta_smlouvy[s["id"]] = k["id"]
        for z in k.get("zakazky") or []:
            karta_zakazky[z["id"]] = k["id"]
        for u in k.get("usneseni") or []:
            karta_usneseni[u["id"]] = k["id"]
    zasobnik_smlouvy, zasobnik_zakazky, zasobnik_okruh = {}, {}, {}
    for p in vystup.get("zasobnik") or []:
        for d in p.get("doklady") or []:
            if d.get("typ") == "smlouva":
                zasobnik_smlouvy[d["id"]] = p["id"]
            elif d.get("typ") == "zakazka":
                zasobnik_zakazky[d["id"]] = p["id"]
        zasobnik_okruh[p["id"]] = p.get("okruh")

    def okruh_vazby(karta_id: str | None, zasobnik_id: str | None) -> str | None:
        if karta_id:
            return karty[karta_id].get("okruh")
        return zasobnik_okruh.get(zasobnik_id) if zasobnik_id else None

    zpravy: list[dict] = []
    pouzita: set[str] = set()                    # usnesení, která už má jiná zpráva (změna, dodatek, RO)

    # --- změna pro občany nahrazuje usnesení
    for z in vystup.get("zmeny") or []:
        if z.get("usneseni_id"):
            pouzita.add(z["usneseni_id"])
        zpravy.append({
            "id": f"zprava-{z['id']}", "druh": "zmena", "datum": z["datum"], "okruh": z["okruh"],
            "titulek": z.get("kdo") or "Změna pro občany", "shrnuti": z["text"], "castka": None,
            "projekt_id": None, "plati_od": z.get("plati_od"),
            "zdroje": [{"nazev": f"Zápis z jednání {'rady' if z.get('organ') == 'rada' else 'zastupitelstva'} města, "
                                 f"{_datum_cz(z['datum'])} – usnesení {z.get('usneseni_cislo')}", "url": z.get("url")}],
            "jistota": "doloženo", "shrnuti_ai": bool(z.get("pro_obcany_ai")),
        })

    # --- dodatky ze smluv + usnesení, které je schválilo (jedna zpráva)
    klic_usneseni: dict[str, dict] = {}
    for u in usneseni.values():
        if u.get("vysledek_hlasovani") != "prijato":
            continue
        for m in RE_DODATEK_USN.finditer(" ".join((u.get("text") or "").split())):
            klic_usneseni[f"{m[2]}/{m[1]}"] = u
    karta_dodatek_usneseni: dict[tuple[str, int], list[dict]] = {}     # záloha: číslo dodatku v usnesení karty
    for k in karty.values():
        for u in k.get("usneseni") or []:
            plne = usneseni.get(u["id"])
            m = re.search(r"Dodatku č\.\s*(\d+)", " ".join(((plne or {}).get("text") or "").split()))
            if plne and plne.get("vysledek_hlasovani") == "prijato" and m:
                karta_dodatek_usneseni.setdefault((k["id"], int(m[1])), []).append(plne)
    karta_dodatky_cisla: dict[tuple[str, int], int] = {}
    for sm in vystup.get("smlouvy") or []:
        k = karta_smlouvy.get(sm["id"])
        m = re.search(r"dodat\w*\s+č\.\s*(\d+)", sm.get("predmet") or "", re.I)
        if k and m and _je_dodatek(sm):
            karta_dodatky_cisla[(k, int(m[1]))] = karta_dodatky_cisla.get((k, int(m[1])), 0) + 1

    for sm in vystup.get("smlouvy") or []:
        if not sm.get("datum_uzavreni"):
            continue
        karta_id = karta_smlouvy.get(sm["id"])
        zas_id = zasobnik_smlouvy.get(sm["id"])
        dodatek = _je_dodatek(sm)
        if not karta_id and not zas_id and _hodnota_pro_prah(sm.get("castky") or []) < PRAH:
            continue                              # práh: malé smlouvy bez vazby se nevypisují
        druh = "dodatek" if dodatek else "smlouva"
        castka = _vyber_castku(sm.get("castky") or [], "dodatek" if dodatek else None)
        zdroje = [{"nazev": f"Registr smluv: {sm['predmet']}", "url": sm["url"]}]
        jistota = "naše propojení" if (karta_id or zas_id) else "doloženo"
        shrnuti = _shrnuti_smlouvy(sm, dodatek)
        if dodatek:
            usn = klic_usneseni.get(sm.get("cislo_smlouvy") or "")
            if usn:
                jistota_usn = "doloženo"
            else:
                usn, jistota_usn = None, None
                m = re.search(r"dodat\w*\s+č\.\s*(\d+)", sm.get("predmet") or "", re.I)
                if karta_id and m and karta_dodatky_cisla.get((karta_id, int(m[1]))) == 1:
                    kandidati = karta_dodatek_usneseni.get((karta_id, int(m[1])), [])
                    if len(kandidati) == 1:
                        usn, jistota_usn = kandidati[0], "naše propojení"
            if usn:
                pouzita.add(usn["id"])
                zdroje.append(_zdroj_zapisu(usn, jednani))
                if jistota_usn == "naše propojení":
                    jistota = "naše propojení"
                shrnuti += f" Schválilo ho usnesení {usn['cislo']}."
        zpravy.append({
            "id": f"zprava-{sm['id']}", "druh": druh, "datum": sm["datum_uzavreni"],
            "okruh": _urci_okruh(cfg, sm["predmet"], okruh_vazby(karta_id, zas_id), okruh_firmy(sm.get("subjekt_ico"))),
            "titulek": sm["predmet"], "shrnuti": shrnuti, "castka": castka,
            "projekt_id": karta_id, "zdroje": zdroje, "jistota": jistota,
        } | _jmeno_podnikatele(sm.get("strany") or []))

    # --- rozpočtová opatření (po položkách z usnesení; bez položek aspoň podle názvu)
    polozky_ro: dict[str, list[dict]] = {}
    for r in vystup.get("rozpoctova_opatreni") or []:
        polozky_ro.setdefault(r["usneseni_id"], []).append(r)
    for u in usneseni.values():
        if u["id"] not in polozky_ro and not RE_RO.search(u.get("tema") or ""):
            continue
        if u["id"] in pouzita or u.get("jednani_id") not in jednani:
            continue
        pouzita.add(u["id"])
        polozky = polozky_ro.get(u["id"], [])
        j = jednani[u["jednani_id"]]
        nazvy = " ".join(p["nazev"] for p in polozky)
        zpravy.append({
            "id": f"zprava-{u['id']}", "druh": "rozpoctove_opatreni", "datum": j["datum"],
            "okruh": _urci_okruh(cfg, nazvy or u.get("tema"), None, u.get("okruh")),
            "titulek": u.get("tema") or "Rozpočtové opatření", "shrnuti": _shrnuti_ro(u, polozky),
            "castka": _castka_ro(polozky), "projekt_id": karta_usneseni.get(u["id"]),
            "zdroje": [_zdroj_zapisu(u, jednani)], "jistota": "doloženo",
            "shrnuti_ai": False if polozky else bool(u.get("shrnuti_ai")),
        })

    # --- ostatní usnesení (kromě procedurálních a už použitých)
    for u in usneseni.values():
        if u["id"] in pouzita or u["jednani_id"] not in jednani:
            continue
        if PROCEDURALNI.search(u.get("tema") or ""):
            continue
        j = jednani[u["jednani_id"]]
        neprijato = u.get("vysledek_hlasovani") == "neprijato"
        zprava = {
            "id": f"zprava-{u['id']}", "druh": "usneseni", "datum": j["datum"], "okruh": u.get("okruh") or modul_okruhy.ZBYTEK,
            "titulek": u.get("tema") or u["cislo"], "shrnuti": u.get("shrnuti") or "", "castka": None,
            "projekt_id": karta_usneseni.get(u["id"]), "zdroje": [_zdroj_zapisu(u, jednani)],
            "jistota": "naše propojení" if karta_usneseni.get(u["id"]) else "doloženo",
            "shrnuti_ai": bool(u.get("shrnuti_ai")),
        }
        if neprijato:
            zprava["stitek"] = "Neschváleno"
        zpravy.append(zprava)

    # --- výběrová řízení (E-ZAK): vyhlášení, výběr dodavatele, zrušení, ukončení plnění
    ukonceni = {k["id"]: k.get("ukonceni_plneni") for k in karty.values()}
    for z in vystup.get("zakazky") or []:
        karta_id = karta_zakazky.get(z["id"])
        zas_id = zasobnik_zakazky.get(z["id"])
        okruh = _urci_okruh(cfg, z["nazev"], okruh_vazby(karta_id, zas_id), okruh_firmy(z.get("subjekt_ico")))
        jistota = "naše propojení" if (karta_id or zas_id) else "doloženo"
        zdroj = [{"nazev": f"Zadávací profil (E-ZAK): {z['nazev']}", "url": z["url"]}]

        def pridej(udalost: str, datum: str | None, titulek: str, shrnuti: str, castka: dict | None = None,
                  extra: dict | None = None, cast: str = "") -> None:
            if datum:
                zpravy.append((extra or {}) | {"id": f"zprava-{z['id']}{cast}-{udalost}-{datum}", "druh": "vyberove_rizeni", "datum": datum,
                               "okruh": okruh, "titulek": titulek, "shrnuti": shrnuti, "castka": castka,
                               "projekt_id": karta_id, "zdroje": zdroj, "jistota": jistota})

        # zadavatel podle IČO ze zdrojového záznamu (config/subjekty.yaml); bez názvu neutrálně (review #252)
        zadavatel = (subjekty or {}).get(str(z.get("subjekt_ico") or ""))
        pridej("vyhlaseni", z.get("datum_zahajeni"), f"Výběrové řízení vyhlášeno: {z['nazev']}",
               (f"Zadavatel {zadavatel} vyhlásil výběrové řízení" if zadavatel else "Bylo vyhlášeno výběrové řízení")
               + f" „{z['nazev']}“ (řízení: {z.get('rezim') or 'neuvedeno'}).")
        vice_casti = len(z.get("casti") or []) > 1
        for i, c in enumerate(z.get("casti") or [], 1):
            # u vícedílné zakázky rozlišit část, jinak by podpis nebo zrušení dvou částí v jeden den dalo stejné ID
            cast = f"-cast{i}" if vice_casti else ""
            vitez = [v for v in c.get("vitezove") or [] if v.get("smlouva_uzavrena")]
            if c.get("datum_uzavreni_smlouvy"):
                kdo = _dodavatel(vitez[:1])[0] if vitez else None
                castka = _vyber_castku(vitez[0].get("castky") or []) if len(vitez) == 1 else None
                pridej("vyber", c["datum_uzavreni_smlouvy"], f"Vybrán dodavatel: {c['nazev']}",
                       f"Ve výběrovém řízení „{c['nazev']}“ byla uzavřena smlouva" + (f" s dodavatelem {kdo.rstrip('.')}" if kdo else "") + ".",
                       castka, _jmeno_podnikatele(vitez[:1]), cast)
            pridej("zruseni", c.get("datum_zruseni"), f"Výběrové řízení zrušeno: {c['nazev']}",
                   f"Výběrové řízení „{c['nazev']}“ bylo zrušeno.", cast=cast)
        u_pl = ukonceni.get(karta_id) if karta_id else None
        if u_pl and u_pl.get("zakazka_id") == z["id"]:
            pridej("ukonceni", u_pl["datum"], f"Plnění ukončeno: {z['nazev']}",
                   f"Podle zadávacího profilu bylo plnění zakázky „{z['nazev']}“ ukončeno.")

    # --- skupiny: víc zpráv k jedné akci ve stejný den
    skupiny: dict[tuple[str, str], list[dict]] = {}
    for zp in zpravy:
        if zp.get("projekt_id"):
            skupiny.setdefault((zp["projekt_id"], zp["datum"]), []).append(zp)
    for (karta_id, datum), cleni in skupiny.items():
        if len(cleni) > 1:
            for zp in cleni:
                zp["skupina"] = {"id": f"{karta_id}:{datum}", "nazev": karty[karta_id]["nazev"], "pocet": len(cleni)}

    zpravy.sort(key=lambda z: (z["datum"], z["id"]), reverse=True)
    return zpravy


def _shrnuti_smlouvy(sm: dict, dodatek: bool) -> str:
    kdo, _ = _dodavatel(sm.get("strany") or [])
    co = "Dodatek ke smlouvě" if dodatek else "Smlouva"
    vety = [f"{co} z {_datum_cz(sm['datum_uzavreni'])}" + (f" s dodavatelem {kdo.rstrip('.')}" if kdo else "") + "."]
    if sm.get("cena_neuvedena"):
        vety.append("Cena není v registru uvedena.")
    return " ".join(vety)


def _castka_ro(polozky: list[dict]) -> dict | None:
    """Částka opatření se opisuje jen když je jednoznačná: jediná položka, nebo jediná položka navýšení/přesunu „do“."""
    cil = [p for p in polozky if p["smer"] in ("do", "navyseni")]
    vyber = cil if len(cil) == 1 else polozky if len(polozky) == 1 else []
    return _castka(vyber[0]["castka"], "rozpoctove_opatreni") if vyber else None


def _kc(hodnota: float) -> str:
    return f"{hodnota:,.0f}".replace(",", " ") + " Kč"


def _shrnuti_ro(u: dict, polozky: list[dict]) -> str:
    organ = MESICE_ORGAN[_organ(u)]
    if not polozky:
        return u.get("shrnuti") or f"{organ} schválila změnu rozpočtu."
    casti = []
    for p in polozky[:4]:
        slovo = {"z": "ubírá", "snizeni": "snižuje", "do": "přidává", "navyseni": "navyšuje"}.get(p["smer"], "mění")
        casti.append(f"{slovo} {_kc(abs(p['zmena']))} u položky „{p['nazev']}“")
    vice = f" a dalších {len(polozky) - 4} položek" if len(polozky) > 4 else ""
    return f"{organ} změnou rozpočtu " + "; ".join(casti) + vice + "."
