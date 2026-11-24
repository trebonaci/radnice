# Grafické návrhy přehledu radnice (23. 11. 2026)

Zadání Ondřeje z 23. 11. 2026: nový vzhled podle grafických návrhů, přejmenování sekcí a „Co se děje“ jako přehled zpráv.
Tento soubor je **závazné zadání** pro PR podle návrhů. Grafické podklady (`*/screen.png`, `*/navrh.html`, `DESIGN.md`)
jsou **jen vizuální vzor**.

## Pozor: návrhy obsahují smyšlené údaje
Návrhy vygeneroval nástroj na grafiku. Čísla, firmy, jména, termíny i fotky v nich jsou ilustrační a neodpovídají
datům. Například u Budějovické ulice uvádějí STRABAG a 19,57 mil. Kč; ve skutečnosti staví K-BUILDING CB, a.s. za 15,54 mil. Kč
s DPH (smlouvy po dodatcích).

Z návrhů přebíráme **rozvržení, typografii, barvy a komponenty**. Údaje nepřebíráme nikdy, všechno se skládá z `data/*.json`.
Platí pravidla obsahu z `ZADANI.md` a `AGENTS.md`:
- každý údaj má zdroj;
- částky různých druhů se nesčítají a u každé je uvedeno s DPH / bez DPH;
- úředníky uvádíme funkcí;
- hodnocení patří jen do `analyzy/`.

Jména osob v `navrh.html` jsou nahrazena značkou. Ve `screen.png` zůstala, ale jsou smyšlená.

## Co z návrhů nepřebíráme
- **Funkce, které nemáme:**
  - Export CSV / GeoJSON, „API endpoint“, iCal kalendář;
  - „Nahlásit podnět / nepřesnost“, „Sledovat milníky“;
  - přihlášení uživatele (ikona účtu);
  - „verze datového parseru“;
  - vrstvy mapy „Katastr“ a „Územní plán 2030“.

  Kdyby je Ondřej chtěl, budou to samostatné issue.
- **Ukazatele, které nemáme doložené:**
  - „termínová spolehlivost 88 %“, „ověřenost dat 100 %“;
  - „z toho dotace 114 mil. Kč“, „zbývá 53 dní“, „fyzický postup 64 %“;
  - „dopravní dopad“, „zvýšený stavební ruch“.

  KPI karty ukazují jen čísla, která počítá testovaný kód z našich dat.
- **„Zpoždění“** (červená kategorie): jen tam, kde data dokládají uplynulý smluvní termín, a to slovy „termín podle smlouvy uplynul“, ne „zpoždění +35 dní“.
- **Fotky z návrhů** jsou vygenerované a nesmějí se použít jako fotky skutečných míst (viz Fotky níže).
- **Tailwind z CDN a Google Fonts:** web nesmí načítat skripty a písma z cizích serverů. Styly píšeme do `web/site/*.css`, písma *Plus Jakarta Sans* a *Inter* (licence OFL) ukládáme do `web/site/fonts/`.

## Sekce a menu
Pořadí menu: **Co se děje · Investice a opravy · Projekty · Usnesení · Místa a služby · Mapa**.
Rozpočet a V číslech zůstávají v patičce a v odkazech z úvodu.

| Sekce | Adresa | Co to je | Vzor |
|---|---|---|---|
| Co se děje | `#` | přehled zpráv (newsfeed) po šesti okruzích | `cosedeje/` |
| Investice a opravy | `#investice` (dosud `#stavby`, zůstane jako přesměrování) | přejmenované Stavby a opravy | `investice/` |
| Projekty | `#projekty` (dosud `#casova-osa`, zůstane jako přesměrování) | časová osa projektů, nově v menu | `projekty/` |
| Usnesení | `#usneseni` | přejmenované Rozhodnutí | `usneseni/` |
| Místa a služby | `#mista` | beze změny obsahu, nový vzhled | – |
| Mapa | `#mapa` | mapa s výpisem vlevo | `mapa/` |
| Karta projektu | `#<id>` | detail investice | `karta-projektu.html` |

Šest okruhů (`config/okruhy.yaml`) zůstává hlavním členěním na všech stránkách, ve stejném pořadí a s okruhem v adrese.

## Co se děje: druhy zpráv
Každá zpráva je **jedna událost z jednoho veřejného dokumentu**. Druh zprávy říká, o jaký dokument jde a odkud ho máme.
Okruh říká, čeho se zpráva týká. Na stránce se dá filtrovat podle obojího.

| Druh | Zdroj | Datum zprávy | Kdy vzniká | Barva |
|---|---|---|---|---|
| **Usnesení** | zápisy rady a zastupitelstva | den jednání | každé přijaté usnesení kromě procedurálních (program, ověřovatelé, volba komisí); u nepřijatého štítek „Neschváleno“ | modrá (`category-rozhodnuti`) |
| **Změna pro občany** | usnesení, z něhož plyne změna služby nebo místa (`data/zmeny.json`) | den jednání; u štítku i „platí od“ | místo usnesení, ze kterého vznikla (usnesení se pak samostatně neukazuje) | zelená (`category-zmena`) |
| **Výběrové řízení** | E-ZAK města a společností | vyhlášení; výběr dodavatele (datum uzavření smlouvy); zrušení; ukončení plnění | každá změna stavu zakázky | technická modř (`tertiary`) |
| **Smlouva** | registr smluv | uzavření smlouvy | smlouva napojená na kartu projektu nebo zásobník, nebo s hodnotou od 500 000 Kč; ostatní smlouvy jen v archivu | oranžová (`category-stavba`) |
| **Dodatek** | registr smluv (dodatek ke smlouvě) + usnesení, které ho schválilo | uzavření dodatku | každý dodatek ke smlouvě nad 500 000 Kč nebo napojené na projekt; usnesení o jeho schválení je ve stejné zprávě | oranžová s okrajem |
| **Rozpočtové opatření** | usnesení + přehled RO finančního odboru | den jednání | každé RO; text = co a o kolik se mění | šedomodrá |

**Proč takto:**
- Ondřejovy čtyři druhy (usnesení, smlouva, dodatek, výběrové řízení) odpovídají zdrojům dat.
- Přidal jsem dva:
  - **Rozpočtová opatření** jsou formálně usnesení, ale je jich hodně (16 ze 139) a čtenáře zajímá změna peněz, ne usnesení.
  - **Změna pro občany** je nejsrozumitelnější zpráva webu.
- Bez obou by se Usnesení zahltilo rozpočtovými technikáliemi a „změny“ by zapadly.

**Pravidla, aby se zprávy neopakovaly:**
1. Dodatek a usnesení, které ho schválilo, dávají jednu zprávu „Dodatek“ s odkazy na oba dokumenty.
2. Změna pro občany nahrazuje usnesení, ze kterého vznikla.
3. Víc zpráv k jedné akci ve stejný den se seskupí pod název akce („2 nové dokumenty“).
4. Smlouvy pod 500 000 Kč bez vazby na projekt se v přehledu neukazují. Je jich většina: od září 2026 je v registru 152 smluv, z toho 20 od 500 000 Kč.

**Data:**
- Nový `pipeline/zpravy.py` vytvoří `data/zpravy.json`.
- Pole zprávy: `id`, `druh`, `datum`, `okruh`, `titulek`, `shrnuti` (jedna věta), `castka` (`hodnota`, `druh`, `s_dph`), `projekt_id`, `zdroje` [{`nazev`, `url`}], `jistota`.
- Okruh smluv a zakázek bez karty určí vzory z `config/okruhy.yaml`.
- Částky se opisují ze zdroje, nepočítají se.
- Testy pokrývají slučování a práh 500 000 Kč.

**Stránka:**
- Nahoře řádek filtrů podle druhu (Všechny · Usnesení · Změna · Výběrové řízení · Smlouva · Dodatek · Rozpočet), pod ním výběr okruhu.
- Pak 6 bloků okruhů po 2 zprávách, jako dosud.
- KPI v záhlaví jen z dat: počty zpráv za posledních 30 dní podle okruhu.

## Karta projektu
Vzor je `karta-projektu.html` (`karta-projektu.png`, `karta-projektu-mobil.png`), sestavený ze skutečných dat projektu `auto-vz-914`:
- štítky: fáze, okruh, výběrové řízení;
- název a jedna věta (z dat; když chybí popis, skládá se z dodavatele, počtu nabídek a dodatků);
- 4 KPI: cena podle smluv, kdy hotovo, kdo staví, v rozpočtu města;
- pruh fází: Projekt → Výběrové řízení → Smlouva → Staví se → Hotovo;
- „Kolik to stojí“ se skladbou ceny;
- „Dodatky“ s rozdílem a novou cenou, opsanými z usnesení;
- „Co se stalo“ (2 poslední, zbytek sbalený);
- vpravo mapka z geometrie v `data/mapa.json`, fotky a „Odkud to víme“ s legendou jistoty.

Na mobilu jsou fáze ve dvou sloupcích, ne pod sebou.

## Fotky
Rozhodnutí Ondřeje 23. 11. 2026: **zůstáváme u současného Cloudflare Pages**, bez dalšího úložiště (R2).
- Fotky jsou součástí webu: `web/site/foto/<projekt>/<soubor>.webp` a nasazují se s ním.
- Do repozitáře jdou **jen zmenšené verze**, ne originály: WebP, šířka 640 a 1280 px, cíl do 250 kB na soubor. Pages mají limit 25 MiB na soubor a 20 000 souborů na web, což při desítkách až stovkách fotek stačí s rezervou.
- Při každé fotce se odstraní EXIF včetně GPS.
- **Postup:**
  1. Redakce vloží fotku přes formulář issue „Fotka k projektu“ (autor, datum, licence, potvrzení „bez rozpoznatelných osob a SPZ, mám právo zveřejnit“).
  2. GitHub Action fotku zmenší, uloží a otevře PR s doplněním `fotky:` do `data/projekty/<slug>.yaml` (soubor, autor, datum, licence, popis pro nevidomé).
  3. Fotku zkontroluje člověk v PR.
- **Pojistky:** CI hlídá velikost a počet souborů ve `web/site/foto/`. Kdyby fotek přibylo tolik, že by repozitář nebo nasazení výrazně rostly, vrátíme se k samostatnému úložišti.

## Pořadí PR
1. Základ vzhledu (tokeny, písma, hlavička, menu, patička, přejmenování sekcí) – nejdřív, ostatní na něm stojí.
2. Data zpráv `data/zpravy.json` – může běžet souběžně s bodem 1 (jen pipeline).
3. Co se děje jako přehled zpráv.
4. Investice a opravy.
5. Karta projektu.
6. Projekty (časová osa).
7. Usnesení.
8. Mapa.
9. Fotky – v současném Cloudflare Pages (rozhodnutí Ondřeje 23. 11. 2026), po kartě projektu.

Každý krok je samostatné issue a PR do náhledu. Na web jde až po „schváleno ke zveřejnění“.
