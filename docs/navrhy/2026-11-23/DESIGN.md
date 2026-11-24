---
name: Třeboň Civic Data System
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#424936'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#727a64'
  outline-variant: '#c1cab0'
  surface-tint: '#416900'
  primary: '#416900'
  on-primary: '#ffffff'
  primary-container: '#84cc16'
  on-primary-container: '#315200'
  inverse-primary: '#91db2a'
  secondary: '#565e74'
  on-secondary: '#ffffff'
  secondary-container: '#dae2fd'
  on-secondary-container: '#5c647a'
  tertiary: '#006398'
  on-tertiary: '#ffffff'
  tertiary-container: '#70bfff'
  on-tertiary-container: '#004d77'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#acf847'
  primary-fixed-dim: '#91db2a'
  on-primary-fixed: '#102000'
  on-primary-fixed-variant: '#304f00'
  secondary-fixed: '#dae2fd'
  secondary-fixed-dim: '#bec6e0'
  on-secondary-fixed: '#131b2e'
  on-secondary-fixed-variant: '#3f465c'
  tertiary-fixed: '#cce5ff'
  tertiary-fixed-dim: '#93ccff'
  on-tertiary-fixed: '#001d31'
  on-tertiary-fixed-variant: '#004b73'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
  accent-lime: '#94C83D'
  accent-lime-light: '#ecfccb'
  accent-lime-dark: '#4d7c0f'
  surface-dark: '#111827'
  surface-dark-subtle: '#1f2937'
  surface-light: '#f8fafc'
  surface-card: '#ffffff'
  category-stavba: '#f59e0b'
  category-zmena: '#84cc16'
  category-rozhodnuti: '#3b82f6'
  category-kriticke: '#ef4444'
  border-subtle: '#e2e8f0'
  border-dark: '#334155'
typography:
  display-hero:
    fontFamily: Plus Jakarta Sans
    fontSize: 56px
    fontWeight: '800'
    lineHeight: 64px
    letterSpacing: -0.03em
  display-hero-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 36px
    fontWeight: '800'
    lineHeight: 42px
    letterSpacing: -0.02em
  kpi-metric:
    fontFamily: Plus Jakarta Sans
    fontSize: 48px
    fontWeight: '800'
    lineHeight: 52px
    letterSpacing: -0.03em
  kpi-metric-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 36px
    fontWeight: '800'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.025em
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 26px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 26px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-uppercase:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 14px
    letterSpacing: 0.08em
  label-badge:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.01em
  code-data:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 2rem
  margin-mobile: 1rem
  space-3xs: 0.125rem
  space-2xs: 0.25rem
  space-xs: 0.5rem
  space-sm: 0.75rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
  space-2xl: 3rem
  space-3xl: 4.5rem
  space-4xl: 6rem
---

## Brand & Style

Tento design systém je navržen pro transparentní komunální správu, městskou analytiku a občanskou participaci. Vychází z principů precizní datové žurnalistiky (Bloomberg Graphics, Axios) a moderních analytických dashboardů (Stripe, Linear). 

Cílem je transformovat složitá městská data, hlasování, rozpočty a územní rozhodnutí do okamžitě srozumitelných, vizuálně působivých a důvěryhodných struktur.

Vizuální směr kombinuje:
- **Minimalistický datový purismus:** Čistý, strukturovaný layout se štědrým prostorem, jemnou linkovou architekturou a striktním typografickým řádem.
- **Vysoký kontrast a akcentní dynamiku:** Hluboké antracitové plochy (`#121820` / `#18181b`) v kontrastu se zářivou limetkovou zelení (`#94C83D`), která slouží jako navigační maják a indikátor klíčových metrik a změn.
- **Funkční modularitu:** Robustní kartový systém s mikrometrikatury (KPI), štítky kategorií (Stavba, Změna, Rozhodnutí) a interaktivními filtry pro přímou práci s informacemi.

## Colors

Barevná paleta je postavena na principu funkční hierarchie a vysoké čitelnosti:

- **Primary (`#84cc16` / `#94C83D`):** Elektrická limetková zeleň. Slouží výhradně pro klíčové interakce, aktivní filtry, schválené stavy a dominantní KPI metriky. V tmavém režimu funguje jako energický neonový akcent.
- **Secondary (`#0f172a` / `#111827`):** Temný grafitový odstín vytvářející autoritativní rámec. Používá se pro hlavní záhlaví, tmavé sekce (hero zóny, footer) a klíčové kontrastní komponenty.
- **Tertiary (`#0284c7`):** Klidná technická modř pro sekundární datové série, infografické linie a informační vazby.
- **Neutrální škála (`#f8fafc` až `#0f172a`):** Základní pozadí tvoří měkká, neoslňující bílá `#f8fafc`. Karty a panely využívají čistě bílou `#ffffff` s ultrajemným ohraničením `#e2e8f0`.

### Kategoriální tokeny
Pro označování městských agend jsou striktně dedikovány semantické barvy:
- `category-stavba` (`#f59e0b`): Projekty v realizaci, stavební uzávěry, infrastruktura.
- `category-zmena` (`#84cc16`): Revize rozpočtu, schválené vyhlášky, modernizace.
- `category-rozhodnuti` (`#3b82f6`): Hlasování zastupitelstva, oficiální usnesení, administrativní akty.
- `category-kriticke` (`#ef4444`): Zamítnuté návrhy, zpoždění, krizová hlášení.

## Typography

Typografický systém vytváří syntézu mezi moderním geometrickým charakterem a technickou čitelností dat:

> **Písmo (24. 11. 2026):** Ondřej rozhodl, že oba weby používají jediné písmo **Inter**. Hodnoty `Plus Jakarta Sans` níže popisují původní grafické návrhy z 23. 11.; v šabloně se nepoužívají. Zbytek odstavce o typografii (tloušťky, záporné prostrkání) platí dál, jen v Interu.

- **Nadpisy & KPI (`Plus Jakarta Sans`):** Vybrán pro moderní proporce a autoritativní tloušťky. Velká čísla a nadpisy sekcí mají záporný letter-spacing (-0.02em až -0.03em), což jim dodává kompaktní, publicistický vzhled v duchu Axios a Financial Times.
- **Běžný text a tabulková data (`Inter`):** Optimální rozložení tahů a neutrální charakter zaručují bezchybnou čitelnost při velkých objemech textu, v tabulkách i na datových osách grafů. Využívá tabular numbers (`tnum`) pro vertikální srovnání číselných hodnot.
- **Nadnadpisy sekcí (Kicker):** Formátovány přes `label-uppercase` – výhradně verzálkami s rozšířeným prostrkáním (+0.08em) pro okamžité uvedení do kontextu kapitoly.

## Layout & Spacing

Systém využívá přísný 8bodový spacingový rastr kombinovaný s flexibilní 12sloupcovou mřížkou:

- **Desktop (od 1200px):** 12 sloupců, maximální šířka obsahu 1280px, gutter `1.5rem` (24px), vnější okraje `2rem` (32px).
- **Tablet (768px – 1199px):** 8 sloupců, gutter `1.25rem` (20px), vnější okraje `1.5rem` (24px).
- **Mobile (do 767px):** 4 sloupce, gutter `1rem` (16px), vnější okraje `1rem` (16px).

### Rytmus a kompozice
- **Vzdušnost:** Sekce jsou odděleny vertikálními mezerami `space-3xl` až `space-4xl`.
- **Datová hustota:** Uvnitř analytických tabulek, grafových legend a seznamů se používá zhuštěné škálování (`space-2xs` až `space-sm`), které minimalizuje nutnost rolování.
- **Asymetrické bloky:** Využití rozdělených řad (split views) – vlevo dominantní metrika nebo kontextové shrnutí, vpravo detailní tabulka nebo rozpadový graf.

## Elevation & Depth

Design odmítá těžké realistické stíny. Hloubka je organizována strukturálně a vrstveně:

- **Hraniční architektura (Borders first):** Většina prvků a karet je vymezena jemnou linkou `1px solid var(--border-subtle)` (`#e2e8f0`) v kombinaci s čistě bílou plochou. V tmavém režimu je použit rámeček `#334155`.
- **Jemný difuzní stín (Ambient Surface):** Karty s vyšší prioritou a KPI widgety používají měkký, nízko-kontrastní stín: `0 4px 20px -2px rgba(15, 23, 42, 0.05)`.
- **Aktivní / Hover elevace:** Při najetí myši se prvek zvedne o 2px s posíleným stínem `0 12px 28px -4px rgba(15, 23, 42, 0.08)` a zvýrazněním rámečku limetkovým akcentem.
- **Tmavé dominantní boxy:** Tmavé karty a hero sekce (`#111827`) fungují jako hloubkový základ celého layoutu. Uvnitř těchto bloků se vnitřní panely odlišují pouze tónem pozadí (`#1f2937`) bez stínů.
- **Sklo (Frosted overlay):** Plovoucí lišty filtrů a navigační hlavičky využívají efekt `backdrop-filter: blur(12px)` s 85% neprůhledností barvy podkladu.

## Shapes

Tvarosloví je vyvážené – dostatečně moderní a vstřícné, přitom precizní a formální:

- **Základní poloměr (`0.5rem` / 8px):** Tlačítka, vstupní pole, buňky tabulek a štítky.
- **Karty a moduly (`rounded-lg` – `1rem` / 16px):** Datové karty, KPI panely, dialogová okna a vyskakovací grafy.
- **Hero karty a vizualizační rámce (`rounded-xl` – `1.5rem` / 24px):** Výrazné tmavé obsahové bloky.
- **Plně zakulacené (Pill / `9999px`):** Indikátory stavu, kategorie, interaktivní chip filtry a kruhové KPI medailony.

## Components

### 1. Tlačítka (Buttons)
- **Primary:** Pozadí `#84cc16`, text `#111827`, font-weight 600, border radius `0.5rem`. Při hoveru `#94C83D` a mírný posun.
- **Secondary Dark:** Pozadí `#111827`, text `#ffffff`, border `1px solid #1f2937`.
- **Ghost / Outline:** Transparentní podklad, border `1px solid #e2e8f0`, text `#0f172a`. Při hoveru podklad `#f1f5f9`.
- **Inline Action:** Textový odkaz doplněný šipkou (`→`), s podtržením až při hoveru a akcentem v limetkové barvě.

### 2. Kategoriální tagy a štítky (Category Badges)
- Tvar: Pill (`rounded-full`), výška 24px, padding `0 10px`, písmo `label-badge` (12px/600).
- **Stavba:** Podklad `rgba(245, 158, 11, 0.12)`, text `#b45309`, tečka indikátoru `#f59e0b`.
- **Změna:** Podklad `rgba(132, 204, 22, 0.15)`, text `#3f6212`, tečka indikátoru `#65a30d`.
- **Rozhodnutí:** Podklad `rgba(59, 130, 246, 0.12)`, text `#1d4ed8`, tečka indikátoru `#3b82f6`.

### 3. Filtry a segmentátory (Interactive Chips & Segmented Controls)
- Horizontálně posuvné pruhy s možností vícenásobného i exkluzivního výběru.
- Neaktivní chip: Světlý podklad `#f1f5f9`, ohraničení `#e2e8f0`, text `#475569`.
- Aktivní chip: Pozadí `#111827`, text `#ffffff`, limetková zvýrazňující tečka nebo lem.

### 4. KPI a analytické karty (Metric Cards)
- Bílý nebo tmavě antracitový podklad, rámeček `1px solid var(--border-subtle)`.
- V horní části: `label-uppercase` název metriky v šedé barvě a kontextová kategorie.
- Uprostřed: Obří hodnota `kpi-metric` (např. „17“, „54,91 %“), doprovázená limetkovým grafickým prvkem nebo mini-grafem trendu (sparkline).
- Spodní část: Srovnání s předchozím obdobím nebo dílčí textová vysvětlivka v `body-sm`.

### 5. Datové pruhy a grafické rozdělení (Distribution Bars)
- Segmentované barevné ukazatele rozložení mandátů a rozpočtů inspirované volebními speciály.
- Výška pruhu 8px až 12px, jednotlivé strany/kategorie barevně odděleny 2px bílou mezerou.
- Následováno legendou s interaktivním hover efektem synchronizovaným s daným segmentem.

### 6. Vstupní pole a vyhledávání (Input Fields)
- Pozadí `#ffffff`, ohraničení `1px solid #cbd5e1`, vnitřní odsazení `0.75rem 1rem`.
- Focus stav: Rámeček ztmavne na `#0f172a`, obvodový prstenec (ring) v polo-transparentní limetkové `rgba(132, 204, 22, 0.35)`.
- Integrovaná ikona lupy a rychlá klávesová zkratka (`/` nebo `⌘K`).