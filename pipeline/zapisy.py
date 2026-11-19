"""Deterministický rozklad textu zápisu (rada / zastupitelstvo) na body programu,
usnesení a hlasování. Bez AI: čísla a výsledky se jen opisují z textu.

Vstup:  raw/texty/<jednani_id>/strana-N.txt
Výstup: slovník se strukturou jednání (viz DATOVY_MODEL.md)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

RE_HLAVICKA = re.compile(r"^(Zápis z \d+\. jednání (ZM|RM)\b.*|Spisová značka:.*)$")
RE_CISLO_STRANY = re.compile(r"^\d{1,3}$")
RE_BOD = re.compile(r"^k bodu (\d+)$")
RE_USNESENI = re.compile(r"^Usnesení (ZM|RM) č\. (\d+)/(\d{4})-(\d+)$")
RE_HLASY = re.compile(r"^Pro:\s*(\d+)\s+Proti:\s*(\d+)\s+Zdrželi se:\s*(\d+)$")
RE_CAST = re.compile(r"^(I{1,3}|IV|V|VI{0,3})\.\s+(\S.*)$")
RE_PROGRAM_POLOZKA = re.compile(r"^(\d+)\.\s+(\S.*)$")
# Výsledek hlasování (zda návrh usnesení prošel). Neříká nic o věcném obsahu –
# „SCHVÁLENO“ u usnesení „bere na vědomí“ znamená jen, že usnesení bylo přijato.
VYSLEDKY = {
    "SCHVÁLENO": "prijato",
    "NESCHVÁLENO": "neprijato",
    "USNESENÍ PŘIJATO": "prijato",
    "USNESENÍ NEPŘIJATO": "neprijato",
    "NÁVRH NESCHVÁLEN – USNESENÍ NEPŘIJATO": "neprijato",
}
# Věcný úkon v části usnesení (I. bere na vědomí, II. ukládá …). Delší výrazy dřív.
UKONY = [
    ("bere na vědomí", "bere_na_vedomi"),
    ("neschvaluje", "neschvaluje"),
    ("schvaluje", "schvaluje"),
    ("nesouhlasí", "nesouhlasi"),
    ("souhlasí", "souhlasi"),
    ("volí", "voli"),
    ("odvolává", "odvolava"),
    ("jmenuje", "jmenuje"),
    ("určuje", "urcuje"),
    ("ukládá", "uklada"),
    ("pověřuje", "poveruje"),
    ("doporučuje", "doporucuje"),
    ("zřizuje", "zrizuje"),
    ("ruší", "rusi"),
    ("revokuje", "revokuje"),
    ("vydává", "vydava"),
    ("rozhoduje", "rozhoduje"),
]


def urci_ukon(text: str) -> tuple[str, str]:
    """Z řádku části usnesení (bez římské číslice) určí věcný úkon."""
    porovnat = text.strip().lower()
    for sloveso, kod in UKONY:
        if porovnat == sloveso or porovnat.startswith(sloveso + " "):
            return kod, sloveso
    return "jiny", text
HLAVICKY_ORGANU = {"Zastupitelstvo města Třeboně", "Rada města Třeboně"}


@dataclass
class Radek:
    text: str
    strana: int


def nacti_radky(adresar: Path) -> list[Radek]:
    """Načte strany v pořadí, odstraní záhlaví/zápatí a prázdné řádky."""
    soubory = sorted(adresar.glob("strana-*.txt"), key=lambda p: int(p.stem.split("-")[1]))
    radky: list[Radek] = []
    for soubor in soubory:
        strana = int(soubor.stem.split("-")[1])
        for r in soubor.read_text(encoding="utf-8").splitlines():
            r = r.strip()
            if not r or RE_HLAVICKA.match(r) or RE_CISLO_STRANY.match(r):
                continue
            radky.append(Radek(r, strana))
    return radky


def normalizuj(text: str) -> str:
    """Sjednotí mezery a zalomení řádků; používá se pro porovnání citací."""
    return re.sub(r"\s+", " ", text).strip()


def _program(radky: list[Radek]) -> dict[int, str]:
    """Najde číslovaný program (RM: 'Program:', ZM: 'Upravený program:').
    Víceřádkové položky spojí."""
    program: dict[int, str] = {}
    start = next((i for i, r in enumerate(radky) if r.text in ("Program:", "Upravený program:")), None)
    if start is None:
        return program
    posledni = None
    zbytek = radky[start + 1:]
    for i, r in enumerate(zbytek):
        m = RE_PROGRAM_POLOZKA.match(r.text)
        if m and (posledni is None or int(m.group(1)) == posledni + 1):
            posledni = int(m.group(1))
            program[posledni] = m.group(2)
        elif posledni is not None and r.text in VYSLEDKY and i + 1 < len(zbytek) and (
                (n := RE_PROGRAM_POLOZKA.match(zbytek[i + 1].text)) and int(n.group(1)) == posledni + 1):
            # značka výsledku přímo v programu (RM 111: „NÁVRH NESCHVÁLEN – USNESENÍ NEPŘIJATO“ pod bodem 3);
            # program pokračuje dalším bodem → značku přeskočit, nepřipojovat
            continue
        elif posledni is not None and not RE_BOD.match(r.text) and r.text not in VYSLEDKY and not r.text.startswith("Návrh na usnesení"):
            program[posledni] += " " + r.text
        else:
            break
    return program


def rozloz(jednani_id: str, adresar: Path) -> dict:
    radky = nacti_radky(adresar)
    program = _program(radky)

    # rozdělení na body
    body: list[dict] = []
    for r in radky:
        m = RE_BOD.match(r.text)
        if m:
            body.append({"cislo": int(m.group(1)), "strana": r.strana, "radky": []})
        elif body:
            body[-1]["radky"].append(r)

    vysledek = {"jednani_id": jednani_id, "body": [], "usneseni": [], "hlasovani": [], "upozorneni": []}

    for bod in body:
        prvni = bod["radky"][0].text if bod["radky"] else ""
        nazev = program.get(bod["cislo"])
        if nazev is None:
            nazev = prvni
            vysledek["upozorneni"].append(
                f"bod {bod['cislo']}: není v programu, název vzat z prvního řádku ('{prvni}')")
        zaznam = {"cislo": bod["cislo"], "nazev": nazev, "strana": bod["strana"], "text": None}
        vysledek["body"].append(zaznam)
        pred = len(vysledek["usneseni"])
        _zpracuj_bod(jednani_id, bod, vysledek)
        if len(vysledek["usneseni"]) == pred:
            # bod bez usnesení (Různé, Diskuze…): text se ukazuje v detailu
            zaznam["text"] = "\n".join(r.text for r in bod["radky"][1:] if r.text != nazev) or None
    return vysledek


def _zpracuj_bod(jednani_id: str, bod: dict, out: dict) -> None:
    radky: list[Radek] = bod["radky"]
    i = 0
    usn = None          # rozpracované usnesení
    cast = None         # aktuální část usnesení (I., II.)
    mimo_kontext = None # popis hlasování mimo usnesení (protinávrh / kandidát)
    protinavrh_text = None
    ceka_hlasy = False

    def uzavri():
        nonlocal usn
        if usn:
            usn["text"] = "\n".join(usn.pop("_radky"))
            out["usneseni"].append(usn)
            usn = None

    while i < len(radky):
        r = radky[i]
        t = r.text
        m_usn = RE_USNESENI.match(t)
        if m_usn:
            uzavri()
            organ, cislo, rok, jed = m_usn.groups()
            usn = {
                "id": f"{organ.lower()}-{rok}-j{int(jed)}-u{int(cislo)}",
                "cislo": f"{organ} {cislo}/{rok}-{jed}",
                "jednani_id": jednani_id,
                "bod": bod["cislo"],
                "strany": [r.strana],
                "vysledek_hlasovani": None,
                "vysledek_zapis": None,
                "ukony": [],
                "_radky": [],
            }
            cast = None
            mimo_kontext = None
        elif t.startswith("Protinávrh"):
            protinavrh_text = t
            j = i + 1
            while j < len(radky) and not radky[j].text.startswith(("Hlasování", "Výsledek")):
                protinavrh_text += " " + radky[j].text
                j += 1
            i = j
            continue
        elif t.startswith("Hlasování o protinávrhu") or t.startswith("Výsledek hlasování o protinávrhu"):
            mimo_kontext = {"typ": "protinavrh", "predmet": protinavrh_text or t}
            ceka_hlasy = True
        elif t.startswith("Výsledek hlasování"):
            ceka_hlasy = True
            if usn is None and mimo_kontext is None:
                mimo_kontext = {"typ": "kandidati"}
        elif RE_HLASY.match(t):
            pro, proti, zdrz = map(int, RE_HLASY.match(t).groups())
            zaznam = {"jednani_id": jednani_id, "bod": bod["cislo"], "strana": r.strana,
                      "pro": pro, "proti": proti, "zdrzel": zdrz, "jmenovite": None,
                      "zdroj_radek": t}
            if usn is not None:
                zaznam.update({"usneseni_id": usn["id"], "cast": cast, "typ": "usneseni"})
                if r.strana not in usn["strany"]:
                    usn["strany"].append(r.strana)
            elif mimo_kontext and mimo_kontext["typ"] == "protinavrh":
                zaznam.update({"usneseni_id": None, "typ": "protinavrh", "predmet": mimo_kontext["predmet"]})
            elif mimo_kontext and mimo_kontext["typ"] == "kandidati":
                kandidat = radky[i - 1].text
                zaznam.update({"usneseni_id": None, "typ": "volba_kandidata", "predmet": kandidat})
            else:
                out["upozorneni"].append(f"bod {bod['cislo']}: hlasování bez kontextu: {t}")
            out["hlasovani"].append(zaznam)
            ceka_hlasy = False
        elif t in VYSLEDKY:
            if usn is not None:
                usn["vysledek_hlasovani"] = VYSLEDKY[t]
                usn["vysledek_zapis"] = t
                if r.strana not in usn["strany"]:
                    usn["strany"].append(r.strana)
                uzavri()
            elif out["hlasovani"] and out["hlasovani"][-1]["typ"] == "protinavrh":
                out["hlasovani"][-1]["vysledek"] = VYSLEDKY[t]
                mimo_kontext = None
        elif usn is not None:
            if t in HLAVICKY_ORGANU:
                pass
            else:
                m_cast = RE_CAST.match(t)
                if m_cast:
                    cast = m_cast.group(1)
                    kod, sloveso = urci_ukon(m_cast.group(2))
                    usn["ukony"].append({"cast": cast, "ukon": kod, "sloveso": sloveso})
                    if kod == "jiny":
                        out["upozorneni"].append(f"{usn['cislo']} část {cast}: neznámý úkon {sloveso!r}")
                usn["_radky"].append(t)
                if r.strana not in usn["strany"]:
                    usn["strany"].append(r.strana)
        i += 1
    if usn is not None:
        out["upozorneni"].append(f"bod {bod['cislo']}: usnesení {usn['cislo']} bez výsledku (SCHVÁLENO apod.)")
        uzavri()

    # část (I., II.) má smysl jen u usnesení s více hlasováními; jinak hlasování platí pro celé usnesení
    for u in out["usneseni"]:
        if u["bod"] != bod["cislo"]:
            continue
        hl = [h for h in out["hlasovani"] if h.get("usneseni_id") == u["id"] and h["typ"] == "usneseni"]
        if len(hl) == 1:
            hl[0]["cast"] = None

    # usnesení bez vlastního hlasování (např. volba po kandidátech)
    for u in out["usneseni"]:
        if u["bod"] == bod["cislo"] and not any(h.get("usneseni_id") == u["id"] for h in out["hlasovani"]):
            kandidati = [h for h in out["hlasovani"] if h["bod"] == bod["cislo"] and h["typ"] == "volba_kandidata"]
            if kandidati:
                for h in kandidati:
                    h["usneseni_id"] = u["id"]
                out["upozorneni"].append(
                    f"{u['cislo']}: bez souhrnného hlasování; navázána hlasování o jednotlivých kandidátech ({len(kandidati)})")
            else:
                out["upozorneni"].append(f"{u['cislo']}: v zápisu chybí výsledek hlasování")
