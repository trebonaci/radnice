# Zdroje a jejich použití

**Stav ověření: 18. 11. 2026.** Dokument zachycuje stav veřejných zdrojů při vstupním ověření pro issue #9. Ověření API není souhlas se zveřejněním žádných dat. Každý veřejný text a každé propojení musí být před vydáním zkontrolováno podle metodiky a schváleno Ondřejem.

## Doporučená hierarchie zdrojů

1. Původní zápis/usnesení, profil zadavatele, záznam v Registru smluv nebo oficiální účetní a strategický dokument.
2. Oficiální městská evidence a WordPress trebonaci.cz jako vlastní redakční evidence.
3. ARES pro ověření právní identity a aktuálního stavu subjektu.
4. Agregátory (např. Hlídač státu, dataobce.cz, statistiku.cz) pouze jako pomůcka pro nalezení dat; výstupy ověřit v primárním zdroji.

U každé importované položky ukládat URL zdroje, datum kontroly a stabilní ID zdroje. Kopie dat musí umět respektovat pozdější znepřístupnění nebo opravu.

## Městské subjekty a IČO

Současná konfigurace už obsahuje město a čtyři uvedené společnosti plus Bertiny lázně. Doplnění níže rozšiřuje monitoring Registru smluv na další právnické osoby, které město uvádí jako své organizace nebo je zahrnuje do společného zadávání. Neznamená to, že všechny mají vlastní profil E‑ZAK nebo že jde ve všech případech o stoprocentní vlastnictví.

| Subjekt | IČO | Vztah / zařazení | Primární ověření |
|---|---:|---|---|
| Město Třeboň | 00247618 | obec | [městský profil E‑ZAK](https://zakazky.mesto-trebon.cz/profile_display_2.html) |
| Městská Vodohospodářská s.r.o. | 28136853 | městská společnost | [profil E‑ZAK](https://zakazky.mesto-trebon.cz/profile_display_354.html) |
| Slatinné lázně Třeboň s.r.o. | 25179896 | městská společnost | [profil E‑ZAK](https://zakazky.mesto-trebon.cz/profile_display_190.html) |
| Technické služby Třeboň, s.r.o. | 62502735 | městská společnost | [profil E‑ZAK](https://zakazky.mesto-trebon.cz/profile_display_132.html) |
| Třeboňské lesy a rybníky s.r.o. | 60838256 | městská společnost | [městské organizace](https://www.mesto-trebon.cz/cz/urady-organizace-a-instituce/mestske-organizace.html), [závěrečný účet](https://www.mesto-trebon.cz/text/uploads/news/id11475/Navrh-zaverecneho-uctu-mesta-Trebone-za-rok-2021.pdf) |
| Autokemp Třeboňský ráj, s.r.o. | 60851422 | městská společnost | [městské organizace](https://www.mesto-trebon.cz/cz/urady-organizace-a-instituce/mestske-organizace.html), [závěrečný účet](https://www.mesto-trebon.cz/text/uploads/news/id11475/Navrh-zaverecneho-uctu-mesta-Trebone-za-rok-2021.pdf) |
| Bertiny lázně Třeboň s. r. o. | 60067837 | historický profil / právní status nutno držet odděleně od současné provozní jednotky | [historická zakázka E‑ZAK](https://zakazky.mesto-trebon.cz/contract_display_64.html); současná městská stránka uvádí Bertiny lázně pod [Slatinnými lázněmi](https://www.mesto-trebon.cz/cz/urady-organizace-a-instituce/mestske-organizace.html) |
| Městská sportovní Třeboň, příspěvková organizace | 06457665 | příspěvková organizace | [oficiální zadávací dokumentace města](https://zakazky.mesto-trebon.cz/document_7130/9276dd4e4fd218ce189f5766c74d5031-zd_ee_nadlimit_pn_trebon_sign_2026-2028-pdf) |
| Městská knihovna Třeboň | 21551464 | příspěvková organizace | [oficiální kontakt knihovny](https://www.knihovnatrebon.cz/kontakt/) |
| Základní škola Třeboň, Sokolská 296 | 60818174 | příspěvková organizace | [oficiální zadávací dokumentace města](https://zakazky.mesto-trebon.cz/document_7130/9276dd4e4fd218ce189f5766c74d5031-zd_ee_nadlimit_pn_trebon_sign_2026-2028-pdf) |
| Základní škola Třeboň, Na Sadech 375 | 60816872 | příspěvková organizace | [oficiální zadávací dokumentace města](https://zakazky.mesto-trebon.cz/document_7130/9276dd4e4fd218ce189f5766c74d5031-zd_ee_nadlimit_pn_trebon_sign_2026-2028-pdf) |
| 3. mateřská škola Třeboň, Jeronýmova 183 | 70989907 | příspěvková organizace | [oficiální zadávací dokumentace města](https://zakazky.mesto-trebon.cz/document_7130/9276dd4e4fd218ce189f5766c74d5031-zd_ee_nadlimit_pn_trebon_sign_2026-2028-pdf) |
| Mateřská škola Sluníčko, Třeboň | 63263777 | příspěvková organizace | [oficiální zadávací dokumentace města](https://zakazky.mesto-trebon.cz/document_7130/9276dd4e4fd218ce189f5766c74d5031-zd_ee_nadlimit_pn_trebon_sign_2026-2028-pdf) |

IČO a právní formu jednou ročně znovu ověřovat vůči ARES a aktuálnímu závěrečnému účtu. IČO je stabilní klíč, název nebo právní stav nikoli.

**Rozsah s nejistým nebo historickým vztahem:**

- E‑ZAK eviduje starší zakázku pod samostatným profilem Bertiných lázní (IČO 60067837). Městská stránka nyní uvádí Bertiny lázně jako součást Slatinných lázní. IČO ponecháváme pro historické hledání, ale nepovažujeme jej bez ověření v ARES za současnou samostatnou organizaci.
- Školní jídelna – CENTRUM Třeboň (IČO 71166599) se podle usnesení města sloučila se ZŠ Na Sadech od 1. 3. 2013. Do aktivní konfigurace ji nezařazovat. [Usnesení města](https://www.mesto-trebon.cz/text/uploads/news/id3488/U-65-12-12.-12..pdf).
- Informační a kulturní středisko města Třeboně (IČO 00365751) je historický zaniklý subjekt; dnešní městské informační centrum je součástí odboru města. Nezařazovat jako současnou samostatnou osobu. [Městský přehled IKS](https://www.mesto-trebon.cz/text/uploads/_mesto/rocenky/rocenka2010.pdf); [městská organizační struktura](https://www.mesto-trebon.cz/cz/mestsky-urad-trebon/odbor-kultury-a-cestovniho-ruchu/o-odboru-2.html).
- Domov pro seniory Třeboňsko (IČO 22032703) je příspěvková organizace Jihočeského kraje, nikoli města. [Zřizovací listina kraje](https://kraj-jihocesky.cz/ku_file/213964/0).
- Stavební bytové družstvo Města Třeboň 2000 (IČO 26019663) a Nadace Jihočeské cyklostezky (IČO 26080320) jsou vazby města, ne běžné městské organizace. Před rozšířením sledování je oddělit podle typu vztahu (vlastnictví, zřizovatelství, zakladatelství, členství) a rozhodnout, zda je uživatel chce zahrnout. [Závěrečný účet](https://www.mesto-trebon.cz/text/uploads/news/id11475/Navrh-zaverecneho-uctu-mesta-Trebone-za-rok-2021.pdf).

IČO v `config/subjekty.yaml` slouží pro vyhledání smluv napříč Registr smluv. Neznamená automaticky, že subjekt má vlastní profil zadavatele.

## E‑ZAK: veřejné zakázky

### Strojový export

Vyhláška č. 345/2023 Sb. předepisuje strukturovaný XML export na adrese:

```text
https://<adresa-profilu>/XMLdataVZ?od=DDMMRRRR&do=DDMMRRRR
```

Parametry `od` a `do` omezují období změn; jeden dotaz smí pokrývat nejvýše 366 dní. Export je GET a zahrnuje zakázky, u nichž v daném období došlo ke změně na profilu. Schéma XML/XSD stanovuje příloha vyhlášky. [§ 11 vyhlášky na e‑Sbírce](https://e-sbirka.gov.cz/sb/2023/345).

Příklad adresy odvozený pro profil města (samotnou XML odpověď v tomto auditu nebylo možné spolehlivě načíst a validovat):

```text
https://zakazky.mesto-trebon.cz/profile_display_2.html/XMLdataVZ?od=01112026&do=18112026
```

První implementační krok musí ověřit HTTP odpověď pro všech pět profilů uvedených v konfiguraci, dekódování, XSD a chování při prázdném období. Zatím nepoužívat HTML jako primární zdroj, dokud tento pokus neproběhne. Výsledek je nutné porovnat s veřejnou stránkou E‑ZAK.

### Fallback HTML

Profil města uvádí název, IČO a ID profilu VVZ `Z2019-003053`; stránkování přehledu používá parametr `page` (např. `?page=2`). Veřejná stránka obsahuje fázi, režim, datum zahájení a lhůtu pro nabídky. Detail zakázky doplňuje smlouvu, vybraného dodavatele a případnou skutečně uhrazenou cenu, pokud je zadavatel doplnil. [Profil města](https://zakazky.mesto-trebon.cz/profile_display_2.html).

**Doporučení:** XML export jako primární strukturovaný přísun, HTML detail zakázky jako kontrola a doplnění veřejných dokumentů. Propojení se smlouvami dělat přes ID smlouvy z Registru smluv nebo přes evidenční číslo zakázky, pokud je přímo doložené. Název zakázky sám nestačí.

## Registr smluv

### Formát a aktualizace

Oficiální otevřená data jsou měsíční XML dumpy v [adresáři Registru smluv](https://data.smlouvy.gov.cz/). Jméno dumpu je `dump_<YYYY>_<MM>.xml`, index je `index.xml`. Aktuální měsíc se přegenerovává denně od začátku měsíce; dokončení měsíce se označí v indexu. Dump obsahuje metadata verzí záznamů a odkazy/hash příloh, nikoli binární přílohy. Znepřístupnění nebo oprava může změnit i starší dumpy; databáze proto musí umět zpětnou synchronizaci a vyřazení neplatných/odvolaných záznamů. [Oficiální popis otevřených dat](https://smlouvy.gov.cz/stranka/otevrena-data).

### Vzor záznamu

[Město Třeboň, záznam 40272565](https://smlouvy.gov.cz/smlouva/40272565) je kontrolní vzorek: stránka ukazuje **ID smlouvy 37878325**, **ID verze 40272565**, číslo verze 1, datum zveřejnění, smluvní strany, datum uzavření, hodnotu bez/včetně DPH a přílohy. Jiný novější záznam se stejným vzorem může mít v roli protistrany městskou organizaci. Pro záznam evidovat alespoň:
- `id_smlouvy` jako identifikátor dlouhodobého záznamu;
- `id_verze` jako identifikátor konkrétního zveřejnění/verze;
- `cislo_verze`, stav platnosti, datum zveřejnění a ID subjektů;
- vazbu na předchozí smlouvu/dodatek pouze tehdy, je-li explicitně přítomna v metadatech nebo textu dokumentu.

Registr udržuje historii verzí a dokumentace popisuje modifikace, přidávání příloh a vazby záznamů. Samotný název „Dodatek č. 1“ ale nestačí k automatickému spárování. [Technické řešení Registru](https://smlouvy.gov.cz/stranka/technicke-reseni), [změny rozhraní](https://smlouvy.gov.cz/stranka/popis-nasazenych-uprav).

**Doporučení:** pro první pilot stáhnout jeden dump XML, ověřit jeho XSD a najít v něm výše uvedený záznam. Pak teprve implementovat parser; při každém běhu porovnávat verze i jejich platnost, ne jen přidávat nová ID.

## WordPress trebonaci.cz: projekty ze strategického plánu

Veřejný endpoint [`/wp-json/trebonaci/v1/projekty`](https://trebonaci.cz/wp-json/trebonaci/v1/projekty) vrací JSON pole. Kontrolní vzorek měl `id: 400`, název aktivity, ID a název osy, opatření, `stav`, komentář a bodovou geometrii. Zaznamenané klíče ve vzorku: `id`, `aktivita`, `osa_id`, `osa_nazev`, `color`, `opatreni`, `stav`, `komentar`, `geometrie`, `geo_sirka`. Endpoint při čtení vracel celý seznam bez stránkování. Klíč `id` je interní ID WordPressu; karty musí používat vlastní stabilní ID a URL zdroje.

Jde o redakční evidenci navázanou na strategický plán a mapu. Záznam projektu v této evidenci nedokládá, že město projekt schválilo, financuje nebo právě realizuje. Význam stavů `Hotovo`, `Plánováno`, `Neřeší se`, `Neznámo` ověřit proti metodice mapy a aktuálnímu strategickému plánu. Použít jako podnět k propojení; rozhodnutí, peníze a průběh potvrzovat úředním zdrojem.

## WordPress trebonaci.cz: občanské podněty

Veřejný endpoint [`/wp-json/trebonaci/v1/podnety`](https://trebonaci.cz/wp-json/trebonaci/v1/podnety) vrací víc než údaje pro mapu: ve vzorcích obsahoval jména nebo přezdívky, celý text, přesné souřadnice, fotografie, komentáře a také interní údaje o předání městu, odboru a způsobu vyřízení. Tento endpoint proto **nepoužít jako veřejný datový feed** pro novou informační stránku.

Navržený oddělený veřejný výstup po redakční kontrole:
- stabilní ID podnětu;
- zobecněná poloha (např. bod zaokrouhlený na 3 desetinná místa, nebo územní oblast);
- kategorie;
- veřejný stav s vysvětlením, co znamená;
- redakčně upravené a anonymizované shrnutí;
- datum poslední redakční aktualizace.

Nevystavovat jméno, e-mail, původní nepročištěný text, diskusi, obrázky, přesné souřadnice, hlasování ani interní názvy odborů, předání městu a workflow. Souřadnice zaokrouhlené na 3 desetinná místa jsou pouze počáteční návrh; před zpřístupněním ověřit, že v kombinaci s textem nejde autora snadno určit. Redakční kontrola má přednost před automatickým přenosem.

## Co ještě ověřit v navazující implementační práci

1. Stáhnout a validovat XML export E‑ZAK pro město a každý existující profil; potvrdit také identitu profilu Bertiných lázní v ARES a zda jde pouze o historický profil.
2. Stáhnout měsíční XML Registru smluv, ověřit XSD a nalézt kontrolní vzorek ID 37852129 / verze 40245369 nebo jiný aktuální záznam města.
3. Ověřit, zda lze u WordPress endpointů přidat omezený parametrický výstup a verzi schématu bez změny současných map.
4. Jednou ročně porovnat seznam IČO s aktuálním závěrečným účtem, zřizovacími listinami a ARES. Oddělovat městské právnické osoby, příspěvkové organizace, historické subjekty a partnerské organizace.
