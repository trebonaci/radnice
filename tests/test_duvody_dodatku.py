"""Důvod dodatku z úryvků (#274): kód vybere druh změny s doslovnou citací, boilerplate smlouvy nebere."""
from pipeline import duvody_dodatku as d


def test_vicepace_a_meneprace_z_dodatku():
    t = "Tímto dodatkem se mění cena díla. V průběhu realizace díla vznikly nepředvídané vícepráce a méněpráce nutné pro řádné provedení díla. Cena se zvyšuje."
    r = d.z_uryvku(t)
    assert r and r["druh"] == "vícepráce" and "méněpráce" in r["dalsi"]
    assert r["citace"] in " ".join(t.split()) and "vícepráce a méněpráce" in r["citace"]


def test_zmena_terminu_z_dodatku():
    t = "Dodatkem č. 2 dochází ke změně termínu dokončení díla z důvodu prodloužení stavebního řízení."
    r = d.z_uryvku(t)
    assert r and r["druh"] == "změna termínu dokončení"


def test_boilerplate_puvodni_smlouvy_se_nebere():
    # obecná věta ze smlouvy bez zmínky o dodatku/změnovém listu → žádný důvod
    t = "Zhotovitel je povinen dokončit a předat dílo v termínu dle této smlouvy. Vícepráce se řeší podle čl. IV."
    assert d.z_uryvku(t) is None


def test_osobni_udaj_v_citaci_se_preskoci():
    t = "Tímto dodatkem se mění vícepráce, zhotovitel se sídlem Husova 1, IČO 12345678, provede dílo."
    # citace kolem „vícepráce“ by obsahovala IČO/sídlo → nebrat
    assert d.z_uryvku(t) is None


def test_sestav_vraci_citaci_ze_zdroje():
    raw = {"rs-1": {"url": "https://smlouvy.gov.cz/smlouva/1", "soubory": [
        {"url": "https://smlouvy.gov.cz/soubor/1.pdf", "uryvky": [
            {"strana": 2, "text": "Tímto dodatkem vznikly vícepráce nutné k dokončení díla podle Změnového listu č. 1."}]}]}}
    vys, chyby = d.sestav(raw)
    assert not chyby and len(vys) == 1
    v = vys[0]
    assert v["zdroj_id"] == "rs-1" and v["druh"] == "vícepráce" and v["duvod_ai"] is False
    assert v["citace"] in raw["rs-1"]["soubory"][0]["uryvky"][0]["text"]
    assert v["url"].endswith("#page=2")
