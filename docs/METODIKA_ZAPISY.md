# Metodika zpracování zápisů (pilot, issue 1)

Pilot: zápis z 1. jednání rady 4. 11. 2026 a zápis z ustavujícího zastupitelstva 2. 11. 2026.

## Postup

| Krok | Kdo/co | Výstup |
|---|---|---|
| 1. Stažení PDF, záznam do `raw/manifest.json` (URL, datum vyvěšení a stažení, sha256) | ručně / skript | manifest |
| 2. Text po stranách | `pdftotext -layout` (textové PDF), OCR jen u skenů | `raw/texty/<jednani>/strana-N.txt` |
| 3. Struktura: body programu, usnesení, hlasování, protinávrhy | `pipeline/zapisy.py`, **bez AI** | čísla a výsledky opsané z textu |
| 4. Anotace: téma, kategorie, shrnutí, citace, částky, parcely, co anonymizovat | AI (model A) | `anotace/<jednani>.yaml` |
| 5. Kontroly kódem: citace doslova ve zdroji, částka v citaci, anonymizované údaje nejsou v citacích, součty hlasů ≤ přítomní | `pipeline/sestav.py` | `data/*.json`, stav `overeno_kodem` |
| 6. Nezávislá kontrola | model B (Codex) | připomínky v PR |
| 7. Schválení | Ondřej | merge; zveřejnění zvlášť |

Spuštění: `python -m pipeline.sestav` a `python -m pytest`.

## Co pilot ukázal

**Formát zápisů**
- Oba zápisy jsou textová PDF z Wordu, OCR není potřeba.
- Struktura je pravidelná: `k bodu N` → `Usnesení RM/ZM č. X/RRRR-J` → `Výsledek hlasování: Pro/Proti/Zdrželi se` → `SCHVÁLENO`. Rada i zastupitelstvo používají stejný vzor, takže stačí jeden parser.
- **Jmenovité hlasování zápisy neobsahují**, jen součty. Pro jmenovité hlasování je potřeba jiný zdroj (protokol hlasovacího zařízení nebo video).
- Zápis rady je zveřejněn s příponou `-A` a město v něm část jmen anonymizovalo, ale ne konzistentně: v bodu 6 a usnesení RM 5/2026-1 je jméno, IČO a adresa fyzické osoby podnikající; v usnesení RM 4/2026-1 jméno chybí, IČO zůstalo.
- V zápisu ZM nesedí číslování: upravený program má 15 bodů, zápis končí body 16 a 17. Jméno předsedající je jednou „Grammetbaurová“ a jednou „Grammetbauerová“.
- Usnesení ZM 11/2026-1 (volba radních) nemá souhrnné hlasování, jen hlasování o jednotlivých kandidátech před ním.
- Usnesení ZM 10/2026-1 má dvě části a každá má vlastní hlasování.
- Protinávrhy mají vlastní hlasování, ale nejsou číslovaná usnesení.
- Rozpočtová opatření obsahují tabulku (schválený rozpočet → po RO). V textu usnesení je zatím jako surový text; pro rozpočet bude potřeba samostatný parser tabulky.
- Zastupitelé během jednání odcházeli (25 → 23 přítomných), což vysvětluje součty hlasů 23 u pozdějších voleb.

**Změny datového modelu** (zapracováno v `DATOVY_MODEL.md` v0.3)
- nová entita *bod programu* (i body bez usnesení),
- `hlasovani.typ`: usnesení / protinávrh / volba kandidáta; `cast` jen u vícečástkových usnesení; `jmenovite: null` = zdroj neuvádí,
- `jednani.pritomnost_zmeny` (odchody a příchody),
- nové druhy částek: `rozpoctove_opatreni`, `najemne_sazba`, `dar_prijaty`; pole `jednotka`,
- identifikátory: jednání `rm-2026-11-04`, usnesení `rm-2026-j1-u7`.

**Číselník kategorií**: návrh v `config/kategorie.yaml` (18 kategorií, usnesení může mít víc).

## Výsledek pilotu

- 2 jednání, 26 bodů programu, 20 usnesení, 26 hlasování (z toho 2 protinávrhy a 4 volby kandidátů).
- Všech 20 usnesení prošlo kontrolou citací kódem.
- Anonymizováno: 2 usnesení a 1 název bodu (fyzické osoby podnikající).

## Časová náročnost (odhad)

- Strojová část (stažení, text, struktura, kontroly) je po napsání parseru otázkou sekund na zápis.
- Anotace AI: jednotky minut na zápis.
- Lidská kontrola anotací: odhad 10–20 minut na zápis rady s ~10 usneseními. **Tohle je jediná část, která roste s počtem zápisů** – změřit při zpracování dalších zápisů.
- Největší zdržení pilotu bylo stažení PDF: web města blokuje automatické stahování (robots.txt) a prohlížeč povolil jen jedno stažení. Pro další zápisy: stahovat skriptem z GitHub Actions, nebo ručně.

## Otevřené otázky pro Ondřeje

1. Členové komisí a další osoby jmenované v usneseních, kteří nejsou volení zástupci (např. komise pro prodej pozemku): uvádět jménem, funkcí, nebo je vynechat?
2. Fyzické osoby podnikající (nájemci): anonymizovat vždy, i když je město v zápisu ponechalo? Pilot je anonymizuje.
3. Body „Různé“ bez usnesení (např. projednání podnětu občana): zobrazovat jen název bodu?
4. PDF zápisu ZM není uložené (prohlížeč zablokoval druhé stažení); text byl získán v prohlížeči. Codex by měl při kontrole porovnat s originálem.
