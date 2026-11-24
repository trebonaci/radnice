"""Relevance usnesení k investicím (#278): kód pozná investiční usnesení z textu (širší definice)."""
from pipeline.relevance import investicni


def test_zakazka_a_vyber_dodavatele():
    assert investicni("Výběr zhotovitele stavby – nejvýhodnější nabídka")[0]
    assert investicni("Zadávací řízení na veřejnou zakázku")[0]


def test_smlouva_o_dilo_a_dodatek():
    assert investicni("Dodatek č. 4 ke smlouvě o dílo na přístavbu")[0]
    assert investicni("Smlouva o dílo – technický dozor stavebníka")[0]


def test_stavba_vcetne_zatepleni_a_siti():
    assert investicni("Rekonstrukce ulice včetně inženýrských sítí")[0]
    assert investicni("Zateplení domů čp. 672 a 1050")[0]
    assert investicni("ZTV Líbalova ulice")[0]


def test_rozpoctove_opatreni_investicni():
    assert investicni("Rozpočtové opatření č. 51 – kapitálové výdaje na akci")[0]
    # rozpočtové opatření bez investičního signálu se nebere jako investiční
    assert not investicni("Rozpočtové opatření č. 50 – dotace spolkům na činnost")[0]


def test_majetek_a_dotace_na_investici():
    assert investicni("Záměr prodeje pozemku pro stavbu")[0]
    assert investicni("Dotace na rekonstrukci sportovního hřiště")[0]


def test_neinvesticni_se_nebere():
    for t in ["Program jednání a zveřejňování zápisů", "Prodloužení nájmu bytu v čp. 2",
              "Členové školské rady při ZŠ Na Sadech", "Veřejnosprávní kontrola hospodaření ZŠ"]:
        assert not investicni(t)[0], t


def test_vraci_duvod_skupiny():
    je, duvod = investicni("Dodatek č. 1 ke smlouvě o dílo")
    assert je and duvod == "smlouva o dílo"
