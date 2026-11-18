# Datový model (koncept 0.3 (upraveno podle pilotu zápisů))

Formát: JSON/CSV v `data/`, jeden soubor na typ entity (nebo na entitu u projektů). Stabilní ID, vazby přes ID.

## Entity

### subjekt
`id` (IČO), `nazev`, `typ` (mesto / sro / po), `zdroj`

### dokument
Každý zdrojový soubor nebo záznam.
`id`, `typ` (zapis_zm / zapis_rada / smlouva / zakazka / rozpocet / jine), `url`, `datum_zverejneni`, `stazeno`, `sha256`, `ocr` (bool), `subjekt_id`

### jednani
`id` = `<organ>-<datum>` (např. `rm-2026-11-04`), `organ` (rada / zastupitelstvo), `druh` (radne / ustavujici / mimoradne), `cislo` (v rámci období), `datum`, `obdobi`, `pritomno_na_zacatku`, `clenu`, `pritomnost_zmeny[]` {`cas`, `udalost`, `osoba`}, `dokument`, `body[]`

### bod_programu (vnořený v jednání)
`cislo`, `nazev`, `strana`, `nazev_anonymizovan`. Body bez usnesení (Různé, Diskuze) se evidují také.

### usneseni
`id` = `<organ>-<rok>-j<jednání>-u<číslo>` (např. `rm-2026-j1-u7` pro „RM č. 7/2026-1“), `jednani_id`, `cislo` (původní označení), `bod`, `text` (+ `text_anonymizovan`), `vysledek` (schvaleno / zamitnuto / vzato_na_vedomi / odlozeno), `kategorie[]`, `tema` (krátký titulek), `shrnuti` + `shrnuti_ai` (bool), `citace` {`dokument_id`, `strana`, `text`}, `castky[]`, `subjekty_ico[]`, `parcely[]`, `projekt_ids[]`, `overeni` (navrh / overeno_kodem / overeno_modelem_b / schvaleno)

### hlasovani
`typ` (usneseni / protinavrh / volba_kandidata), `usneseni_id` (u protinávrhu null), `cast` (I., II. – jen u usnesení s více hlasováními), `predmet` (text protinávrhu / jméno kandidáta), `pro`, `proti`, `zdrzel`, `hlasu_celkem`, `vysledek` (u protinávrhu), `jmenovite` (null = zdroj neuvádí) [{`osoba_id`, `hlas`}], `jednani_id`, `bod`, `strana`

### osoba
Jen volení zástupci. `id`, `jmeno`, `klub`, `obdobi[]`

### zakazka
`id` (ID z E-ZAK), `subjekt_id`, `nazev`, `druh` (stavebni / dodavky / sluzby), `rezim` (VZMR / zjednodušené podlimitní / …), `predpokladana_hodnota`, `stav`, `datum_zahajeni`, `datum_zadani`, `vitez_ico`, `vysoutezena_cena`, `url`, `projekt_ids[]`

### smlouva
`id` (ID verze z registru smluv), `subjekt_id`, `protistrana_ico`, `predmet`, `hodnota_bez_dph`, `hodnota_s_dph`, `dph_dopocteno` (bool), `datum_uzavreni`, `typ` (smlouva / dodatek), `navazuje_na` (u dodatku), `zakazka_id`, `projekt_ids[]`, `url`

### castka
Jednotný zápis peněz kvůli rozlišení druhů.
`hodnota`, `mena`, `s_dph` (bool / null = neuvedeno), `jednotka` (Kč, Kč/m2/rok, …), `druh` (odhad / rozpocet_schvaleny / rozpocet_upraveny / rozpoctove_opatreni / predpokladana_hodnota / vysoutezena / smluvni / dodatek / zaplaceno / najemne_sazba / dar_prijaty / dar_poskytnuty / dotace_prislib / dotace_prijata), `citace`, `datum`, `zdroj`

### projekt
Ručně spravovaný soubor `data/projekty/<slug>.yaml`.
`id`, `nazev`, `oblast` (investice / sport / kultura / social / skolstvi / doprava / zivotni_prostredi / …), `sprm_opatreni[]`, `stav` (namet / priprava / rozhodnuto / soutez / realizace / dokonceno / zastaveno), `popis`, `castky[]`, `udalosti[]`, `usneseni_ids[]`, `zakazka_ids[]`, `smlouva_ids[]`, `parcely[]`, `plan` [{`krok`, `planovano`, `skutecnost`}], `jistota_vazeb` (doloženo / naše propojení)

### udalost
Krok časové osy projektu. `datum`, `typ` (zamer / usneseni / soutez / smlouva / zahajeni / dodatek / dokonceni / kolaudace / jine), `popis`, `zdroj`, `jistota`

### sprm_opatreni
Ze Strategického plánu 2021–2030. `id`, `oblast`, `cil`, `nazev`, `stav_dle_trebonaci` (z endpointu `/projekty`)

### podnet
Z mapy na trebonaci.cz (`/wp-json/trebonaci/v1/podnety`). `id` (WP ID), `typ` (prani / zavada), `stav`, `souradnice`, `kategorie`, `datum`, `usneseni_ids[]`, `projekt_ids[]`. Bez jmen a kontaktů podatelů.

### parcela
`katastralni_uzemi`, `cislo`, `ruian_id`, `geometrie` (z ČÚZK)

## Zásady
- Surová data (`raw/`) se neupravují; vše odvozené je reprodukovatelné skriptem.
- Každé pole odvozené AI má příznak a stav ověření.
- Osobní údaje fyzických osob se do `data/` nezapisují (anonymizace už v extrakci).
