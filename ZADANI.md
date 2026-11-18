# Přehled dění a rozvoje Třeboně

**Pracovní zadání v0.2 · 18. 11. 2026 · návrh k připomínkám**

## Cíl

Rozšířit trebonaci.cz o srozumitelný, průběžně aktualizovaný přehled toho, co se v Třeboni projednává, připravuje, soutěží a realizuje. Zahrnout investiční projekty i měkké aktivity – sport, kulturu, sociální oblast, školství a další služby.

Osa přehledu je **Strategický plán rozvoje města Třeboň 2021–2030**. U projektů ukazovat příslušné opatření plánu, případně výslovně uvést, že přímá vazba nebyla doložena.

Veřejný výstup bude novou stránkou na **trebonaci.cz**, nikoli samostatným veřejným webem. Stránka jasně uvede, kdo ji provozuje, a nebude se vydávat za oficiální web města. GitHub repo `trebonaci/radnice` je společné pracovní místo pro zadání, metodiku, data a kód.

## Rozhodnutí pro první verzi

- První veřejný výstup: **datový přehled města** s jasně uvedeným obdobím, definicí ukazatele a odkazem na zdroj.
- První pracovní úloha: **třídění a zpracování zápisů rady a zastupitelstva**.
- Čas Ondřeje: nejvýše **4 hodiny týdně**.
- Začínáme dokumenty volebního období **2026–2030**. Starší období doplňujeme výběrově, pokud vysvětluje pokračování konkrétního projektu.
- Projekty v přípravě zadává Ondřej ručně; zahrnujeme i neinvestiční aktivity.
- Fable se nepoužívá.
- Žádný automatický výstup se nezveřejňuje bez lidské kontroly a Ondřejova schválení.

## Zdroje

### Rozhodování a strategie

- Samospráva města: https://www.mesto-trebon.cz/cz/mestsky-urad-trebon/samosprava-mesta.html
- Zápisy rady – přehled: https://www.mesto-trebon.cz/cz/mestsky-urad-trebon/samosprava-mesta/rada-mesta/zapisy-z-jednani-rady-mesta.html
- Zápisy rady 2026–2030: https://www.mesto-trebon.cz/cz/mestsky-urad-trebon/samosprava-mesta/rada-mesta/zapisy-z-jednani-rady-mesta/volebni-obdobi-2026---2030.html
- Zápisy zastupitelstva – přehled: https://www.mesto-trebon.cz/cz/mestsky-urad-trebon/samosprava-mesta/zastupitelstvo-mesta/zapisy-zastupitelstva-mesta.html
- Zápisy zastupitelstva 2026–2030: https://www.mesto-trebon.cz/cz/mestsky-urad-trebon/samosprava-mesta/zastupitelstvo-mesta/zapisy-zastupitelstva-mesta/volebni-obdobi-2026---2030-2.html
- Strategický plán rozvoje města: https://www.mesto-trebon.cz/cz/mestsky-urad-trebon/strategicky-plan.html

### Zakázky a smlouvy

- E-ZAK Třeboň: https://zakazky.mesto-trebon.cz/profile_index.html
- Registr smluv: https://smlouvy.gov.cz/

Počáteční rozsah smluv:
| Subjekt | IČO |
|---|---:|
| Město Třeboň | 00247618 |
| Městská Vodohospodářská s.r.o. | 28136853 |
| Slatinné lázně Třeboň s.r.o. | 25179896 |
| Technické služby Třeboň, s.r.o. | 62502735 |

E-ZAK má navíc profil Bertiných lázní Třeboň s. r. o. (IČO 60067837). Zahrnout je do přehledu zakázek. Smlouvy Bertiných lázní a další příspěvkové organizace přidat až po potvrzení rozsahu.

### Veřejná data

- Národní katalog otevřených dat: https://data.gov.cz/
- ČSÚ VDB: https://vdb.czso.cz/vdbvo2/
- ČSÚ: https://csu.gov.cz/
- Monitor státní pokladny: https://monitor.statnipokladna.gov.cz/
- Datastat ČSÚ: https://data.csu.gov.cz/datastat/dash?fTab=tree
- Volby: https://volby.gov.cz/

Statistiku.cz a Dataobce.cz mohou sloužit k orientaci a srovnání. Veřejné výstupy mají přednostně odkazovat na původní dataset či dokument.

## Fáze

1. **Vymezení a kontrola zdrojů:** ověřit dostupnost a podobu zápisů 2026–2030, existující evidenci projektů SPRM, živý stav REST endpointu a zdroje prvních ukazatelů.
2. **Datový přehled + pilot zápisu:** připravit návrh datové stránky a zpracovat jedno aktuální jednání podle metodiky. Pilot je redakční koncept, zveřejnění schvaluje Ondřej.
3. **Pravidelné zpracování:** opakovat třídění zápisů; zaznamenat skutečnou časovou náročnost. Pak přidat sledování zakázek a smluv v dohodnutém rozsahu.
4. **Projektové karty:** spojovat doložené události s projekty, smlouvami, zakázkami, částkami, mapou a harmonogramem.
5. **Automatizace a historie:** rozhodnout podle naměřené práce, dostupných exportů a přínosu. Starší OCR archiv ani noční běh nejsou podmínkou první verze.

## Finanční a stavové údaje

Nezaměňovat návrh, doporučení, rozhodnutí, vyhlášení soutěže, smlouvu a realizaci. Každá částka má vlastní typ: odhad, předpokládaná hodnota zakázky, vysoutěžená cena, cena smlouvy, dodatek, schválený/upravený rozpočet, dotace nebo skutečný výdaj. Uvést DPH a období, pokud jsou k dispozici. Nesčítat nesrovnatelné částky.

Projektový stav je redakční shrnutí s datem a zdroji, ne úřední kategorie. Vazba dokumentu na projekt se označí jako ověřená nebo jako redakční propojení.

## Hlasování a osobní údaje

Jmenovité hlasování uvádět jen tehdy, pokud ho dokládá dostupný zdroj. Plošný ruční přepis z videozáznamů není součástí první verze. Osobní údaje lidí, kteří nejsou volenými zástupci, zveřejňovat jen tehdy, když jsou nezbytné pro pochopení veřejného rozhodnutí; citlivé údaje z příloh vynechat.

## Technické zásady

- Toto repo je jediný zdroj pravdy pro zadání, metodiku, datový model, prompty a pracovní data projektu.
- Veřejná prezentace zůstane na trebonaci.cz a naváže na stávající WordPress web. Před návrhem implementace ověřit současnou šablonu a způsob nasazení přes FTP.
- V lokálním tématu je definovaný typ obsahu `trebonaci_projekt` a REST route `/wp-json/trebonaci/v1/projekty`. Živá dostupnost endpointu musí být ověřena; byl hlášen problém 404.
- Nezakládat zatím samostatný veřejný web, databázi ani noční pipeline.
- GitHub Issues slouží pro ohraničené úkoly; změny přes větev a PR. Sloučení do `main` není samo o sobě schválením veřejného textu ani nasazením na web.
- Do repozitáře ani do modelů nevkládat hesla, tokeny, neveřejné interní podklady nebo osobní údaje, které nejsou pro práci nutné.

## Kritéria úspěchu první verze

- Čtenář pochopí hlavní údaje a vybraná témata z radnice bez studování všech PDF.
- Každé tvrzení vede na přesný zdroj a místo v něm.
- Jsou viditelně přiznané mezery, nejistoty a odlišné typy částek.
- Týdenní kontrola Ondřejem se vejde do čtyř hodin.
- Výstup působí jako věcný informační přehled s jasně uvedeným provozovatelem.
