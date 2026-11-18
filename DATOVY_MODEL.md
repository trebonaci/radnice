# Datový model – první verze

## Základní princip

Oddělovat dlouhodobý **projekt**, jednotlivé **události**, **zdrojové dokumenty**, **finanční údaje** a **ukazatele datového přehledu**. Usnesení, zakázka ani smlouva samy o sobě nejsou projektem.

## Projekt

| Pole | Význam |
|---|---|
| `project_id` | Stabilní interní identifikátor |
| `title` | Srozumitelný název |
| `summary` | Účel a očekávaný přínos |
| `category` | Doprava, bydlení, sport, kultura, sociální oblast, školství, životní prostředí, správa města aj. |
| `project_kind` | Investiční / neinvestiční / smíšený |
| `editorial_status` | Připravuje se / schváleno / soutěží se / smluvně zajištěno / probíhá / dokončeno / pozastaveno / zrušeno / neznámé |
| `status_as_of` | Datum, ke kterému stav platí |
| `strategic_links[]` | Odkazy na opatření SPRM, pokud jsou doloženy |
| `owner_entity_id` | Město nebo městská organizace |
| `location` | Adresa, parcela nebo geometrie; volitelné |
| `updated_at` | Datum redakční aktualizace |

Stav je redakční přehled založený na událostech a zdrojích. Nesmí být zaměněn za formální úřední stav.

## Událost

Událost zaznamenává jeden ověřitelný krok projektu nebo téma z jednání, které zatím nemá potvrzenou vazbu na projekt.

| Pole | Význam |
|---|---|
| `event_id` | Stabilní identifikátor |
| `project_id` | Volitelná vazba; prázdná, pokud není potvrzena |
| `event_date` | Datum jednání, zveřejnění nebo události; zaznamenat druh data |
| `event_type` | Projednáno / navrženo / doporučeno / rozhodnuto / soutěž vyhlášena / smlouva uzavřena / dodatek / zahájení / průběžná informace / dokončení / jiné |
| `title` | Krátký popis |
| `source_statement` | Co zdroj výslovně říká |
| `plain_language_summary` | Ověřené vysvětlení pro občana |
| `decision_result` | Schváleno / neschváleno / doporučeno / odloženo / vzato na vědomí / nerozhodnuto / neuvedeno |
| `source_refs[]` | Odkazy na dokumenty a přesná místa |
| `review_status` | Rozpracováno / zdrojem ověřeno / nezávisle zkontrolováno / schváleno |

## Zdrojový dokument

| Pole | Význam |
|---|---|
| `source_id` | Interní identifikátor |
| `source_type` | Zápis rady / zápis ZM / usnesení / E-ZAK / registr smluv / rozpočet / ČSÚ / Monitor / SPRM / jiné |
| `title` | Název dokumentu |
| `publisher` | Orgán nebo instituce |
| `url` | Původní zdroj |
| `document_date` | Datum dokumentu nebo jednání |
| `published_at` | Datum zveřejnění, je-li známo |
| `retrieved_at` | Datum kontroly zdroje |
| `locator` | Strana, bod, ID smlouvy/zakázky nebo jiný přesný lokátor |
| `text_method` | HTML / textové PDF / OCR / ruční přepis / dataset |
| `limitations` | Chybějící příloha, nečitelné OCR, neúplný archiv apod. |

## Finanční údaj

| Pole | Význam |
|---|---|
| `amount_id` | Identifikátor |
| `project_id` | Volitelná vazba |
| `value` | Číselná hodnota |
| `currency` | Typicky CZK |
| `amount_type` | Odhad / předpokládaná hodnota VZ / vysoutěžená cena / cena smlouvy / dodatek / rozpočet / dotace požadovaná / dotace přiznaná / skutečný výdaj / jiné |
| `vat_basis` | S DPH / bez DPH / neuvedeno |
| `period` | Období, kterého se údaj týká |
| `source_ref` | Primární zdroj |
| `as_of` | Datum platnosti nebo zjištění |
| `note` | Rozsah plnění a omezení |

Nesčítat ani přímo neporovnávat částky různých typů bez doloženého převodu na srovnatelný základ.

## Ukazatel datového přehledu

| Pole | Význam |
|---|---|
| `metric_id` | Stabilní ID |
| `label` | Čitelný název |
| `value` | Hodnota nebo časová řada |
| `unit` | Osoby, Kč, %, index aj. |
| `reference_period` | Období platnosti |
| `definition` | Přesný význam ukazatele |
| `calculation` | Postup výpočtu, pokud se počítá |
| `source_ref` | Primární zdroj |
| `last_checked_at` | Datum kontroly |
| `comparability_note` | Revize dat nebo změna metodiky |

## Subjekt

| Pole | Význam |
|---|---|
| `entity_id` | Stabilní ID |
| `name` | Oficiální název |
| `ico` | IČO |
| `entity_type` | Město / městská společnost / příspěvková organizace / jiné |
| `monitoring_scope` | Smlouvy / zakázky / obojí / nezařazeno |

## Vazby a pravidla

- Projekt má více událostí a finančních údajů.
- Událost odkazuje na jeden či více zdrojů, vždy s přesným lokátorem.
- Vazbu projektu na smlouvu nebo zakázku lze potvrdit jen přímým identifikátorem nebo ruční kontrolou.
- Automatická shoda názvů vytváří návrh, nikoli potvrzený vztah.
- Neznámá hodnota je `null`/„neuvedeno“, nikdy nula.
- Existující WordPress evidence `trebonaci_projekt` a její pole se zmapují před migrací či rozšířením. Nevytvářet druhý katalog SPRM bez rozhodnutí.
