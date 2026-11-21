# Designová pravidla: Přehled dění na radnici

Pracovní podklad pro návrh a implementaci nové části webu trebonaci.cz. Pravidla navazují na současnou WordPress šablonu a mají se použít pouze pro novou část. Nejsou zadáním k celkové změně vizuální identity ani k refaktoru stávajících stránek.

## 1. Účel stránky

Stránka má návštěvníkovi srozumitelně ukázat, co se na radnici projednává, rozhoduje nebo připravuje. Má oddělit ověřitelné informace od komentáře a nabídnout cestu ke zdrojovému dokumentu či původnímu záznamu.

- Piš věcně, jednoduše a bez stranického žargonu.
- U každé položky uveď, co se stalo nebo má stát, kdy, kdo o tom rozhodoval a jaký je další krok — pouze pokud jsou tyto informace doložené.
- Rozlišuj **rozhodnuto**, **navrženo**, **projednává se** a **plánuje se**. Neprezentuj návrh jako hotové rozhodnutí.
- Uveď datum jednání/rozhodnutí a datum poslední aktualizace přehledu.
- Každé tvrzení opři o odkaz na veřejný zdroj (usnesení, zápis, materiál, veřejnou zakázku nebo oficiální zprávu). Pokud zdroj chybí, položku nezveřejňuj jako ověřený fakt.
- Odděluj shrnutí dokumentu od stanoviska Třeboňáků. Stanovisko označ samostatně a podepiš či připiš autora.
- Opravy a aktualizace popisuj otevřeně; nemaž historii tak, aby nebylo poznat, že se údaj změnil.

## 2. Vizuální směr

- Zachovej společnou hlavičku, navigaci, patičku a základní šířku webu. Nová stránka je součást trebonaci.cz, ne samostatný mikroweb.
- Použij běžný světlý systém vnitřních stránek. Tmavý hero je vyhrazený zejména pro současnou homepage; nová stránka nemá zavádět další výraznou barevnou identitu.
- Použij stávající hero/stránkovou kompozici a designové tokeny. Nevytvářej novou globální paletu, typografii ani vlastní hlavičku.
- Primární obsah má být klidný a redakční: jasný nadpis, krátké vysvětlení, přehledné filtry a čitelné položky v kartách nebo seznamu.
- Stav položky vyjadřuj vždy textovým štítkem; barva je pouze doplňková. Nepoužívej samotnou barvu jako jediný nositel významu.
- Akcentní zelenou používej střídmě pro orientaci nebo akci. Růžovou STAN ponech pro označení podpory Starostů, ne pro obecné stavy či varování.

## 3. Existující tokeny a technické meze

Podkladem je aktuální `css/01-tokens.css`, ne staré hodnoty natvrdo opsané do nové komponenty:

- primární barva: `var(--primary)` — nyní `#006684`;
- pozadí a text: `var(--canvas)`, `var(--text-color)`, `var(--text-mid)`;
- akcenty: `var(--green)`, `var(--green-dark)`, `var(--green-bg)`, `var(--blue)`;
- písmo: `var(--font-head)` a `var(--font-body)`;
- šířka stránky: `var(--trb-page-max)` (nyní 1140 px);
- rohy: `var(--r-sm)`, `var(--r-md)`, `var(--r-lg)`, `var(--r-xl)`;
- rozestupy: stávající `--space-*` a `--trb-section-*`.

Nehardcoduj nové hex barvy, fonty, radiusy ani náhodné šířky, pokud pro ně existuje token. Před úpravou ověř konkrétní dostupné názvy v tokenovém souboru.

V souborech je známý nesoulad: `theme.json` používá jiné barvy a font než CSS tokeny (např. `#00618d` a Plus Jakarta Sans oproti `#006684` a system-ui). Pro tuto implementaci **nesnaž se tento globální nesoulad napravit**. Nová stránka má zdědit současný běh webu a používat CSS tokeny. Případná sjednocující migrace je samostatný úkol.

## 4. Typografie a rozvržení

- Dědí se existující font z tokenů; nenačítej další font.
- Nadpisy krátké, popisné a s jasnou hierarchií. Text běžné velikosti musí zůstat pohodlně čitelný na telefonu.
- Hlavní sloupec drž v rámci šířky webu; delší vysvětlující text může být užší než seznam záznamů.
- Na začátku stránky nabídni stručné vysvětlení, co přehled zahrnuje, jak často se aktualizuje a co znamenají štítky stavu.
- Na mobilu přeuspořádej filtry nad seznam; nepoužívej horizontální tabulku ani ovládání, které vyžaduje přesné míření.
- Zajisti viditelný focus, ovládání klávesnicí, dostatečný kontrast a respektování `prefers-reduced-motion`.

## 5. Obsahové komponenty

### Záznam / karta

Každá karta má v tomto pořadí:

1. typ nebo oblast tématu (např. rada města, zastupitelstvo, investice),
2. stav jako textový štítek,
3. věcný titulek,
4. krátké shrnutí v několika větách,
5. datum události a případně datum aktualizace,
6. odkaz na primární zdroj,
7. případně stručně uvedený další krok.

Nevkládej do karty dlouhé citace, neověřené odhady ani více témat, která spolu nesouvisí. Detailní podklady otevři v samostatném detailu nebo přímo na zdrojovém dokumentu.

### Filtry a řazení

- Filtry mají být jednoduché: téma/oblast a stav; datum jen pokud objem záznamů skutečně vyžaduje časové filtrování.
- Ukaž možnost filtr zrušit a srozumitelný počet výsledků nebo prázdný stav.
- Výchozí řazení: nejnovější události nahoře; datum aktualizace nesmí potichu měnit datum samotné události.
- Filtry nesmí skrývat zásadní vysvětlení ani zdrojové odkazy.

### Odkazy a dokumenty

- Popiš cíl odkazu konkrétně (např. „Zápis ze zasedání zastupitelstva, 12. 11. 2026“), ne pouze „Více“.
- U externích dokumentů zachovej informaci o typu zdroje a datu.
- Pokud odkaz vede na PDF, označ to v textu odkazu.

## 6. Politická a institucionální přesnost

- Nepřipisuj radnici ani zastupitelům motivy, které nejsou doložené.
- Nezaměňuj radu města, zastupitelstvo, městský úřad a městské společnosti.
- Výsledek hlasování uváděj pouze z primárního záznamu a ve stejném významu, v jakém je zdroj uvádí.
- U sporných bodů nabídni odkaz na původní dokument a jasně odliš citaci, shrnutí a vlastní komentář.
- Stávající pravidlo o nezveřejňování odpovědných odborů a stavů se týká veřejné části občanských podnětů fáze 1. **Automaticky ho nerozšiřuj na tento nový přehled**; pro přehled radničního dění uváděj instituci či odpovědnost jen tehdy, je-li to věcně nutné a veřejně doložené.

## 7. CSS/WordPress implementace

- Nové styly drž v samostatném stránkovém souboru, např. `css/pages/radnice-prehled.css`, a napoj je přes existující logiku `inc/enqueue.php` pouze na příslušnou stránku/šablonu.
- Všechny nové selektory omez pod jediný kořen, např. `.trb-radnice-prehled`; pro prvky používej konzistentní prefix `trb-radnice-*`.
- Respektuj současné pořadí načítání CSS. Nevkládej další globální override ani nové `!important` bez konkrétního zdokumentovaného důvodu.
- Znovu použij existující komponentu hero, kontejner, tlačítka a karty, pokud odpovídají účelu. Nezakládej paralelní kopii stejného prvku.
- Neměň menu v PHP — jeho obsah a pořadí spravuje administrace WordPressu.
- Neprováděj v rámci této stránky celkovou opravu `theme.json`, globálních tokenů ani historických CSS souborů.

## 8. Kontrola před předáním

- Ověřit desktop i mobil, klávesnici, focus, stav bez výsledků, dlouhé titulky a položku bez volitelného údaje.
- Ověřit, že stránka používá společný header/footer a její CSS se nenačítá na ostatních stránkách.
- Ověřit všechny odkazy na primární zdroje a zkontrolovat data a stav každého záznamu.
- Porovnat před/po screenshot nové stránky; při změně sdílené komponenty zkontrolovat také stránky, které ji používají.
- Neprovádět nevyžádaný refaktor zbytku webu.

## 9. Verzování webu — doporučený postup, odděleně od designu

Celkovou revizi webu je vhodné dělat po malých, vratných změnách v GitHubu. Nejdřív zjistit skutečný stav místního Git repozitáře a případného vzdáleného repozitáře; nepřepisovat historii ani znovu nevytvářet repozitář bez kontroly.

1. Založit nebo potvrdit **soukromý GitHub repozitář** obsahující pouze zdroj vlastní WordPress šablony a potřebné projektové soubory.
2. Před prvním push ověřit `.gitignore`: nezahrnout přístupové údaje, FTP/WordPress hesla, tajné klíče, databázi, produkční uploady, cache, logy a dočasné exporty.
3. Zachovat `main` jako stabilní větev; práci dělat v samostatných větvích a vracet přes pull request. První PR má být pouze dokumentační/designové, bez produkční změny.
4. Nechat současné ruční nahrávání přes FTP beze změny, dokud nebude GitHub historie kompletní a bezpečný postup nasazení ověřený na stagingu.
5. Později přidat automatické nasazení až po odsouhlasení: nejdřív staging, kontrola diffu a záloha; produkci nasazovat jen z konkrétní schválené verze.

GitHub se má stát záznamem zdrojových změn a kontrolou před nasazením, ne paralelní neřízenou kopií webu. Živý obsah WordPressu a databáze jsou samostatná vrstva.
