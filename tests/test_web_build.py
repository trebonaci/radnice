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
