"""Rozpočtová opatření (RO) z usnesení rady a zastupitelstva → položky rozpočtu.

Zdroj je text usnesení ze zápisu (už v `data/usneseni.json`), bez AI:
- věta „provedení rozpočtového opatření č. N“ dá číslo RO,
- řádky „-z položky 5171 „Název“, § 3322, ORJ 750, ORG …, UZ 0 v částce Kč 80.000,00“
  (a varianty „navýšení/snížení/ponížení příjmové/výdajové položky … o částku … Kč“) dají položky,
- tabulka pod nimi („Schválený rozpočet / Rozpočet po schválení RO / Rozpočtové opatření / Rozpočet po RO“)
  dá stav položky před a po opatření.

Klíč investiční akce: kapitálové akce (položka 6121 aj.) mají v rozpočtu vlastní ORG (např. 6230000000
„Přístavba tělocvičen“), opravy a vybavení často sdílené obecné ORG (9750000000) – u nich je klíčem
název položky. Čísla se opisují ze zdroje; kód je jen převádí a kontroluje (před ± změna = po).
"""
from __future__ import annotations

import re

from pipeline.zapisy import normalizuj

N_TEXT = r"\d{1,3}(?:[. ]\d{3})*(?:,\d{2})?"          # 80.000,00 / 20 000 / 1.165.000,00
N_TAB = r"\d{1,3}(?: \d{3})*(?:,\d{2})?"              # 2 600 000 / 59 245 143,49

RE_RO = re.compile(r"rozpočtového opatření č\.\s*(\d+)")
RE_POLOZKA = re.compile(
    r"-\s*(?P<smer>z|do|navýšení|snížení|ponížení)\s+(?:(?P<strana>příjmové|výdajové)\s+)?položky\s+"
    r"(?P<pol>\d{4}),?\s+(?:„(?P<nazev>[^“]+)“|(?P<nazev2>[^„“§]+?)),\s*§\s*(?P<par>\d{4}),\s*"
    r"ORJ\s+(?P<orj>\d+),\s*ORG\s+(?P<org>[0-9x]+),\s*\w*UZ\s*(?P<uz>\d*)\s+"
    rf"(?:v\s+částce\s+Kč\s+(?P<c1>{N_TEXT})|o\s+částku\s+(?P<c2>{N_TEXT})\s+Kč)")
RE_ODDIL = re.compile(r"^Rozpočtové (?P<strana>výdaje|příjmy)(?P<fond>[^(]*)\(Kč\):\s*$")
RE_RADEK = re.compile(
    rf"^(?:\d+\.\s+)?(?P<uz>\d+)\s+(?P<org>[0-9x]+)\s+(?P<orj>\d{{3,4}})\s+(?P<par>\d{{4}})\s+(?P<pol>\d{{4}})\s+"
    rf"(?P<sch>{N_TAB})\s+(?P<pred>{N_TAB})\s+(?P<zn>[+-])\s*(?P<zmena>{N_TAB})\s+(?P<po>{N_TAB})$")

SMER = {"z": "z", "do": "do", "navýšení": "navyseni", "snížení": "snizeni", "ponížení": "snizeni"}
ORGAN = {"rm": "rada", "zm": "zastupitelstvo"}


def na_halere(s: str) -> int:
    """Český zápis částky → haléře (celé číslo, bez zaokrouhlovacích chyb)."""
    s = s.replace(" ", "")
    if s.startswith(("-", "−")):                  # „-522,85“ = −52 285 haléřů (ne −52 200 + 85)
        return -na_halere(s[1:])
    if "," in s:
        cela, des = s.split(",")
    else:
        cela, des = s, "00"
    return int(cela.replace(".", "")) * 100 + int(des.ljust(2, "0")[:2])


def _kc(halere: int) -> float:
    return halere / 100


def radky_tabulky(text: str) -> list[dict]:
    """Řádky tabulky RO (stav položky před a po) s oddílem, ve kterém stojí."""
    radky, oddil = [], None
    for radek in text.splitlines():
        r = radek.strip()
        m = RE_ODDIL.match(r)
        if m:
            oddil = {"strana": "vydaje" if m["strana"] == "výdaje" else "prijmy",
                     "fond": re.sub(r"^fondu\s+", "", m["fond"].strip()) or None, "text": r}
            continue
        m = RE_RADEK.match(r)
        if m and oddil:
            zmena = na_halere(m["zmena"]) * (1 if m["zn"] == "+" else -1)
            radky.append({"oddil": oddil, "pol": m["pol"], "par": m["par"], "org": m["org"],
                          "orj": m["orj"].lstrip("0"), "schvaleny": na_halere(m["sch"]),
                          "pred": na_halere(m["pred"]), "zmena": zmena, "po": na_halere(m["po"]),
                          "text": r, "pouzit": False})
    return radky


def polozky_ro(u: dict) -> tuple[list[dict], list[str]]:
    """Položky RO z jednoho usnesení. Vrací (záznamy, chyby)."""
    text = u.get("text") or ""
    m_ro = RE_RO.search(text)
    if not m_ro:
        return [], []
    chyby: list[str] = []
    souvisly = " ".join(text.split())
    cast = souvisly[m_ro.start():]
    vydajova_cast = re.search(r"ve výdajové části", cast[:300]) is not None
    tabulka = radky_tabulky(text)
    organ_kod = u["id"].split("-")[0]
    rok = int(re.search(r"/(\d{4})-", u["cislo"])[1])
    zaznamy = []
    for i, m in enumerate(RE_POLOZKA.finditer(cast), start=1):
        smer = SMER[m["smer"]]
        castka_text = m["c1"] or m["c2"]
        hodnota = na_halere(castka_text)
        if smer in ("z", "snizeni"):
            zmena = -hodnota
        else:
            zmena = hodnota
        strana = {"příjmové": "prijmy", "výdajové": "vydaje"}.get(m["strana"] or "")
        if strana is None and smer in ("z", "do") and vydajova_cast:
            strana = "vydaje"
        citace_text = m.group(0)
        poznamky = []
        # řádek tabulky: stejná položka, paragraf a změna (ORG se ve zdroji občas liší, viz poznámka)
        radek = next((r for r in tabulka if not r["pouzit"] and r["pol"] == m["pol"] and r["par"] == m["par"]
                      and r["zmena"] == zmena), None)
        rozpocet = None
        if radek:
            radek["pouzit"] = True
            if radek["pred"] + radek["zmena"] != radek["po"]:
                chyby.append(f"{u['id']}: RO č. {m_ro[1]}, položka {m['pol']} § {m['par']}: "
                             f"před {radek['pred']} + změna {radek['zmena']} ≠ po {radek['po']} (haléře)")
            if radek["org"] != m["org"]:
                poznamky.append(f"ORG v tabulce {radek['org']} se liší od textu usnesení {m['org']}")
            if strana is None:
                strana = radek["oddil"]["strana"]
            rozpocet = {"schvaleny": _kc(radek["schvaleny"]), "pred_ro": _kc(radek["pred"]),
                        "po_ro": _kc(radek["po"]), "fond": radek["oddil"]["fond"],
                        "citace": radek["text"]}
        else:
            poznamky.append("řádek tabulky k položce nenalezen")
        zaznamy.append({
            "id": f"{u['id']}-p{i}",
            "rok": rok,
            "cislo_ro": int(m_ro[1]),
            "usneseni_id": u["id"],
            "usneseni_cislo": u["cislo"],
            "jednani_id": u["jednani_id"],
            "organ": ORGAN.get(organ_kod, organ_kod),
            "vysledek_hlasovani": u.get("vysledek_hlasovani"),
            "strana": strana,
            "smer": smer,
            "polozka": m["pol"],
            "nazev": (m["nazev"] or m["nazev2"]).strip(),
            "paragraf": m["par"],
            "orj": m["orj"].lstrip("0"),
            "org": m["org"],
            "uz": m["uz"] or None,
            "zmena": _kc(zmena),
            "castka": {"hodnota": _kc(hodnota), "mena": "CZK", "jednotka": "Kč", "s_dph": None,
                       "druh": "rozpoctove_opatreni", "citace": citace_text},
            "rozpocet": rozpocet,
            "citace": {"dokument_id": (u.get("citace") or {}).get("dokument_id"),
                       "strany": (u.get("citace") or {}).get("strany", []), "text": citace_text},
            "poznamka": "; ".join(poznamky) or None,
        })
    if not zaznamy:
        chyby.append(f"{u['id']}: RO č. {m_ro[1]} bez rozpoznaných položek")
    return zaznamy, chyby


def z_usneseni(usneseni: list[dict]) -> tuple[list[dict], list[str]]:
    vysledek, chyby = [], []
    for u in usneseni:
        z, c = polozky_ro(u)
        vysledek += z
        chyby += c
    return vysledek, chyby


def zkontroluj(zaznamy: list[dict], usneseni: list[dict]) -> list[str]:
    """Citace doslova v textu usnesení; RO převodem (z/do) se v rámci jednoho RO vyrovnává."""
    texty = {u["id"]: normalizuj(u["text"]) for u in usneseni}
    chyby = []
    for z in zaznamy:
        zdroj = texty.get(z["usneseni_id"], "")
        if normalizuj(z["citace"]["text"]) not in zdroj:
            chyby.append(f"{z['id']}: citace není doslova v usnesení")
        if z["rozpocet"] and normalizuj(z["rozpocet"]["citace"]) not in zdroj:
            chyby.append(f"{z['id']}: citace řádku tabulky není doslova v usnesení")
    prevody: dict[tuple, int] = {}
    for z in zaznamy:
        if z["smer"] in ("z", "do"):
            klic = (z["usneseni_id"], z["cislo_ro"])
            prevody[klic] = prevody.get(klic, 0) + round(z["zmena"] * 100)
    for (uid, cislo), soucet in prevody.items():
        if soucet != 0:
            chyby.append(f"{uid}: RO č. {cislo} – přesun z/do nesedí o {soucet / 100:.2f} Kč")
    return chyby
