"""Přehled rozpočtových opatření za rok z PDF finančního odboru → `data/rozpocet_zmeny.json` (#138).

Zdroj: `raw/rozpocet/<rok>/rozpoctova_opatreni/strana-N.txt` („Rozpočtová opatření schválená orgány města
Třeboně v roce RRRR“, pdftotext -layout). Bez AI, čísla se opisují (v tis. Kč) a kód je jen převádí na Kč.

Řádek tabulky: ORJ, oddíl, druh (BV běžné výdaje, KV kapitálové výdaje, BP běžné příjmy, T transfery,
DP daňové příjmy, F financování…), účel a čtyři sloupce v tis. Kč: schválený rozpočet, upravený rozpočet
(před opatřením), rozpočtové opatření, rozpočet po opatření.

Číslo RO, usnesení a orgán jsou ve zdroji svisle uprostřed skupiny řádků (pdftotext je dá na samostatný
řádek mezi řádky, u lichého počtu na prostřední řádek). Řádky se k opatření přiřazují podle této souměrnosti:
nad popiskem je stejně řádků jako pod ním. Kontroly (chyba = data se nemění):
- upravený + opatření = po opatření u každého řádku,
- souměrnost vychází beze zbytku (žádný řádek bez opatření),
- s `rozpoctova_opatreni` z usnesení (#86): u každého RO, které je i v zápisu, sedí změny řádek po řádku.
Řetěz položky (po opatření = upravený v dalším opatření) se jen hlásí v `upozorneni` (název položky se
mezi opatřeními občas mírně liší).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pipeline.rozpocet import na_halere

N = r"-?\d{1,3}(?: \d{3})*,\d{2}"
RE_RADEK = re.compile(rf"(?P<orj>\d{{3}})\s+(?P<od>\d{{1,2}})\s+(?P<druh>[A-Z]{{1,2}})\s+(?P<ucel>\S.*?)\s+"
                      rf"(?P<s>{N})\s+(?P<u>{N})\s+(?P<z>{N})\s+(?P<po>{N})\s*$")
RE_RO = re.compile(r"^\s*(?P<ro>\d+)\.\s")
RE_USNESENI_SAM = re.compile(r"^\s*\d+/\d{4}-\d+\s+(?:RM|ZM)\s*$")       # popisek bez čísla RO
RE_USNESENI = re.compile(r"(\d+)/(\d{4})-\s*(\d+)")
DRUH = {"BV": "bezne_vydaje", "KV": "kapitalove_vydaje", "BP": "bezne_prijmy", "KP": "kapitalove_prijmy",
        "T": "transfery", "DP": "danove_prijmy", "F": "financovani"}


def _kc(tis: str) -> int:
    """„26 000,00“ (tis. Kč) → 26 000 000 Kč, celé číslo bez zaokrouhlení (zdroj má 2 desetinná místa)."""
    return na_halere(tis) * 10


def normalizuj_nazev(nazev: str) -> str:
    return re.sub(r"\s+", " ", nazev.replace("–", "-").replace("*", "")).strip().lower()


def klic_polozky(orj: str, oddil: int, druh: str, ucel: str) -> tuple:
    """Klíč položky pro řetěz změn: ORJ, oddíl, druh a název bez rozdílů v pomlčkách, mezerách a hvězdičce."""
    return (orj, int(oddil), druh, normalizuj_nazev(ucel))


def _prvky(strany: list[str]) -> list[dict]:
    prvky = []
    for cislo_strany, text in enumerate(strany, start=1):
        for radek in text.splitlines():
            m = RE_RADEK.search(radek)
            mro = RE_RO.match(radek)
            if m:
                predpona = radek[:m.start()]
                prvky.append({"typ": "radek", "strana": cislo_strany, "m": m, "text": radek,
                              "predpona": predpona,
                              "popisek": bool(mro) or bool(RE_USNESENI_SAM.match(predpona)),
                              "ro": int(mro["ro"]) if mro else None})
            elif mro:
                prvky.append({"typ": "popisek", "strana": cislo_strany, "text": radek, "ro": int(mro["ro"])})
            elif radek.strip():
                prvky.append({"typ": "text", "strana": cislo_strany, "text": radek})
    return prvky


def zmeny(strany: list[str], rok: int, dokument: str) -> tuple[list[dict], list[str], list[str]]:
    """Vrací (řádky opatření, chyby, upozornění)."""
    chyby: list[str] = []
    prvky = _prvky(strany)
    bloky: list[dict] = []
    cekajici: list[int] = []          # indexy řádků bez opatření
    dluh = 0                          # kolik dalších řádků patří pod popisek předchozího opatření
    for i, p in enumerate(prvky):
        if p["typ"] == "radek" and not p["popisek"]:
            cekajici.append(i)
            continue
        if p["typ"] == "text":
            continue
        if len(cekajici) < dluh:
            chyby.append(f"přehled RO {rok}: před popiskem „{p['text'].strip()[:40]}“ chybí řádky předchozího opatření")
            return [], chyby, []
        if bloky:
            bloky[-1]["radky"] += cekajici[:dluh]
            bloky[-1]["konec"] = cekajici[dluh - 1] if dluh else bloky[-1]["konec"]
        nad = cekajici[dluh:]
        blok = {"ro": p["ro"], "popisek": i, "radky": nad + ([i] if p["typ"] == "radek" else []),
                "zacatek": nad[0] if nad else i, "konec": i}
        bloky.append(blok)
        dluh, cekajici = len(nad), []
    if not bloky:
        return [], [f"přehled RO {rok}: žádné opatření"], []
    if len(cekajici) != dluh:
        chyby.append(f"přehled RO {rok}: na konci zbývá {len(cekajici)} řádků, poslednímu opatření patří {dluh}")
        return [], chyby, []
    bloky[-1]["radky"] += cekajici
    if cekajici:
        bloky[-1]["konec"] = cekajici[-1]

    vysledek = []
    for b in bloky:
        if not b["radky"]:
            chyby.append(f"přehled RO {rok}: opatření {b['ro']} bez řádků")
            continue
        od, do = min(b["radky"] + [b["popisek"]]), max(b["radky"] + [b["popisek"]])
        # číslo usnesení a orgán z levé části řádků a z popisku (u RM/ZM je číslo rozdělené na více řádků)
        levy = " ".join((prvky[k].get("predpona") if prvky[k]["typ"] == "radek" else prvky[k]["text"]) or ""
                        for k in range(od, do + 1))
        usneseni = [f"{a}/{r}-{j}" for a, r, j in RE_USNESENI.findall(levy)]
        organ = "RM/ZM" if "RM/ZM" in levy else "ZM" if re.search(r"\bZM\b", levy) else "RM" if "RM" in levy else None
        nazev_ro = None if b["ro"] is not None else " ".join(
            prvky[k]["text"].strip() for k in range(od, do + 1) if prvky[k]["typ"] == "text")
        for poradi, k in enumerate(sorted(b["radky"]), start=1):
            m = prvky[k]["m"]
            s, u, z, po = (_kc(m[x]) for x in ("s", "u", "z", "po"))
            if u + z != po:
                chyby.append(f"přehled RO {rok}: RO {b['ro']} „{m['ucel']}“: {u} + {z} ≠ {po} Kč")
            ucel = m["ucel"].strip()
            vysledek.append({
                "id": f"ro-{rok}-{b['ro'] if b['ro'] is not None else 'x' + str(len(vysledek))}-{poradi:02d}",
                "rok": rok, "cislo_ro": b["ro"], "nazev_ro": nazev_ro or None,
                "usneseni": usneseni, "organ": organ,
                "orj": m["orj"], "oddil": int(m["od"]), "druh": DRUH.get(m["druh"], m["druh"]), "druh_zkratka": m["druh"],
                "ucel": ucel.rstrip("*").strip(), "fond": ucel.endswith("*"),
                "schvaleny": s, "upraveny_pred": u, "zmena": z, "po_zmene": po,
                "castka": {"hodnota": float(z), "mena": "CZK", "jednotka": "Kč", "s_dph": None,
                           "druh": "rozpoctove_opatreni", "citace": m["z"],
                           "poznamka": f"{dokument}, strana {prvky[k]['strana']}; zdroj v tis. Kč"},
                "citace": {"dokument": dokument, "strana": prvky[k]["strana"],
                           "text": " ".join(m.group(0).split())},
            })
    upozorneni = retez(vysledek)
    return vysledek, chyby, upozorneni


def retez(radky: list[dict]) -> list[str]:
    """Po opatření = upravený rozpočet v dalším opatření téže položky."""
    posledni: dict[tuple, dict] = {}
    upozorneni = []
    for r in radky:
        k = _klic(r)
        if k in posledni and posledni[k]["po_zmene"] != r["upraveny_pred"]:
            upozorneni.append(f"RO {r['cislo_ro']} „{r['ucel']}“: upravený {r['upraveny_pred']} Kč ≠ po RO "
                              f"{posledni[k]['cislo_ro']} {posledni[k]['po_zmene']} Kč")
        posledni[k] = r
    return upozorneni


def porovnej_s_usnesenimi(radky: list[dict], ro_usneseni: list[dict]) -> list[str]:
    """RO z textu usnesení (#86) i z přehledu: změny výdajových položek musí sedět (Kč, multimnožina)."""
    chyby = []
    prijate = [r for r in ro_usneseni if r.get("vysledek_hlasovani") == "prijato" and r.get("strana") == "vydaje"]
    for rok, cislo in sorted({(r["rok"], r["cislo_ro"]) for r in prijate}):
        if not any(r["rok"] == rok and r["cislo_ro"] == cislo for r in radky):
            continue                       # přehled ještě není aktualizovaný
        z_usn = sorted(round(r["zmena"] * 100) for r in prijate if r["rok"] == rok and r["cislo_ro"] == cislo)
        z_prehledu = sorted(r["zmena"] * 100 for r in radky if r["rok"] == rok and r["cislo_ro"] == cislo
                            and r["druh_zkratka"] in ("BV", "KV"))
        # přehled je v tis. Kč a některé řádky zaokrouhluje na celé tisíce (RO 58: 16 293 600 → 16 294,00)
        if len(z_usn) != len(z_prehledu) or any(abs(a - b) > 100_000 for a, b in zip(z_usn, z_prehledu)):
            chyby.append(f"přehled RO {rok}: opatření {cislo} nesedí s usnesením (usnesení {z_usn}, přehled {z_prehledu})")
    return chyby


def nacti(koren: Path) -> tuple[list[dict], list[str], list[str]]:
    manifest_cesta = koren / "raw" / "rozpocet" / "manifest.json"
    if not manifest_cesta.exists():
        return [], [], []
    manifest = json.loads(manifest_cesta.read_text(encoding="utf-8"))
    vse, chyby, upozorneni = [], [], []
    for klic, zaznam in sorted(manifest.items()):
        rok, druh = klic.split("/")
        if druh != "rozpoctova_opatreni":
            continue
        adresar = koren / "raw" / "rozpocet" / rok / druh
        soubory = sorted(adresar.glob("strana-*.txt"), key=lambda p: int(p.stem.split("-")[1]))
        r, ch, up = zmeny([p.read_text(encoding="utf-8") for p in soubory], int(rok), zaznam.get("url", ""))
        vse += r
        chyby += ch
        upozorneni += up
    return vse, chyby, upozorneni


def zkontroluj(radky: list[dict], koren: Path) -> list[str]:
    """Citovaný řádek je doslova (po sjednocení mezer) na uvedené straně a obsahuje citovanou změnu."""
    chyby, cache = [], {}
    for r in radky:
        cesta = koren / "raw" / "rozpocet" / str(r["rok"]) / "rozpoctova_opatreni" / f"strana-{r['citace']['strana']}.txt"
        if cesta not in cache:
            cache[cesta] = " ".join(cesta.read_text(encoding="utf-8").split()) if cesta.exists() else ""
        if r["citace"]["text"] not in cache[cesta]:
            chyby.append(f"{r['id']}: citace není doslova ve zdroji")
        if r["castka"]["citace"] not in r["citace"]["text"]:
            chyby.append(f"{r['id']}: citace změny není v citovaném řádku")
    return chyby


def sjednot_nazvy(radky: list[dict], rozpocet: list[dict]) -> list[str]:
    """Přehled občas zkrátí název položky (RO 43: „Snížení energetické náročnosti“ = „… DPS 3“). Řádek, jehož
    název ve schváleném rozpočtu není, ale má nenulový schválený rozpočet, se přiřadí položce téhož ORJ, oddílu
    a třídy se stejným schváleným rozpočtem, jejíž název začíná stejně (`nazev_polozky`). Vrací upozornění."""
    index: dict[tuple, list[dict]] = {}
    for p in rozpocet:
        index.setdefault((p["rok"], p["orj"], p["oddil"], "KV" if p["trida"] == "kapitalove" else "BV"), []).append(p)
    upozorneni = []
    for r in radky:
        r["nazev_polozky"] = r["ucel"]
        if r["druh_zkratka"] not in ("BV", "KV") or not r["schvaleny"]:
            continue
        kandidati = index.get((r["rok"], r["orj"], r["oddil"], r["druh_zkratka"]), [])
        n = normalizuj_nazev(r["ucel"])
        if any(normalizuj_nazev(p["nazev"]) == n for p in kandidati):
            continue
        stejna_castka = [p for p in kandidati if round(p["castka"]["hodnota"]) == r["schvaleny"]]
        shoda = [p for p in stejna_castka
                 if normalizuj_nazev(p["nazev"]).startswith(n) or n.startswith(normalizuj_nazev(p["nazev"]))]
        # jinak pojmenovaná položka (RO 20 „Divadlo J.K. Tyla - opravy“ = „Opravy v Divadle J.K. Tyla“):
        # jediná položka téhož ORJ, oddílu a třídy se stejným schváleným rozpočtem
        shoda = shoda or (stejna_castka if len(stejna_castka) == 1 else [])
        if len(shoda) == 1:
            r["nazev_polozky"] = shoda[0]["nazev"]
            r["prirazeni"] = "nazev" if normalizuj_nazev(shoda[0]["nazev"]).startswith(n) \
                or n.startswith(normalizuj_nazev(shoda[0]["nazev"])) else "castka"
        else:
            r["neprirazeno"] = True
            upozorneni.append(f"RO {r['cislo_ro']} „{r['ucel']}“: položku schváleného rozpočtu nelze určit")
    return upozorneni


def _klic(r: dict) -> tuple:
    return (r["rok"],) + klic_polozky(r["orj"], r["oddil"], r["druh_zkratka"], r.get("nazev_polozky") or r["ucel"])


def doplnit_rozpocet(rozpocet: list[dict], radky: list[dict]) -> None:
    """K položkám schváleného rozpočtu (`data/rozpocet.json`) doplní stav po posledním opatření z přehledu:
    `po_zmenach` (Kč) a `zmeny_ro[]` (čísla RO). Párování: rok, ORJ, oddíl, třída (BV/KV) a název."""
    posledni: dict[tuple, dict] = {}
    seznam: dict[tuple, list] = {}
    for r in radky:
        if r["druh_zkratka"] not in ("BV", "KV"):
            continue
        k = _klic(r)
        posledni[k] = r
        seznam.setdefault(k, []).append(r["cislo_ro"])
    # nepřiřazené řádky přehledu: položku se stejným schváleným rozpočtem nelze označit „beze změny“
    nejasne = {(r["rok"], r["orj"], r["oddil"], r["druh_zkratka"], r["schvaleny"]) for r in radky if r.get("neprirazeno")}
    for p in rozpocet:
        druh = "KV" if p["trida"] == "kapitalove" else "BV"
        k = (p["rok"],) + klic_polozky(p["orj"], p["oddil"], druh, p["nazev"])
        p["stav_zmen"] = ("zmeneno" if k in posledni else
                          "nejasne" if (p["rok"], p["orj"], p["oddil"], druh, round(p["castka"]["hodnota"])) in nejasne
                          else "beze_zmeny")
        if k in posledni:
            p["po_zmenach"] = {"hodnota": float(posledni[k]["po_zmene"]), "mena": "CZK", "jednotka": "Kč",
                               "s_dph": None, "druh": "rozpocet_upraveny", "po_ro": posledni[k]["cislo_ro"],
                               "zdroj_id": posledni[k]["id"]}
            p["zmeny_ro"] = seznam[k]
        else:
            p["po_zmenach"] = None
            p["zmeny_ro"] = []


def posledni_stav(radky: list[dict]) -> dict[tuple, dict]:
    """Poslední řádek přehledu pro každou výdajovou položku: klíč (rok, ORJ, oddíl, BV/KV, název)."""
    vysledek: dict[tuple, dict] = {}
    for r in radky:
        if r["druh_zkratka"] in ("BV", "KV"):
            vysledek[_klic(r)] = r
    return vysledek


ODDILY = {21: "Služby a cestovní ruch", 22: "Doprava, ulice a chodníky", 23: "Voda a kanalizace", 31: "Školy a školky",
          32: "Školy a školky", 33: "Kultura a památky", 34: "Sport a hřiště", 35: "Zdravotnictví",
          36: "Bydlení, osvětlení a budovy", 37: "Životní prostředí a zeleň", 43: "Sociální služby",
          53: "Bezpečnost", 55: "Hasiči", 61: "Městský úřad", 63: "Finance", 64: "Rezerva"}


def prehled_investic(rozpocet: list[dict], radky: list[dict], projekty: list[dict], rok: int) -> dict:
    """Investice (kapitálové výdaje) roku: položky schváleného rozpočtu + položky přidané opatřeními během roku,
    se stavem po změnách, po oblastech (oddíl rozpočtu). Součty počítá kód v haléřích; schválený a upravený
    rozpočet se sčítají každý zvlášť (různé druhy částek)."""
    naprojekt = {}
    for p in projekty:
        for s in p.get("schvaleny_rozpocet", []):
            naprojekt[(s["rok"], normalizuj_nazev(s["nazev"]), s["trida"])] = p["id"]
    polozky = []
    v_rozpoctu = set()
    for r in rozpocet:
        if r["rok"] != rok or r["trida"] != "kapitalove":
            continue
        v_rozpoctu.add((rok,) + klic_polozky(r["orj"], r["oddil"], "KV", r["nazev"]))
        po = r["po_zmenach"]["hodnota"] if r.get("po_zmenach") else r["castka"]["hodnota"]
        polozky.append({"nazev": r["nazev"], "orj": r["orj"], "oddil": r["oddil"], "schvaleny": r["castka"]["hodnota"],
                        "stav_zmen": r.get("stav_zmen", "beze_zmeny"),
                        "po_zmenach": po, "zmeny_ro": r.get("zmeny_ro", []), "nova": False, "zdroj_id": r["id"]})
    prvni: dict[tuple, dict] = {}
    for x in radky:
        prvni.setdefault(_klic(x), x)
    for k, r in posledni_stav(radky).items():
        # nová položka = při prvním výskytu nemá schválený ani upravený rozpočet (jinak jde o přejmenovanou)
        if k[0] == rok and k[3] == "KV" and k not in v_rozpoctu and not prvni[k]["schvaleny"]:
            polozky.append({"nazev": r["ucel"], "orj": r["orj"], "oddil": r["oddil"], "schvaleny": 0.0,
                            "stav_zmen": "zmeneno",
                            "po_zmenach": float(r["po_zmene"]),
                            "zmeny_ro": [x["cislo_ro"] for x in radky if _klic(x) == k],
                            "nova": True, "zdroj_id": r["id"]})
    for p in polozky:
        p["oblast"] = ODDILY.get(p["oddil"], f"Oddíl {p['oddil']}")
        p["projekt_id"] = naprojekt.get((rok, normalizuj_nazev(p["nazev"]), "kapitalove"))
    oblasti = []
    for oblast in dict.fromkeys(ODDILY.get(p["oddil"], f"Oddíl {p['oddil']}")
                                for p in sorted(polozky, key=lambda x: x["oddil"])):
        pp = [p for p in polozky if p["oblast"] == oblast]
        oblasti.append({"oblast": oblast,
                        "schvaleny": sum(round(p["schvaleny"] * 100) for p in pp) / 100,
                        "po_zmenach": sum(round(p["po_zmenach"] * 100) for p in pp) / 100,
                        "polozky": sorted(pp, key=lambda x: -x["po_zmenach"])})
    def soucet(pole, jen=None):
        return sum(round(p[pole] * 100) for p in polozky if jen is None or jen(p)) / 100
    return {"rok": rok, "druh": "rozpocet / rozpocet_upraveny", "s_dph": None,
            "schvaleny": soucet("schvaleny"), "po_zmenach": soucet("po_zmenach"),
            "bez_rezervy_po_zmenach": soucet("po_zmenach", lambda p: p["oddil"] != 64),
            "nejasne_polozky": [p["nazev"] for p in polozky if p["stav_zmen"] == "nejasne"],
            "oblasti": oblasti, "fondy_poznamka": "Investice z fondů (lázeňský investiční fond, fond obnovy "
            "vodohospodářského majetku) rozpočet uvádí jen souhrnně, nejsou zahrnuty."}
