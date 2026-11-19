"""Sestaví data/ z rozloženého zápisu (pipeline/zapisy.py) a AI anotací (anotace/*.yaml).

Kontroly (selhání = nenulový návratový kód):
- každá citace doslova (po sjednocení mezer) existuje ve zdroji;
  citace usnesení musí být uvnitř textu daného usnesení;
- každá částka se jako číslo vyskytuje ve své citaci;
- anotace neodkazuje na neexistující usnesení a každé usnesení má anotaci;
- součet hlasů nepřesahuje počet přítomných na začátku jednání;
- citace neobsahují řetězce určené k anonymizaci;
- štítky věcné relevance (`pipeline/stitky.py`): číselník je konzistentní, štítky z AI mají doslovnou citaci.

Spuštění: python -m pipeline.sestav
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

from pipeline import stitky as modul_stitky
from pipeline.verze import zkontroluj as zkontroluj_verze
from pipeline.zapisy import normalizuj, rozloz

KOREN = Path(__file__).resolve().parent.parent
ANONYM = "[fyzická osoba]"
RE_CISLO = re.compile(r"\d{1,3}(?:[ .]\d{3})+(?:,\d+)?|\d+(?:,\d+)?")


def cisla_v_textu(text: str) -> list[float]:
    """Najde čísla v českém zápisu (223.850,00 / 25.000 / 2 100 / 16,34)."""
    vysledek = []
    for m in RE_CISLO.finditer(text):
        s = m.group(0).replace(" ", "").replace(".", "").replace(",", ".")
        try:
            vysledek.append(float(s))
        except ValueError:
            pass
    return vysledek


def _polozky(retezce: list) -> list[tuple[str, str]]:
    """Položka anonymizace je řetězec (nahradí se [fyzická osoba]) nebo {retezec, nahrada}."""
    return [(r, ANONYM) if isinstance(r, str) else (r["retezec"], r["nahrada"]) for r in retezce]


def anonymizuj(text: str, retezce: list) -> str:
    for r, nahrada in _polozky(retezce):
        text = text.replace(r, nahrada)
    return text


RE_TITUL_JMENO = re.compile(
    r"(?:(?:Ing|Mgr|Bc|MUDr|MVDr|PaedDr|JUDr|PhDr|RNDr|doc|prof)\.\s*)+"
    r"[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+){1,2}")
RE_ZAPSAL = re.compile(r"Zapsal[a]?:\s*([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ]\S*\s+\S+)")


def nacti_osoby(koren: Path | None = None) -> dict:
    return yaml.safe_load(((koren or KOREN) / "config" / "osoby.yaml").read_text(encoding="utf-8"))


def _vzor(text: str) -> re.Pattern:
    """Regex z textu, který toleruje libovolné mezery a zalomení řádků."""
    return re.compile(r"\s+".join(re.escape(c) for c in text.split()))


def anonymizuj_urednici(text: str, osoby: dict) -> str:
    """Nahradí jména úředníků a dalších nevolených osob funkcí."""
    if not text:
        return text
    for u in osoby["urednici"]:
        for v in u["varianty"]:
            hledat, nahrada = (v, u["funkce"]) if isinstance(v, str) else (v["text"], v["nahrada"])
            text = _vzor(hledat).sub(nahrada, text)
    return text


RE_TITULY = re.compile(r"^(?:(?:Ing|Mgr|Bc|MUDr|MVDr|PaedDr|JUDr|PhDr|RNDr|doc|prof)\.\s*)+")


def je_zastupitel(jmeno_s_titulem: str, osoby: dict, obdobi: str | None = None) -> bool:
    """Přesná shoda po celých slovech: jméno (bez titulů) musí začínat některým
    povoleným tvarem jména zastupitele. Regex může zachytit i slovo z dalšího řádku
    ("Lenka Blažková Pro"), proto se porovnává začátek, nikoli celý zachycený řetězec.
    Se zadaným `obdobi` platí jen zastupitelé toho období (bývalý zastupitel v zápisu
    jiného období je soukromá osoba)."""
    slova = RE_TITULY.sub("", jmeno_s_titulem).split()
    for z in osoby["zastupitele"]:
        if obdobi is not None and obdobi not in z.get("obdobi", []):
            continue
        for tvar in z["tvary"]:
            t = tvar.split()
            if slova[:len(t)] == t:
                return True
    return False


def najdi_osobni_udaje(text: str, osoby: dict, obdobi: str | None = None) -> list[str]:
    """Kontrola výstupu: jména s titulem, která nepatří zastupitelům, známá jména úředníků
    a podpis zapisovatele. Vrací nalezené problémy."""
    nalezy = []
    for m in RE_TITUL_JMENO.finditer(text):
        if not je_zastupitel(m.group(0), osoby, obdobi):
            nalezy.append(" ".join(m.group(0).split()))
    for u in osoby["urednici"]:
        for v in u["varianty"]:
            hledat = v if isinstance(v, str) else v["text"]
            prijmeni = hledat.split()[-1]
            if prijmeni[0].isupper() and prijmeni in text:
                nalezy.append(prijmeni)
    for m in RE_ZAPSAL.finditer(text):
        if not m.group(1).startswith(("pracovn", "zapisovatel")):
            nalezy.append("Zapsal(a): " + m.group(1))
    return nalezy


def _retezce(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _retezce(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _retezce(v)


def adresar_textu(koren: Path, dok: dict) -> Path:
    """Text AKTUÁLNÍ verze dokumentu: cesta z poslední položky `verze[].texty` (starší záznamy bez ní
    mají text přímo v raw/texty/<jednani_id>)."""
    texty = (dok.get("verze") or [{}])[-1].get("texty")
    return koren / (texty or f"raw/texty/{dok['jednani_id']}")


def zpracuj_jednani(jednani_id: str, manifest: dict, chyby: list[str], osoby: dict,
                    koren: Path | None = None, stitky_cfg: dict | None = None) -> tuple[dict, list, list]:
    koren = koren or KOREN
    stitky_cfg = stitky_cfg or modul_stitky.nacti_ciselnik(koren)
    dok = manifest[jednani_id]
    adresar = adresar_textu(koren, dok)
    rozlozeno = rozloz(jednani_id, adresar)
    anot = yaml.safe_load((koren / "anotace" / f"{jednani_id}.yaml").read_text(encoding="utf-8"))
    dokument = normalizuj(" ".join(p.read_text(encoding="utf-8") for p in sorted(adresar.glob("strana-*.txt"))))

    def over(citace: str, kde: str, kontext: str) -> bool:
        if normalizuj(citace) not in normalizuj(kde):
            chyby.append(f"{jednani_id}: citace nenalezena ({kontext}): {citace!r}")
            return False
        return True

    meta = anot["jednani"]
    over(meta["citace"], dokument, "jednani")
    for z in meta.get("pritomnost_zmeny", []):
        over(z["citace"], dokument, "pritomnost")

    usn_ids = {u["id"] for u in rozlozeno["usneseni"]}
    for klic in anot["usneseni"]:
        if klic not in usn_ids:
            chyby.append(f"{jednani_id}: anotace pro neexistující usnesení {klic}")

    usneseni_out = []
    for u in rozlozeno["usneseni"]:
        a = anot["usneseni"].get(u["id"])
        if a is None:
            chyby.append(f"{jednani_id}: usnesení {u['id']} nemá anotaci")
            continue
        anon = a.get("anonymizace", [])
        ok = over(a["citace"], u["text"], u["id"])
        for c in a.get("castky", []):
            ok &= over(c["citace"], dokument, f"{u['id']} castka")
            if not any(abs(x - float(c["hodnota"])) < 0.005 for x in cisla_v_textu(c["citace"])):
                chyby.append(f"{jednani_id}: {u['id']} částka {c['hodnota']} není v citaci {c['citace']!r}")
                ok = False
        for p in a.get("parcely", []):
            ok &= over(p["citace"], dokument, f"{u['id']} parcela")
        for cit in [a["citace"]] + [c["citace"] for c in a.get("castky", [])] + [p["citace"] for p in a.get("parcely", [])]:
            for r, _ in _polozky(anon):
                if r in cit:
                    chyby.append(f"{jednani_id}: {u['id']} citace obsahuje anonymizovaný údaj {r!r}")
                    ok = False
        for r, _ in _polozky(anon):
            if r not in normalizuj(u["text"]) and r not in u["text"]:
                chyby.append(f"{jednani_id}: {u['id']} řetězec k anonymizaci nenalezen: {r!r}")
        verejny = anonymizuj_urednici(anonymizuj(u["text"], anon), osoby)
        citace_usn = {"dokument_id": dok["dokument_id"], "strany": u["strany"], "text": a["citace"]}
        stitky = modul_stitky.pravidlove_stitky(stitky_cfg, verejny, a["kategorie"], citace_usn)
        stitky += modul_stitky.ai_stitky(stitky_cfg, a.get("stitky"), u["text"], citace_usn,
                                         [r for r, _ in _polozky(anon)], f"{jednani_id}: {u['id']}", chyby)
        usneseni_out.append({
            "id": u["id"],
            "cislo": u["cislo"],
            "jednani_id": jednani_id,
            "bod": u["bod"],
            "vysledek_hlasovani": u["vysledek_hlasovani"],
            "vysledek_zapis": u["vysledek_zapis"],
            "ukony": u["ukony"],
            "text": verejny,
            "text_anonymizovan": verejny != u["text"],
            "tema": a["tema"],
            "tema_ai": True,
            "kategorie": a["kategorie"],
            "kategorie_ai": True,
            "shrnuti": a["shrnuti"],
            "shrnuti_ai": True,
            "stitky": stitky,
            "citace": citace_usn,
            "castky": [{**c, "mena": "CZK"} for c in a.get("castky", [])],
            "parcely": a.get("parcely", []),
            "poznamka": a.get("poznamka"),
            "otazky": a.get("otazky", []),
            "overeni": "overeno_kodem" if ok else "navrh",
        })

    hlasovani_out = []
    for h in rozlozeno["hlasovani"]:
        soucet = h["pro"] + h["proti"] + h["zdrzel"]
        if soucet > meta["pritomno"]:
            chyby.append(f"{jednani_id}: hlasování {h['zdroj_radek']} má víc hlasů ({soucet}) než přítomných")
        zaznam = {k: v for k, v in h.items() if k != "zdroj_radek"} | {"hlasu_celkem": soucet}
        if zaznam.get("predmet"):
            zaznam["predmet"] = anonymizuj_urednici(zaznam["predmet"], osoby)
        hlasovani_out.append(zaznam)

    body = rozlozeno["body"]
    for b in body:
        upr = (anot.get("body") or {}).get(b["cislo"]) or {}
        if "nazev" in upr:
            b["nazev"] = upr["nazev"]
            b["nazev_anonymizovan"] = True
        anon = upr.get("anonymizace", [])
        if b["text"]:
            for r, _ in _polozky(anon):
                if r not in b["text"]:
                    chyby.append(f"{jednani_id}: bod {b['cislo']} řetězec k anonymizaci nenalezen: {r!r}")
        puvodni = b["text"]
        if b["text"]:
            b["text"] = anonymizuj_urednici(anonymizuj(b["text"], anon), osoby)
        b["nazev"] = anonymizuj_urednici(b["nazev"], osoby)
        b["text_anonymizovan"] = b["text"] != puvodni

    jednani_out = {
        "id": jednani_id,
        "organ": meta["organ"],
        "druh": meta.get("druh", "radne"),
        "cislo": meta["cislo"],
        "datum": meta["datum"],
        "obdobi": meta["obdobi"],
        "pritomno_na_zacatku": meta["pritomno"],
        "clenu": meta["clenu"],
        "pritomnost_zmeny": [{k: v for k, v in z.items() if k != "citace"} for z in meta.get("pritomnost_zmeny", [])],
        "dokument": {k: dok[k] for k in ("dokument_id", "url", "stranka_zdroje", "vyveseno", "sha256", "pocet_stran")},
        "body": body,
        "upozorneni_parseru": rozlozeno["upozorneni"],
    }
    return jednani_out, usneseni_out, hlasovani_out


def sestav(koren: Path | None = None) -> tuple[dict[str, list], list[str]]:
    """Sestaví výstupy z `koren` (raw/, anotace/, config/) bez zápisu na disk.
    Vrací ({"jednani": [...], "usneseni": [...], "hlasovani": [...]}, chyby)."""
    koren = koren or KOREN
    seznam = json.loads((koren / "raw" / "manifest.json").read_text(encoding="utf-8"))
    manifest = {d["jednani_id"]: d for d in seznam}
    chyby: list[str] = zkontroluj_verze(seznam)
    osoby = nacti_osoby(koren)
    stitky_cfg = modul_stitky.nacti_ciselnik(koren)
    kategorie = yaml.safe_load((koren / "config" / "kategorie.yaml").read_text(encoding="utf-8"))
    chyby += modul_stitky.zkontroluj_ciselnik(stitky_cfg, kategorie)
    jednani, usneseni, hlasovani = [], [], []
    for jednani_id in sorted(manifest):
        if not (koren / "anotace" / f"{jednani_id}.yaml").exists():
            continue
        j, u, h = zpracuj_jednani(jednani_id, manifest, chyby, osoby, koren, stitky_cfg)
        jednani.append(j)
        usneseni += u
        hlasovani += h
    vystup = {"jednani": jednani, "usneseni": usneseni, "hlasovani": hlasovani}
    # kontrola osobních údajů v celém výstupu (kromě doslovných citací, ty kontroluje sestavení)
    # (zastupitelé jen z období daného jednání)
    obdobi_jednani = {j["id"]: j["obdobi"] for j in jednani}
    for nazev, obsah in vystup.items():
        for zaznam in obsah:
            obdobi = zaznam.get("obdobi") or obdobi_jednani.get(zaznam.get("jednani_id"))
            for r in _retezce(zaznam):
                for n in najdi_osobni_udaje(r, osoby, obdobi):
                    chyby.append(f"{nazev}: osobní údaj ve výstupu: {n!r}")
    return vystup, chyby


def serializuj(obsah) -> str:
    return json.dumps(obsah, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    vystup, chyby = sestav(KOREN)
    data = KOREN / "data"
    data.mkdir(exist_ok=True)
    for nazev, obsah in vystup.items():
        (data / f"{nazev}.json").write_text(serializuj(obsah), encoding="utf-8")
    print(f"jednání {len(vystup['jednani'])}, usnesení {len(vystup['usneseni'])}, hlasování {len(vystup['hlasovani'])}")
    for c in chyby:
        print("CHYBA:", c, file=sys.stderr)
    return 1 if chyby else 0


if __name__ == "__main__":
    sys.exit(main())
