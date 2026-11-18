# Pravidla pro AI agenty (Claude, Codex)

Tento soubor čtou všichni agenti pracující v repozitáři. Platí pro Claude i Codex stejně.

## Nejdřív přečti
1. `ZADANI.md`: cíl, rozsah, pravidla obsahu, fáze.
2. `DATOVY_MODEL.md`: entity a pole.
3. Issue, na kterém pracuješ.

## Jak pracujeme
- Jeden issue = jedna větev = jeden PR. Větev `<agent>/<cislo-issue>-<kratky-popis>`, např. `claude/3-registr-smluv`.
- Nikdy necommituj přímo do `main`. Merguje jen Ondřej.
- Merge ≠ zveřejnění. Na web jde jen to, co Ondřej výslovně schválí („schváleno ke zveřejnění“).
- Kdo PR napsal, ten ho nereviewuje. PR od Clauda kontroluje Codex a obráceně.
- PR lze sloučit jen se zelenou automatickou kontrolou (`.github/workflows/ci.yml`: sestavení dat, shoda `data/` se sestavením, testy). Před pushem spusť `python -m pipeline.sestav` a `python -m pytest` lokálně.
- PR popis: co se změnilo, jak to ověřit, co zůstává otevřené, zdroje dat použité v PR.
- Pokud zadání v issue nestačí nebo je v rozporu se `ZADANI.md`, zastav se a napiš otázku do issue místo dohadu.

## Pravidla obsahu (výtah ze ZADANI.md kap. 4; při rozporu platí ZADANI.md)
- Každý údaj má zdroj (URL, datum, u PDF strana/bod).
- Úrovně jistoty: `doloženo` / `naše propojení` / `nevíme`.
- Druhy částek se nesčítají napříč (odhad ≠ rozpočet ≠ smluvní cena ≠ zaplaceno). Vždy uveď s DPH / bez DPH / neuvedeno.
- AI nepočítá čísla: čísla se opisují ze zdroje a počítá je testovaný kód.
- Výstupy AI mají citaci, která se strojově ověří (doslovná shoda ve zdroji), a příznak `*_ai`.
- Fyzické osoby anonymizovat. Volení zástupci jménem, úředníci funkcí.
- Do repozitáře ani do promptů nepatří interní dokumenty (GINIS, neveřejné podklady), tokeny a hesla. Tajné hodnoty jen přes GitHub Secrets.
- Datové sekce píšeme neutrálně. Hodnocení patří jen do `analyzy/` a je podepsané.

## Technické konvence
- Python 3.12, závislosti v `requirements.txt`. Skripty spustitelné bez interaktivního vstupu.
- `raw/`: stažená data beze změn (velké soubory necommitovat, jen manifest s URL a sha256).
- `data/`: odvozená data (JSON/CSV), reprodukovatelná ze skriptů.
- `data/projekty/*.yaml`: ručně spravované projekty; agent je upravuje jen na výslovný pokyn v issue.
- Testy v `tests/` (pytest). Každý výpočet částek má test.
- Kódování UTF-8, česká jména polí podle `DATOVY_MODEL.md` (bez diakritiky).
