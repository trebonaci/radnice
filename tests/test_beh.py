"""Testy běhu pipeline na uložených vzorcích: texty zápisů z raw/texty, vzorek HTML ze stránek města,
výpadek zdroje, chybová stránka místo PDF, prázdná stránka, zámek, atomický zápis."""
import copy
import hashlib
import json
import os
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from pipeline import beh, verze
from pipeline.zdroje import ChybaZdroje
from conftest import jen_pilot
from pipeline.zdroje.zapisy_mesta import STRANKY, ZapisyMesta, datum_zapisu, parsuj_stranku

KOREN = Path(__file__).resolve().parent.parent
VZORKY = Path(__file__).resolve().parent / "vzorky"
URL_RM, URL_ZM = STRANKY[0][2], STRANKY[1][2]
URL_RM_2022, URL_ZM_2022 = STRANKY[2][2], STRANKY[3][2]
PDF = {  # dokument_id → (URL, obsah „PDF“ – jen hlavička pro test, text bereme z uložených stran)
    "rm-2026-11-04": ("https://www.mesto-trebon.cz/uploads/news/id15223/Z-1-26-11-04-A.pdf", b"%PDF-1.7 vzorek RM"),
    "zm-2026-11-02": ("https://www.mesto-trebon.cz/uploads/news/id15220/Z-01-26-11-02.pdf", b"%PDF-1.7 vzorek ZM"),
}
DNES = date(2026, 11, 19)
TED = datetime(2026, 11, 19, 6, 0, tzinfo=timezone.utc)


def strany(jednani_id):
    soubory = sorted((KOREN / "raw" / "texty" / jednani_id).glob("strana-*.txt"), key=lambda p: int(p.stem.split("-")[1]))
    return [p.read_text(encoding="utf-8") for p in soubory]


class Web:
    """Falešný web: URL → obsah; extrakce vrací uložené strany podle obsahu PDF."""
    def __init__(self):
        self.stranky = {URL_RM: (VZORKY / "zapisy_rm.html").read_bytes(), URL_ZM: (VZORKY / "zapisy_zm.html").read_bytes(),
                        URL_RM_2022: b"<html></html>", URL_ZM_2022: b"<html></html>"}
        self.pdf = {url: obsah for url, obsah in PDF.values()}
        self.texty = {obsah: strany(j) for j, (_, obsah) in PDF.items()}
        self.vypadek = False
        self.stazeno = []

    def ziskej(self, url):
        if self.vypadek:
            raise ChybaZdroje(f"{url}: HTTP 503")
        self.stazeno.append(url)
        return self.stranky[url] if url in self.stranky else self.pdf[url]

    def extrahuj(self, obsah):
        return self.texty[obsah]

    def zdroj(self):
        return ZapisyMesta(ziskej=self.ziskej, extrahuj=self.extrahuj, pauza=0)


@pytest.fixture
def koren(tmp_path):
    for d in ("raw/texty", "anotace", "config", "data"):
        shutil.copytree(KOREN / d, tmp_path / d)
    shutil.copy(KOREN / "raw" / "manifest.json", tmp_path / "raw" / "manifest.json")
    jen_pilot(tmp_path)
    # otisky v manifestu odpovídají našim vzorkům PDF
    manifest = json.loads((tmp_path / "raw" / "manifest.json").read_text(encoding="utf-8"))
    for z in manifest:
        sha = hashlib.sha256(PDF[z["jednani_id"]][1]).hexdigest()
        z["sha256"] = z["verze"][0]["sha256"] = sha
    (tmp_path / "raw" / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    # data odpovídají tomuto manifestu
    assert beh.modul_sestav.sestav(tmp_path)[1] == []
    vystup, _ = beh.modul_sestav.sestav(tmp_path)
    for n, o in vystup.items():
        (tmp_path / "data" / f"{n}.json").write_text(beh.modul_sestav.serializuj(o), encoding="utf-8")
    return tmp_path


def spust(koren, web, **kw):
    return beh.spust(koren, [web.zdroj()], dnes=kw.get("dnes", DNES), ted=TED)


def cti(koren, rel):
    return (koren / rel).read_text(encoding="utf-8")


def stav(koren):
    return {p.relative_to(koren).as_posix(): p.read_bytes() for p in sorted(koren.rglob("*")) if p.is_file()}


def zaloha_dat(koren):
    return {r: b for r, b in stav(koren).items() if r.startswith(("data/", "raw/")) and r != "data/beh.json"}


def test_parsuje_vzorek_stranky():
    dok, upoz = parsuj_stranku((VZORKY / "zapisy_rm.html").read_text(encoding="utf-8"), URL_RM, "zapis_rada", "rm")
    assert [d.dokument_id for d in dok] == ["zapis-rm-2026-11-04"] and upoz == []
    assert dok[0].url == PDF["rm-2026-11-04"][0]
    assert datum_zapisu("", "https://x/uploads/news/id1/Z-01-26-11-02.pdf") == "2026-11-02"


def test_obdobi_2022_2026_jen_od_zari_2026(koren):
    """Ze stránek minulého období se berou jen jednání od 1. 9. 2026 (#38)."""
    web = Web()
    web.stranky[URL_RM_2022] = (
        '<a href="/uploads/news/id15000/Z-109-26-08-26-A.pdf">Z-109-26-08-26-A.pdf</a>'
        '<a href="/uploads/news/id15037/Z-110-26-09-09-A.pdf">Z-110-26-09-09-A.pdf</a>').encode()
    web.stranky[URL_ZM_2022] = b'<a href="/uploads/news/id15066/Z-31-26-09-21-A.pdf">Z-31-26-09-21-A.pdf</a>'
    for url in ("https://www.mesto-trebon.cz/uploads/news/id15037/Z-110-26-09-09-A.pdf",
                "https://www.mesto-trebon.cz/uploads/news/id15066/Z-31-26-09-21-A.pdf"):
        web.pdf[url] = PDF["rm-2026-11-04"][1]
    stazeno = web.zdroj().stahni(json.loads(cti(koren, "raw/manifest.json")), DNES)
    jednani = {d.jednani_id for d in stazeno.dokumenty}
    assert {"rm-2026-09-09", "zm-2026-09-21"} <= jednani and "rm-2026-08-26" not in jednani
    assert not any("Z-109" in u for u in web.stazeno)


def test_beh_beze_zmeny_nic_nemeni_a_posune_plan(koren):
    web = Web()
    pred = copy.deepcopy(json.loads(cti(koren, "raw/manifest.json")))
    assert spust(koren, web) == 0
    po = json.loads(cti(koren, "raw/manifest.json"))
    assert [len(z["verze"]) for z in po] == [1, 1]
    assert po[0]["posledni_kontrola"] == "2026-11-19" and po[0]["posledni_kontrola"] != pred[0]["posledni_kontrola"]
    assert json.loads(cti(koren, "data/udalosti.json")) == []
    b = json.loads(cti(koren, "data/beh.json"))
    assert b["stav"] == "ok" and b["pocty"]["usneseni"] == 20 and b["posledni_uspesny"]


def test_nesplatny_dokument_se_nestahuje(koren):
    web = Web()
    assert spust(koren, web, dnes=date(2026, 11, 18)) == 0
    assert [u for u in web.stazeno if u.endswith(".pdf")] == []


def test_novy_dokument_dostane_prvni_verzi_pred_sestavenim_a_prvni_beh_neoznamuje(koren):
    web = Web()
    novy = "https://www.mesto-trebon.cz/uploads/news/id99999/Z-2-26-11-18.pdf"
    web.stranky[URL_RM] = web.stranky[URL_RM].replace(
        b"</ul>", '<li><a href="/uploads/news/id99999/Z-2-26-11-18.pdf">Zápis z 2. jednání Rady města Třeboně ze dne 18.11.2026</a></li></ul>'.encode())
    web.pdf[novy] = b"%PDF-1.7 novy"
    web.texty[b"%PDF-1.7 novy"] = ["Zápis\n" + "Nějaký text zápisu. " * 20]
    assert spust(koren, web) == 0
    z = {x["dokument_id"]: x for x in json.loads(cti(koren, "raw/manifest.json"))}["zapis-rm-2026-11-18"]
    assert z["verze"][0]["cislo"] == 1 and z["verze"][0]["texty"] == "raw/texty/rm-2026-11-18/v1"
    assert (koren / "raw/texty/rm-2026-11-18/v1/strana-1.txt").exists()
    assert verze.zkontroluj(json.loads(cti(koren, "raw/manifest.json"))) == []
    udalosti = json.loads(cti(koren, "data/udalosti.json"))
    assert [(u["klic"], u["nove"]) for u in udalosti] == [("novy_dokument:zapis-rm-2026-11-18", False)]
    # opakovaný běh: žádné duplicity
    assert spust(koren, web, dnes=date(2026, 11, 20)) == 0
    assert len(json.loads(cti(koren, "data/udalosti.json"))) == 1


def test_zmeneny_otisk_ulozi_novy_text_a_vystupy_se_prepocitaji(koren):
    web = Web()
    assert spust(koren, web) == 0                      # první běh uloží historii
    nove_pdf = b"%PDF-1.7 vzorek RM opraveny"
    web.pdf[PDF["rm-2026-11-04"][0]] = nove_pdf
    web.texty[nove_pdf] = strany("rm-2026-11-04")[:-1] + [strany("rm-2026-11-04")[-1] + "\nOpraveno 20. 11. 2026\n"]
    assert spust(koren, web, dnes=date(2026, 11, 20)) == 0
    z = {x["jednani_id"]: x for x in json.loads(cti(koren, "raw/manifest.json"))}["rm-2026-11-04"]
    assert [v["cislo"] for v in z["verze"]] == [1, 2]
    assert z["verze"][1]["texty"] == "raw/texty/rm-2026-11-04/v2"
    assert z["sha256"] == hashlib.sha256(nove_pdf).hexdigest()
    assert "Opraveno 20. 11. 2026" in cti(koren, "raw/texty/rm-2026-11-04/v2/strana-4.txt")
    assert "Opraveno" not in cti(koren, "raw/texty/rm-2026-11-04/strana-4.txt")   # stará verze zůstává
    jednani = {j["id"]: j for j in json.loads(cti(koren, "data/jednani.json"))}
    assert jednani["rm-2026-11-04"]["dokument"]["sha256"] == z["sha256"]
    udalosti = json.loads(cti(koren, "data/udalosti.json"))
    assert [(u["klic"], u["nove"]) for u in udalosti] == [("nova_verze:zapis-rm-2026-11-04:2", True)]
    assert spust(koren, web, dnes=date(2026, 11, 21)) == 0       # znovu: žádná další verze ani událost
    assert len(json.loads(cti(koren, "data/udalosti.json"))) == 1


def test_zmeneny_text_rozbije_citace_beh_se_zastavi_a_data_zustanou(koren):
    web = Web()
    nove_pdf = b"%PDF-1.7 rozbity"
    web.pdf[PDF["rm-2026-11-04"][0]] = nove_pdf
    web.texty[nove_pdf] = [s.replace("Usnesení RM č.", "Usnesení RMX č.") for s in strany("rm-2026-11-04")]
    pred = zaloha_dat(koren)
    assert spust(koren, web) == 1
    assert zaloha_dat(koren) == pred
    b = json.loads(cti(koren, "data/beh.json"))
    assert b["stav"] == "zastaveno" and any("citace nenalezena" in c or "neznámý" in c or "anotac" in c for c in b["chyby"])
    assert not (koren / "raw/texty/rm-2026-11-04/v2").exists()


def test_vypadek_zdroje_zachova_posledni_data(koren):
    web = Web()
    web.vypadek = True
    pred = zaloha_dat(koren)
    assert spust(koren, web) == 1
    assert zaloha_dat(koren) == pred
    b = json.loads(cti(koren, "data/beh.json"))
    assert b["stav"] == "zastaveno" and "nedostupný" in b["chyby"][0]


def test_prazdna_stranka_zastavi_beh(koren):
    web = Web()
    web.stranky[URL_RM] = b"<html><body>Nic</body></html>"
    web.stranky[URL_ZM] = b"<html><body>Nic</body></html>"
    pred = zaloha_dat(koren)
    assert spust(koren, web) == 1
    assert zaloha_dat(koren) == pred
    assert "žádné zápisy" in json.loads(cti(koren, "data/beh.json"))["chyby"][0]


def test_prudky_pokles_nabidky_zastavi_beh(koren):
    web = Web()
    web.stranky[URL_ZM] = b"<html></html>"
    web.stranky[URL_RM] = b"<html></html>"
    # jediný odkaz z dvou dosavadních dokumentů by byl 50 %; úplně prázdná nabídka je chyba o krok dřív
    assert spust(koren, web) == 1


def test_chybova_stranka_misto_pdf(koren):
    web = Web()
    web.pdf[PDF["rm-2026-11-04"][0]] = b"<html>Chyba 500</html>"
    pred = zaloha_dat(koren)
    assert spust(koren, web) == 1
    assert zaloha_dat(koren) == pred
    assert "není PDF" in json.loads(cti(koren, "data/beh.json"))["chyby"][0]


def test_pdf_bez_textove_vrstvy(koren):
    web = Web()
    sken = b"%PDF-1.7 sken"
    web.pdf[PDF["zm-2026-11-02"][0]] = sken
    web.texty[sken] = ["", ""]
    assert spust(koren, web) == 1
    assert any("textovou vrstvu" in c for c in json.loads(cti(koren, "data/beh.json"))["chyby"])


def test_pokles_poctu_ve_vystupu(koren):
    vystup = {"jednani": [1], "usneseni": [1] * 5, "hlasovani": [1] * 26}
    assert any("pokles" in c for c in beh.kontrola_poklesu(vystup, koren))
    plny = {n: json.loads(cti(koren, f"data/{n}.json")) for n in beh.VYSTUPY}
    assert beh.kontrola_poklesu(plny, koren) == []


def test_zamek_proti_soubehu(koren):
    web = Web()
    with beh.zamek(koren):
        assert spust(koren, web) == 2
        assert web.stazeno == []
    assert not (koren / "data" / ".beh.lock").exists()
    assert spust(koren, web) == 0


def test_stary_zamek_po_padu_se_prepise(koren):
    lock = koren / "data" / ".beh.lock"
    lock.write_text("1")
    import os
    stare = lock.stat().st_mtime - beh.ZAMEK_STARY - 10
    os.utime(lock, (stare, stare))
    assert spust(koren, Web()) == 0 and not lock.exists()


def test_zapis_atomicky_pri_chybe_nezapise_nic(tmp_path):
    (tmp_path / "a.json").write_text("stare", encoding="utf-8")
    blokace = tmp_path / "soubor"
    blokace.write_text("x", encoding="utf-8")
    with pytest.raises(OSError):
        beh.zapis_atomicky({tmp_path / "a.json": "nove", blokace / "b.json": "nove"})
    assert (tmp_path / "a.json").read_text(encoding="utf-8") == "stare"
    assert not list(tmp_path.glob("*.tmp"))


def _tri_soubory(tmp_path):
    a, b, c = tmp_path / "data" / "a.json", tmp_path / "data" / "b.json", tmp_path / "data" / "c.json"
    a.parent.mkdir(parents=True)
    a.write_text("stare-a", encoding="utf-8")
    b.write_text("stare-b", encoding="utf-8")
    return a, b, c                                  # c předtím neexistuje


def test_selhani_druheho_replace_vrati_vse(tmp_path, monkeypatch):
    """Regrese (review Codexu k PR #24): selhání uprostřed nahrazování nesmí nechat mix nových a starých souborů."""
    a, b, c = _tri_soubory(tmp_path)
    puvodni = os.replace
    volani = {"n": 0}

    def replace(src, dst):
        volani["n"] += 1
        if volani["n"] == 2:
            raise OSError("simulovaná chyba disku")
        return puvodni(src, dst)

    monkeypatch.setattr(beh.os, "replace", replace)
    with pytest.raises(OSError):
        beh.zapis_atomicky({a: "nove-a", b: "nove-b", c: "nove-c"}, tmp_path)
    assert a.read_text(encoding="utf-8") == "stare-a"
    assert b.read_text(encoding="utf-8") == "stare-b"
    assert not c.exists()
    assert not (tmp_path / "data" / beh.DENIK).exists()
    assert not (tmp_path / "data" / beh.ZALOHY).exists()
    assert not list((tmp_path / "data").glob("*.tmp"))


def test_pad_uprostred_zapisu_obnovi_dalsi_beh(tmp_path, monkeypatch):
    """Simulovaný pád procesu po nahrazení části souborů: deník a zálohy zůstanou, obnova vrátí původní stav."""
    a, b, c = _tri_soubory(tmp_path)
    puvodni = os.replace
    volani = {"n": 0}

    class Pad(BaseException):
        pass

    def replace(src, dst):
        volani["n"] += 1
        if volani["n"] == 2:
            raise Pad()
        return puvodni(src, dst)

    monkeypatch.setattr(beh.os, "replace", replace)
    monkeypatch.setattr(beh, "obnov_ze_zalohy", lambda adresar: False)   # pád = obnova neproběhne
    with pytest.raises(Pad):
        beh.zapis_atomicky({a: "nove-a", b: "nove-b", c: "nove-c"}, tmp_path)
    monkeypatch.undo()
    assert a.read_text(encoding="utf-8") == "nove-a"          # mix po pádu
    assert (tmp_path / "data" / beh.DENIK).exists()
    assert beh.obnov_ze_zalohy(tmp_path / "data") is True
    assert a.read_text(encoding="utf-8") == "stare-a"
    assert b.read_text(encoding="utf-8") == "stare-b"
    assert not c.exists()
    assert not (tmp_path / "data" / beh.DENIK).exists()
    assert beh.obnov_ze_zalohy(tmp_path / "data") is False   # opakování je bezpečné


def test_uspesny_zapis_uklidi_denik_a_zalohy(tmp_path):
    a, b, c = _tri_soubory(tmp_path)
    beh.zapis_atomicky({a: "nove-a", b: "nove-b", c: "nove-c"}, tmp_path)
    assert [p.read_text(encoding="utf-8") for p in (a, b, c)] == ["nove-a", "nove-b", "nove-c"]
    assert not (tmp_path / "data" / beh.DENIK).exists()
    assert not (tmp_path / "data" / beh.ZALOHY).exists()


def test_beh_po_padu_obnovi_stav_a_upozorni(koren):
    """Zbylý deník z předchozího pádu: běh nejdřív vrátí data ze zálohy a zapíše upozornění."""
    usneseni = koren / "data" / "usneseni.json"
    puvodni = usneseni.read_text(encoding="utf-8")
    zalohy = koren / "data" / beh.ZALOHY
    zalohy.mkdir()
    (zalohy / "0-usneseni.json").write_text(puvodni, encoding="utf-8")
    usneseni.write_text("rozbito pádem", encoding="utf-8")
    (koren / "data" / beh.DENIK).write_text(json.dumps(
        {"soubory": [{"cil": str(usneseni), "zaloha": str(zalohy / "0-usneseni.json")}]}), encoding="utf-8")
    assert spust(koren, Web()) == 0
    assert usneseni.read_text(encoding="utf-8") == puvodni
    assert any("spadl uprostřed zápisu" in u for u in json.loads(cti(koren, "data/beh.json"))["upozorneni"])
    assert not (koren / "data" / beh.DENIK).exists()


def test_denik_a_poskozeny_beh_json_obnova_probehne_a_beh_dobehne(koren):
    """Pád rozbil i beh.json: obnova z deníku musí proběhnout dřív, než se beh.json čte."""
    beh_json = koren / "data" / "beh.json"
    puvodni_beh = beh_json.read_text(encoding="utf-8") if beh_json.exists() else None
    usneseni = koren / "data" / "usneseni.json"
    puvodni = usneseni.read_text(encoding="utf-8")
    zalohy = koren / "data" / beh.ZALOHY
    zalohy.mkdir()
    (zalohy / "0-usneseni.json").write_text(puvodni, encoding="utf-8")
    (zalohy / "1-beh.json").write_text(puvodni_beh or "{}", encoding="utf-8")
    usneseni.write_text("rozbito pádem", encoding="utf-8")
    beh_json.write_text('{"zacatek": "2026-11-1', encoding="utf-8")       # neúplný JSON
    (koren / "data" / beh.DENIK).write_text(json.dumps({"soubory": [
        {"cil": str(usneseni), "zaloha": str(zalohy / "0-usneseni.json")},
        {"cil": str(beh_json), "zaloha": str(zalohy / "1-beh.json")}]}), encoding="utf-8")
    assert spust(koren, Web()) == 0
    assert usneseni.read_text(encoding="utf-8") == puvodni
    b = json.loads(cti(koren, "data/beh.json"))
    assert b["stav"] == "ok"
    assert any("spadl uprostřed zápisu" in u for u in b["upozorneni"])
    assert not (koren / "data" / beh.DENIK).exists()


def test_poskozeny_beh_json_bez_deniku_upozorni_a_beh_dobehne(koren):
    (koren / "data" / "beh.json").write_text("{nesmysl", encoding="utf-8")
    assert spust(koren, Web()) == 0
    b = json.loads(cti(koren, "data/beh.json"))
    assert b["stav"] == "ok"
    assert any("nečitelný" in u for u in b["upozorneni"])


def test_pad_pri_mazani_zaloh_nevyvola_obnovu(tmp_path, monkeypatch):
    """Regrese (2. review Codexu): po dokončení zápisu (smazaný deník) pád během mazání záloh
    nesmí vést k částečné obnově – nová data platí, osiřelé zálohy se jen uklidí."""
    a, b, c = _tri_soubory(tmp_path)

    class Pad(BaseException):
        pass

    puvodni_rmtree = shutil.rmtree
    volani = {"n": 0}

    def rmtree(*args, **kwargs):
        volani["n"] += 1
        if volani["n"] == 2:                  # 1. volání = úklid před zápisem, 2. = úklid po dokončení
            raise Pad()
        return puvodni_rmtree(*args, **kwargs)

    monkeypatch.setattr(beh.shutil, "rmtree", rmtree)
    with pytest.raises(Pad):
        beh.zapis_atomicky({a: "nove-a", b: "nove-b", c: "nove-c"}, tmp_path)
    monkeypatch.undo()
    assert not (tmp_path / "data" / beh.DENIK).exists()           # zápis byl dokončen
    assert (tmp_path / "data" / beh.ZALOHY).exists()              # zálohy osiřely
    (next((tmp_path / "data" / beh.ZALOHY).iterdir())).unlink()   # a jsou neúplné
    assert beh.obnov_ze_zalohy(tmp_path / "data") is False
    assert [p.read_text(encoding="utf-8") for p in (a, b, c)] == ["nove-a", "nove-b", "nove-c"]
    assert not (tmp_path / "data" / beh.ZALOHY).exists()


def test_denik_s_chybejici_zalohou_obnovu_odmitne(tmp_path):
    a, b, c = _tri_soubory(tmp_path)
    data = tmp_path / "data"
    (data / beh.DENIK).write_text(json.dumps({"soubory": [
        {"cil": str(a), "zaloha": str(data / beh.ZALOHY / "0-a.json")},
        {"cil": str(c), "zaloha": None}]}), encoding="utf-8")
    c.write_text("nove-c", encoding="utf-8")
    with pytest.raises(beh.NeuplnaZaloha):
        beh.obnov_ze_zalohy(data)
    assert c.read_text(encoding="utf-8") == "nove-c"              # nic se nezměnilo
    assert (data / beh.DENIK).exists()
    with pytest.raises(beh.NeuplnaZaloha):                        # ani nový zápis nepřepíše důkazy
        beh.zapis_atomicky({a: "x"}, tmp_path)
    assert a.read_text(encoding="utf-8") == "stare-a"


def test_beh_s_neuplnou_zalohou_nic_nezmeni(koren):
    data = koren / "data"
    (data / beh.DENIK).write_text(json.dumps({"soubory": [
        {"cil": str(data / "usneseni.json"), "zaloha": str(data / beh.ZALOHY / "chybi.json")}]}), encoding="utf-8")
    pred = stav(koren)
    assert spust(koren, Web()) == 1
    assert stav(koren) == pred


def test_beh_vidi_zakazky_z_ezak(koren):
    """Běh sestavuje ve zkušebním adresáři; musí tam mít i raw/ezak, jinak by zakázky zmizely (Codex P1, #74)."""
    d = koren / "raw" / "ezak" / "00247618"
    d.mkdir(parents=True)
    shutil.copy(VZORKY / "ezak" / "2026.xml", d / "2026.xml")
    assert spust(koren, Web()) == 0
    assert len(json.loads(cti(koren, "data/zakazky.json"))) == 4
    assert spust(koren, Web()) == 0                      # druhý běh: žádný „pokles“
