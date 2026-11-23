from pipeline.projekty import casti_akce


def test_smlouva_ezak_podle_casti_a_viteze():
    def cast(datum, jmeno, ico):
        return {"nazev": jmeno, "datum_uzavreni_smlouvy": datum, "vitezove": [
            {"nazev": jmeno, "ico": ico, "smluvni": [{"hodnota": 784080, "s_dph": True}]}]}

    zakazka = {"id": "ezak-VZ-913", "nazev": "Technický dozor", "role": "technicky_dozor",
               "url": "https://example.cz/913", "casti": [cast("2026-02-11", "IPD", "1"),
                                                          cast(None, "B", "2")]}
    udalosti = []
    bez_udalosti = casti_akce([zakazka], [])
    assert casti_akce([zakazka], [], udalosti=udalosti) == bez_udalosti
    assert [(e["datum"], e["ezak_smlouva"]["dodavatel"], e["ezak_smlouva"]["s_dph"])
            for e in udalosti] == [("2026-02-11", "IPD", 784080)]
