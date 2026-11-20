"""Registr smluv: výběr záznamů z dumpu (bez sítě) a převod na data/smlouvy.json."""
import io
import json
import shutil
from pathlib import Path

import pytest

from pipeline import smlouvy
from pipeline.sestav import sestav
from pipeline.zdroje import registr_smluv as rs

KOREN = Path(__file__).resolve().parent.parent
NS = "http://portal.gov.cz/rejstriky/ISRS/1.2/"


def zaznam(id_sml, id_verze, cas, subjekt_ico, strana, predmet, platny=1, bez=None, s=None, navazany=None,
           cena_neuvedena=False):
    nazev_s, ico_s = strana
    return (f"<zaznam><identifikator><idSmlouvy>{id_sml}</idSmlouvy><idVerze>{id_verze}</idVerze></identifikator>"
            f"<odkaz>https://smlouvy.gov.cz/smlouva/{id_verze}</odkaz><casZverejneni>{cas}</casZverejneni>"
            f"<smlouva><subjekt><datovaSchranka>abc</datovaSchranka><nazev>Město Třeboň</nazev><ico>{subjekt_ico}</ico>"
            f"<adresa>Palackého nám. 46/II, 37901 Třeboň</adresa></subjekt>"
            f"<smluvniStrana><nazev>{nazev_s}</nazev>{f'<ico>{ico_s}</ico>' if ico_s else ''}"
            f"<adresa>Ulice 1, 37901 Třeboň</adresa><prijemce>1</prijemce></smluvniStrana>"
            f"<predmet>{predmet}</predmet><datumUzavreni>2026-10-01</datumUzavreni><cisloSmlouvy>S-{id_sml}</cisloSmlouvy>"
            f"<schvalil>Ing. Petra Pikna Jánská</schvalil>"
            f"{f'<hodnotaBezDph>{bez}</hodnotaBezDph>' if bez else ''}{f'<hodnotaVcetneDph>{s}</hodnotaVcetneDph>' if s else ''}"
            f"{'<cenaNeuvedena>1</cenaNeuvedena>' if cena_neuvedena else ''}"
            f"{f'<navazanyZaznam>{navazany}</navazanyZaznam>' if navazany else ''}</smlouva>"
            f"<prilohy><priloha><nazevSouboru>s.pdf</nazevSouboru></priloha></prilohy><platnyZaznam>{platny}</platnyZaznam></zaznam>")


DUMP = (f'<?xml version="1.0" encoding="UTF-8"?><dump xmlns="{NS}"><mesic>10</mesic><rok>2026</rok>'
        + zaznam(1, 11, "2026-10-02T08:00:00+02:00", "00247618", ("VH-TRES spol. s r. o.", "15771822"),
                 "Oprava chodníku", bez="100000", s="121000")
        + zaznam(1, 12, "2026-10-05T08:00:00+02:00", "00247618", ("VH-TRES spol. s r. o.", "15771822"),
                 "Oprava chodníku – opravená verze", bez="110000", s="133100")
        + zaznam(2, 21, "2026-10-03T08:00:00+02:00", "00247618", ("Jan Novák", "87654321"),
                 "Nájem pozemku – Jan Novák, IČO 87654321, Ulice 1, 37901 Třeboň", bez="5000")
        + zaznam(3, 31, "2026-10-04T08:00:00+02:00", "00247618", ("Firma a.s.", "11111111"), "Zrušená", platny=0)
        + zaznam(4, 41, "2026-10-04T09:00:00+02:00", "99999999", ("Cizí s.r.o.", "22222222"), "Nesledovaný subjekt")
        + zaznam(5, 51, "2026-10-06T08:00:00+02:00", "99999999", ("Město Třeboň", "00247618"), "Město jako strana",
                 cena_neuvedena=True)
        + zaznam(6, 61, "2026-10-07T08:00:00+02:00", "00247618", ("VH-TRES spol. s r. o.", "15771822"),
                 "Dodatek č. 1", bez="10000", navazany="12")
        + "</dump>")

INDEX = (f'<index xmlns="{NS}">'
         f'<dump><mesic>6</mesic><rok>2016</rok><hashDumpu>a</hashDumpu><odkaz>https://data.smlouvy.gov.cz/dump_2016_06.xml</odkaz></dump>'
         f'<dump><mesic>9</mesic><rok>2026</rok><hashDumpu>h9</hashDumpu><dokoncenyMesic>1</dokoncenyMesic><odkaz>https://data.smlouvy.gov.cz/dump_2026_09.xml</odkaz></dump>'
         f'<dump><mesic>10</mesic><rok>2026</rok><hashDumpu>h10</hashDumpu><dokoncenyMesic>0</dokoncenyMesic><odkaz>https://data.smlouvy.gov.cz/dump_2026_10.xml</odkaz></dump>'
         f'<dump><den>16</den><mesic>10</mesic><rok>2026</rok><hashDumpu>d</hashDumpu><odkaz>https://data.smlouvy.gov.cz/dump_2026_10_16.xml</odkaz></dump>'
         f'</index>').encode()


@pytest.fixture
def koren(tmp_path):
    for d in ("config", "anotace"):
        shutil.copytree(KOREN / d, tmp_path / d)
    (tmp_path / "raw").mkdir()
    (tmp_path / "raw" / "manifest.json").write_text("[]", encoding="utf-8")
    return tmp_path


def otevri_z(obsah: dict, volano: list):
    def otevri(url):
        volano.append(url)
        if url not in obsah:
            raise OSError(f"404 {url}")
        return io.BytesIO(obsah[url])
    return otevri


def test_stahni_vybere_sledovane_a_zpracuje_jen_zmenene(koren):
    volano = []
    web = {rs.INDEX_URL: INDEX, "https://data.smlouvy.gov.cz/dump_2026_10.xml": DUMP.encode(),
           "https://data.smlouvy.gov.cz/dump_2026_09.xml": DUMP.replace("<mesic>10", "<mesic>9").encode()}
    zmeny, chyby = rs.stahni(koren, otevri_z(web, volano), max_dumpu=1)
    assert chyby == [] and zmeny == ["2026-10.json"]              # nejnovější první, limit 1 dump za běh
    assert not any("dump_2016_06" in u or "_10_16" in u for u in volano)  # před 7/2016 a denní dumpy ne
    zaznamy = json.loads((koren / "raw/smlouvy/2026-10.json").read_text(encoding="utf-8"))
    assert sorted(z["identifikator"]["idVerze"] for z in zaznamy) == ["11", "12", "21", "31", "51", "61"]
    assert all("prilohy" not in z for z in zaznamy)
    volano.clear()
    zmeny, _ = rs.stahni(koren, otevri_z(web, volano), max_dumpu=5)
    # dokončený 2026-09 poprvé; rozpracovaný 2026-10 se čte znovu, ale beze změny výběru nic nemění
    assert zmeny == ["2026-09.json"] and "https://data.smlouvy.gov.cz/dump_2026_10.xml" in volano
    volano.clear()
    rs.stahni(koren, otevri_z(web, volano), max_dumpu=5)
    assert "https://data.smlouvy.gov.cz/dump_2026_09.xml" not in volano          # dokončený se znovu nečte


def test_chyba_dumpu_nezastavi_ostatni_a_index_nedostupny(koren):
    web = {rs.INDEX_URL: INDEX, "https://data.smlouvy.gov.cz/dump_2026_09.xml": DUMP.encode()}
    zmeny, chyby = rs.stahni(koren, otevri_z(web, []), max_dumpu=5)
    assert zmeny == ["2026-09.json"] and any("2026-10" in c for c in chyby)
    assert rs.stahni(koren, otevri_z({}, []))[1][0].startswith("index:")


def nactene(koren):
    web = {rs.INDEX_URL: INDEX, "https://data.smlouvy.gov.cz/dump_2026_10.xml": DUMP.encode()}
    rs.stahni(koren, otevri_z(web, []), max_dumpu=1)
    return {s["id_smlouvy"]: s for s in smlouvy.nacti_smlouvy(koren)}


def test_posledni_platna_verze_a_neplatne_vynechane(koren):
    s = nactene(koren)
    assert set(s) == {"1", "2", "5", "6"}                        # 3 neplatná, 4 nesledovaný (vyřazen už při výběru)
    assert s["1"]["id_verze"] == "12" and s["1"]["predmet"] == "Oprava chodníku – opravená verze"
    assert s["6"]["navazuje_na"] == "12"


def test_castky_s_druhem_a_dph(koren):
    s = nactene(koren)
    assert {(k["s_dph"], k["hodnota"]) for k in s["1"]["castky"]} == {(False, 110000.0), (True, 133100.0)}
    assert all(k["druh"] == "smluvni" for k in s["1"]["castky"])
    assert {k["citace"] for k in s["1"]["castky"]} == {'"hodnotaBezDph": "110000"',
                                                       '"hodnotaVcetneDph": "133100"'}
    assert all(k["poznamka"] == "2026-10.json; záznam idVerze 12" for k in s["1"]["castky"])
    assert s["5"]["castky"] == [] and s["5"]["cena_neuvedena"] is True
    assert smlouvy.zkontroluj(list(s.values()), koren) == []
    s["1"]["castky"][0]["citace"] = '"hodnotaBezDph": "1"'
    assert any("citace" in c for c in smlouvy.zkontroluj(list(s.values()), koren))


def test_fyzicka_osoba_bez_jmena_ico_a_adresy(koren):
    s = nactene(koren)
    assert s["2"]["strany"] == [{"nazev": "fyzická osoba", "ico": None, "fyzicka_osoba": True, "prijemce": True,
                                 "jmeno_podnikatele": "Jan Novák"}]          # podnikatel–příjemce jménem (#93)
    vse = json.dumps(list(s.values()), ensure_ascii=False)
    assert "87654321" not in vse and "Ulice 1" not in vse and "Pikna" not in vse and "Palackého" not in vse


def test_sestaveni_maskuje_jmena_v_predmetu(koren):
    nactene(koren)
    vystup, chyby = sestav(koren)
    s = {x["id_smlouvy"]: x for x in vystup["smlouvy"]}
    assert s["2"]["predmet"] == "Nájem pozemku – [jméno], IČO [údaj], [údaj]"
    assert not [c for c in chyby if "smlouvy" in c]


def test_sledovana_pravnicka_osoba_bez_pravni_formy_zustava():
    s = smlouvy.strana({"nazev": "Městská knihovna Třeboň", "ico": "21551464"}, frozenset({"21551464"}))
    assert s["fyzicka_osoba"] is False and s["ico"] == "21551464"


def test_zmena_sledovanych_ico_vynuti_nove_zpracovani(koren):
    web = {rs.INDEX_URL: INDEX, "https://data.smlouvy.gov.cz/dump_2026_10.xml": DUMP.encode(),
           "https://data.smlouvy.gov.cz/dump_2026_09.xml": DUMP.replace("<mesic>10", "<mesic>9").encode()}
    rs.stahni(koren, otevri_z(web, []), max_dumpu=5)
    m = json.loads((koren / "raw/smlouvy/manifest.json").read_text(encoding="utf-8"))
    d = {"klic": "2026-09", "hash": "h9"}
    assert rs._zastarale(m, d, rs.sledovana_ico(koren)) is False
    assert rs._zastarale(m, d, {"123"}) is True


def test_novejsi_verze_bez_sledovaneho_ico_nahradi_starou(koren):
    """Oprava metadat odebrala sledované IČO: smlouva už nemá u subjektu figurovat (Codex P2, #75)."""
    nactene(koren)
    oprava = (f'<dump xmlns="{NS}">' + zaznam(1, 13, "2026-11-02T08:00:00+01:00", "99999999",
              ("Cizí s.r.o.", "22222222"), "Oprava – jiný subjekt", bez="1") + "</dump>")
    idx = INDEX.replace(b"</index>", b'<dump><mesic>11</mesic><rok>2026</rok><hashDumpu>h11</hashDumpu>'
                        b'<odkaz>https://data.smlouvy.gov.cz/dump_2026_11.xml</odkaz></dump></index>')
    rs.stahni(koren, otevri_z({rs.INDEX_URL: idx, "https://data.smlouvy.gov.cz/dump_2026_11.xml": oprava.encode()}, []),
              max_dumpu=1)
    assert "1" not in {s["id_smlouvy"] for s in smlouvy.nacti_smlouvy(koren)}


def test_zverejnila_fyzicka_osoba(koren):
    """Smlouvu zveřejnila FO a město je stranou: jméno ani IČO zveřejňovatele se neukáže (Codex P1, #75)."""
    d = (f'<dump xmlns="{NS}">' + zaznam(9, 91, "2026-10-08T08:00:00+02:00", "87654321",
         ("Město Třeboň", "00247618"), "Nájem", bez="1000").replace("<nazev>Město Třeboň</nazev><ico>87654321",
         "<nazev>Jan Novák</nazev><ico>87654321") + "</dump>")
    rs.stahni(koren, otevri_z({rs.INDEX_URL: INDEX, "https://data.smlouvy.gov.cz/dump_2026_10.xml": d.encode()}, []),
              max_dumpu=1)
    s = {x["id_smlouvy"]: x for x in smlouvy.nacti_smlouvy(koren)}["9"]
    assert (s["subjekt_nazev"], s["subjekt_ico"]) == ("fyzická osoba", None)
    assert "Novák" not in json.dumps(s, ensure_ascii=False)


def test_rozpracovany_mesic_nemeni_manifest(koren):
    """Denně přegenerovaný dump aktuálního měsíce bez změny výběru nesmí měnit raw/smlouvy (Codex P2, #75)."""
    web = {rs.INDEX_URL: INDEX, "https://data.smlouvy.gov.cz/dump_2026_10.xml": DUMP.encode(),
           "https://data.smlouvy.gov.cz/dump_2026_09.xml": DUMP.replace("<mesic>10", "<mesic>9").encode()}
    rs.stahni(koren, otevri_z(web, []), max_dumpu=5)
    pred = {p.name: p.read_bytes() for p in (koren / "raw/smlouvy").iterdir()}
    web[rs.INDEX_URL] = INDEX.replace(b"<hashDumpu>h10</hashDumpu>", b"<hashDumpu>h10b</hashDumpu>")
    zmeny, _ = rs.stahni(koren, otevri_z(web, []), max_dumpu=5)
    assert zmeny == [] and pred == {p.name: p.read_bytes() for p in (koren / "raw/smlouvy").iterdir()}


def test_jmeno_bez_titulu_v_predmetu(koren):
    from pipeline.jmena import zakryj_jmena
    from pipeline.sestav import nacti_osoby
    o = nacti_osoby(KOREN)
    assert zakryj_jmena("Vystoupení – Andrea Kalivodová", o, KOREN) == "Vystoupení – [jméno]"
    assert zakryj_jmena("Koncert Jany Novákové", o, KOREN) == "Koncert [jméno]"
    assert zakryj_jmena("Nájem pro Ondřeje Zbudila", o, KOREN) == "Nájem pro Ondřeje Zbudila"     # zastupitel
    assert zakryj_jmena("Dodávka elektřiny 2027", o, KOREN) == "Dodávka elektřiny 2027"


def test_podnikajici_fo_jmenem_nepodnikajici_anonymne():
    from pipeline.smlouvy import strana
    p = strana({"nazev": "Ing. Jan Projektant", "ico": "12345678", "prijemce": "1"})
    assert (p["nazev"], p["ico"], p["fyzicka_osoba"], p["jmeno_podnikatele"]) == \
        ("fyzická osoba", None, True, "Ing. Jan Projektant")
    assert strana({"nazev": "Jana Nájemnice", "prijemce": "1"})["jmeno_podnikatele"] is None     # bez IČO
    assert strana({"nazev": "Petr Plátce", "ico": "87654321", "prijemce": "0"})["jmeno_podnikatele"] is None


def test_nezpracovane_mesice_maji_prednost_pred_zmenenym_hashem(koren):
    index = INDEX.replace(b'<dump><mesic>10</mesic>', (
        b'<dump><mesic>8</mesic><rok>2026</rok><hashDumpu>h8</hashDumpu><dokoncenyMesic>1</dokoncenyMesic>'
        b'<odkaz>https://data.smlouvy.gov.cz/dump_2026_08.xml</odkaz></dump><dump><mesic>10</mesic>'))
    web = {rs.INDEX_URL: index, "https://data.smlouvy.gov.cz/dump_2026_10.xml": DUMP.encode(),
           "https://data.smlouvy.gov.cz/dump_2026_09.xml": DUMP.replace("<mesic>10", "<mesic>9").encode(),
           "https://data.smlouvy.gov.cz/dump_2026_08.xml": DUMP.replace("<mesic>10", "<mesic>8").encode()}
    m = koren / "raw/smlouvy/manifest.json"
    m.parent.mkdir(parents=True, exist_ok=True)
    m.write_text(json.dumps({"2026-09": {"hash": "stary", "ico": sorted(rs.sledovana_ico(koren))}}), encoding="utf-8")
    volano = []
    rs.stahni(koren, otevri_z(web, volano), max_dumpu=2)
    dumpy = [u for u in volano if u != rs.INDEX_URL]
    # rozpracovaný říjen, pak dosud nezpracovaný srpen; září se změněným hashem až v dalším běhu
    assert dumpy == ["https://data.smlouvy.gov.cz/dump_2026_10.xml", "https://data.smlouvy.gov.cz/dump_2026_08.xml"]


def test_predmet_maskuje_cast_jmena_fyzicke_osoby():
    strany = [{"nazev": "Nováková Dvořáková Jana nar. 1960", "ico": None, "prijemce": "1"}]
    vysl = smlouvy._skryj_fo("Dotace (p. Nováková Dvořáková)", strany, frozenset())
    assert "Nováková" not in vysl and "Dvořáková" not in vysl
    assert "Dotace" in vysl
