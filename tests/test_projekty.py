"""Projektové karty (pipeline/projekty.py) na malých vzorcích ve tvaru data/*.json."""
from pipeline import projekty as pr

PROJEKT = {"id": "telocvicny", "nazev": "Přístavba tělocvičen", "vazby": {"hledat": ["přístavb\\w* dvou tělocvič"],
           "vyloucit": ["servisní"]}, "rozpocet": {"org": ["6230000000"], "nazvy": ["Přístavba tělocvičen - vybavení"]}}


def ro(id_, org, nazev, zmena, usn="rm-u1", vysledek="prijato", po=1.0):
    return {"id": id_, "org": org, "nazev": nazev, "polozka": "6121" if org.startswith("6") else "5137",
            "zmena": zmena, "cislo_ro": 57, "organ": "rada", "strana": "vydaje", "vysledek_hlasovani": vysledek,
            "usneseni_id": usn, "jednani_id": "rm-2026-10-21",
            "rozpocet": {"schvaleny": 70.0, "pred_ro": po - zmena, "po_ro": po, "fond": None, "citace": "x"}}


def data(**k):
    d = {"jednani": [{"id": "rm-2026-10-21", "datum": "2026-10-21"}], "usneseni": [], "zakazky": [], "smlouvy": [],
         "rozpoctova_opatreni": []}
    d.update(k)
    return d


def usn(id_, text):
    return {"id": id_, "cislo": "RM 1/2026-1", "jednani_id": "rm-2026-10-21", "tema": "t", "tema_ai": True,
            "shrnuti": "s", "shrnuti_ai": True, "citace": {"dokument_id": "z", "strany": [1], "text": text},
            "overeni": "overeno_kodem", "vysledek_hlasovani": "prijato", "text": text}


def smlouva(id_, predmet, datum="2026-09-30"):
    return {"id": id_, "predmet": predmet, "datum_uzavreni": datum, "strany": [{"nazev": "Firma s.r.o."}],
            "castky": [{"hodnota": 10.0, "s_dph": False}], "url": "u"}


def test_role():
    assert pr.role("Příkazní smlouva - Technický dozor stavebníka na akci X - dodatek č. 1") == "technicky_dozor"
    assert pr.role("Zpracování projektové dokumentace ve stupni DZS/DPS") == "projekt"
    assert pr.role("Přístavba dvou tělocvičen - dodatek č. 5") == "stavba"


def test_rozpocet_org_dolozeno_nazev_propojeni_neprijate_vynechano():
    d = data(rozpoctova_opatreni=[ro("a", "6230000000", "Přístavba tělocvičen", -253000.0, po=58.0),
                                  ro("b", "9750000000", "Přístavba tělocvičen - vybavení", 253000.0, usn="rm-u2"),
                                  ro("c", "6230000000", "Přístavba tělocvičen", 5.0, vysledek="neprijato"),
                                  ro("d", "9750000000", "Něco jiného", 5.0)],
             usneseni=[usn("rm-u1", "RO"), usn("rm-u2", "RO")])
    k = pr.sestav_projekt(PROJEKT, d)
    assert [(r["org"], r["jistota"], len(r["zmeny"])) for r in k["rozpocet"]] == \
        [("6230000000", "dolozeno", 1), ("9750000000", "nase_propojeni", 1)]
    assert k["rozpocet"][0]["po_poslednim_ro"] == 58.0
    assert {u["id"]: u["jistota"] for u in k["usneseni"]} == {"rm-u1": "dolozeno", "rm-u2": "nase_propojeni"}


def test_smlouvy_vzor_pres_zalomeni_vylouceni_a_dodatky():
    d = data(smlouvy=[smlouva("s3", "Přístavba dvou tělocvičen - dodatek č. 3"),
                      smlouva("s5", "Přístavba dvou\ntělocvičen - dodatek č. 5", "2026-11-02"),
                      smlouva("t1", "Technický dozor na akci Přístavba dvou tělocvičen - dodatek č. 1"),
                      smlouva("x", "Servisní smlouva výtah přístavba dvou tělocvičen")])
    k = pr.sestav_projekt(PROJEKT, d)
    assert [s["id"] for s in k["smlouvy"]] == ["s3", "t1", "s5"]
    assert k["posledni_dodatek"] == {"stavba": 5, "technicky_dozor": 1}
    assert k["faze"] == "probiha" and k["posledni_udalost"]["zdroj_id"] == "s5"


def test_faze():
    stavba = {"role": "stavba", "stav": "zahájen", "casti": [{"vitezove": []}]}
    assert pr.faze([], []) == "pripravuje_se"
    assert pr.faze([stavba], []) == "soutezi_se"
    assert pr.faze([dict(stavba, stav="ukončeno plnění")], []) == "dokonceno"


def test_ai_puvod_a_mena_zustavaji():
    d = data(usneseni=[usn("rm-u9", "Dodatek ke smlouvě – přístavba dvou tělocvičen")],
             smlouvy=[dict(smlouva("e", "Přístavba dvou tělocvičen – vybavení"),
                           castky=[{"hodnota": 5.0, "s_dph": False, "druh": "smluvni", "mena": "EUR", "jednotka": "EUR"}])])
    k = pr.sestav_projekt(PROJEKT, d)
    u = k["usneseni"][0]
    assert (u["tema_ai"], u["shrnuti_ai"], u["overeni"], u["citace"]["dokument_id"]) == (True, True, "overeno_kodem", "z")
    assert next(e for e in k["udalosti"] if e["typ"] == "usneseni")["text_ai"] is True
    assert k["smlouvy"][0]["castky"][0]["mena"] == "EUR"


def test_souhrn_scita_jen_v_ramci_druhu():
    rozpocet = [{"kapitalova": True, "po_poslednim_ro": 58992143.49, "jistota": "dolozeno"},
                {"kapitalova": False, "po_poslednim_ro": 587000.0, "jistota": "nase_propojeni"},
                {"kapitalova": False, "po_poslednim_ro": None, "jistota": "dolozeno"}]
    zak = [{"id": "z1", "role": "stavba", "casti": [{"vitezove": [{"nazev": "A", "smluvni": [
        {"hodnota": 66097418.09, "s_dph": True}, {"hodnota": 54625965.36, "s_dph": False, "mena": "CZK"}]}]}]}]
    sml = [{"id": "s1", "role": "stavba", "dodatek_cislo": None, "strany": ["A"],
            "castky": [{"hodnota": 54625965.36, "s_dph": False}]},                       # tatáž smlouva jako z1
           {"id": "s2", "role": "vybaveni", "dodatek_cislo": None, "strany": ["B"],
            "castky": [{"hodnota": 310125.87, "s_dph": False}, {"hodnota": 375252.3, "s_dph": True}]},
           {"id": "s3", "role": "stavba", "dodatek_cislo": 5, "strany": ["A"],
            "castky": [{"hodnota": 2501117.05, "s_dph": False}]},
           {"id": "s4", "role": "bozp", "dodatek_cislo": None, "strany": ["C"], "castky": []}]
    s = pr.souhrn(rozpocet, zak, sml)
    assert s["rozpocet"]["celkem"] == 59579143.49 and s["rozpocet"]["neinvesticni"] == 587000.0
    assert s["rozpocet"]["jistota"] == "nase_propojeni" and s["rozpocet"]["polozek"] == 2
    m = s["smluvni_bez_dph"]
    assert m["celkem"] == 54936091.23 and [c["zdroj_id"] for c in m["casti"]] == ["z1", "s2"]
    assert m["bez_ceny"] == ["s4"] and m["dodatku_nezapocteno"] == 1 and m["s_dph"] is False
