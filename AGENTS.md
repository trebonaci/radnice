# Pravidla pro AI agenty (Claude, Codex)

Tento soubor čtou všichni agenti pracující v repozitáři. Platí pro Claude i Codex stejně.

## Nejdřív přečti
1. `ZADANI.md`: cíl, rozsah, pravidla obsahu, fáze.
2. `DATOVY_MODEL.md`: entity a pole.
3. Issue, na kterém pracuješ.

## Cíl (pro koho to děláme)
Relevantní, jednoduchá, graficky a jazykově srozumitelná informace pro občany, **co a jak se v Třeboni děje**:
- **měkké aktivity:** změny v přístupu ke sportu, kultuře, sociálním a komunitním službám,
- **tvrdé aktivity:** investice plánované, probíhající a dokončené.

Píšeme pro běžného čtenáře, ne pro úředníky: krátce, bez zkratek a úředních obratů, s odkazem na zdroj. Legislativa a celostátní témata jsou mimo rozsah, pokud nemají přímý dopad na konkrétní věc v Třeboni.

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

## Architektura
Vše běží **nezávisle na počítači Ondřeje** – v GitHub Actions (rozhodnutí 18. 11. 2026). AI se přihlašuje tokenem předplatného uloženým v GitHub Secrets.

```
zdroje (web města, registr smluv, E-ZAK, trebonaci.cz)
   │  pipeline/zdroje/*      stažení + kontrola před zápisem (při chybě zůstanou poslední správná data)
   ▼
raw/   manifest (URL, datum, sha256, verze) + texty po stranách
   │  pipeline/zapisy.py     struktura bez AI (body, usnesení, hlasování)
   │  anotace/*.yaml         AI návrh s doslovnými citacemi
   │  pipeline/sestav.py     anonymizace + kontroly (citace, částky, osoby)
   ▼
data/*.json  ──►  PR  ──►  CI „Kontrola“ + Codex review  ──►  merge (Ondřej)
                                                               │
                                       „schváleno ke zveřejnění“ (Ondřej)
                                                               ▼
                                         WordPress na trebonaci.cz (Vedos)
```

Plánované kroky: jeden běh `pipeline/beh.py` se zámkem (#16), verze dokumentů (#17), štítky věcné relevance (#18), Claude spouštěný štítkem `agent:claude` (#13).

## Zdroje dat – technické poznámky
| Zdroj | Co víme | Ověřeno |
|---|---|---|
| Zápisy rady: `mesto-trebon.cz/.../rada-mesta/zapisy-z-jednani-rady-mesta/volebni-obdobi-2026---2030.html` | PDF v `/uploads/news/id<N>/<soubor>.pdf`, textová vrstva (ne sken), přípona `-A` = verze s anonymizací (nekonzistentní: u RM 5/2026-1 ponecháno jméno, IČO i adresa podnikatelky) | pilot 18. 11. 2026 |
| Zápisy ZM: `.../zastupitelstvo-mesta/zapisy-zastupitelstva-mesta/volebni-obdobi-2026---2030-2.html` | stejný formát; **jmenovité hlasování neobsahují**, jen součty; číslování bodů může nesedět s programem | pilot 18. 11. 2026 |
| Struktura zápisu | `k bodu N` → `Usnesení RM/ZM č. X/RRRR-J` → části `I. schvaluje…` → `Výsledek hlasování: Pro/Proti/Zdrželi se` → `SCHVÁLENO`; protinávrhy a volby kandidátů mají vlastní hlasování | pilot |
| Členové ZM: `mesto-trebon.cz/text/cz/mestsky-urad-trebon/samosprava-mesta/zastupitelstvo-mesta/clenove-zastupitelstva-mesta.html` | 25 členů se stranou; funkce jen u starosty → ostatní ze zápisu ZM | 18. 11. 2026 |
| Registr smluv, E-ZAK (5 profilů), ISVZ | viz issue #9 / PR #14 a `docs/ZDROJE.md` | probíhá |
| trebonaci.cz `/wp-json/trebonaci/v1/projekty` | evidence SPRM (`trebonaci_projekt`) | neověřeno |
| trebonaci.cz `/wp-json/trebonaci/v1/podnety` | vrací i jména podatelů a diskusi → **přímo nepoužívat**, jen omezený výstup | dle Codexu |

Přístup: web města z cloudového prostředí Clauda nedostupný (omezení sítě); stahování přes prohlížeč fungovalo, ale prohlížeč blokuje opakované stahování. Z GitHub Actions zatím neověřeno.

## Stav a další kroky
**Hotovo:** zadání a datový model (#4), pilot zápisů RM 4. 11. a ZM 2. 11. 2026 (#5), CI (#7), 25 zastupitelů (#11).

**Rozpracováno:** orchestrace (#13), zdroje a IČO (#9, PR #14).

**Neověřeno / TODO:**
1. Automatické stahování z webu města v GitHub Actions.
2. Tabulky rozpočtových opatření jsou v datech jen jako surový text.
3. Jméno nevolené osoby bez titulu, které není v `config/osoby.yaml`, kontrola nezachytí – nové zápisy vyžadují lidskou kontrolu.
4. Výstup do WordPressu (šablona stránky, JSON) zatím neexistuje.
