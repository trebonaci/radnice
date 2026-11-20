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


def smlouva(id_, predmet, datum="2026-09-30", navazuje_na=None):
    return {"id": id_, "id_smlouvy": "i" + id_, "navazuje_na": navazuje_na, "predmet": predmet, "datum_uzavreni": datum, "strany": [{"nazev": "Firma s.r.o."}],
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


def sml(id_, role, cislo=None, castka=None, navazuje=None, strana="A", url=None):
    return {"id": id_, "id_smlouvy": "i" + id_, "navazuje_na": navazuje, "role": role, "dodatek_cislo": cislo,
            "datum_uzavreni": "2026-09-30", "url": url or "u" + id_,
            "strany": [{"nazev": strana, "jmeno_podnikatele": None}],
            "castky": [] if castka is None else [{"hodnota": castka, "s_dph": False}]}


def test_casti_dodatek_k_puvodni_smlouve_a_cena_po_dodatcich():
    # BOZP: původní 138 900 + dodatek č. 1 7 750 = 146 650 Kč bez DPH (doslova v dodatku, registr 20. 11. 2026)
    c = pr.casti_akce([], [sml("b0", "bozp", castka=138900.0), sml("b1", "bozp", 1, 7750.0, navazuje="ib0")])
    assert len(c) == 1 and c[0]["cena_po_dodatcich"] == 146650.0 and c[0]["vazba_dodatku"] == "dolozeno"
    assert c[0]["dodatky_bez_dph"] == 7750.0


def test_casti_chybejici_dodatek_nebo_puvodni_cena_bez_souctu():
    zak = [{"id": "z1", "role": "stavba", "url": "e", "casti": [{"registr_smluv": [], "vitezove": [
        {"nazev": "A", "smluvni": [{"hodnota": 100.0, "s_dph": False}]}]}]}]
    c = pr.casti_akce(zak, [sml("d3", "stavba", 3, 10.0, navazuje="x"), sml("d4", "stavba", 4, navazuje="x"),
                            sml("t1", "technicky_dozor", 1, 5.0, navazuje="y")])
    stavba, tds = c
    assert stavba["puvodni"]["bez_dph"] == 100.0 and stavba["chybi_dodatky"] == [1, 2]
    assert stavba["cena_po_dodatcich"] is None and stavba["dodatky"][1]["bez_castky"] is True
    assert tds["puvodni"] is None and tds["cena_po_dodatcich"] is None and tds["dodatky_bez_dph"] == 5.0


def test_souhrn_scita_jen_v_ramci_druhu():
    rozpocet = [{"kapitalova": True, "po_poslednim_ro": 58992143.49, "jistota": "dolozeno"},
                {"kapitalova": False, "po_poslednim_ro": 587000.0, "jistota": "nase_propojeni"},
                {"kapitalova": False, "po_poslednim_ro": None, "jistota": "dolozeno"}]
    zak = [{"id": "z1", "role": "stavba", "url": "e", "casti": [{"registr_smluv": ["u-s1"], "vitezove": [
        {"nazev": "A", "smluvni": [{"hodnota": 66097418.09, "s_dph": True}, {"hodnota": 54625965.36, "s_dph": False}]}]}]}]
    casti = pr.casti_akce(zak, [sml("s1", "stavba", castka=54625965.36, url="u-s1"),     # tatáž smlouva jako z1
                                sml("s2", "vybaveni", castka=310125.87, strana="B"),
                                sml("s3", "stavba", 1, 2501117.05, navazuje="is1")])
    s = pr.souhrn(rozpocet, casti)
    assert s["rozpocet"]["celkem"] == 59579143.49 and s["rozpocet"]["neinvesticni"] == 587000.0
    assert s["rozpocet"]["jistota"] == "nase_propojeni" and s["rozpocet"]["polozek"] == 2
    m = s["smluvni_bez_dph"]
    assert m["celkem"] == 54936091.23 and m["po_dodatcich"] == 57437208.28 and m["neuplne"] == []
    assert m["s_dph"] is False


def test_souhrn_stejna_cena_ruzne_smlouvy_a_neznamy_soucet():
    casti = pr.casti_akce([], [sml("s1", "stavba", castka=100.0), sml("s2", "stavba", castka=100.0, strana="B")])
    assert pr.souhrn([], casti)["smluvni_bez_dph"]["celkem"] == 200.0
    s = pr.souhrn([], [])
    assert s["rozpocet"]["celkem"] is None and s["rozpocet"]["jistota"] == "nevime"
    assert s["smluvni_bez_dph"]["celkem"] is None


def test_podnikatel_jmenem_v_karte():
    d = data(smlouvy=[dict(smlouva("p", "Technický dozor na akci Přístavba dvou tělocvičen"),
                           strany=[{"nazev": "fyzická osoba", "jmeno_podnikatele": "Ing. Jan Projektant"}])])
    k = pr.sestav_projekt(PROJEKT, d)
    assert k["smlouvy"][0]["strany"] == [{"nazev": "fyzická osoba", "jmeno_podnikatele": "Ing. Jan Projektant"}]
    assert k["casti"][0]["dodavatel"]["jmeno_podnikatele"] == "Ing. Jan Projektant"


def test_puvodni_smlouva_pres_navazany_zaznam_dolozena():
    puv = dict(smlouva("p0", "Příkazní smlouva – koordinátor BOZP"), castky=[{"hodnota": 138900.0, "s_dph": False}])
    dod = dict(smlouva("p1", "Koordinátor BOZP na akci Přístavba dvou tělocvičen - dodatek č. 1", navazuje_na="ip0"),
               castky=[{"hodnota": 7750.0, "s_dph": False}])
    k = pr.sestav_projekt(PROJEKT, data(smlouvy=[puv, dod]))
    assert {s["id"]: s["jistota"] for s in k["smlouvy"]} == {"p1": "nase_propojeni", "p0": "dolozeno"}
    assert k["casti"][0]["cena_po_dodatcich"] == 146650.0


def test_dodatek_bez_castky_necha_cenu_neznamou_a_ruzni_dodavatele_zvlast():
    c = pr.casti_akce([], [sml("s0", "stavba", castka=100.0), sml("s1", "stavba", 1, navazuje="is0")])
    assert c[0]["cena_po_dodatcich"] is None and c[0]["dodatky"][0]["bez_castky"] is True
    zak = [{"id": "z1", "role": "vybaveni", "url": "e", "casti": [{"registr_smluv": [], "vitezove": [
        {"nazev": "A", "smluvni": [{"hodnota": 100.0, "s_dph": False}]}]}]}]
    c = pr.casti_akce(zak, [sml("b0", "vybaveni", castka=200.0, strana="B")])
    assert sorted(x["puvodni"]["bez_dph"] for x in c) == [100.0, 200.0]


def test_cena_z_registru_kdyz_ezak_cenu_nema():
    zak = [{"id": "z1", "role": "stavba", "url": "e", "casti": [{"registr_smluv": ["u-s0"], "vitezove": [
        {"nazev": "A", "smluvni": []}]}]}]
    c = pr.casti_akce(zak, [sml("s0", "stavba", castka=500.0, url="u-s0")])
    assert c[0]["puvodni"] == {"bez_dph": 500.0, "s_dph": 605.0, "zdroj_id": "s0", "url": "u-s0",
                               "s_dph_dopocteno": True, "sazba_dph": 21, "sazba_dph_zdroj": "zakladni_sazba"}


def test_parovani_podle_cisla_zakazky_a_dalsi_dodatky_teze_smlouvy():
    zak = [{"id": "ezak-VZ-1", "role": "stavba", "url": "e", "casti": [{"registr_smluv": [], "vitezove": [
        {"nazev": "ACME s.r.o.", "smluvni": [{"hodnota": 100.0, "s_dph": False}]}]}]}]
    c = pr.casti_akce(zak, [dict(sml("s0", "stavba", castka=100.0, strana="ACME, s.r.o."),
                                 evidencni_cislo_zakazky="VZ-1")])
    assert len(c) == 1 and c[0]["vazba_dodatku"] == "dolozeno"
    puv = dict(smlouva("p0", "Smlouva o dílo"), castky=[{"hodnota": 100.0, "s_dph": False}])
    d1 = dict(smlouva("p1", "Přístavba dvou tělocvičen - dodatek č. 1", navazuje_na="ip0"),
              castky=[{"hodnota": 10.0, "s_dph": False}])
    d2 = dict(smlouva("p2", "Dodatek č. 2", navazuje_na="ip0"), castky=[])
    k = pr.sestav_projekt(PROJEKT, data(smlouvy=[puv, d1, d2]))
    assert [d["cislo"] for d in k["casti"][0]["dodatky"]] == [1, 2] and k["casti"][0]["cena_po_dodatcich"] is None


def test_dodatek_jen_o_terminu_podle_usneseni_a_cena_s_dph():
    usn_ = [{"id": "rm-u463", "vysledek_hlasovani": "prijato", "text":
             "uzavření Dodatku č. 4 ke smlouvě o dílo č. 750/9256/25 ze dne 23.12.2025 na zhotovení stavby „Hala“ "
             "se společností X, jehož předmětem je změna termínu dokončení díla."},
            {"id": "rm-u9", "vysledek_hlasovani": "prijato", "text":
             "uzavření Dodatku č. 5 ke smlouvě o dílo č. 750/9256/25, jehož předmětem je změna ceny díla."}]
    jt = pr.dodatky_jen_termin(usn_)
    assert jt == {"750/9256/25/4": "rm-u463"}
    sm = [dict(sml("s0", "stavba", castka=100.0), castky=[{"hodnota": 100.0, "s_dph": False}, {"hodnota": 121.0, "s_dph": True}]),
          dict(sml("s1", "stavba", 1, navazuje="is0"), castky=[{"hodnota": -12.1, "s_dph": True}]),   # jen s DPH
          dict(sml("s2", "stavba", 2, navazuje="is0"), cislo_smlouvy="750/9256/25/4")]          # bez částky
    sm[2]["dodatek_cislo"] = 4
    sm.append(dict(sml("s3", "stavba", 3, 10.0, navazuje="is0"), castky=[{"hodnota": 10.0, "s_dph": False},
                                                                      {"hodnota": 12.1, "s_dph": True}]))
    sm[1]["dodatek_cislo"], sm[3]["dodatek_cislo"] = 1, 2
    sm.append(dict(sml("s5", "stavba", 3, navazuje="is0"), cislo_smlouvy="750/9256/25/3"))      # bez částky, bez usnesení
    c = pr.casti_akce([], sm[:4], jt)[0]
    d4 = next(d for d in c["dodatky"] if d["cislo"] == 4)
    assert d4["jen_termin"] and d4["doklad_usneseni"] == "rm-u463" and d4["bez_dph"] == 0.0
    assert c["chybi_dodatky"] == [3] and c["cena_po_dodatcich_s_dph"] is None
    c = pr.casti_akce([], sm[:4] + [dict(sm[4], castky=[{"hodnota": 1.0, "s_dph": False}, {"hodnota": 1.21, "s_dph": True}])], jt)[0]
    assert c["cena_po_dodatcich"] is None                         # dodatek č. 1 nemá cenu bez DPH
    assert c["cena_po_dodatcich_s_dph"] == 121.0 - 12.1 + 12.1 + 0.0 + 1.21
    assert pr.casti_akce([], [sm[0], dict(sm[2], cislo_smlouvy="jine/4")], jt)[0]["cena_po_dodatcich"] is None


def test_souhrn_s_dph_zvlast():
    casti = pr.casti_akce([], [dict(sml("s0", "stavba"), castky=[{"hodnota": 100.0, "s_dph": False}, {"hodnota": 121.0, "s_dph": True}]),
                               dict(sml("s1", "stavba", 1, navazuje="is0"), castky=[{"hodnota": -12.1, "s_dph": True}])])
    s = pr.souhrn([], casti)
    assert s["smluvni_s_dph"]["celkem"] == 121.0 and s["smluvni_s_dph"]["po_dodatcich"] == 108.9
    assert s["smluvni_s_dph"]["s_dph"] is True and s["smluvni_bez_dph"]["po_dodatcich"] is None


def test_dopocet_dph_sazbou_teze_smlouvy_nebo_21():
    neplatce = pr.casti_akce([], [dict(sml("t0", "technicky_dozor"), castky=[{"hodnota": 100.0, "s_dph": False}]),
                                  dict(sml("t1", "technicky_dozor", 1, navazuje="it0"),
                                       castky=[{"hodnota": 14500.0, "s_dph": False}, {"hodnota": 14500.0, "s_dph": True}])])[0]
    assert neplatce["puvodni"]["s_dph"] == 100.0 and neplatce["puvodni"]["sazba_dph"] == 0
    assert neplatce["puvodni"]["sazba_dph_zdroj"] == "jina_polozka_smlouvy" and neplatce["cena_po_dodatcich_s_dph"] == 14600.0
    c = pr.casti_akce([], [dict(sml("s0", "stavba"), castky=[{"hodnota": 1000.0, "s_dph": False}]),
                           dict(sml("s1", "stavba", 1, navazuje="is0"), castky=[{"hodnota": 10.0, "s_dph": False}])])[0]
    assert c["puvodni"]["s_dph"] == 1210.0 and c["dodatky"][0]["s_dph"] == 12.1 and c["obsahuje_dopocet_dph"]
    assert c["cena_po_dodatcich_s_dph"] == 1222.1


def test_kratke_popisy_historie():
    assert pr.druh_projektu("Zpracování projektové dokumentace ve stupni DZS/DPS přístavby") == "projekt prováděcí"
    assert pr.druh_projektu("Projekt pro stavební povolení a DPS") == "projekt pro stavební řízení a prováděcí"
    assert pr.druh_projektu("Vypracování projektové dokumentace pro provedení stavby") == "projekt prováděcí"
    assert pr.druh_projektu("Architektonická studie revitalizace") == "architektonická studie"
    assert pr.druh_projektu("Zpracování PD - stavební úpravy hřbitova") == "projektová dokumentace"
    assert pr.kratky_popis("bozp", "Příkazní smlouva - Koordinátor BOZP", 1) == "dodatek 1 (BOZP)"
    assert pr.kratky_popis("stavba", "Přístavba dvou tělocvičen") == "smlouva o dílo"
    assert pr.dni_mezi("2026-08-12", "2026-09-16") == 35 and pr.dni_mezi(None, "2026-09-16") is None


def test_soutez_zverejnena_po_lhute_bez_doby_trvani():
    zak = {"id": "ezak-VZ-1", "nazev": "Přístavba dvou tělocvičen", "stav": "dokončen", "url": "e",
           "casti": [{"nazev": "x", "stav": "dokončen", "pocet_nabidek": 2, "datum_uverejneni": "2026-08-24",
                      "lhuta_nabidek": "2026-07-22", "datum_uzavreni_smlouvy": None, "vitezove": []}]}
    e = next(x for x in pr.sestav_projekt(PROJEKT, data(zakazky=[zak]))["udalosti"] if x["typ"] == "soutez")
    assert e["datum"] == "2026-07-22" and e["kratce"] == "stavba, 2 nabídky" and e["lhuta_dni"] is None


def test_kratce_usneseni():
    assert pr.kratce_usneseni({"vysledek_hlasovani": "prijato", "text": "uzavření Dodatku č. 5 ke smlouvě o dílo"}) == \
        "schválení dodatku 5"
    assert pr.kratce_usneseni({"vysledek_hlasovani": "prijato", "tema": "T", "text":
                               "že nejvýhodnější nabídkou je nabídka s nejnižší cenou"}) == "výběr dodavatele"
    assert pr.kratce_usneseni({"vysledek_hlasovani": "neprijato", "text": "x"}) == "návrh nepřijat"
    assert pr.kratce_usneseni({"vysledek_hlasovani": "prijato", "tema": "Téma", "text": "jiné"}) == "Téma"
