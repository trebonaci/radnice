"""Statický web radnice.trebonaci.cz (#191): web/build.py."""
from web import build


def test_sestaveni_bez_zbylych_znacek():
    html = build.sestav()
    assert "__STITEK__" not in html and "__DATA__" not in html
    assert "neschváleno" not in html
    assert "Nejde o web Města Třeboň" in html


def test_nahled_je_oznaceny():
    assert "neschváleno ke zveřejnění" in build.sestav(nahled=True)


def test_datum_z_behu():
    assert build._datum({"zacatek": "2026-11-21T13:41:17+00:00"}) == "21. 11. 2026"
    assert build._datum({}) == ""


def test_usneseni_pro_web_odkaz_na_stranu_a_razeni():
    from web.build import usneseni_pro_web
    jd = [{"id": "rm-1", "organ": "rada", "cislo": "1", "datum": "2026-11-04", "dokument": {"url": "https://z.pdf"}},
          {"id": "zm-1", "organ": "zastupitelstvo", "cislo": "1", "datum": "2026-11-02", "dokument": {"url": "https://y.pdf"}}]
    us = [{"id": "zm-1-u1", "cislo": "ZM 1/2026-1", "jednani_id": "zm-1", "vysledek_hlasovani": "prijato",
           "shrnuti": "S", "shrnuti_ai": True, "kategorie": ["samosprava"], "citace": {"strany": [4]}},
          {"id": "rm-1-u1", "cislo": "RM 1/2026-1", "jednani_id": "rm-1", "vysledek_hlasovani": "neprijato",
           "pro_obcany": {"text": "P"}, "pro_obcany_ai": True, "kategorie": [], "citace": {"strany": []}}]
    r = usneseni_pro_web(us, jd)
    assert [x["id"] for x in r] == ["rm-1-u1", "zm-1-u1"]
    assert r[1]["url"] == "https://y.pdf#page=4" and r[0]["url"] == "https://z.pdf"
    assert r[0]["shrnuti"] == "P" and r[0]["kategorie"] == ["ostatni"] and r[0]["vysledek"] == "neprijato"


def test_co_se_deje_ma_sest_okruhu_a_pet_polozek_menu():
    import re
    html = build.sestav()
    okruhy = re.search(r"const OK=(\[.*?\]);\n", html)
    assert okruhy and okruhy.group(1).count('"popis"') == 6
    menu = re.search(r'<nav id="menu"[^>]*>(.*?)</nav>', html).group(1)
    assert re.findall(r'href="([^"]*)"', menu) == ["#", "#stavby", "#usneseni", "#mista", "#mapa"]
    # Časová osa, Rozpočet a V číslech zůstávají dostupné z patičky
    for h in ("#casova-osa", "#pripravovane", "#dokoncene", "#rozpocet", "#cisla"):
        assert f'href="{h}"' in html


def test_usneseni_pro_web_nese_okruhy():
    from web.build import usneseni_pro_web
    r = usneseni_pro_web([{"id": "u", "jednani_id": "x", "okruh": "skoly", "okruhy": ["skoly", "rozvoj_sprava"]}], [])
    assert r[0]["okruh"] == "skoly" and r[0]["okruhy"] == ["skoly", "rozvoj_sprava"]


def test_mapa_po_okruzich():
    html = build.sestav()
    assert 'okruhChips("mapa")' in html and "data-gtema" not in html
    assert '["stavby","usneseni","mista","mapa","casova-osa"].includes(str)' in html   # okruh v adrese i pro mapu a časovou osu
