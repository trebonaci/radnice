"""Zprávy pro „Co se děje“ (#244): slučování výběru a smlouvy, skupiny, KPI za 30 dní."""
from datetime import date

from web.zpravy import dodavatel, kpi_30_dni, prepocitej_skupiny, slouc_vyber_a_smlouvu, zpravy_pro_web


def zp(id, druh, datum, okruh="skoly", dod=None, castka=None, projekt=None, skupina=None, jistota="naše propojení"):
    z = {"id": id, "druh": druh, "datum": datum, "okruh": okruh, "titulek": "T " + id,
         "shrnuti": f"Smlouva s dodavatelem {dod}." if dod else "Věta.", "castka": castka,
         "projekt_id": projekt, "zdroje": [{"nazev": id, "url": "https://x/" + id}], "jistota": jistota}
    if skupina:
        z["skupina"] = skupina
    return z


C = {"hodnota": 1000.0, "druh": "smluvni", "s_dph": True}


def test_dodavatel_ze_shrnuti():
    assert dodavatel(zp("a", "smlouva", "2026-11-01", dod="ABC s.r.o.")) == "abc s.r.o."
    assert dodavatel(zp("b", "usneseni", "2026-11-01")) is None


def test_vyber_a_smlouva_jedne_zakazky_jsou_jeden_radek_se_dvema_zdroji():
    v = zp("v", "vyberove_rizeni", "2026-11-18", dod="ABC s.r.o.", castka=C)
    v["zdroje"] = [{"nazev": "Zadávací profil (E-ZAK): T", "url": "https://x/v"}]
    s = zp("s", "smlouva", "2026-11-18", dod="ABC s.r.o.", castka={**C, "s_dph": False})
    s["zdroje"] = [{"nazev": "Registr smluv: T", "url": "https://x/s"}]
    r = slouc_vyber_a_smlouvu([v, s])
    assert len(r) == 1 and r[0]["druhy"] == ["vyberove_rizeni", "smlouva"]
    assert [x["url"] for x in r[0]["zdroje"]] == ["https://x/v", "https://x/s"]
    # zdroje se liší v DPH: obě částky zůstanou s uvedením zdroje a nesčítají se (review #257)
    assert r[0]["castka"] is None
    assert [(c["s_dph"], c["zdroj"]) for c in r[0]["castky"]] == [(True, "Zadávací profil (E-ZAK)"), (False, "Registr smluv")]


def test_shodna_castka_zustane_jedna():
    v = zp("v", "vyberove_rizeni", "2026-11-18", dod="ABC s.r.o.", castka=C)
    s = zp("s", "smlouva", "2026-11-18", dod="ABC s.r.o.", castka=dict(C))
    r = slouc_vyber_a_smlouvu([v, s])
    assert r[0]["castka"] == C and "castky" not in r[0]


def test_ruzna_zakazka_se_neslucuje():
    v = zp("v", "vyberove_rizeni", "2026-11-18", dod="ABC s.r.o.", castka=C)
    jiny_den = zp("s1", "smlouva", "2026-11-19", dod="ABC s.r.o.", castka=C)
    jiny_dod = zp("s2", "smlouva", "2026-11-18", dod="XYZ a.s.", castka=C)
    jina_castka = zp("s3", "smlouva", "2026-11-18", dod="ABC s.r.o.", castka={**C, "hodnota": 5.0})
    assert len(slouc_vyber_a_smlouvu([v, jiny_den, jiny_dod, jina_castka])) == 4


def test_stejny_projekt_se_slouci_i_pri_ruzne_castce():
    v = zp("v", "vyberove_rizeni", "2026-11-18", dod="ABC s.r.o.", castka=C, projekt="p1")
    s = zp("s", "smlouva", "2026-11-18", dod="ABC s.r.o.", castka={**C, "hodnota": 1200.0}, projekt="p1")
    assert len(slouc_vyber_a_smlouvu([v, s])) == 1


def test_jedna_smlouva_se_neslouci_dvakrat():
    v1 = zp("v1", "vyberove_rizeni", "2026-11-18", dod="ABC s.r.o.", castka=C)
    v2 = zp("v2", "vyberove_rizeni", "2026-11-18", dod="ABC s.r.o.", castka=C)
    s = zp("s", "smlouva", "2026-11-18", dod="ABC s.r.o.", castka=C)
    assert len(slouc_vyber_a_smlouvu([v1, v2, s])) == 2


def test_skupina_se_po_slouceni_prepocita():
    sk = {"id": "p:2026-11-18", "nazev": "Akce", "pocet": 2}
    v = zp("v", "vyberove_rizeni", "2026-11-18", dod="A", castka=C, projekt="p", skupina=sk)
    s = zp("s", "smlouva", "2026-11-18", dod="A", castka=C, projekt="p", skupina=sk)
    r = zpravy_pro_web([v, s], ["skoly"], date(2026, 11, 20))["zpravy"]
    assert len(r) == 1 and "skupina" not in r[0]
    t = zp("t", "usneseni", "2026-11-18", projekt="p", skupina=sk)
    assert [x["skupina"]["pocet"] for x in prepocitej_skupiny([v, t])] == [2, 2]


def test_kpi_30_dni_podle_okruhu_a_hranice():
    zs = [zp("a", "usneseni", "2026-11-20", "skoly"), zp("b", "usneseni", "2026-10-22", "skoly"),
          zp("c", "usneseni", "2026-10-21", "skoly"), zp("d", "smlouva", "2026-11-01", "doprava_prostor"),
          zp("e", "smlouva", "2026-11-21", "doprava_prostor")]
    k = kpi_30_dni(zs, ["skoly", "doprava_prostor", "bydleni_pece"], date(2026, 11, 20))
    assert k["od"] == "2026-10-22" and k["do"] == "2026-11-20"
    assert k["okruhy"] == {"skoly": 2, "doprava_prostor": 1, "bydleni_pece": 0} and k["celkem"] == 3
