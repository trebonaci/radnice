"""Datový přehled (#177, fáze 3): ukazatele z `data/*.json` → `data/ukazatele.json`.

Každý ukazatel podle modelu `ukazatel` (DATOVY_MODEL.md): `id`, `nazev`, `hodnota` (číslo nebo řada),
`jednotka`, `obdobi`, `definice`, `vypocet`, `zdroj`, `zkontrolovano`, `srovnatelnost`.
Počty a součty počítá jen tento kód. Částky se sčítají jen v rámci jednoho druhu (např. přiznané dotace),
nikdy napříč druhy; u každé řady je druh a DPH.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from pipeline.zdroje.rozpocet_mesta import STRANKA as URL_ROZPOCET
from pipeline.zdroje.zapisy_mesta import ZAKLAD_RM, ZAKLAD_ZM

ZDROJ_ZAPISY = [{"nazev": "Zápisy z jednání rady města", "url": ZAKLAD_RM},
                {"nazev": "Zápisy zastupitelstva města", "url": ZAKLAD_ZM}]
ZDROJ_REGISTR = {"nazev": "Registr smluv (otevřená data)", "url": "https://data.smlouvy.gov.cz/"}
ZDROJ_EZAK = {"nazev": "Profily zadavatelů E-ZAK", "url": "https://zakazky.mesto-trebon.cz/"}
ZDROJ_ROZPOCET = {"nazev": "Rozpočet města a přehled rozpočtových opatření", "url": URL_ROZPOCET}
ZDROJ_SPRM = {"nazev": "Evidence Strategického plánu na trebonaci.cz", "url": "https://trebonaci.cz/wp-json/trebonaci/v1/projekty"}

KATEGORIE = {
    "samosprava": "Samospráva a úřad", "majetek_najem": "Nájmy a pronájmy", "investice": "Investice",
    "majetek_prevod": "Prodej a nákup majetku", "rozpocet": "Rozpočet", "sport": "Sport", "skolstvi": "Školy",
    "prispevkove_organizace": "Městské organizace", "socialni": "Sociální služby", "verejne_zakazky": "Zakázky",
    "kultura": "Kultura", "dotace_dary": "Dotace a dary", "doprava": "Doprava", "lazne_spolecnosti": "Lázně a městské firmy",
    "ostatni": "Ostatní", "voda_odpady": "Voda a odpady", "personalni": "Personální věci",
}
FAZE = {"pripravuje_se": "Připravuje se", "soutezi_se": "Soutěží se", "probiha": "Stavba probíhá", "dokonceno": "Dokončeno"}
OBLAST_DOTACI = {"tělovýchovy a sportu": "Sport a tělovýchova", "sociálních služeb a zdravotnictví": "Sociální služby a zdravotnictví",
                 "ostatních zájmových činností": "Ostatní zájmová činnost", "kultury": "Kultura"}
ORGAN = {"rada": "Rada města", "zastupitelstvo": "Zastupitelstvo"}


def _ukazatel(id_, nazev, hodnota, jednotka, od, do, definice, vypocet, zdroj, srovnatelnost=None, **navic) -> dict:
    return {"id": id_, "nazev": nazev, "hodnota": hodnota, "jednotka": jednotka, "obdobi": {"od": od, "do": do},
            "definice": definice, "vypocet": f"pipeline/ukazatele.py:{vypocet}", "zdroj": zdroj,
            "zkontrolovano": None, "srovnatelnost": srovnatelnost, **navic}


def jednani(jednani: list[dict]) -> dict:
    data = sorted(j["datum"] for j in jednani)
    pocty = Counter(j["organ"] for j in jednani)
    rada = [{"klic": k, "nazev": ORGAN.get(k, k), "hodnota": pocty[k]} for k in ("rada", "zastupitelstvo") if pocty[k]]
    return _ukazatel("jednani", "Zpracovaná jednání", rada, "jednání", data[0] if data else None, data[-1] if data else None,
                     "Jednání rady a zastupitelstva, jejichž zápis je zveřejněný a zpracovaný.", "jednani", ZDROJ_ZAPISY,
                     "Zpracováváme zápisy od 1. 9. 2026 (konec období 2022–2026 a období 2026–2030).")


def usneseni_oblasti(usneseni: list[dict], jednani: list[dict]) -> dict:
    datum = {j["id"]: j["datum"] for j in jednani}
    data = sorted(datum[u["jednani_id"]] for u in usneseni if u["jednani_id"] in datum)
    pocty = Counter(k for u in usneseni for k in dict.fromkeys(u.get("kategorie") or ["ostatni"]))
    rada = [{"klic": k, "nazev": KATEGORIE.get(k, k), "hodnota": n} for k, n in sorted(pocty.items(), key=lambda x: (-x[1], x[0]))]
    neprijato = sum(1 for u in usneseni if u.get("vysledek_hlasovani") == "neprijato")
    return _ukazatel("usneseni-oblasti", "Usnesení podle oblastí", rada, "usnesení", data[0] if data else None,
                     data[-1] if data else None,
                     "Počet usnesení, která se oblasti týkají. Jedno usnesení může patřit do více oblastí, proto se řada nesčítá.",
                     "usneseni_oblasti", ZDROJ_ZAPISY, "Oblasti přiřazuje AI s kontrolou, viz metodika.",
                     celkem=len(usneseni), neprijato=neprijato, kategorie_ai=True)


def _sledovana(subjekty: dict, s: dict) -> list[str]:
    ica = [s.get("subjekt_ico")] + [st.get("ico") for st in s.get("strany", [])]
    return list(dict.fromkeys(i for i in ica if i in subjekty))


def smlouvy(smlouvy: list[dict], subjekty: dict, od: str = "2024-03-01") -> dict:
    """Smlouvy zveřejněné v registru (podle data zveřejnění) za každou sledovanou organizaci a rok.
    Smlouva dvou sledovaných organizací se počítá u obou (řady se proto nesčítají)."""
    videno, pocty = set(), defaultdict(Counter)
    do = ""
    for s in smlouvy:
        zverejneno = (s.get("datum_zverejneni") or "")[:10]
        if zverejneno < od or s.get("id_smlouvy") in videno:
            continue
        videno.add(s.get("id_smlouvy"))
        do = max(do, zverejneno)
        for ico in _sledovana(subjekty, s):
            pocty[ico][zverejneno[:4]] += 1
    rada = [{"klic": ico, "nazev": subjekty[ico], "hodnota": sum(r.values()), "podle_let": dict(sorted(r.items()))}
            for ico, r in sorted(pocty.items(), key=lambda x: (-sum(x[1].values()), x[0]))]
    return _ukazatel("smlouvy-organizace", "Smlouvy v registru podle organizací", rada, "smluv", od, do or None,
                     "Smlouvy zveřejněné v registru smluv, kde je sledovaná organizace smluvní stranou. Verze téže smlouvy se počítají jednou.",
                     "smlouvy", [ZDROJ_REGISTR],
                     "Registr zpracováváme od března 2024. Do registru se nemusí zveřejňovat smlouvy do 50 000 Kč bez DPH.",
                     celkem=len(videno))


def zakazky(zakazky: list[dict], subjekty: dict) -> dict:
    pocty, stavy = defaultdict(Counter), defaultdict(Counter)
    data = sorted(z["datum_zahajeni"] for z in zakazky if z.get("datum_zahajeni"))
    for z in zakazky:
        ico = z.get("subjekt_ico")
        pocty[ico][(z.get("datum_zahajeni") or "")[:4] or "neuvedeno"] += 1
        stavy[ico][z.get("stav") or "neuvedeno"] += 1
    rada = [{"klic": ico, "nazev": subjekty.get(ico, ico), "hodnota": sum(r.values()), "podle_let": dict(sorted(r.items())),
             "podle_stavu": dict(sorted(stavy[ico].items()))}
            for ico, r in sorted(pocty.items(), key=lambda x: (-sum(x[1].values()), x[0]))]
    return _ukazatel("zakazky-organizace", "Veřejné zakázky podle zadavatelů", rada, "zakázek", data[0] if data else None,
                     data[-1] if data else None, "Zakázky zveřejněné na profilech zadavatelů v E-ZAK, podle roku zahájení.",
                     "zakazky", [ZDROJ_EZAK],
                     "Strojově čitelný export mají jen město, Městská Vodohospodářská a Slatinné lázně; malé zakázky se na profilu nezveřejňují.",
                     celkem=len(zakazky))


def dotace(dotace: list[dict]) -> dict:
    """Přiznané dotace (usnesení rady a zastupitelstva) podle oblasti: počet a součet – jeden druh částky.
    Počítají se jen přijatá usnesení; nepřijatý návrh není přiznaná dotace."""
    dotace = [d for d in dotace if d.get("vysledek_hlasovani") == "prijato"]
    pocty, soucty = Counter(), defaultdict(float)
    druhy = {d["castka"]["druh"] for d in dotace if d.get("castka")}
    if len(druhy) > 1:
        raise ValueError(f"dotace: různé druhy částek {sorted(druhy)} se nesčítají")
    for d in dotace:
        pocty[d["oblast"]] += 1
        if d.get("castka"):
            soucty[d["oblast"]] += d["castka"]["hodnota"]
    data = sorted(d["datum"] for d in dotace if d.get("datum"))
    rada = [{"klic": o, "nazev": OBLAST_DOTACI.get(o, o[:1].upper() + o[1:]), "pocet": pocty[o], "hodnota": round(soucty[o], 2)}
            for o in sorted(pocty, key=lambda o: (-soucty[o], o))]
    return _ukazatel("dotace-oblasti", "Dotace přiznané radou a zastupitelstvem", rada, "Kč", data[0] if data else None,
                     data[-1] if data else None, "Součet dotací přiznaných v usneseních, podle oblasti programu.",
                     "dotace", ZDROJ_ZAPISY, "Přiznaná částka, ne vyplacená. DPH se u dotací neuplatňuje.",
                     druh=next(iter(druhy), None), s_dph=None, celkem_pocet=len(dotace))


def investice(investice: list[dict]) -> dict | None:
    if not investice:
        return None
    i = investice[-1]
    rezerva = sum(o["schvaleny"] for o in i["oblasti"] if o["oblast"] == "Rezerva")
    rada = [{"klic": o["oblast"], "nazev": o["oblast"], "schvaleny": o["schvaleny"], "hodnota": o["po_zmenach"]}
            for o in sorted(i["oblasti"], key=lambda o: -o["po_zmenach"]) if o["oblast"] != "Rezerva"]
    return _ukazatel("investice-rozpocet", f"Investice v rozpočtu {i['rok']}", rada, "Kč", f"{i['rok']}-01-01", f"{i['rok']}-12-31",
                     "Kapitálové výdaje rozpočtu města po rozpočtových opatřeních, bez rezerv, podle oblastí.",
                     "investice", [ZDROJ_ROZPOCET], i.get("fondy_poznamka"), druh="rozpocet_upraveny", s_dph=None,
                     schvaleny=round(i["schvaleny"] - rezerva, 2), po_zmenach=i["bez_rezervy_po_zmenach"])


def projekty(projekty: list[dict], zasobnik: list[dict]) -> dict:
    pocty = Counter(p.get("faze") for p in projekty)
    odhad = Counter(p.get("faze") for p in projekty if p.get("faze_jistota") != "dolozeno")
    rada = [{"klic": k, "nazev": n, "hodnota": pocty[k], "z_toho_odhad": odhad[k]} for k, n in FAZE.items() if pocty[k]]
    v_zasobniku = sum(1 for z in zasobnik if z["typ"] == "polozka" and z.get("faze") in ("zasobnik", "stavba"))
    namety = sum(1 for z in zasobnik if z["typ"] == "namet")
    return _ukazatel("investicni-akce", "Investiční akce podle fáze", rada, "akcí", None, None,
                     "Karty investičních akcí města a městských společností; fáze se určuje z dokladů (rozpočet, zakázka, smlouva, předání) a je naším odhadem (`z_toho_odhad`), ne potvrzením města.",
                     "projekty", [ZDROJ_ROZPOCET, ZDROJ_EZAK, ZDROJ_REGISTR, ZDROJ_SPRM],
                     "Karty zakládáme postupně; automaticky pro stavební zakázky města od roku 2025 nad 1 mil. Kč.",
                     zasobnik=v_zasobniku, namety=namety)


def sestav(vystup: dict, subjekty: dict) -> list[dict]:
    vysledek = [jednani(vystup["jednani"]), usneseni_oblasti(vystup["usneseni"], vystup["jednani"]),
                smlouvy(vystup["smlouvy"], subjekty), zakazky(vystup["zakazky"], subjekty), dotace(vystup["dotace"]),
                investice(vystup.get("investice") or []), projekty(vystup["projekty"], vystup.get("zasobnik") or [])]
    return [u for u in vysledek if u]
