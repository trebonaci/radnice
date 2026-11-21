"""Karty míst a služeb a proud „Co se mění“ (#183): pipeline/mista.py."""
from pipeline import mista


def _data():
    j = [{"id": "rm-1", "organ": "rada", "datum": "2026-09-09",
          "dokument": {"dokument_id": "zapis-rm-1", "url": "https://example.cz/rm1.pdf"}},
         {"id": "rm-2", "organ": "rada", "datum": "2026-10-07", "dokument": None}]
    po = lambda text, kdo: {"text": text, "kdo": kdo, "oblast": "socialni", "plati_od": None,
                            "citace": {"dokument_id": "zapis-rm-1", "strany": [4], "text": "x"}}
    u = [{"id": "u1", "cislo": "RM 1/2026-1", "jednani_id": "rm-1", "vysledek_hlasovani": "prijato",
          "pro_obcany": po("Klubovna zůstává seniorům.", "Klubovna, Chelčického 2/II"), "pro_obcany_ai": True},
         {"id": "u2", "cislo": "RM 2/2026-2", "jednani_id": "rm-2", "vysledek_hlasovani": "prijato",
          "pro_obcany": po("Město přijme darem loutkové divadlo.", "Loutkové divadlo"), "pro_obcany_ai": True},
         {"id": "u3", "cislo": "RM 3/2026-2", "jednani_id": "rm-2", "vysledek_hlasovani": "neprijato",
          "pro_obcany": po("Nepřijato.", "DPS Chelčického")}]
    return {"jednani": j, "usneseni": u}


def test_proud_zmen():
    z = mista.zmeny(_data())
    assert [x["usneseni_id"] for x in z] == ["u2", "u1"]          # nejnovější první, nepřijaté ne
    assert z[1]["url"] == "https://example.cz/rm1.pdf#page=4" and z[1]["pro_obcany_ai"] is True


def test_karta_mista(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data/mista.yaml").write_text(
        "mista:\n  - id: dps\n    nazev: DPS Chelčického\n    oblast: socialni\n    zmeny: ['Klubovna, Chelčického']\n"
        "    investice: [kotle]\n    zasobnik: [z1]\n", encoding="utf-8")
    karty = [{"id": "kotle", "nazev": "Výměna kotlů", "faze": "probiha"}]
    (tmp_path / "data/mista.yaml").write_text((tmp_path / "data/mista.yaml").read_text(encoding="utf-8")
                                              .replace("[kotle]", "[kotle, neni]"), encoding="utf-8")
    zas = [{"typ": "polozka", "id": "z1", "nazev": "Kotelny", "pripravenost": {"nazev": "projekt zadán"}}]
    m, z, chyby = mista.sestav(tmp_path, _data(), karty, zas)
    assert chyby == []
    assert m[0]["zmeny"] == ["zmena-u1"] and m[0]["investice"][0]["faze"] == "probiha"
    assert m[0]["zasobnik"] == [{"id": "z1", "nazev": "Kotelny", "pripravenost": "projekt zadán", "jistota": "dolozeno"}]
    assert m[0]["posledni_zmena"] == "2026-09-09" and m[0]["geometrie"] is None
    po = {x["usneseni_id"]: x for x in z}
    assert po["u1"]["misto_id"] == "dps" and po["u1"]["misto_jistota"] == "nase_propojeni"
    assert po["u2"]["misto_id"] is None                               # změna bez karty zůstává v proudu


def test_kontrola_katalogu():
    chyby = mista.zkontroluj([{"id": "a", "nazev": "A", "oblast": "vesmir", "zmeny": ["("], "investice": ["x"],
                               "zasobnik": ["y"]}, {"id": "a"}], [], [])
    for co in ("neznámá oblast", "chybný vzor", "duplicitní", "chybí pole"):
        assert any(co in c for c in chyby), co
