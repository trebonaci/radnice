"""Jeden běh pipeline: zdroje → kontrola před zápisem → sestavení → atomický zápis.

Postup:
1. zámek proti souběhu (`data/.beh.lock`);
2. každý zdroj (`pipeline/zdroje/*`) stáhne nové / splatné dokumenty a zkontroluje je;
3. změny se provedou jen v dočasné kopii (staging): nový dokument dostane první verzi
   (`pipeline.verze`) a text do `raw/texty/<jednani_id>/v<N>`, změněný otisk novou verzi a nový text;
4. nad kopií proběhne `pipeline.sestav` (citace, částky, osoby, vazby na anotace) a kontrola
   poklesu počtů proti dosavadním datům;
5. teprve když vše projde, zapíše se všechno najednou (dočasné soubory, záloha + deník, `os.replace`,
   při selhání návrat ze zálohy; po pádu uprostřed obnoví stav další běh);
   jinak se běh zastaví, v repozitáři zůstanou poslední správná data a do `data/beh.json`
   se zapíše důvod.

Události (`data/udalosti.json`) mají jednoznačný klíč; opakovaný běh duplicity nevytvoří.
První úspěšný běh události jen uloží (`nove: false`), neoznamuje je.

Kroky smlouvy, zakázky a propojení přibudou jako další zdroje / kroky (zatím nejsou).

Spuštění: python -m pipeline.beh [--dnes YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path

from pipeline import sestav as modul_sestav
from pipeline import verze
from pipeline.zdroje import ChybaZdroje, Dokument, Zdroj
from pipeline.zdroje.zapisy_mesta import ZapisyMesta

KOREN = Path(__file__).resolve().parent.parent
ZAMEK_STARY = 2 * 3600     # zámek starší než 2 hodiny považujeme za zbylý po pádu
POKLES = 0.5               # výstup pod touto částí dosavadního počtu = podezřelý pokles
VYSTUPY = ("jednani", "usneseni", "hlasovani", "zakazky", "smlouvy")


class ZamekObsazen(Exception):
    pass


@contextmanager
def zamek(koren: Path, ted: float | None = None):
    cesta = koren / "data" / ".beh.lock"
    cesta.parent.mkdir(exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(cesta, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            stari = (ted or time.time()) - cesta.stat().st_mtime
            if stari < ZAMEK_STARY:
                raise ZamekObsazen(f"běží jiný běh (zámek {cesta.name} je starý {int(stari)} s)") from None
            cesta.unlink(missing_ok=True)       # zbylý po pádu
    else:
        raise ZamekObsazen("zámek se nepodařilo získat")
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        cesta.unlink(missing_ok=True)


DENIK = ".beh-zapis.json"
ZALOHY = ".beh-zaloha"


def _denik_adresar(soubory: dict[Path, str], koren: Path | None) -> Path:
    return (koren / "data") if koren is not None else next(iter(soubory)).parent


class NeuplnaZaloha(RuntimeError):
    """Deník existuje, ale některá záloha chybí – stav nejde bezpečně obnovit, rozhoduje člověk."""


def obnov_ze_zalohy(adresar: Path) -> bool:
    """Když v `adresar` zůstal deník nedokončeného zápisu (pád uprostřed nahrazování),
    vrátí všechny cílové soubory do stavu před zápisem. Lze bezpečně opakovat.
    Vrací True, pokud se obnovovalo.

    Pořadí je podstatné: deník je značka „transakce nedokončena“. Zálohy se mažou až po
    smazání deníku, takže deník nikdy neexistuje vedle neúplných záloh. Když přesto některá
    záloha chybí, obnova se nespustí vůbec (vyhodí `NeuplnaZaloha`) – částečná obnova by
    vytvořila směs starých a nových dat."""
    denik = adresar / DENIK
    zalohy = adresar / ZALOHY
    if not denik.exists():
        # osiřelé zálohy po pádu během úklidu dokončeného zápisu: zápis platí, jen uklidit
        shutil.rmtree(zalohy, ignore_errors=True)
        return False
    zaznam = json.loads(denik.read_text(encoding="utf-8"))
    chybi = [p["zaloha"] for p in zaznam["soubory"] if p["zaloha"] is not None and not Path(p["zaloha"]).exists()]
    if chybi:
        raise NeuplnaZaloha(f"deník {denik} odkazuje na chybějící zálohy: {chybi}")
    for polozka in zaznam["soubory"]:
        cil = Path(polozka["cil"])
        if polozka["zaloha"] is not None:
            shutil.copy2(Path(polozka["zaloha"]), cil)
        else:
            cil.unlink(missing_ok=True)          # soubor předtím neexistoval
        cil.with_name(cil.name + ".tmp").unlink(missing_ok=True)
    denik.unlink()                                # nejdřív zrušit značku nedokončené transakce …
    shutil.rmtree(zalohy, ignore_errors=True)     # … pak teprve zálohy
    return True


def zapis_atomicky(soubory: dict[Path, str], koren: Path | None = None) -> None:
    """Celý nebo nic:
    1. všechny soubory se zapíšou vedle cíle jako `.tmp` (při chybě se smažou, cíle beze změny);
    2. původní obsah cílů se zazálohuje a zapíše se deník (`data/.beh-zapis.json`);
    3. cíle se nahradí; když nahrazení selže, všechny cíle se vrátí ze zálohy;
    4. po úspěchu se nejdřív smaže deník (tím je zápis dokončen) a teprve pak zálohy.
    Když proces spadne mezi 2. a smazáním deníku, deník zůstane a `obnov_ze_zalohy` stav vrátí na začátku
    dalšího běhu; po smazání deníku platí nová data a osiřelé zálohy se jen uklidí."""
    tmp: list[tuple[Path, Path]] = []
    try:
        for cil, obsah in soubory.items():
            cil.parent.mkdir(parents=True, exist_ok=True)
            t = cil.with_name(cil.name + ".tmp")
            t.write_text(obsah, encoding="utf-8")
            tmp.append((t, cil))
    except BaseException:
        for t, _ in tmp:
            t.unlink(missing_ok=True)
        raise

    adresar = _denik_adresar(soubory, koren)
    adresar.mkdir(parents=True, exist_ok=True)
    denik = adresar / DENIK
    if denik.exists():
        for t, _ in tmp:
            t.unlink(missing_ok=True)
        raise NeuplnaZaloha(f"nedokončený předchozí zápis ({denik}); nejdřív obnov stav (obnov_ze_zalohy)")
    zalohy = adresar / ZALOHY
    shutil.rmtree(zalohy, ignore_errors=True)
    zalohy.mkdir()
    polozky = []
    for i, (_, cil) in enumerate(tmp):
        zaloha = None
        if cil.exists():
            zaloha = zalohy / f"{i}-{cil.name}"
            shutil.copy2(cil, zaloha)
        polozky.append({"cil": str(cil), "zaloha": str(zaloha) if zaloha else None})
    with open(denik, "w", encoding="utf-8") as f:
        json.dump({"soubory": polozky}, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())

    try:
        for t, cil in tmp:
            os.replace(t, cil)
    except BaseException:
        obnov_ze_zalohy(adresar)
        raise
    denik.unlink()                                # dokončení transakce (commit) …
    shutil.rmtree(zalohy, ignore_errors=True)     # … teprve potom úklid záloh


def _nacti_json(cesta: Path, vychozi):
    return json.loads(cesta.read_text(encoding="utf-8")) if cesta.exists() else vychozi


def _novy_zaznam(d: Dokument, dnes: date) -> dict:
    return {
        "dokument_id": d.dokument_id, "typ": d.typ, "jednani_id": d.jednani_id, "nazev": d.nazev,
        "url": d.url, "stranka_zdroje": d.stranka_zdroje, "vyveseno": d.vyveseno,
        "stazeno": dnes.isoformat(), "sha256": d.sha256, "bytes": d.bytes,
        "pocet_stran": len(d.strany or []), "textova_vrstva": True,
        "extrakce": "pdftotext -layout (poppler), po stranách",
    }


def _udalost(klic: str, typ: str, d: Dokument, dnes: date, text: str, cislo: int, nove: bool) -> dict:
    return {"klic": klic, "typ": typ, "dokument_id": d.dokument_id, "verze": cislo,
            "zjisteno": dnes.isoformat(), "text": text, "nove": nove}


def aplikuj(manifest: list[dict], dokumenty: list[Dokument], dnes: date, stage: Path,
            rel_soubory: dict[str, str], prvni_beh: bool) -> list[dict]:
    """Zapíše výsledek stažení do `manifest` (na místě) a texty do `stage`. Vrací nové události.
    Nový záznam dostane první verzi dřív, než poběží sestavení; změněný otisk novou verzi + nový text."""
    udalosti = []
    podle_id = {z["dokument_id"]: z for z in manifest}

    def uloz_texty(rel: str, strany: list[str]):
        for i, t in enumerate(strany, 1):
            cesta = f"{rel}/strana-{i}.txt"
            (stage / cesta).parent.mkdir(parents=True, exist_ok=True)
            (stage / cesta).write_text(t, encoding="utf-8")
            rel_soubory[cesta] = t

    for d in dokumenty:
        z = podle_id.get(d.dokument_id)
        if z is None:
            rel = f"raw/texty/{d.jednani_id}/v1"
            z = _novy_zaznam(d, dnes)
            z["vyveseno"] = d.vyveseno
            verze.doplni_historii(z, texty=rel)
            manifest.append(z)
            uloz_texty(rel, d.strany or [])
            udalosti.append(_udalost(f"novy_dokument:{d.dokument_id}", "novy_dokument", d, dnes,
                                     f"Nový dokument: {d.nazev}", 1, not prvni_beh))
            continue
        verze.doplni_historii(z)
        rel = f"raw/texty/{d.jednani_id}/v{len(z['verze']) + 1}"
        zmena = d.sha256 != z["sha256"]
        if verze.zaznamenej_kontrolu(z, d.sha256, dnes, bytes_=d.bytes, texty=rel if zmena else None):
            uloz_texty(rel, d.strany or [])
            z["pocet_stran"] = len(d.strany or [])
            cislo = z["verze"][-1]["cislo"]
            udalosti.append(_udalost(f"nova_verze:{d.dokument_id}:{cislo}", "nova_verze", d, dnes,
                                     f"Změněný dokument (verze {cislo}): {d.nazev}", cislo, not prvni_beh))
        if z["url"] != d.url:
            z["url"] = d.url
    return udalosti


def kontrola_poklesu(vystup: dict, koren: Path) -> list[str]:
    chyby = []
    for nazev in VYSTUPY:
        dosud = len(_nacti_json(koren / "data" / f"{nazev}.json", []))
        ted = len(vystup.get(nazev, []))
        if dosud >= 2 and ted < dosud * POKLES:
            chyby.append(f"prudký pokles počtu ({nazev}): {ted} proti dosavadním {dosud}")
        elif ted < dosud:
            chyby.append(f"počet ({nazev}) klesl z {dosud} na {ted}; zkontrolovat ručně")
    return chyby


def spust(koren: Path = KOREN, zdroje: list[Zdroj] | None = None, dnes: date | None = None,
          ted: datetime | None = None) -> int:
    """Vrací 0 = hotovo, 1 = zastaveno kontrolou / chybou (data beze změny), 2 = zámek obsazen."""
    zdroje = zdroje if zdroje is not None else [ZapisyMesta()]
    ted = ted or datetime.now(timezone.utc)
    dnes = dnes or ted.date()
    try:
        with zamek(koren):
            return _beh(koren, zdroje, dnes, ted)
    except ZamekObsazen as e:
        print("Běh přeskočen:", e, file=sys.stderr)
        return 2


def _beh(koren: Path, zdroje: list[Zdroj], dnes: date, ted: datetime) -> int:
    cesta_beh = koren / "data" / "beh.json"
    # obnova je první krok: po pádu může být beh.json poškozený, a ten se čte až po ní
    try:
        obnoveno = obnov_ze_zalohy(koren / "data")
    except NeuplnaZaloha as e:
        # nic nezapisovat (ani beh.json): deník a zálohy jsou důkaz pro ruční řešení
        print("CHYBA:", e, "– stav je nutné vyřešit ručně, běh nic nezměnil", file=sys.stderr)
        return 1
    upozorneni = []
    if obnoveno:
        upozorneni.append("předchozí běh spadl uprostřed zápisu; stav byl obnoven ze zálohy")
    try:
        predchozi = _nacti_json(cesta_beh, {})
        if not isinstance(predchozi, dict):
            raise ValueError("beh.json není objekt")
    except (ValueError, OSError):      # JSONDecodeError i UnicodeDecodeError jsou ValueError
        predchozi = {}
        upozorneni.append("předchozí záznam běhu (data/beh.json) byl nečitelný; pokračuji bez něj")
    zaznam = {"zacatek": ted.isoformat(timespec="seconds"), "stav": "bezi", "zdroje": [], "chyby": [],
              "upozorneni": upozorneni, "pocty": None, "posledni_uspesny": predchozi.get("posledni_uspesny")}
    prvni_beh = not predchozi.get("posledni_uspesny")
    manifest_cesta = koren / "raw" / "manifest.json"
    manifest = copy.deepcopy(_nacti_json(manifest_cesta, []))

    def zastav(chyby: list[str]) -> int:
        zaznam.update(stav="zastaveno", chyby=zaznam["chyby"] + chyby,
                      konec=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        zapis_atomicky({cesta_beh: modul_sestav.serializuj(zaznam)}, koren)
        for c in zaznam["chyby"]:
            print("CHYBA:", c, file=sys.stderr)
        return 1

    # 1. zdroje: stažení + kontrola před zápisem
    stazene: list[Dokument] = []
    for zdroj in zdroje:
        try:
            stazeno = zdroj.stahni(manifest, dnes)
        except ChybaZdroje as e:
            zaznam["zdroje"].append({"nazev": zdroj.nazev, "stav": "nedostupny"})
            return zastav([f"{zdroj.nazev}: zdroj nedostupný: {e}"])
        chyby = zdroj.zkontroluj(stazeno, manifest)
        zaznam["zdroje"].append({"nazev": zdroj.nazev, "stav": "chyba" if chyby else "ok",
                                 "odkazu": stazeno.odkazu, "stazeno": len(stazeno.dokumenty)})
        zaznam["upozorneni"] += stazeno.upozorneni
        if chyby:
            return zastav(chyby)
        stazene += stazeno.dokumenty

    # 2. staging: změny a sestavení nad kopií, ostrá data se zatím nedotknou
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp)
        for podadresar in ("raw/texty", "raw/ezak", "raw/smlouvy", "anotace", "config"):
            if (koren / podadresar).exists():
                shutil.copytree(koren / podadresar, stage / podadresar)
        (stage / "raw").mkdir(exist_ok=True)
        rel_soubory: dict[str, str] = {}
        try:
            udalosti_nove = aplikuj(manifest, stazene, dnes, stage, rel_soubory, prvni_beh)
        except ChybaZdroje as e:
            return zastav([str(e)])
        (stage / "raw" / "manifest.json").write_text(modul_sestav.serializuj(manifest), encoding="utf-8")
        vystup, chyby = modul_sestav.sestav(stage)
        chyby += kontrola_poklesu(vystup, koren)
    if chyby:
        return zastav(chyby)

    # 3. všechno prošlo: zapsat najednou
    udalosti = _nacti_json(koren / "data" / "udalosti.json", [])
    klice = {u["klic"] for u in udalosti}
    udalosti += [u for u in udalosti_nove if u["klic"] not in klice]
    zaznam.update(stav="ok", pocty={n: len(vystup[n]) for n in VYSTUPY},
                  nove_dokumenty=sum(u["typ"] == "novy_dokument" for u in udalosti_nove),
                  nove_verze=sum(u["typ"] == "nova_verze" for u in udalosti_nove),
                  konec=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    zaznam["posledni_uspesny"] = zaznam["konec"]
    soubory = {koren / rel: t for rel, t in rel_soubory.items()}
    soubory |= {koren / "data" / f"{n}.json": modul_sestav.serializuj(vystup[n]) for n in VYSTUPY}
    soubory[koren / "data" / "udalosti.json"] = modul_sestav.serializuj(udalosti)
    soubory[manifest_cesta] = modul_sestav.serializuj(manifest)
    soubory[cesta_beh] = modul_sestav.serializuj(zaznam)       # nakonec
    zapis_atomicky(soubory, koren)
    print(f"běh hotov: {zaznam['pocty']}, nové dokumenty {zaznam['nove_dokumenty']}, nové verze {zaznam['nove_verze']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dnes", default=None, help="datum YYYY-MM-DD (pro testy)")
    args = p.parse_args(argv)
    return spust(dnes=date.fromisoformat(args.dnes) if args.dnes else None)


if __name__ == "__main__":
    sys.exit(main())
