"""Testy AI vrstvy: pořadí a přeskakování poskytovatelů, schéma, citace, strop, nezávislost ověření."""
import pytest

from pipeline import ai
from pipeline.ai import AIChyba, Brana, StropVyčerpán

SCHEMA = {"type": "object", "required": ["tema"], "properties": {"tema": {"type": "string"}}}


def konfig(**kw):
    k = ai.nacti_konfig()
    k.update(kw)
    return k


def adapter(text, poznamka=None):
    def f(prompt, model, env, k):
        if poznamka is not None:
            poznamka.append(model)
        if isinstance(text, Exception):
            raise text
        return text
    return f


def vse(text):
    return {n: adapter(text) for n in ("claude_cli", "anthropic_api", "openai_api", "openai_compatible")}


def test_repozitarni_konfig_je_v_poradku():
    assert ai.zkontroluj_konfig(ai.nacti_konfig()) == []


def test_bez_secretu_se_krok_preskoci():
    assert Brana(konfig(), env={}, adaptery=vse('{"tema":"x"}')).zeptej_se("anotace", "p", SCHEMA) is None


def test_prvni_dostupny_a_puvod():
    b = Brana(konfig(), env={"ANTHROPIC_API_KEY": "x", "OPENAI_API_KEY": "y"}, adaptery=vse('```json\n{"tema":"x"}\n```'))
    v = b.zeptej_se("anotace", "p", SCHEMA)
    assert v.data == {"tema": "x"} and v.puvod() == {"poskytovatel": "anthropic_api", "model": "claude-sonnet-5-5"}


def test_pri_chybe_dalsi_v_poradi():
    a = vse('{"tema":"x"}')
    a["claude_cli"] = adapter(AIChyba("pad"))
    v = Brana(konfig(), env={"CLAUDE_CODE_OAUTH_TOKEN": "t", "OPENAI_API_KEY": "y"}, adaptery=a).zeptej_se("anotace", "p", SCHEMA)
    assert v.poskytovatel == "openai_api"


def test_spatne_schema_je_chyba():
    b = Brana(konfig(), env={"OPENAI_API_KEY": "y"}, adaptery=vse('{"jine":1}'))
    with pytest.raises(AIChyba, match="chybí tema"):
        b.zeptej_se("anotace", "p", SCHEMA)


def test_overeni_jiny_vyrobce():
    volane = []
    a = {n: adapter('{"tema":"x"}', volane) for n in ("claude_cli", "openai_api")}
    b = Brana(konfig(), env={"CLAUDE_CODE_OAUTH_TOKEN": "t", "OPENAI_API_KEY": "y"}, adaptery=a)
    assert b.zeptej_se("overeni", "p", SCHEMA, vyloucit_vyrobce="openai").poskytovatel == "claude_cli"
    # když je jediný dostupný od stejného výrobce, krok se přeskočí
    b2 = Brana(konfig(), env={"OPENAI_API_KEY": "y"}, adaptery=a)
    assert b2.zeptej_se("overeni", "p", SCHEMA, vyloucit_vyrobce="openai") is None


def test_strop_volani():
    b = Brana(konfig(max_volani_za_beh=1), env={"OPENAI_API_KEY": "y"}, adaptery=vse('{"tema":"x"}'))
    b.zeptej_se("anotace", "p", SCHEMA)
    with pytest.raises(StropVyčerpán):
        b.zeptej_se("anotace", "p", SCHEMA)


def test_openai_compatible_vyzaduje_adresu():
    k = konfig()
    k["role"]["x"] = [{"poskytovatel": "openai_compatible", "model": "m"}]
    assert ai.dostupne(k, "x", {"OPENAI_COMPATIBLE_API_KEY": "k"}) == []
    assert len(ai.dostupne(k, "x", {"OPENAI_COMPATIBLE_API_KEY": "k", "OPENAI_COMPATIBLE_BASE_URL": "https://e"})) == 1


def test_konfig_stejny_vyrobce_overeni():
    k = konfig()
    k["role"]["overeni"] = [{"poskytovatel": "anthropic_api", "model": "m"}]
    assert ai.zkontroluj_konfig(k)


def test_citace_doslovne_po_sjednoceni_mezer():
    assert ai.overit_citace("program  1.\njednání", "Schvaluje program 1. jednání rady")
    assert not ai.overit_citace("program 2. jednání", "Schvaluje program 1. jednání rady")
    assert not ai.overit_citace("  ", "cokoli")
