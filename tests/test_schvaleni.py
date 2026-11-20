"""Stav schválení rada → zastupitelstvo (pipeline/schvaleni.py)."""
from pipeline import schvaleni as s

TEXT = "uzavření Smlouvy o bezúplatném převodu pozemku č. 1009992617 mezi Státním pozemkovým úřadem a městem Třeboň"


def u(id_, jednani, text, vysledek="prijato"):
    return {"id": id_, "jednani_id": jednani, "text": text, "vysledek_hlasovani": vysledek}


def test_parovani_a_stavy():
    rm = u("rm-1", "rm-a", "I. schvaluje a doporučuje ZM schválit " + TEXT)
    rm_ceka = u("rm-2", "rm-a", "I. schvaluje a doporučuje ZM schválit prodej pozemku p. č. 9999 v Holičkách")
    rm_sama = u("rm-3", "rm-a", "I. schvaluje " + TEXT)
    zm = u("zm-1", "zm-b", "I. schvaluje " + TEXT)
    zm_drive = u("zm-0", "zm-0", "I. schvaluje prodej pozemku p. č. 9999 v Holičkách")   # dřív než rada → nepárovat
    vse = [rm, rm_ceka, rm_sama, zm, zm_drive]
    s.oznac(vse, {"rm-a": "2026-09-09", "zm-b": "2026-09-21", "zm-0": "2026-09-01"})
    assert rm["schvaleni"] == {"stav": "konecne", "rada_usneseni_id": None, "zm_usneseni_id": "zm-1",
                               "jistota": "nase_propojeni"}
    assert zm["schvaleni"]["rada_usneseni_id"] == "rm-1" and zm["schvaleni"]["stav"] == "konecne"
    assert rm_ceka["schvaleni"]["stav"] == "ceka_na_zm" and rm_sama["schvaleni"]["stav"] == "konecne"


def test_zastupitelstvo_neschvalilo():
    rm = u("rm-1", "rm-a", "I. schvaluje a doporučuje ZM schválit " + TEXT)
    zm = u("zm-1", "zm-b", "I. schvaluje " + TEXT, vysledek="neprijato")
    s.oznac([rm, zm], {"rm-a": "2026-09-09", "zm-b": "2026-09-21"})
    assert rm["schvaleni"]["stav"] == "zm_neschvalilo" and zm["schvaleni"]["stav"] == "neprijato"
def test_neschvaluje_a_jine_cislo_dodatku():
    rm = u("rm-1", "rm-a", "I. schvaluje a doporučuje ZM schválit Dodatek č. 13 ke Zřizovací listině základní školy " + TEXT)
    zm = u("zm-1", "zm-b", "I. neschvaluje Dodatek č. 13 ke Zřizovací listině základní školy " + TEXT)
    s.oznac([rm, zm], {"rm-a": "2026-09-09", "zm-b": "2026-09-21"})
    assert rm["schvaleni"]["stav"] == "zm_neschvalilo"
    rm2 = u("rm-2", "rm-a", "I. schvaluje a doporučuje ZM schválit Dodatek č. 13 ke Zřizovací listině základní školy " + TEXT)
    zm2 = u("zm-2", "zm-b", "I. schvaluje Dodatek č. 14 ke Zřizovací listině základní školy " + TEXT)
    s.oznac([rm2, zm2], {"rm-a": "2026-09-09", "zm-b": "2026-09-21"})
    assert rm2["schvaleni"]["stav"] == "ceka_na_zm"
