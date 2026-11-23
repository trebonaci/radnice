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
from pipeline import okruhy as modul_okruhy
from pipeline import smlouvy as modul_smlouvy
from pipeline.jmena import zakryj_jmena
from pipeline import dotace as modul_dotace
from pipeline import projekty as modul_projekty
from pipeline import zasobnik as modul_zasobnik
from pipeline import harmonogram as modul_harmonogram
from pipeline import terminy as modul_terminy
from pipeline import ukonceni as modul_ukonceni
from pipeline import ukazatele as modul_ukazatele
from pipeline import mapa as modul_mapa
from pipeline import mista as modul_mista
from pipeline import prehled as modul_prehled
from pipeline import rozpocet as modul_rozpocet
from pipeline import rozpocet_akce as modul_rozpocet_akce
from pipeline import rozpocet_zmeny as modul_rozpocet_zmeny
from pipeline import schvaleni as modul_schvaleni
from pipeline import zakazky as modul_zakazky
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


OBLASTI_PRO_OBCANY = {"socialni", "sport", "kultura", "skolstvi", "komunity_spolky", "doprava", "voda_odpady",
                      "uzemni_plan", "bydleni", "zivotni_prostredi", "bezpecnost", "jine"}
RE_URADNI_ZACATEK = re.compile(r"^(Rada|Zastupitelstvo|RM|ZM)\b")


def _kmeny(text: str) -> list[str]:
    """Kmeny slov (první 4 znaky slov o 3+ písmenech) – tolerance ke skloňování („Sokolská“ ~ „Sokolskou“)."""
    return [w.lower()[:max(3, min(4, len(w) - 1))] for w in re.findall(r"\w{3,}", text or "")]


def zkontroluj_pro_obcany(pro: dict, text_usneseni: str | None = None) -> list[str]:
    """Pravidla věty „Co se mění pro vás“ (docs/ANOTACE.md), která jde ohlídat kódem."""
    chyby = []
    kdo = pro.get("kdo")
    if kdo is not None:
        if not str(kdo).strip() or len(str(kdo)) > 60:
            chyby.append("kdo musí být krátký název organizace nebo místa (nejvýš 60 znaků)")
        elif text_usneseni is not None:
            zdroj = " ".join(_kmeny(text_usneseni))
            chybi = [k for k in _kmeny(kdo) if not k.isdigit() and k not in zdroj]
            if chybi:
                chyby.append(f"kdo {kdo!r}: slova nejsou v textu usnesení ({', '.join(chybi)})")
    text = (pro.get("text") or "").strip()
    if not text:
        chyby.append("chybí text")
    if len(text) > 220:
        chyby.append(f"text má {len(text)} znaků (nejvýš 220)")
    if RE_URADNI_ZACATEK.match(text):
        chyby.append("text začíná orgánem – psát z pohledu občana")
    if pro.get("oblast") not in OBLASTI_PRO_OBCANY:
        chyby.append(f"neznámá oblast {pro.get('oblast')!r}")
    od = pro.get("plati_od")
    if od is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(od)):
        chyby.append(f"plati_od není datum RRRR-MM-DD: {od!r}")
    return chyby


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


POLE_BEZ_KONTROLY_JMEN = {"jmeno_podnikatele"}   # podnikající FO jako dodavatel jménem (#93)


def _retezce(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k not in POLE_BEZ_KONTROLY_JMEN:
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
    strany_text = [p.read_text(encoding="utf-8") for p in sorted(adresar.glob("strana-*.txt"),
                                                                 key=lambda x: int(x.stem.split("-")[1]))]
    dokument = normalizuj(" ".join(strany_text))

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
        pro = a.get("pro_obcany")          # „co se mění pro vás“ (AI, věta pro čtenáře + doslovná citace)
        if pro:
            ok &= over(pro["citace"], u["text"], f"{u['id']} pro_obcany")
            for c in zkontroluj_pro_obcany(pro, u["text"]):
                chyby.append(f"{jednani_id}: {u['id']} pro_obcany: {c}")
        for cit in ([a["citace"]] + [c["citace"] for c in a.get("castky", [])] + [p["citace"] for p in a.get("parcely", [])]
                    + ([pro["citace"]] if pro else [])):
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
            "stitky": modul_stitky.jeden_na_stitek(stitky),
            "citace": citace_usn,
            "castky": [{**c, "mena": "CZK"} for c in a.get("castky", [])],
            "parcely": a.get("parcely", []),
            "pro_obcany": {"text": pro["text"], "kdo": pro.get("kdo"), "oblast": pro.get("oblast"),
                           "plati_od": pro.get("plati_od"),
                           "citace": {"dokument_id": dok["dokument_id"], "strany": u["strany"], "text": pro["citace"]}}
            if pro else None,
            "pro_obcany_ai": True if pro else None,
            "poznamka": a.get("poznamka"),
            "otazky": a.get("otazky", []),
            "overeni": "overeno_kodem" if ok else "navrh",
        })
        # dotace z tabulky v usnesení (bez AI): rozložení stran po stejné anonymizaci jako text usnesení
        radky = anonymizuj_urednici(anonymizuj("\n".join(strany_text), anon), osoby).splitlines()
        dot, chyby_d = modul_dotace.z_usneseni({**u, "jednani_id": jednani_id}, radky, verejny,
                                               dok["dokument_id"], meta.get("datum"))
        chyby += [f"{jednani_id}: {c}" for c in chyby_d]
        usneseni_out[-1]["_dotace"] = dot

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
    Vrací ({"jednani": [...], "usneseni": [...], "hlasovani": [...], "zakazky": [...]}, chyby)."""
    koren = koren or KOREN
    seznam = json.loads((koren / "raw" / "manifest.json").read_text(encoding="utf-8"))
    manifest = {d["jednani_id"]: d for d in seznam}
    chyby: list[str] = zkontroluj_verze(seznam)
    osoby = nacti_osoby(koren)
    stitky_cfg = modul_stitky.nacti_ciselnik(koren)
    kategorie = yaml.safe_load((koren / "config" / "kategorie.yaml").read_text(encoding="utf-8"))
    chyby += modul_stitky.zkontroluj_ciselnik(stitky_cfg, kategorie)
    okruhy_cfg = modul_okruhy.nacti(koren)
    chyby += modul_okruhy.zkontroluj(okruhy_cfg, kategorie)
    jednani, usneseni, hlasovani = [], [], []
    for jednani_id in sorted(manifest):
        if not (koren / "anotace" / f"{jednani_id}.yaml").exists():
            continue
        j, u, h = zpracuj_jednani(jednani_id, manifest, chyby, osoby, koren, stitky_cfg)
        jednani.append(j)
        usneseni += u
        hlasovani += h
    zakazky = modul_zakazky.nacti_zakazky(koren)
    for z in zakazky:
        # jména osob s titulem v názvu a předmětu (např. autor projektu) → „[jméno]“ (ostrý běh 20. 11. 2026)
        for pole, drzak in [("nazev", z), ("predmet", z)] + [("nazev", c) for c in z["casti"]]:
            if not drzak[pole]:
                continue
            drzak[pole] = anonymizuj_urednici(drzak[pole], osoby)
            for n in najdi_osobni_udaje(drzak[pole], osoby):
                drzak[pole] = drzak[pole].replace(n, "[jméno]")
            drzak[pole] = zakryj_jmena(drzak[pole], osoby, koren)       # jména bez titulu (#84)
    chyby += modul_zakazky.zkontroluj(zakazky, koren)
    smlouvy = modul_smlouvy.nacti_smlouvy(koren)
    for sm in smlouvy:
        # jména osob s titulem v předmětu (mimo zastupitele) se maskují; adresy a IČO FO vynechal už převod
        sm["predmet"] = anonymizuj_urednici(sm["predmet"], osoby) if sm["predmet"] else sm["predmet"]
        for n in najdi_osobni_udaje(sm["predmet"] or "", osoby):
            sm["predmet"] = sm["predmet"].replace(n, "[jméno]")
        if not modul_smlouvy.je_kulturni_akce(sm["predmet"]):                # umělci jménem (#131)
            sm["predmet"] = zakryj_jmena(sm["predmet"], osoby, koren)        # jména bez titulu (#84)
    chyby += modul_smlouvy.zkontroluj(smlouvy, koren)
    dotace = [d for u in usneseni for d in u.pop("_dotace", [])]
    # stav schválení: rada sama / rada doporučila zastupitelstvu / zastupitelstvo rozhodlo (#115)
    modul_schvaleni.oznac(usneseni, {j["id"]: j["datum"] for j in jednani})
    # rozpočtová opatření po položkách z textu usnesení (bez AI; před ± změna = po kontroluje kód)
    rozpoctova_opatreni, chyby_ro = modul_rozpocet.z_usneseni(usneseni)
    chyby += chyby_ro + modul_rozpocet.zkontroluj(rozpoctova_opatreni, usneseni)
    # schválený rozpočet po položkách z PDF rozpočtu (#129; bez AI, součty kontroluje kód)
    rozpocet, chyby_r = modul_rozpocet_akce.nacti(koren)
    chyby += chyby_r + modul_rozpocet_akce.zkontroluj(rozpocet, koren)
    # přehled rozpočtových opatření za rok (PDF finančního odboru, #138) → stav položek po změnách
    rozpocet_zmeny, chyby_z, _upozorneni_z = modul_rozpocet_zmeny.nacti(koren)
    _upozorneni_z += modul_rozpocet_zmeny.sjednot_nazvy(rozpocet_zmeny, rozpocet)
    chyby += (chyby_z + modul_rozpocet_zmeny.zkontroluj(rozpocet_zmeny, koren)
              + modul_rozpocet_zmeny.porovnej_s_usnesenimi(rozpocet_zmeny, rozpoctova_opatreni))
    modul_rozpocet_zmeny.doplnit_rozpocet(rozpocet, rozpocet_zmeny)
    vystup = {"jednani": jednani, "usneseni": usneseni, "hlasovani": hlasovani, "zakazky": zakazky,
              "smlouvy": smlouvy, "rozpoctova_opatreni": rozpoctova_opatreni, "rozpocet": rozpocet,
              "rozpocet_zmeny": rozpocet_zmeny,
              "dotace": dotace}
    # projektové karty: ručně spravované data/projekty/*.yaml + vazby na výstupy výše
    vystup["projekty"], chyby_p = modul_projekty.sestav(koren, vystup)
    chyby += chyby_p
    # pracovní zásobník projektů a náměty ze Strategického plánu (#172)
    vystup["zasobnik"], chyby_z2 = modul_zasobnik.sestav(koren, vystup, vystup["projekty"])
    chyby += chyby_z2
    # mapa investic (#180): ulice liniově, budovy bodově (RÚIAN), náměty SPRM bodově
    vystup["mapa"], chyby_m, _upozorneni_m = modul_mapa.sestav(
        koren, vystup["projekty"], vystup["zasobnik"], modul_zasobnik.nacti(koren), modul_projekty.nacti_sprm(koren)[0])
    for u in _upozorneni_m:
        print(f"UPOZORNĚNÍ: {u}", file=sys.stderr)
    chyby += chyby_m
    # měkké aktivity: karty míst a služeb + proud „Co se mění“ (#183); místa jsou body na mapě
    vystup["mista"], vystup["zmeny"], chyby_mi = modul_mista.sestav(koren, vystup, vystup["projekty"], vystup["zasobnik"])
    chyby += chyby_mi
    # přehled dění na radnici pro web (#187): změny, investice a příprava, nejnovější nahoře
    vystup["prehled"] = modul_prehled.sestav(vystup["zmeny"], vystup["projekty"], vystup["zasobnik"])
    vystup["mapa"] += [{"id": m["id"], "typ": "misto", "nazev": m["nazev"], "faze": None, "oblast": m["oblast"],
                        "misto": m["misto"], "geometrie": m["geometrie"]} for m in vystup["mista"]]
    # termín dokončení stavby podle smlouvy (#205): úryvky příloh z registru smluv → karty
    cesta_t = koren / "raw" / "smlouvy" / "terminy.json"
    vystup["terminy"], chyby_t = modul_terminy.sestav(json.loads(cesta_t.read_text(encoding="utf-8")) if cesta_t.exists() else {})
    chyby += chyby_t
    podle_id = {t["zdroj_id"]: t for t in vystup["terminy"]}
    for k in vystup["projekty"]:
        k["termin_dokonceni"] = modul_terminy.pro_kartu(k, podle_id)
    # doložené ukončení plnění stavební smlouvy z E-ZAK (#207): archiv dokončených projektů po letech
    cesta_pl = koren / "raw" / "ezak" / "plneni.json"
    plneni = json.loads(cesta_pl.read_text(encoding="utf-8")) if cesta_pl.exists() else {}
    for k in vystup["projekty"]:
        k["ukonceni_plneni"] = modul_ukonceni.pro_kartu(k, plneni)
    # harmonogram investic, zásobníku a dlouhodobých neinvestičních projektů (#194)
    vystup["harmonogram"], chyby_h = modul_harmonogram.sestav(koren, vystup, vystup["projekty"], vystup["zasobnik"])
    chyby += chyby_h
    # šest okruhů webu (audit 23. 11. 2026): téma → okruh u všech položek, usnesení i věcný okruh
    chyby += modul_okruhy.oznac(okruhy_cfg, vystup)
    vystup["okruhy"] = modul_okruhy.ciselnik(okruhy_cfg)
    # přehled investic roku (kapitálové výdaje po změnách, #138) – jen když je rozpočet stažený
    roky = sorted({r["rok"] for r in rozpocet})
    vystup["investice"] = [modul_rozpocet_zmeny.prehled_investic(rozpocet, rozpocet_zmeny, vystup["projekty"], r)
                           for r in roky]
    chyby += modul_okruhy.oznac_investice(okruhy_cfg, vystup["investice"], vystup["projekty"])
    # datový přehled (#177): ukazatele počítá kód z hotových výstupů
    vystup["ukazatele"] = modul_ukazatele.sestav(vystup, modul_zasobnik.nacti_subjekty(koren))
    # kontrola osobních údajů v celém výstupu (kromě doslovných citací, ty kontroluje sestavení)
    # (zastupitelé jen z období daného jednání)
    obdobi_jednani = {j["id"]: j["obdobi"] for j in jednani}
    for nazev, obsah in vystup.items():
        for zaznam in obsah:
            obdobi = zaznam.get("obdobi") if isinstance(zaznam.get("obdobi"), str) else None
            obdobi = obdobi or obdobi_jednani.get(zaznam.get("jednani_id"))
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
    print(f"jednání {len(vystup['jednani'])}, usnesení {len(vystup['usneseni'])}, hlasování {len(vystup['hlasovani'])}, "
          f"zakázky {len(vystup['zakazky'])}, smlouvy {len(vystup['smlouvy'])}, "
          f"položky RO {len(vystup['rozpoctova_opatreni'])}, rozpočet {len(vystup['rozpocet'])}, změny rozpočtu {len(vystup['rozpocet_zmeny'])}, projekty {len(vystup['projekty'])}, zásobník {len(vystup['zasobnik'])}, ukazatele {len(vystup['ukazatele'])}, mapa {sum(1 for m in vystup['mapa'] if m['geometrie'])}/{len(vystup['mapa'])}, místa {len(vystup['mista'])}, změny {len(vystup['zmeny'])}, přehled {len(vystup['prehled'])}, okruhy {len(vystup['okruhy'])}, dotace {len(vystup['dotace'])}")
    for c in chyby:
        print("CHYBA:", c, file=sys.stderr)
    return 1 if chyby else 0


if __name__ == "__main__":
    sys.exit(main())
