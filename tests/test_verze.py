from datetime import date

import pytest

from pipeline import verze


def zaznam():
    return {"dokument_id": "d1", "jednani_id": "rm-1", "vyveseno": "2026-11-11", "stazeno": "2026-11-18",
            "sha256": "a" * 64, "bytes": 10}


@pytest.mark.parametrize("stari,interval", [(0, 1), (14, 1), (15, 7), (60, 7), (61, 30), (365, 30), (366, 90)])
def test_interval_podle_stari(stari, interval):
    assert verze.interval_kontroly(stari) == interval


def test_doplni_historii_je_idempotentni():
    z = zaznam()
    assert verze.doplni_historii(z) is True
    kopie = {**z}
    assert verze.doplni_historii(z) is False
    assert z == kopie
    assert z["verze"][0]["sha256"] == "a" * 64
    assert z["dalsi_kontrola"] == "2026-11-19"  # dokument starý 7 dní → kontrola denně


def test_stejny_otisk_nevytvori_verzi_ale_posune_plan():
    z = zaznam()
    verze.doplni_historii(z)
    assert verze.zaznamenej_kontrolu(z, "a" * 64, date(2026, 12, 1)) is False
    assert len(z["verze"]) == 1
    assert z["posledni_kontrola"] == "2026-12-01"
    assert z["dalsi_kontrola"] == "2026-12-08"  # stáří 20 dní → týdně


def test_zmena_otisku_prida_verzi_a_stara_zustane():
    z = zaznam()
    verze.doplni_historii(z)
    assert verze.zaznamenej_kontrolu(z, "b" * 64, date(2026, 11, 20), bytes_=11, zmena="jiná anonymizace") is True
    assert [v["cislo"] for v in z["verze"]] == [1, 2]
    assert z["verze"][0]["sha256"] == "a" * 64
    assert z["verze"][1]["zmena"] == "jiná anonymizace"
    assert z["sha256"] == "b" * 64 and z["bytes"] == 11 and z["stazeno"] == "2026-11-20"
    assert verze.zkontroluj([z]) == []


def test_k_kontrole():
    z = zaznam()
    verze.doplni_historii(z)  # další kontrola 2026-11-19
    assert verze.k_kontrole([z], date(2026, 11, 18)) == []
    assert verze.k_kontrole([z], date(2026, 11, 19)) == [z]
    assert verze.k_kontrole([zaznam()], date(2026, 11, 18)) != []  # bez plánu


def test_zkontroluj_zachyti_nesoulad():
    z = zaznam()
    verze.doplni_historii(z)
    z["sha256"] = "c" * 64
    assert any("není otiskem poslední verze" in c for c in verze.zkontroluj([z]))


def test_skutecny_manifest_je_konzistentni():
    assert verze.zkontroluj(verze.nacti()) == []
