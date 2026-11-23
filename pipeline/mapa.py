"""Mapa investic (#180): místa karet, zásobníku a námětů SPRM → `data/mapa.json`.

Budovy bodově, ulice liniově (celá definiční čára ulice z RÚIAN). Místo se bere:
1. z ručního pole `misto` v `data/projekty/<id>.yaml` nebo v položce `data/zasobnik.yaml` (doloženo ručně):
   `- ulice: Valy` · `- adresa: Na Sadech 375` · `- cp: 1` + `cast_obce: Třeboň I` · `- bod: [49.0035, 14.7706]`
   nebo `usek: [[šířka, délka], ...]` se `zdroj_url` pro doložený rozsah (+ volitelně `popis`),
2. jinak z názvu akce (naše propojení): „ul. Budějovické“, „v Jateční ulici“ → ulice; „Chelčického 1“ → adresa;
   „č.p. 1/I“ → budova v části Třeboň I,
3. náměty SPRM mají bod z evidence na trebonaci.cz.
Bez stažených dat RÚIAN (`raw/ruian/`) se ulice a adresy nevyřeší (jen upozornění); ruční `bod` a body SPRM ano.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

RIMSKE = {"I": "Třeboň I", "II": "Třeboň II"}
SAMOHLASKY = "aeiouyáéíóúůý"
RE_UL_PRED = re.compile(r"\b(?:ul\.|ulice|ulici|ulic|MK v ul\.)\s+([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][\wáčďéěíňóřšťúůýž.]*(?:\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][\wáčďéěíňóřšťúůýž]*)?)")
RE_UL_ZA = re.compile(r"\b([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][\wáčďéěíňóřšťúůýž]+)\s+(?:ulici|ulice|ul\.)")
RE_CP = re.compile(r"\bč\.\s?p\.\s*(\d+)\s*/\s*(I{1,2})\b|\bčp\.\s*(\d+)\s*/\s*(I{1,2})\b")
RE_BUDOVA = re.compile(r"\b(?:bytov\w* d[oů]m\w*|d[oů]m\w* s pečovatelskou|budov\w*|objekt\w*|novostavb\w*)\b", re.I)
RE_ADRESA = re.compile(r"\b([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)?)\s+(\d{1,4})\b")


SPRM_URL = "https://trebonaci.cz/wp-json/trebonaci/v1/projekty"


def _datum_sprm(koren: Path) -> str | None:
    """Datum stažení evidence SPRM z raw/sprm/manifest.json."""
    cesta = koren / "raw" / "sprm" / "manifest.json"
    if not cesta.exists():
        return None
    return json.loads(cesta.read_text(encoding="utf-8")).get("stazeno")


class Ruian:
    def __init__(self, koren: Path):
        adr = koren / "raw" / "ruian"
        nacti = lambda n: json.loads((adr / f"{n}.json").read_text(encoding="utf-8")) if (adr / f"{n}.json").exists() else []
        self.ulice = {u["nazev"]: u for u in nacti("ulice") if u.get("nazev") and u.get("linie")}
        self.budovy = nacti("budovy")
        self.adresy = nacti("adresy")
        self.k_dispozici = bool(self.ulice)

    def ulice_podle_tvaru(self, slovo: str) -> str | None:
        """Ulice podle tvaru v textu: přesně, nebo stejný kmen (Budějovické → Budějovická, Lázeňské → Lázeňská)."""
        slovo = slovo.rstrip(".")
        if slovo in self.ulice:
            return slovo
        for nazev in self.ulice:
            if " " in nazev:
                continue
            kmen = nazev.rstrip(SAMOHLASKY)
            if len(kmen) >= 4 and slovo.startswith(kmen) and len(slovo) - len(kmen) <= 3 and slovo[len(kmen):].strip(SAMOHLASKY + "mh") == "":
                return nazev
        return None

    def adresa(self, ulice: str, cislo: str, pismeno: str | None = None) -> dict | None:
        for a in self.adresy:
            # RÚIAN píše „Na sadech“, lidé „Na Sadech“: název ulice se porovnává bez ohledu na velikost písmen;
            # písmeno čísla orientačního („1a“) musí sedět (#179)
            if ((a.get("ulice") or "").casefold() == (ulice or "").casefold()
                    and cislo in (a.get("cislo_domovni"), a.get("cislo_orientacni"))
                    and (a.get("pismeno") or "").casefold() == (pismeno or "").casefold()):
                return a
        return None

    def stred_casti(self, cast_obce: str) -> list[float] | None:
        """Přibližný střed části obce: medián definičních bodů jejích budov (RÚIAN)."""
        body = [b["bod"] for b in self.budovy if b.get("cast_obce") == cast_obce and b.get("bod")]
        if not body:
            return None
        med = lambda xs: sorted(xs)[len(xs) // 2]
        return [med([b[0] for b in body]), med([b[1] for b in body])]

    def budova(self, cp: str, cast_obce: str) -> dict | None:
        for b in self.budovy:
            if b.get("cast_obce") == cast_obce and cp in b.get("cisla", []) and b.get("typ_cisla") in (None, "1"):
                return b
        return None


def _geometrie(misto: list[dict]) -> dict | None:
    linie = [l for m in misto for l in m.get("linie", [])]
    body = [m["bod"] for m in misto if m.get("bod")]
    casti = []
    if linie:
        casti.append({"type": "MultiLineString", "coordinates": linie})
    if body:
        casti.append({"type": "Point", "coordinates": body[0]} if len(body) == 1 else {"type": "MultiPoint", "coordinates": body})
    if not casti:
        return None
    return casti[0] if len(casti) == 1 else {"type": "GeometryCollection", "geometries": casti}


def vyres_rucni(misto: list[dict], ruian: Ruian, kdo: str) -> tuple[list[dict], list[str], list[str]]:
    """Ruční `misto` → části s geometrií. Vrací (části, chyby, upozornění).
    Místo, které v RÚIAN není (překlep, jiné číslo), je jen upozornění: denní běh kvůli němu nesmí selhat."""
    casti, chyby, upozorneni = [], [], []
    for m in misto or []:
        popis = m.get("popis")
        if "usek" in m:
            usek = m["usek"]
            url = m.get("zdroj_url")
            if not isinstance(url, str) or not url.startswith("https://"):
                chyby.append(f"mapa {kdo}: úsek musí mít odkaz na zdroj rozsahu")
                continue
            if (not isinstance(usek, list) or len(usek) < 2 or not all(
                isinstance(b, list) and len(b) == 2
                and all(isinstance(s, (float, int)) for s in b)
                and 48.8 < b[0] < 49.2 and 14.5 < b[1] < 15.0
                for b in usek
            )):
                chyby.append(f"mapa {kdo}: úsek potřebuje body na Třeboňsku ve formátu [šířka, délka]")
                continue
            casti.append({"druh": "usek", "nazev": popis,
                          "linie": [[[lon, lat] for lat, lon in usek]],
                          "jistota": "nase_propojeni", "zdroj": "RÚIAN a rozsah podle zakázky", "zdroj_url": url})
        elif "bod" in m:
            lat, lon = m["bod"]
            if not (48.8 < lat < 49.2 and 14.5 < lon < 15.0):
                chyby.append(f"mapa {kdo}: bod {m['bod']} není na Třeboňsku (zadávat [šířka, délka])")
                continue
            cast = {"druh": "bod", "nazev": popis, "bod": [lon, lat],
                    "jistota": "nase_propojeni" if m.get("priblizne") else "dolozeno", "zdroj": m.get("zdroj") or "ručně"}
            if m.get("zdroj_url"):
                cast["zdroj_url"] = m["zdroj_url"]
            casti.append(cast)
        elif "cast_obce" in m and "cp" not in m:
            stred = ruian.stred_casti(m["cast_obce"])
            if stred:
                casti.append({"druh": "cast_obce", "nazev": popis or m["cast_obce"], "bod": stred,
                              "jistota": "nase_propojeni", "zdroj": "RÚIAN – přibližně střed části obce"})
            elif ruian.k_dispozici:
                upozorneni.append(f"mapa {kdo}: část obce {m['cast_obce']!r} v RÚIAN není – místo vynecháno")
        elif "ulice" in m:
            for nazev in ([m["ulice"]] if isinstance(m["ulice"], str) else m["ulice"]):
                u = ruian.ulice.get(nazev)
                if u:
                    casti.append({"druh": "ulice", "nazev": nazev, "linie": u["linie"], "jistota": "dolozeno",
                                  "zdroj": "RÚIAN", "ruian_kod": u["kod"]})
                elif ruian.k_dispozici:
                    upozorneni.append(f"mapa {kdo}: ulice {nazev!r} v RÚIAN není – místo vynecháno")
                else:
                    upozorneni.append(f"mapa {kdo}: ulice {nazev!r} – chybí data RÚIAN")
        elif "adresa" in m:
            shoda = re.fullmatch(r"(.+?)\s+(\d+)([a-zA-Z]?)", m["adresa"].strip())
            a = ruian.adresa(shoda.group(1), shoda.group(2), shoda.group(3) or None) if shoda else None
            if a:
                casti.append({"druh": "adresa", "nazev": popis or m["adresa"], "bod": a["bod"], "jistota": "dolozeno",
                              "zdroj": "RÚIAN", "ruian_kod": a["kod"]})
            elif ruian.k_dispozici:
                upozorneni.append(f"mapa {kdo}: adresa {m['adresa']!r} v RÚIAN není – místo vynecháno")
            else:
                upozorneni.append(f"mapa {kdo}: adresa {m['adresa']!r} – chybí data RÚIAN")
        elif "cp" in m:
            b = ruian.budova(str(m["cp"]), m.get("cast_obce") or "Třeboň I")
            if b:
                casti.append({"druh": "budova", "nazev": popis or f"č. p. {m['cp']}", "bod": b["bod"], "jistota": "dolozeno",
                              "zdroj": "RÚIAN", "ruian_kod": b["kod"]})
            elif ruian.k_dispozici:
                upozorneni.append(f"mapa {kdo}: budova č. p. {m['cp']} ({m.get('cast_obce')}) v RÚIAN není – místo vynecháno")
            else:
                upozorneni.append(f"mapa {kdo}: č. p. {m['cp']} – chybí data RÚIAN")
        else:
            chyby.append(f"mapa {kdo}: neznámý druh místa {m}")
    return casti, chyby, upozorneni


def z_nazvu(text: str, ruian: Ruian) -> list[dict]:
    """Místo odvozené z názvu akce (naše propojení)."""
    if not ruian.k_dispozici or not text:
        return []
    casti, videno = [], set()

    def pridej(cast):
        klic = (cast["druh"], cast.get("ruian_kod"))
        if klic not in videno:
            videno.add(klic)
            casti.append(cast | {"jistota": "nase_propojeni", "zdroj": "RÚIAN podle názvu akce"})

    for m in RE_CP.finditer(text):
        cp, rim = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        b = ruian.budova(cp, RIMSKE[rim])
        if b:
            pridej({"druh": "budova", "nazev": f"č. p. {cp}/{rim}", "bod": b["bod"], "ruian_kod": b["kod"]})
    for m in RE_ADRESA.finditer(text):
        ul = ruian.ulice_podle_tvaru(m.group(1))
        a = ruian.adresa(ul, m.group(2)) if ul else None
        if a:
            pridej({"druh": "adresa", "nazev": f"{ul} {m.group(2)}", "bod": a["bod"], "ruian_kod": a["kod"]})
        elif not ul:
            # „Stará Hlína 27“: číslo popisné v části obce bez ulic
            b = ruian.budova(m.group(2), m.group(1))
            if b:
                pridej({"druh": "budova", "nazev": f"{m.group(1)} {m.group(2)}", "bod": b["bod"], "ruian_kod": b["kod"]})
    # Budova („bytový dům v Lázeňské ulici“) bez čísla není ulice: celá čára ulice by místo zkreslila (#223).
    budova_bez_cisla = bool(RE_BUDOVA.search(text)) and not casti
    for rx in (() if budova_bez_cisla else (RE_UL_PRED, RE_UL_ZA)):
        for m in rx.finditer(text):
            kandidat = m.group(1)
            ul = ruian.ulice_podle_tvaru(kandidat) or ruian.ulice_podle_tvaru(kandidat.split()[0])
            if ul and not any(c["druh"] == "adresa" and c["nazev"].startswith(ul + " ") for c in casti):
                u = ruian.ulice[ul]
                pridej({"druh": "ulice", "nazev": ul, "linie": u["linie"], "ruian_kod": u["kod"]})
    return casti


def nacti_nazvy(koren: Path) -> list[dict]:
    """Místa podle názvu (`config/mista_nazvy.yaml`): známá místa, která RÚIAN z názvu akce nenajde."""
    cesta = koren / "config" / "mista_nazvy.yaml"
    if not cesta.exists():
        return []
    return (yaml.safe_load(cesta.read_text(encoding="utf-8")) or {}).get("mista") or []


def podle_nazvu(text: str, nazvy: list[dict], ruian: Ruian) -> tuple[list[dict], list[str]]:
    """První položka seznamu, jejíž vzor je v textu → místo. Shoda podle názvu je vždy naše propojení."""
    for polozka in nazvy:
        if re.search(polozka["vzor"], text or ""):
            casti, chyby, _ = vyres_rucni(polozka["misto"], ruian, f"název {polozka['vzor']!r}")
            return [c | {"jistota": "nase_propojeni", "zdroj": f"{c.get('zdroj')} podle názvu akce"} for c in casti], chyby
    return [], []


def _yaml_mista(koren: Path) -> dict[str, list]:
    mista = {}
    for cesta in sorted((koren / "data" / "projekty").glob("*.yaml")):
        p = yaml.safe_load(cesta.read_text(encoding="utf-8")) or {}
        if p.get("misto"):
            mista[p["id"]] = p["misto"]
    return mista


def sestav(koren: Path, projekty: list[dict], zasobnik: list[dict], zasobnik_yaml: list[dict],
           aktivity: dict) -> tuple[list[dict], list[str], list[str]]:
    ruian = Ruian(koren)
    rucni = _yaml_mista(koren) | {p["id"]: p["misto"] for p in zasobnik_yaml if p.get("misto")}
    nazvy = nacti_nazvy(koren)
    vysledek, chyby, upozorneni = [], [], []

    def misto_pro(id_, text):
        if id_ in rucni:
            casti, ch, up = vyres_rucni(rucni[id_], ruian, id_)
            chyby.extend(ch)
            upozorneni.extend(up)
            return casti
        casti = z_nazvu(text, ruian)
        if not casti:
            casti, ch = podle_nazvu(text, nazvy, ruian)
            chyby.extend(ch)
        return casti

    for p in projekty:
        casti = misto_pro(p["id"], " ".join(filter(None, [p["nazev"], p.get("popis")])))
        vysledek.append({"id": p["id"], "typ": "investice", "nazev": p["nazev"], "faze": p.get("faze"),
                         "oblast": p.get("oblast"), "misto": casti, "geometrie": _geometrie(casti)})
    for z in zasobnik:
        if z["typ"] == "polozka" and z.get("faze") in ("zasobnik", "stavba"):
            casti = misto_pro(z["id"], " ".join([z["nazev"]] + [d["text"] for d in z.get("doklady", [])[:1]]))
            vysledek.append({"id": z["id"], "typ": "zasobnik", "nazev": z["nazev"], "faze": "zasobnik",
                             "oblast": z.get("oblast"), "misto": casti, "geometrie": _geometrie(casti)})
        elif z["typ"] == "namet":
            a = aktivity.get(int(z["id"].removeprefix("sprm-")), {})
            g = a.get("geometrie")
            if isinstance(g, dict) and g.get("type") == "Point":
                casti = [{"druh": "bod", "nazev": None, "bod": g["coordinates"], "jistota": "dolozeno",
                          "zdroj": "evidence SPRM na trebonaci.cz",
                          "zdroj_url": SPRM_URL, "zdroj_datum": _datum_sprm(koren)}]
                vysledek.append({"id": z["id"], "typ": "namet", "nazev": z["nazev"], "faze": "namet", "oblast": None,
                                 "osa": z.get("osa"), "misto": casti, "geometrie": _geometrie(casti)})
    if not ruian.k_dispozici:
        upozorneni.append("mapa: chybí raw/ruian (stahuje běh v Actions) – ulice a adresy nejsou vyřešené")
    return vysledek, chyby, upozorneni
