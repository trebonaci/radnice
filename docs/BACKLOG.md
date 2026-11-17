# Backlog

Každou položku převést na GitHub issue. Pořadí odpovídá závislostem.

---

## 1. Zpracování jednoho nejnovějšího zápisu podle metodiky (první issue)
**Kdo:** Claude zpracuje · **Kontrola:** Codex · **Schvaluje:** Ondřej

**Vstup:** nejnovější zveřejněný zápis rady v období 2026–2030 a zápis z ustavujícího ZM 2. 11. 2026 (`Z-01-26-11-02.pdf`). Dva dokumenty proto, že rada a ZM mají odlišnou strukturu.

**Postup:**
1. Uložit PDF do `raw/` (manifest: URL, datum stažení, sha256). Zjistit, zda jde o text, nebo sken.
2. Vyextrahovat text po stranách.
3. Rozložit na `jednani` a `usneseni` podle `DATOVY_MODEL.md`: číslo, text, výsledek, hlasování (pro/proti/zdržel; jmenovitě jen pokud je v zápisu).
4. Ke každému usnesení navrhnout `tema`, `kategorie[]`, `shrnuti` (AI, příznak `shrnuti_ai`) a doslovnou `citace`.
5. Skriptem ověřit, že každá citace doslova existuje v textu dané strany.
6. Vytáhnout strukturované údaje: částky (s druhem a DPH), IČO a názvy protistran, parcely. Fyzické osoby anonymizovat.
7. Zapsat `data/jednani.json`, `data/usneseni.json`.
8. Do PR zapsat: časovou náročnost, co v datovém modelu chybí nebo přebývá, návrh číselníku `kategorie`.

**Kontrola (Codex):** porovnat každé usnesení s PDF: úplnost (nic nechybí), čísla, výsledky hlasování, citace, anonymizace, výstižnost shrnutí.

**Hotovo, když:** obě kontroly prošly, datový model a číselník kategorií jsou upravené podle zjištění a Ondřej potvrdil metodiku.

## 2. Ověření zdrojů a současného webu
**Kdo:** Codex · **Kontrola:** Claude
Do `docs/ZDROJE.md`:
- `trebonaci.cz/wp-json/trebonaci/v1/podnety` a `/projekty`: dostupnost, struktura, osobní údaje, jak spárovat podnět/projekt s usnesením.
- Šablona `Trebonaci-web`: jak přidat novou stránku (šablona + JSON), jak řešit WP Super Cache.
- Stránky se zápisy rady a ZM: seznam období, formát, od kterého roku jsou zápisy, zda obsahují jmenovité hlasování.
- Registr smluv, E-ZAK (XML export?), ISVZ, Hlídač státu: formát, přístup, vzorový záznam.

## 3. Zbytek zápisů 2026–2030
Po schválení metodiky z issue 1.

## 4. Smlouvy všech subjektů
Z `config/subjekty.yaml`; dodatky navázané, DPH s příznakem.

## 5. Zakázky z 5 profilů E-ZAK
Všechny stavy, šetrné stahování.

## 6. Propojení zakázka ↔ smlouva ↔ dodavatel ↔ usnesení
Každá vazba s `jistota`.

## 7. Datový přehled na trebonaci.cz
Šablona stránky čtoucí JSON; náhled ke schválení; zveřejnění až po souhlasu.

---

## Náměty (bez termínu)
- **Etapizace výměny oken**: zakázky a smlouvy všech etap, důvody z usnesení, srovnání s limity. Formulace bez právních verdiktů.
- **Přepis videí ZM**: změřit cenu za hodinu a ověřit, zda z videa jde určit jmenovité hlasování.
- **Automatizace**: noční stahování a nasazení přes FTPS, až bude ruční postup změřený.
