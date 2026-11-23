"""Termín dokončení stavby podle smlouvy (#205): pipeline/terminy.py a pipeline/zdroje/prilohy_smluv.py."""
import json

from pipeline import terminy
from pipeline.zdroje import prilohy_smluv


def test_datum_z_uryvku():
    t = terminy.z_uryvku("4.2 Termín zahájení díla: 1. 4. 2026 4.3 Termín dokončení díla: 30. 9. 2026 4.4 Zhotovitel")
    assert (t["druh"], t["datum"]) == ("datum", "2026-09-30")
    assert t["citace"].startswith("Termín dokončení díla") and t["citace"].endswith("30. 9. 2026")
    t = terminy.z_uryvku("Zhotovitel se zavazuje dokončit dílo a předat jej objednateli nejpozději do 15.12.2026.")
    assert t["datum"] == "2026-12-15"


def test_datum_zahajeni_se_nebere():
    assert terminy.z_uryvku("Termín předání staveniště a zahájení prací: 6. 10. 2026") is None


def test_lhuta_bez_data():
    t = terminy.z_uryvku("Termín dokončení díla: do 120 kalendářních dnů od předání a převzetí staveniště.")
    assert t["druh"] == "lhuta" and t["datum"] is None and "120 kalendářních dnů" in t["citace"]


def test_neplatne_datum():
    assert terminy.z_uryvku("Termín dokončení díla: 31. 11. 2026") is None


def test_sestav_preferuje_datum_a_odkaz_na_stranu():
    raw = {"rs-1": {"url": "https://smlouvy.gov.cz/smlouva/1", "soubory": [
        {"url": "https://smlouvy.gov.cz/smlouva/soubor/9/SOD.pdf", "uryvky": [
            {"strana": 2, "text": "Termín dokončení díla: do 90 dnů od předání staveniště."},
            {"strana": 3, "text": "Termín dokončení stavby: 31. 3. 2027."}]}]}}
    v, chyby = terminy.sestav(raw)
    assert chyby == [] and v[0]["datum"] == "2027-03-31"
    assert v[0]["url"] == "https://smlouvy.gov.cz/smlouva/soubor/9/SOD.pdf#page=3" and v[0]["jistota"] == "dolozeno"


def test_karta_bere_posledni_dodatek_s_terminem():
    k = {"casti": [{"role": "stavba", "puvodni": {"zdroj_id": "rs-1"},
                    "dodatky": [{"zdroj_id": "rs-2", "cislo": 1, "datum": "2026-11-01"},
                                {"zdroj_id": "rs-3", "cislo": 2, "datum": "2026-11-19"}]}]}
    t = {"rs-1": {"druh": "datum", "datum": "2026-12-31"}, "rs-2": {"druh": "datum", "datum": "2027-03-31"},
         "rs-3": {"druh": "lhuta", "datum": None}}
    r = terminy.pro_kartu(k, t)
    assert (r["druh"], r["podle"]) == ("lhuta", "dodatek č. 2")
    del t["rs-3"]
    assert terminy.pro_kartu(k, t)["podle"] == "dodatek č. 1"
    assert terminy.pro_kartu({"casti": [{"role": "projekt"}]}, t) is None


def test_stazeni_uklada_jen_uryvky(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "projekty.json").write_text(json.dumps([{"casti": [
        {"role": "stavba", "puvodni": {"zdroj_id": "rs-7", "url": "https://smlouvy.gov.cz/smlouva/7"}, "dodatky": []},
        {"role": "projekt", "puvodni": {"zdroj_id": "rs-8", "url": "https://smlouvy.gov.cz/smlouva/8"}, "dodatky": []}]}]))
    stranka = '<a href="/smlouva/soubor/55/SOD%20podepsana.pdf">SOD</a> <a href="/smlouva/soubor/56/rozpocet.xlsx">x</a>'
    stazeno = []
    def ziskej(u):
        stazeno.append(u)
        return stranka.encode() if u.endswith("/7") else b"%PDF"
    def extrahuj(_):
        return ["Smluvní strany: Jan Novák, Lesní 5", "Článek IV. Termín dokončení díla: 30. 9. 2026. Další text"]
    nove, chyby = prilohy_smluv.stahni(tmp_path, ziskej, extrahuj)
    assert (nove, chyby) == (1, []) and "https://smlouvy.gov.cz/smlouva/8" not in stazeno
    ulozeno = json.loads((tmp_path / "raw" / "smlouvy" / "terminy.json").read_text())
    s = ulozeno["rs-7"]["soubory"]
    assert s[0]["url"] == "https://smlouvy.gov.cz/smlouva/soubor/55/SOD%20podepsana.pdf" and s[1]["preskoceno"] == "není PDF"
    text = json.dumps(ulozeno, ensure_ascii=False)
    assert "Novák" not in text and "Termín dokončení díla: 30. 9. 2026" in text
    # podruhé se už nestahuje
    stazeno.clear()
    assert prilohy_smluv.stahni(tmp_path, ziskej, extrahuj) == (0, []) and stazeno == []


def test_uryvky_odrizne_osobni_udaje_na_stejne_strane():
    u = prilohy_smluv.uryvky(["Kontaktní osoba objednatele: Jan Novák, Lesní 5. Termín dokončení díla: 30. 9. 2026. "
                              "Za zhotovitele podepsal Petr Svoboda, tel. 602 111 222."])
    text = " ".join(x["text"] for x in u)
    assert "30. 9. 2026" in text
    assert "Novák" not in text and "Svoboda" not in text and "602" not in text


def test_datum_zacatku_lhuty_neni_termin_dokonceni():
    t = terminy.z_uryvku("Termín dokončení díla: do 120 dnů od předání staveniště dne 1. 4. 2026.")
    assert t["druh"] == "lhuta" and t["datum"] is None


def test_slova_objednatel_a_zhotovitel_uryvek_nezkrati():
    u = prilohy_smluv.uryvky(["Lhůta pro dokončení prací: do 270 kalendářních dnů od převzetí staveniště zhotovitelem. "
                              "Objednatel převezme dílo."])
    assert "zhotovitelem" in u[0]["text"]
    u = prilohy_smluv.uryvky(["Termín dokončení díla: 30. 9. 2026. Kontaktní osoba: Jan Novák, tel. 777 123 456"])
    assert "Novák" not in u[0]["text"] and "30. 9. 2026" in u[0]["text"]


def test_klic_stahovani_odpovida_cteni_terminu():
    for veta in ("Zhotovitel se zavazuje dokončit stavbu do 30. 9. 2026.", "Datum dokončení díla: 30. 9. 2026."):
        u = prilohy_smluv.uryvky([veta])
        assert u and terminy.z_uryvku(u[0]["text"])["datum"] == "2026-09-30"


def test_dodatek_se_lhutou_nahrazuje_starsi_datum():
    k = {"casti": [{"role": "stavba", "puvodni": {"zdroj_id": "rs-1"},
                    "dodatky": [{"zdroj_id": "rs-2", "cislo": 1, "datum": "2026-11-01"}]}]}
    t = {"rs-1": {"druh": "datum", "datum": "2026-12-31"}, "rs-2": {"druh": "lhuta", "datum": None}}
    assert terminy.pro_kartu(k, t)["podle"] == "dodatek č. 1"
