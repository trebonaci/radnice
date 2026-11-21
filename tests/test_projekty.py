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
    assert pr.role("Vypracování projektu interiéru akce Sportovní hala") == "projekt"
    assert pr.role("Zhotovení PD, příkazní činnost a výkon AD pro Modernizaci objektu B LDA") == "projekt"
    assert pr.role("Objednávka PD na interiéry - ubytovací zařízení G - LDA") == "projekt"
    assert pr.role("Příkazní smlouva - TDS na akci Stavební úpravy ulice Valy v Třeboni") == "technicky_dozor"
    assert pr.role("Příkazní smlouva na výkon Koordinátora bezpečnosti a ochrany zdraví při práci (BOZP)") == "bozp"
    assert pr.role("Stavební úpravy kotelen a výměna plynových kotlů v objektu DPS IA a DPS IC") == "stavba"
    assert pr.role("Činnost AD při realizaci akce Oprava fasády objektu čp. 20/I Třeboň") == "projekt"
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
    assert stavba["puvodni"]["muze_obsahovat_dodatky"] is True      # smluvní cena E-ZAK u smlouvy s dodatky
    assert stavba["cena_po_dodatcich"] == 110.0 and stavba["dodatky"][1]["bez_castky"] is True
    assert any("bez ceny" in d for d in stavba["neuplne_cena_po_dodatcich"])   # součet známých + důvod
    assert tds["puvodni"] is None and tds["cena_po_dodatcich"] == 5.0 and tds["dodatky_bez_dph"] == 5.0
    assert "původní cena není známa" in tds["neuplne_cena_po_dodatcich"]


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
    assert k["smlouvy"][0]["strany"] == [{"nazev": "fyzická osoba", "jmeno_podnikatele": "Ing. Jan Projektant", "ico": None}]
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
    assert c[0]["cena_po_dodatcich"] == 100.0 and c[0]["dodatky"][0]["bez_castky"] is True
    assert c[0]["neuplne_cena_po_dodatcich"] == ["dodatek č. 1 bez ceny"]
    zak = [{"id": "z1", "role": "vybaveni", "url": "e", "casti": [{"registr_smluv": [], "vitezove": [
        {"nazev": "A", "smluvni": [{"hodnota": 100.0, "s_dph": False}]}]}]}]
    c = pr.casti_akce(zak, [sml("b0", "vybaveni", castka=200.0, strana="B")])
    assert sorted(x["puvodni"]["bez_dph"] for x in c) == [100.0, 200.0]


def test_cena_z_registru_kdyz_ezak_cenu_nema():
    zak = [{"id": "z1", "role": "stavba", "url": "e", "casti": [{"registr_smluv": ["u-s0"], "vitezove": [
        {"nazev": "A", "smluvni": []}]}]}]
    c = pr.casti_akce(zak, [sml("s0", "stavba", castka=500.0, url="u-s0")])
    assert c[0]["puvodni"] == {"bez_dph": 500.0, "s_dph": 605.0, "zdroj_id": "s0", "url": "u-s0",
                               "zdroj_druh": "registr", "muze_obsahovat_dodatky": False, "zaklady_z_ezak_po_dodatcich": [], "s_dph_dopocteno": True, "sazba_dph": 21, "sazba_dph_zdroj": "zakladni_sazba"}


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
    assert [d["cislo"] for d in k["casti"][0]["dodatky"]] == [1, 2] and k["casti"][0]["cena_po_dodatcich"] == 110.0
    assert k["casti"][0]["neuplne_cena_po_dodatcich"]


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
    assert c["chybi_dodatky"] == [3] and c["cena_po_dodatcich_s_dph"] == 121.0
    assert "chybí dodatek č. 3" in c["neuplne_cena_po_dodatcich_s_dph"]
    c = pr.casti_akce([], sm[:4] + [dict(sm[4], castky=[{"hodnota": 1.0, "s_dph": False}, {"hodnota": 1.21, "s_dph": True}])], jt)[0]
    assert c["neuplne_cena_po_dodatcich"] == ["dodatek č. 1 bez ceny"]   # dodatek č. 1 nemá cenu bez DPH
    assert c["cena_po_dodatcich_s_dph"] == 121.0 - 12.1 + 12.1 + 0.0 + 1.21
    jina = pr.casti_akce([], [sm[0], dict(sm[2], cislo_smlouvy="jine/4")], jt)[0]
    assert jina["dodatky"][0]["jen_termin"] is False and jina["neuplne_cena_po_dodatcich"]


def test_souhrn_s_dph_zvlast():
    casti = pr.casti_akce([], [dict(sml("s0", "stavba"), castky=[{"hodnota": 100.0, "s_dph": False}, {"hodnota": 121.0, "s_dph": True}]),
                               dict(sml("s1", "stavba", 1, navazuje="is0"), castky=[{"hodnota": -12.1, "s_dph": True}])])
    s = pr.souhrn([], casti)
    assert s["smluvni_s_dph"]["celkem"] == 121.0 and s["smluvni_s_dph"]["po_dodatcich"] == 108.9
    assert s["smluvni_s_dph"]["s_dph"] is True and s["smluvni_bez_dph"]["po_dodatcich"] == 100.0
    assert s["smluvni_bez_dph"]["neuplne"]


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


def test_zrusene_rizeni_bez_smlouvy():
    zak = {"id": "ezak-VZ-891", "nazev": "Přístavba dvou tělocvičen", "stav": "zrušen", "url": "e",
           "casti": [{"nazev": "x", "stav": "zrušen", "pocet_nabidek": 1, "datum_uverejneni": "2025-10-10",
                      "lhuta_nabidek": "2025-11-27", "datum_uzavreni_smlouvy": None, "datum_zruseni": "2025-12-02",
                      "vitezove": []}]}
    e = next(x for x in pr.sestav_projekt(PROJEKT, data(zakazky=[zak]))["udalosti"] if x["typ"] == "soutez")
    assert e["zruseno"] and e["kratce"] == "stavba, řízení zrušeno 2. 12. 2025 po 53 dnech, 1 nabídka"
    assert "smlouva" not in e["kratce"]


def test_kratce_usneseni():
    assert pr.kratce_usneseni({"vysledek_hlasovani": "prijato", "text": "uzavření Dodatku č. 5 ke smlouvě o dílo"}) == \
        "schválení dodatku 5"
    assert pr.kratce_usneseni({"vysledek_hlasovani": "prijato", "tema": "T", "text":
                               "že nejvýhodnější nabídkou je nabídka s nejnižší cenou"}) == "výběr dodavatele"
    assert pr.kratce_usneseni({"vysledek_hlasovani": "neprijato", "text": "x"}) == "návrh nepřijat"
    assert pr.kratce_usneseni({"vysledek_hlasovani": "prijato", "tema": "Téma", "text": "jiné"}) == "Téma"


def test_puvodni_cena_ze_smlouvy_ne_ze_smluvni_ceny_ezak_po_dodatcich():
    """Přístavba tělocvičen (#136): E-ZAK uvádí smluvní cenu „po dodatku č. 5“, podepsaná smlouva 60,1 mil."""
    zak = [{"id": "z1", "role": "stavba", "url": "e", "casti": [{"registr_smluv": ["u-s0"], "vitezove": [
        {"nazev": "MANE", "smluvni": [{"hodnota": 66097418.09, "s_dph": True}, {"hodnota": 54625965.36, "s_dph": False}],
         "nabidkova": [{"hodnota": 60144956.84, "s_dph": True}, {"hodnota": 49706575.90, "s_dph": False}]}]}]}]
    c = pr.casti_akce(zak, [dict(sml("s0", "stavba", castka=49706575.90, url="u-s0"),
                                 castky=[{"hodnota": 49706575.90, "s_dph": False}, {"hodnota": 60144956.84, "s_dph": True}]),
                            dict(sml("s1", "stavba", 1, navazuje="is0"),
                                 castky=[{"hodnota": 4919389.46, "s_dph": False}, {"hodnota": 5952461.25, "s_dph": True}])])
    (st,) = c
    assert st["puvodni"]["s_dph"] == 60144956.84 and st["puvodni"]["zdroj_druh"] == "registr"
    assert st["vysoutezena"] == {"bez_dph": 49706575.90, "s_dph": 60144956.84}
    assert st["cena_po_dodatcich_s_dph"] == 66097418.09 and st["souhlas_ezak"] is True


def test_dokonceni_z_yaml_s_datem_bez_uvozovek():
    import datetime, json
    data = {"jednani": [], "usneseni": [], "rozpoctova_opatreni": [], "zakazky": [], "smlouvy": []}
    p = {"id": "x", "nazev": "X", "vazby": {"hledat": ["nic"]},
         "dokonceni": {"datum": datetime.date(2026, 11, 20), "popis": "kolaudace", "url": "u"}}
    k = pr.sestav_projekt(p, data)
    assert k["faze"] == "dokonceno" and k["dokonceni"]["datum"] == "2026-11-20"
    json.dumps(k)


def test_puvod_ceny_po_zakladech_dph():
    """Nabídka jen bez DPH, smluvní cena E-ZAK s DPH už po dodatcích → s DPH se po dodatcích nepočítá."""
    zak = [{"id": "z1", "role": "stavba", "url": "e", "casti": [{"registr_smluv": [], "vitezove": [
        {"nazev": "A", "smluvni": [{"hodnota": 145.20, "s_dph": True}], "nabidkova": [{"hodnota": 100.0, "s_dph": False}]}]}]}]
    (c,) = pr.casti_akce(zak, [sml("d1", "stavba", 1, 20.0, navazuje="x")])
    assert c["puvodni"]["zaklady_z_ezak_po_dodatcich"] == ["s_dph"]
    assert c["cena_po_dodatcich"] == 120.0 and c["neuplne_cena_po_dodatcich"] == []
    # s DPH: smluvní cena E-ZAK už po dodatcích + dodatek → sečteno, ale označeno
    assert c["cena_po_dodatcich_s_dph"] == 169.4
    assert c["neuplne_cena_po_dodatcich_s_dph"] == ["původní cena z E-ZAK může už zahrnovat dodatky"]


def test_skladba_ceny_akce():
    casti = [{"role": "stavba", "cena_po_dodatcich_s_dph": 66097418.09},
             {"role": "projekt", "cena_po_dodatcich_s_dph": 1092000.0},
             {"role": "administrace", "cena_po_dodatcich_s_dph": 90750.0},
             {"role": "technicky_dozor", "cena_po_dodatcich_s_dph": 246500.0},
             {"role": "bozp", "cena_po_dodatcich_s_dph": 177446.5},
             {"role": "vybaveni", "cena_po_dodatcich_s_dph": 0.1},
             {"role": "vybaveni", "cena_po_dodatcich_s_dph": 0.2}]
    sk = {x["skupina"]: x for x in pr.skladba(casti)}
    assert sk["priprava"]["castka"] == 1182750.0 and sk["priprava"]["casti"] == 2
    assert sk["dozor"]["castka"] == 423946.5
    assert sk["vybaveni"]["castka"] == 0.3                    # haléře bez chyby plovoucí čárky
    assert all(x["druh"] == "smluvni" and x["s_dph"] is True for x in sk.values())
    casti[1]["cena_po_dodatcich_s_dph"] = None
    sk = {x["skupina"]: x for x in pr.skladba(casti)}
    assert sk["priprava"]["castka"] == 90750.0 and sk["priprava"]["nezname"] == ["projekt"]
    assert [x["skupina"] for x in pr.skladba(casti[:1])] == ["stavba"]


def test_dopocet_dph_z_ceny_po_dodatcich_nedostane_dodatky_znovu():
    zak = [{"id": "z1", "role": "stavba", "url": "e", "casti": [{"registr_smluv": [], "vitezove": [
        {"nazev": "A", "smluvni": [{"hodnota": 120.0, "s_dph": False}], "nabidkova": []}]}]}]
    (c,) = pr.casti_akce(zak, [sml("d1", "stavba", 1, 20.0, navazuje="x")])
    assert c["puvodni"]["s_dph_dopocteno"] and c["puvodni"]["zaklady_z_ezak_po_dodatcich"] == ["bez_dph", "s_dph"]
    assert c["cena_po_dodatcich"] == 140.0 and c["neuplne_cena_po_dodatcich"] == ["původní cena z E-ZAK může už zahrnovat dodatky"]
    assert c["neuplne_cena_po_dodatcich_s_dph"] == ["původní cena z E-ZAK může už zahrnovat dodatky"]


def test_celkova_cena_soucet_znamych_casti():
    casti = [{"role": "stavba", "puvodni": None, "cena_po_dodatcich": None, "neuplne_cena_po_dodatcich": [],
              "cena_po_dodatcich_s_dph": 66097418.09, "neuplne_cena_po_dodatcich_s_dph": []},
             {"role": "projekt", "puvodni": None, "cena_po_dodatcich": None, "neuplne_cena_po_dodatcich": [],
              "cena_po_dodatcich_s_dph": 929500.0,
              "neuplne_cena_po_dodatcich_s_dph": ["původní cena z E-ZAK může už zahrnovat dodatky"]},
             {"role": "bozp", "puvodni": None, "cena_po_dodatcich": None, "neuplne_cena_po_dodatcich": [],
              "cena_po_dodatcich_s_dph": None, "neuplne_cena_po_dodatcich_s_dph": ["původní cena není známa"]}]
    c = pr.souhrn([], casti)["celkova_cena_s_dph"]
    assert c["castka"] == 67026918.09 and c["neuplne"] == ["projekt", "bozp"]
    assert c["druh"] == "smluvni" and c["s_dph"] is True


def test_dodatek_s_celkovou_cenou_a_bez_vazby_v_registru():
    """Balneo LDA (Slatinné lázně): dodatky bez `navazuje_na`, č. 1 a 3 uvádějí novou celkovou cenu, č. 2 změnu."""
    def d(id_, n, h):
        return dict(sml(id_, "stavba", n, h), strany=[{"nazev": "Metrostav CZ s.r.o.", "ico": "25021915", "jmeno_podnikatele": None}])
    sm = [dict(sml("s0", "stavba", castka=64330560.0), strany=[{"nazev": "Metrostav DIZ s.r.o.", "ico": "25021915",
                                                                  "jmeno_podnikatele": None}]),
          d("s1", 1, 64480654.46), d("s2", 2, 1189186.64), d("s3", 3, 65226157.70)]
    (c,) = pr.casti_akce([], sm)
    zm = [(x["cislo"], x["bez_dph"], x.get("castka_je_celkova", False)) for x in c["dodatky"]]
    assert zm == [(1, 150094.46, True), (2, 1189186.64, False), (3, -443683.4, True)]
    assert c["cena_po_dodatcich"] == 65226157.70 and c["neuplne_cena_po_dodatcich"] == []
    # dodatek z jiné firmy (jiné IČO) se nepřipojí
    sm.append(dict(sml("x1", "stavba", 1, 5.0), strany=[{"nazev": "Jiná a.s.", "ico": "1", "jmeno_podnikatele": None}]))
    assert len(pr.casti_akce([], sm)) == 2


def test_spojeni_jen_podle_role_hlida_cenu():
    sm = [dict(sml("p0", "projekt", castka=190000.0), strany=[{"nazev": "fyzická osoba", "jmeno_podnikatele": None}])]
    zak = [{"id": "z1", "role": "projekt", "url": "e", "casti": [{"registr_smluv": [], "vitezove": [
        {"nazev": "JK s.r.o.", "smluvni": [{"hodnota": 1982000.0, "s_dph": False}], "nabidkova": []}]}]}]
    assert len(pr.casti_akce(zak, sm)) == 2                  # 190 000 vs 1 982 000 → dvě různé smlouvy
    sm[0]["castky"] = [{"hodnota": 1900000.0, "s_dph": False}]
    assert len(pr.casti_akce(zak, sm)) == 1


def test_celkova_cena_s_dph_po_dopoctu_dph_starsiho_dodatku():
    sm = [dict(sml("s0", "stavba"), castky=[{"hodnota": 100.0, "s_dph": False}, {"hodnota": 121.0, "s_dph": True}]),
          dict(sml("s1", "stavba", 1, navazuje="is0"), castky=[{"hodnota": 10.0, "s_dph": False}]),
          dict(sml("s2", "stavba", 2, navazuje="is0"), castky=[{"hodnota": 120.0, "s_dph": False}, {"hodnota": 145.2, "s_dph": True}])]
    (c,) = pr.casti_akce([], sm)
    assert c["cena_po_dodatcich"] == 120.0 and c["cena_po_dodatcich_s_dph"] == 145.2
    assert c["dodatky"][1]["castka_je_celkova"] and c["dodatky"][1]["s_dph"] == 12.1


def test_vyslovna_vazba_dodatku_ma_prednost_a_ico_vazba_je_nase_propojeni():
    f = [{"nazev": "Firma s.r.o.", "ico": "9", "jmeno_podnikatele": None}]
    sm = [dict(sml("s0", "stavba", castka=100.0), strany=f),
          dict(sml("s1", "stavba", 1, 5.0, navazuje="jina-puvodni"), strany=f)]
    assert len(pr.casti_akce([], sm)) == 2
    sm[1]["navazuje_na"] = None
    (c,) = pr.casti_akce([], sm)
    assert c["vazba_dodatku"] == "nase_propojeni" and c["cena_po_dodatcich"] == 105.0


def test_blizkost_cen_podle_nabidky():
    assert pr._ceny_blizko({"castky": [{"hodnota": 100.0, "s_dph": False}]},
                           {"smluvni": [{"hodnota": 130.0, "s_dph": False}], "nabidkova": [{"hodnota": 100.0, "s_dph": False}]})


def test_dodatek_termin_podle_predmetu_registru():
    sm = [sml("s0", "stavba", castka=545631.8),
          dict(sml("s1", "stavba", 1, navazuje="is0"), predmet="Rozšíření veřejného osvětlení v Branné - dodatek č. 1 (termín)")]
    (c,) = pr.casti_akce([], sm)
    assert c["dodatky"][0]["jen_termin"] and c["dodatky"][0]["doklad_usneseni"] == "predmet_registru"
    assert c["neuplne_cena_po_dodatcich"] == [] and c["cena_po_dodatcich"] == 545631.8


def test_automaticke_karty_ze_stavebnich_zakazek():
    def zak(id_, nazev, cena, druh="stavebni", datum="2026-02-09", ico="00247618"):
        return {"id": id_, "subjekt_ico": ico, "nazev": nazev, "druh": druh, "stav": "dokončen", "datum_zahajeni": datum,
                "url": "e", "casti": [{"vitezove": [{"castky": [{"druh": "smluvni", "s_dph": True, "hodnota": cena}]}]}]}
    data_ = {"zakazky": [zak("ezak-VZ-914", "Stavební úpravy MK v ul. Budějovické v Třeboni", 14493110.17),
                         zak("ezak-VZ-1", "Malá oprava", 500000.0), zak("ezak-VZ-2", "Elektřina", 5e7, druh="dodavky"),
                         zak("ezak-VZ-3", "Stará akce", 5e6, datum="2024-12-31"), zak("ezak-VZ-4", "Lázně", 5e6, ico="25179896"),
                         zak("ezak-VZ-5", "Už v kartě", 5e6)]}
    auto = pr.automaticke_projekty(data_, [{"zakazky": [{"id": "ezak-VZ-5"}]}])
    assert [a["id"] for a in auto] == ["auto-vz-914"] and auto[0]["oblast"] == "doprava" and auto[0]["automaticka"]
    vzor = auto[0]["vazby"]["hledat"][0]
    import re
    assert re.search(vzor, "Činnost TDS při provádění stavby Stavební úpravy MK v ul. Budějovické v Třeboni.")
    assert re.search(vzor, "Stavební  úpravy MK v ul. Budějovické - dodatek č. 1")
    assert re.search(auto[0]["vazby"]["vyloucit"][0], "Rámcová příkazní smlouva - Administrování veřejných zakázek")


def test_ramcova_smlouva_se_nepritahne_pres_navazanou_dilci():
    sm = [{"id": "r", "id_smlouvy": "R", "navazuje_na": None, "predmet": "Rámcová příkazní smlouva - Administrování",
           "datum_uzavreni": "2025-01-01", "strany": [], "castky": [], "url": "u"},
          {"id": "a", "id_smlouvy": "A", "navazuje_na": "R", "predmet": "Administrace zadávacího řízení VZ Budějovická",
           "datum_uzavreni": "2025-02-01", "strany": [], "castky": [], "url": "u"},
          {"id": "b", "id_smlouvy": "B", "navazuje_na": "R", "predmet": "Administrace zadávacího řízení VZ Jiná akce",
           "datum_uzavreni": "2025-02-01", "strany": [], "castky": [], "url": "u"}]
    p = {"id": "x", "nazev": "X", "vazby": {"hledat": ["Budějovick"], "vyloucit": ["[Rr]ámcov"]}}
    k = pr.sestav_projekt(p, data(smlouvy=sm))
    assert [s["id"] for s in k["smlouvy"]] == ["a"]


def test_prirazeni_sprm_pravidlem_a_z_yaml():
    akt = {280: {"id": 280, "aktivita": "Komplexní rekonstrukce komunikací vč. sítí", "opatreni": "2. Technická infrastruktura",
                 "osa_nazev": "Doprava", "stav": "Plánováno"},
           351: {"id": 351, "aktivita": "Budování dětských hřišť", "opatreni": "3. Sportovní infrastruktura",
                 "osa_nazev": "Kultura", "stav": "Hotovo"}}
    pravidla = [{"vzor": r"\bMK\b", "sprm_id": 280, "potvrzeno": False}, {"vzor": "hřiště", "sprm_id": 351, "potvrzeno": True}]
    (s,) = pr.prirad_sprm({"nazev": "Stavební úpravy MK v ul. Budějovické"}, {}, akt, pravidla)
    assert s["id"] == 280 and s["potvrzeno"] is False and s["opatreni"] == "2. Technická infrastruktura"
    (s,) = pr.prirad_sprm({"nazev": "Dětské HŘIŠTĚ Kopeček".replace("HŘIŠTĚ", "hřiště")}, {}, akt, pravidla)
    assert s["id"] == 351 and s["potvrzeno"] is True
    assert pr.prirad_sprm({"nazev": "Kašna"}, {}, akt, pravidla) == []
    # YAML karty má přednost a je potvrzené; prázdný seznam = výslovně k žádnému opatření
    (s,) = pr.prirad_sprm({"nazev": "Stavební úpravy MK"}, {"sprm": [351]}, akt, pravidla)
    assert s["id"] == 351 and s["potvrzeno"] is True
    assert pr.prirad_sprm({"nazev": "Stavební úpravy MK"}, {"sprm": []}, akt, pravidla) == []
    assert pr.prirad_sprm({"nazev": "Stavební úpravy MK"}, {}, {}, pravidla) == []
