# Zadání: Přehled radnice Třeboň (pracovní název)

Verze 0.3 · 18. 11. 2026 · sjednoceno s připomínkami Codexu a rozhodnutím Ondřeje

## 0. Rozhodnutí

| Téma | Rozhodnutí |
|---|---|
| Veřejný výstup | nová sekce na **trebonaci.cz** (WordPress, hosting Vedos). Repozitář `trebonaci/radnice` = zadání, metodika, data, kód. |
| Mapa podnětů | součást přehledu: podněty z mapy na trebonaci.cz se propojují s rozhodnutími a projekty (kap. 6) |
| Značka | otevřeně projekt Třeboňáků; nesmí působit jako oficiální web města |
| Základ | datový model; první veřejný výstup = datový přehled |
| První pracovní úloha | zpracování zápisů rady a zastupitelstva podle metodiky |
| Období | pilot 2026–2030 → 2022–2026 → postupně zpět do 2012 |
| Smlouvy | město, 4 obchodní společnosti a příspěvkové organizace (IČO doplnit) |
| Zakázky | všech 5 profilů E-ZAK včetně Bertiných lázní |
| Hlasování | jen to, co je doložené zdrojem (zápisy ZM). Přepis videa jen pokud se ověří, že je nákladově výhodný a dává jmenovité údaje |
| Automatizace | až podle skutečné časové náročnosti ručního postupu; zatím žádný noční běh ani nový generátor webu |
| Merge vs. zveřejnění | merge do `main` = schválený pracovní stav; zveřejnění na webu je samostatný krok, který schvaluje Ondřej |
| Etapizace oken | námět v backlogu, ne slíbený výstup |

## 1. Cíl

Srozumitelně ukázat, co se na radnici v Třeboni děje:
- o čem rozhoduje rada a zastupitelstvo,
- jaké projekty a aktivity město připravuje, soutěží a realizuje (investice i měkké aktivity: sport, kultura, sociál, školství),
- kolik věci stojí a jak se cena vyvíjí,
- kde se věci dějí (mapa) a kdy (termínový plán).

Osou je **Strategický plán rozvoje města 2021–2030**. Každý projekt ukazuje, ke kterému opatření patří (nebo že k žádnému).

Signál navenek: autoři věcem rozumí a informují přesně. Správnost má přednost před rychlostí a rozsahem.

**Značka:** stránka nese značku Třeboňáků (tiráž, kontakt). Nepoužívá znak města a v patičce uvádí: „Nejde o web Města Třeboň. Data pocházejí z veřejných zdrojů uvedených u každého údaje.“

## 2. Rozsah

### Subjekty
| Subjekt | IČO | Smlouvy | Zakázky (E-ZAK) |
|---|---|---|---|
| Město Třeboň | 00247618 | ano | ano |
| Městská Vodohospodářská s.r.o. | 28136853 | ano | ano |
| Slatinné lázně Třeboň s.r.o. | 25179896 | ano | ano |
| Technické služby Třeboň, s.r.o. | 62502735 | ano | ano |
| Bertiny lázně Třeboň s. r. o. | 60067837 | ano | ano |
| Příspěvkové organizace města | doplnit | ano | dle vlastních profilů |

Seznam subjektů žije v jednom konfiguračním souboru (`config/subjekty.yaml`); přidání IČO nesmí vyžadovat změnu kódu.

### Zdroje
| Zdroj | Od kdy | Poznámka |
|---|---|---|
| Zápisy ZM a rady (web města) | ověřit pro každé období | starší PDF pravděpodobně skeny → OCR |
| Registr smluv | 7/2016 | smlouvy nad 50 000 Kč bez DPH |
| Profil zadavatele E-ZAK | ověřit | na stránce profilu není vidět XML export; ověřit export dle vyhl. 345/2023 Sb., jinak HTML |
| Otevřená data ISVZ | 2/2024 (nová) | doplněk pro zakázky ve Věstníku |
| Hlídač státu API | 2016 | křížová kontrola registru smluv |
| Monitor státní pokladny | 2010 | už zpracováno v dashboardu rozpočtů |
| trebonaci.cz REST: `/podnety`, `/projekty` | živě | mapa podnětů a 128 položek Strategického plánu; ověřit dostupnost a strukturu |

Mezery se na webu uvádějí výslovně, nedoplňují se odhadem.

## 3. Sekce veřejné stránky

1. **Datový přehled** (první výstup): kolik jednání, usnesení, smluv a zakázek, podle oblastí a subjektů, s odkazem na zdroje.
2. **Rozhodnutí**: témata z jednání rady a ZM, kategorie, výsledek, datum, odkaz na místo v zápisu.
3. **Projekty a aktivity**: projektové karty (kap. 5).
4. **Zakázky a smlouvy**.
5. **Mapa**: projekty, pozemkové záležitosti a podněty občanů na jedné mapě.
6. **Metodika** a **Opravy**.

## 4. Pravidla obsahu (závazná)

1. **Každý údaj má zdroj**: odkaz, datum, u PDF strana nebo bod.
2. **Úrovně jistoty**, viditelně označené: *doloženo* / *naše propojení* / *nevíme*.
3. **Částky se nesčítají napříč druhy**: odhad, schválený a upravený rozpočet, předpokládaná hodnota, vysoutěžená cena, smluvní cena, dodatky, zaplaceno, dotace (přislíbená/přijatá). Vždy s DPH / bez DPH / neuvedeno.
4. **AI nepočítá čísla.** Opisuje je s citací; výpočty dělá testovaný kód.
5. **Kontrola AI výstupů**: model A navrhne s citací → skript ověří doslovnou shodu citace se zdrojem → model B (jiný výrobce) nezávisle posoudí → Ondřej schválí zveřejnění. AI výstupy jsou označené.
6. **Osobní údaje**: fyzické osoby anonymizovat. Volení zástupci jménem, úředníci funkcí. Totéž platí pro podněty z mapy (bez jmen a kontaktů podatelů).
7. **Interní zdroje** (GINIS, neveřejné podklady) se do repozitáře ani do AI nástrojů nevkládají; nejvýš slouží k ručnímu ověření. Zveřejňuje se jen to, co je veřejně dostupné nebo zákonně zveřejnitelné.
8. **Neutrální jazyk** v datových sekcích; hodnocení jen v podepsaných analýzách.

## 5. Projektová karta

Seznam: stav, název, oblast, opatření SPRM, jedno klíčové číslo s druhem částky, poslední událost.

Detail: popis · časová osa (záměr → rozhodnutí → soutěž → smlouva → realizace → dodatky → dokončení) · peníze podle druhů · navázaná usnesení a hlasování · zakázky a smlouvy · související podněty z mapy · mapa · plán vs. skutečnost.

Projekty v přípravě zadává Ondřej ručně. Výchozí seznam = položky SPRM z endpointu `/projekty`.

## 6. Architektura (verze 1)

```
repozitář trebonaci/radnice              trebonaci.cz (WordPress, Vedos)
───────────────────────────              ───────────────────────────────
zdroje → ruční/poloautomatické    JSON   šablona stránky v trebonaci-theme
zpracování → data/*.json  ───────────▶   čte JSON a vykreslí přehled
                    ▲                          │
                    └──── /podnety, /projekty ─┘  (REST z WordPressu)
```

- **Zpracování** běží lokálně nebo v Claude/Codex nad repozitářem; skripty v Pythonu, výsledky v `data/`.
- **Publikace**: schválené JSON soubory se nahrají na Vedos (FTP, jako dnes šablona) a vykreslí je nová šablona stránky v `trebonaci-theme`. Mapa podnětů i přehled jsou ve stejném WordPressu, takže propojení podnět ↔ projekt je jen vazba ID.
- **Cache**: data načítat v prohlížeči z JSON souboru (nezávisle na WP Super Cache), nebo po každém nahrání cache vyprázdnit.
- **Automatizace** (GitHub Actions, nasazení přes FTPS, noční aktualizace) se přidá až po vyhodnocení ručního postupu.
- Před prvním kódem ověřit: současnou šablonu (`Trebonaci-web`), živou dostupnost a strukturu `/podnety` a `/projekty`.

## 7. Hlasování

- Zdrojem jsou zápisy ZM. Zveřejňuje se jen jmenovité hlasování, které zápis přímo obsahuje.
- Přepis videa: samostatné ověření (náklady na hodinu záznamu, a hlavně zda z videa vůbec jde určit, kdo jak hlasoval; přepis zvuku jména nedá, pokud se nehlasuje nahlas).
- Systémově: navrhnout městu zveřejňování usnesení a jmenovitých hlasování jako otevřených dat.

## 8. Spolupráce Claude ↔ Codex

- Repozitář je jediný zdroj pravdy. `AGENTS.md` (Codex) a `CLAUDE.md` (Claude) mají stejná pravidla.
- Úkoly = GitHub issues; každá změna přes PR; kdo napsal, ten nereviewuje; merguje Ondřej.
- **Merge ≠ zveřejnění.** Zveřejnění je samostatný krok s výslovným souhlasem Ondřeje (komentář „schváleno ke zveřejnění“ v PR nebo issue).
- Dělba se určuje u každého issue; výchozí: Claude zpracování a kód, Codex kontrola faktů a review.

## 9. Fáze

| Fáze | Obsah | Hotovo, když |
|---|---|---|
| 0 | Zadání, datový model, ověření šablony a endpointů | sjednoceno, endpointy popsané v `docs/ZDROJE.md` |
| 1 | Metodika zpracování zápisu na **jednom** nejnovějším zápisu rady a ustavujícím ZM | usnesení v `data/` podle modelu, ověřené citace, změřený čas |
| 2 | Všechny zápisy 2026–2030 + smlouvy a zakázky všech subjektů | data kompletní pro období |
| 3 | **Datový přehled** na trebonaci.cz (první veřejný výstup) | schváleno Ondřejem a zveřejněno |
| 4 | Projektové karty: SPRM + ruční projekty + vazby + podněty | 10 pilotních karet |
| 5 | Zpětně 2022–2026, pak postupně do 2012 | |
| 6 | Mapy, termínové plány, automatizace podle potřeby | |

Backlog námětů: analýza etapizace oken, přepis videa ZM.

## 10. Otevřené otázky

1. Název a URL sekce na trebonaci.cz.
2. Seznam příspěvkových organizací (IČO).
3. Zda zápisy ZM obsahují jmenovité hlasování a od kterého roku.
