"""Přehled dění na radnici pro web (#187): pipeline/prehled.py."""
from pipeline import prehled

ZMENA = {"id": "zmena-u1", "text": "Klubovna zůstává seniorům.", "kdo": "Klubovna, Chelčického 2/II", "oblast": "socialni",
         "plati_od": "2027-01-01", "datum": "2026-10-21", "organ": "rada", "usneseni_cislo": "RM 497/2026-113",
         "url": "https://example.cz/z.pdf#page=4", "pro_obcany_ai": True, "misto_id": "dps"}
KARTA = {"id": "hala", "nazev": "Přístavba tělocvičen", "popis": "Dvě nové tělocvičny.", "oblast": "sport",
         "faze": "probiha", "faze_jistota": "nase_propojeni",
         "posledni_udalost": {"datum": "2026-11-02", "typ": "dodatek", "kratce": "dodatek 5 (smlouva o dílo)",
                              "url": "https://smlouvy.gov.cz/smlouva/1"}}
POLOZKA = {"typ": "polozka", "id": "parkovaci-dum", "nazev": "Parkovací dům", "oblast": "doprava", "faze": "zasobnik",
           "nositele": [{"ico": "00247618", "nazev": "Město Třeboň"}],
           "pripravenost": {"nazev": "projektová dokumentace zadána",
                            "doklad": {"typ": "smlouva", "text": "Úprava PD parkovacího domu", "datum": "2026-04-24",
                                       "url": "https://smlouvy.gov.cz/smlouva/2"}},
           "doklady": [{"typ": "smlouva", "text": "x", "datum": "2026-04-24", "url": "u"}]}


def test_zmena_je_rozhodnuti_se_zdrojem_a_dalsim_krokem():
    z = prehled.ze_zmen([ZMENA])[0]
    assert z["typ"] == "Rada města" and z["stav"] == "rozhodnuto" and z["oblast_nazev"] == "Sociální služby"
    assert z["zdroj"] == {"nazev": "Zápis z jednání rady města, 21. 10. 2026 – usnesení RM 497/2026-113",
                          "url": "https://example.cz/z.pdf#page=4", "druh": "zápis", "pdf": True, "strana": 4,
                          "datum": "2026-10-21"}
    assert z["dalsi_krok"] == "Platí od 1. 1. 2027." and z["text_ai"] is True


def test_investice_a_zasobnik():
    i = prehled.z_investic([KARTA])[0]
    assert i["stav"] == "realizuje_se" and i["datum"] == "2026-11-02"
    assert i["zdroj"]["nazev"] == "Registr smluv: dodatek 5 (smlouva o dílo), 2. 11. 2026" and i["zdroj"]["pdf"] is False
    p = prehled.ze_zasobniku([POLOZKA, POLOZKA | {"id": "hotovo", "faze": "realizovano"}])
    assert len(p) == 1 and p[0]["stav"] == "planuje_se"
    assert p[0]["shrnuti"] == "Připravuje se: projektová dokumentace zadána."
    assert p[0]["zdroj"]["url"] == "https://smlouvy.gov.cz/smlouva/2"


def test_razeni_a_bez_zdroje_se_nezverejnuje():
    bez = KARTA | {"id": "bez", "posledni_udalost": {"datum": "2026-12-01", "typ": "smlouva", "kratce": "x"}}
    zaznamy = prehled.sestav([ZMENA], [KARTA, bez], [POLOZKA])
    assert [z["id"] for z in zaznamy] == ["investice-hala", "zmena-u1", "zasobnik-parkovaci-dum"]
    assert all(z["stav_nazev"] and z["stav_popis"] for z in zaznamy)
