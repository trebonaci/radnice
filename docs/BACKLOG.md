# Backlog: fáze 0 a 1

Každou položku převést na GitHub issue (nadpis = název, tělo = text pod ním). Pořadí odpovídá závislostem.

---

## 1. Kostra repozitáře a pipeline
**Kdo:** Claude · **Review:** Codex
- Adresáře `pipeline/`, `raw/`, `data/`, `web/`, `tests/`, `requirements.txt`.
- `pipeline/subjekty.py`: seznam sledovaných subjektů (IČO) z jednoho konfiguračního souboru `config/subjekty.yaml`.
- GitHub Actions: `ci.yml` (testy na PR).

**Hotovo, když:** `pytest` běží zeleně v CI.

## 2. Ověření zdrojů pro smlouvy a zakázky (spike)
**Kdo:** Codex · **Review:** Claude
Zjistit a zapsat do `docs/ZDROJE.md`:
- Registr smluv: otevřená data (formát, URL, frekvence, struktura, jak poznat dodatek a jeho vazbu na původní smlouvu, znečištění duplicitami/verzemi).
- E-ZAK `zakazky.mesto-trebon.cz`: existuje XML export profilu podle vyhl. 345/2023 Sb.? Pokud ne, struktura HTML (seznam, detail, stavy, dokumenty), stránkování, robots.txt.
- ISVZ open data: co pokryje navíc.
- Hlídač státu API: co dává navíc (směr peněz, kategorie), podmínky použití.

**Hotovo, když:** pro každý zdroj je vzorový záznam pro Město Třeboň a doporučení, který zdroj je primární.

## 3. Stahování registru smluv
**Kdo:** Claude · **Review:** Codex · **Závisí na:** 1, 2
- Stáhnout smlouvy všech subjektů z `config/subjekty.yaml` od 7/2016.
- Normalizace do `data/smlouvy.json` podle `DATOVY_MODEL.md` (verze → poslední platná, dodatky navázané, DPH dopočtené s příznakem).
- Testy: deduplikace verzí, výpočet DPH.

**Hotovo, když:** počty smluv na subjekt odpovídají vyhledávání na smlouvy.gov.cz (ruční kontrola 1 subjektu, zapsat do PR).

## 4. Stahování zakázek z E-ZAK
**Kdo:** Claude · **Review:** Codex · **Závisí na:** 1, 2
- Všech 5 profilů, všechny stavy, včetně ukončených.
- `data/zakazky.json`: název, druh, režim, předpokládaná hodnota, stav, termíny, vítěz, cena, odkazy na dokumenty.
- Šetrné stahování (pauzy, cache, identifikace v User-Agent).

**Hotovo, když:** počet zakázek odpovídá profilu, 5 náhodných zakázek ručně zkontrolováno.

## 5. Propojení zakázka ↔ smlouva ↔ dodavatel
**Kdo:** Codex · **Review:** Claude · **Závisí na:** 3, 4
- Párování podle IČO dodavatele, data a předmětu. Každá vazba nese `jistota`: `doloženo` (číslo zakázky ve smlouvě) / `naše propojení` (heuristika).
- `data/dodavatele.json`: souhrn podle IČO (počet, součet smluvních cen s DPH, roky). Finanční smlouvy (úvěry, pojištění) zvlášť.
- Názvy dodavatelů z ARES.

## 6. Web: kostra a nasazení
**Kdo:** Claude · **Review:** Codex · **Závisí na:** 1
- Statický generátor (návrh: Astro), čte `data/`.
- Stránky: úvod, Smlouvy, Zakázky, Dodavatelé, Metodika. Patička se značkou Třeboňáků a větou, že nejde o web města.
- GitHub Actions: build → náhled na Cloudflare Pages pro PR → nasazení `main` přes FTPS na Vedos (přístupy v GitHub Secrets nastaví Ondřej).

**Hotovo, když:** web z `main` běží na zvolené doméně.

## 7. Noční aktualizace
**Kdo:** Claude · **Review:** Codex · **Závisí na:** 3, 4, 6
- Plánovaný workflow: stáhnout → přepočítat → otevřít PR s rozdílem dat (ne přímý push), aby nová data prošla schválením.

## 8. Analýza: výměna oken po etapách
**Kdo:** Codex (rešerše) + Claude (data) · **Závisí na:** 5
- Najít zakázky a smlouvy k výměně oken (všechny etapy, objekty, dodavatelé, ceny, roky).
- Doplnit z usnesení důvody etapizace.
- Výstup `analyzy/okna.md` podle ZADANI.md kap. 6. Před zveřejněním schvaluje Ondřej.
