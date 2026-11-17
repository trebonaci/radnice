# Zadání: Přehled radnice Třeboň (pracovní název)

Verze 0.2 · 18. 11. 2026 · koncept k připomínkám (Ondřej, Claude, Codex)

**Rozhodnuto:** samostatný web, projekt Třeboňáků, hosting Vedos, historie od 2012, první veřejný výstup = smlouvy a zakázky.

## 1. Cíl

Samostatný web, který srozumitelně ukazuje, co se na radnici v Třeboni děje:
- o čem rozhoduje rada a zastupitelstvo,
- jaké projekty a aktivity město připravuje, soutěží a realizuje (investice i měkké aktivity: sport, kultura, sociál, školství),
- kolik věci stojí a jak se cena vyvíjí,
- kde se věci dějí (mapa) a kdy (termínový plán).

Osou je **Strategický plán rozvoje města 2021–2030**. Každý projekt ukazuje, ke kterému opatření plánu patří (nebo že nepatří k žádnému).

Signál navenek: autoři věcem rozumí a informují přesně. Proto je přednější správnost než rychlost a rozsah.

**Značka:** web je otevřeně projekt Třeboňáků (logo, tiráž, kontakt). Zároveň nesmí působit jako oficiální web města: jiný vizuál, žádný znak města, v patičce věta „Nejde o web Města Třeboň. Data pocházejí z veřejných zdrojů uvedených u každého údaje.“

## 2. Rozsah

### Subjekty
| Subjekt | IČO | Poznámka |
|---|---|---|
| Město Třeboň | 00247618 | |
| Městská Vodohospodářská s.r.o. | 28136853 | |
| Slatinné lázně Třeboň s.r.o. | 25179896 | |
| Technické služby Třeboň, s.r.o. | 62502735 | |
| Bertiny lázně Třeboň s. r. o. | 60067837 | je na profilu zadavatele E-ZAK |
| Příspěvkové organizace města | TODO | doplnit seznam a IČO (školy, MŠ, kultura, sociální služby…) |

### Období
Od roku 2012. Dostupnost se liší podle zdroje:
| Zdroj | Od kdy reálně | Poznámka |
|---|---|---|
| Zápisy a usnesení ZM a rady (web města) | ověřit pro každé volební období | starší PDF budou nejspíš skeny, tj. OCR |
| Registr smluv | 7/2016 | smlouvy nad 50 000 Kč bez DPH; před 2016 nic |
| Profil zadavatele E-ZAK | ověřit | na stránce profilu není vidět odkaz na XML export; ověřit zákonný export podle vyhl. 345/2023 Sb., jinak HTML |
| Otevřená data ISVZ (Věstník VZ) | 2/2024 (nová), starší ve „původních“ | doplňkový zdroj pro zakázky zveřejněné ve Věstníku |
| Hlídač státu API | 2016 | záloha a křížová kontrola registru smluv; vyžaduje token |
| Monitor státní pokladny (FIN 2-12 M) | 2010 | už zpracováno v dashboardu rozpočtů |
| ČSÚ, volby.gov.cz | dle datové sady | |

Mezery se na webu uvádějí výslovně (jako u Humpolce), nedoplňují se odhadem.

## 3. Sekce webu

1. **Rozhodnutí**: témata z jednání rady a zastupitelstva, kategorie, stav (navrženo / schváleno / zamítnuto / odloženo), datum, odkaz na přesné místo v zápisu; u zastupitelstva jmenovité hlasování.
2. **Projekty a aktivity**: projektové karty (viz kap. 5).
3. **Zakázky a smlouvy**: soutěže, smlouvy, dodatky, dodavatelé; postupně navázané na karty.
4. **Analýzy**: tematické rozbory, např. etapizace zakázek (kap. 6).
5. **Město v datech**: obyvatelstvo, hospodaření, srovnání s podobnými městy (navazuje na stávající dashboard rozpočtů).
6. **Mapa**: projekty a pozemkové záležitosti na katastrální mapě.
7. **Metodika** a **Opravy**: jak data vznikají, co chybí, seznam opravených chyb s datem.

## 4. Pravidla obsahu (závazná)

1. **Každý údaj má zdroj**: odkaz na dokument, datum, u PDF číslo strany nebo bodu.
2. **Tři úrovně jistoty**, viditelně označené:
   - *doloženo*: přímo ve zdroji,
   - *naše propojení*: vazbu mezi dokumenty jsme dovodili (např. smlouva → projekt),
   - *nevíme*: chybí podklad.
3. **Částky se nesčítají napříč druhy.** Rozlišujeme: odhad, schválený rozpočet, upravený rozpočet, předpokládaná hodnota zakázky, vysoutěžená cena, smluvní cena, dodatky, skutečně zaplaceno, dotace (přislíbená / přijatá). U každé částky uvést, zda je s DPH, nebo bez DPH.
4. **AI nepočítá čísla.** Čísla opisuje ze zdroje s citací. Výpočty dělá kód a jsou testované.
5. **Kontrola AI výstupů**: model A navrhne s citací → skript ověří, že citace ve zdroji doslova existuje → model B (jiný výrobce) nezávisle posoudí → člověk schválí publikaci. AI výstupy jsou na webu označené.
6. **Osobní údaje**: fyzické osoby (prodeje pozemků, věcná břemena, nájmy, sociální věci) se anonymizují. Volení zástupci uvedeni jménem, úředníci funkcí.
7. **Interní zdroje (GINIS a neveřejné podklady)** se do repozitáře ani do AI nástrojů nevkládají. Slouží nejvýš jako vodítko k ověření a publikuje se jen to, co je veřejně dostupné nebo zákonně zveřejnitelné.
8. **Neutrální jazyk** v datových sekcích. Hodnocení a komentáře patří jen do Analýz, oddělené od faktů a podepsané.

## 5. Projektová karta

Karta v seznamu: stav, název, oblast (investice / sport / kultura / sociál / školství / …), opatření SPRM, jedno klíčové číslo s druhem částky, poslední událost.

Detail:
- **Popis**: co a proč.
- **Časová osa**: záměr → rozhodnutí → soutěž → smlouva → zahájení → průběh/dodatky → dokončení → vyúčtování. Každý krok s datem a zdrojem.
- **Peníze**: tabulka druhů částek (kap. 4.3) v čase.
- **Rozhodnutí**: navázaná usnesení rady a ZM, včetně hlasování.
- **Zakázky a smlouvy**: navázané záznamy.
- **Mapa**: parcely nebo místo.
- **Termínový plán**: plán vs. skutečnost.

Projekty v přípravě zadává Ondřej ručně (formát: jeden YAML/Markdown soubor na projekt v repozitáři; jednoduchý formulář případně později).

Výchozí data: 128 položek SPRM z endpointu `trebonaci.cz/wp-json/trebonaci/v1/projekty`.

## 6. Analýzy: první téma

**Etapizace zakázek** (podnět: výměna oken v 8 etapách místo najednou).
- Seskupit zakázky a smlouvy podle předmětu, objektu, dodavatele a období.
- Ukázat součet etap a srovnat ho s limity veřejných zakázek a s tím, jaký režim by platil pro zadání najednou.
- Hledat důvody etapizace v zápisech: rozpočet, dotace, provoz budovy.
- Pozor na výklad: rozdělení může mít legitimní důvod. Výstup popisuje fakta a otázky, neobviňuje. U právních závěrů (§ 18 ZZVZ) neformulujeme verdikt.

## 7. Hlasování

- Ověřit, zda zápisy ZM obsahují jmenovité hlasování a od kterého roku.
- Pokud ne: ruční přepis z videozáznamů nebo protokolů hlasovacího zařízení pro vybraná usnesení.
- Systémové řešení: navrhnout městu, aby zveřejňovalo usnesení a jmenovitá hlasování jako otevřená data (export z hlasovacího systému). Tím odpadne většina parsování.

## 8. Architektura

- **Repozitář** `trebonaci/<název>` (soukromý; veřejný později podle rozhodnutí).
- **Pipeline** (Python): stahování → extrakce (PDF/OCR) → normalizace → propojení → JSON/CSV v repozitáři (`data/`).
- **Web**: statický, generovaný z `data/` (Astro nebo prostý generátor; rozhodnout ve fázi 0).
- **Běh**: GitHub Actions, noční aktualizace + ruční spuštění.
- **Hosting**: statické soubory nasazené přes FTP(S) na Vedos (subdoména nebo vlastní doména). Náhledy větví na Cloudflare Pages, stejně jako u volejbalu.
- Žádná databáze ani serverová aplikace, dokud to objem dat nevyžádá.

## 9. Spolupráce Claude ↔ Codex

- **Jediný zdroj pravdy je repozitář.** Pravidla v `AGENTS.md` (čte Codex) a `CLAUDE.md` (čte Claude) odkazují na tento soubor a na `DATOVY_MODEL.md`.
- **Úkoly = GitHub issues**, jeden issue = jedna ohraničená věc s kritériem hotovo.
- **Každá změna přes PR.** Kdo PR napsal, ten ho nereviewuje: Claude píše → Codex kontroluje, a obráceně.
- **Merge = publikace.** Merguje jen Ondřej.
- Výchozí dělba (lze měnit po issue):
  | Role | Kdo | Vlastní |
  |---|---|---|
  | Zadavatel a schvalovatel | Ondřej | priority, ruční data o projektech, schválení publikace |
  | Pipeline a web | Claude | sběr, extrakce, propojení, frontend |
  | Kontrola a fakta | Codex | review PR, ověření citací a čísel, testy |
  | Texty | střídavě | vysvětlující texty; finální znění schvaluje Ondřej |

## 10. Fáze

| Fáze | Obsah | Hotovo, když |
|---|---|---|
| 0 | Repo, zadání, datový model, kostra webu, nasazení na Vedos | prázdný web běží na doméně z automatického buildu |
| 1 | Smlouvy + zakázky všech subjektů od 2016 (**první veřejný výstup**) | seznam se zdroji, filtr podle subjektu/dodavatele/roku, dodavatelé, dodatky u smluv |
| 2 | Zápisy ZM a rady 2022–2026 → Rozhodnutí | témata a kategorie s ověřenými citacemi |
| 3 | Projektové karty: SPRM + ruční projekty + vazby z F1/F2 | 10 pilotních karet ručně zkontrolovaných |
| 4 | Analýza etapizace (okna) | publikovatelný rozbor |
| 5 | Zápisy 2012–2022 (OCR), hlasování | historie zpětně |
| 6 | Mapy a termínové plány | parcely z usnesení na mapě |

## 11. Otevřené otázky

1. Název a doména webu.
2. Kolik času týdně na kontrolu a schvalování.
3. Seznam příspěvkových organizací a dalších subjektů (IČO).
4. Zda zápisy ZM obsahují jmenovité hlasování a od kterého roku.
