# Datový model (koncept 0.1)

Formát: JSON/CSV v `data/`, jeden soubor na typ entity (nebo na entitu u projektů). Stabilní ID, vazby přes ID.

## Entity

### subjekt
`id` (IČO), `nazev`, `typ` (mesto / sro / po), `zdroj`

### dokument
Každý zdrojový soubor nebo záznam.
`id`, `typ` (zapis_zm / zapis_rada / smlouva / zakazka / rozpocet / jine), `url`, `datum_zverejneni`, `stazeno`, `sha256`, `ocr` (bool), `subjekt_id`

### jednani
`id` (např. `zm-2026-01`), `organ` (zm / rada), `cislo`, `datum`, `dokument_id`

### usneseni
`id` (např. `rm-2026-03-045`), `jednani_id`, `cislo`, `text`, `vysledek` (schvaleno / zamitnuto / vzato_na_vedomi / odlozeno), `kategorie[]`, `tema` (krátký titulek), `shrnuti` + `shrnuti_ai` (bool), `citace` {`dokument_id`, `strana`, `text`}, `castky[]`, `subjekty_ico[]`, `parcely[]`, `projekt_ids[]`, `overeni` (navrh / overeno_kodem / overeno_modelem_b / schvaleno)

### hlasovani
`usneseni_id`, `pro`, `proti`, `zdrzel`, `nehlasoval`, `jmenovite` [{`osoba_id`, `hlas`}], `zdroj`

### osoba
Jen volení zástupci. `id`, `jmeno`, `klub`, `obdobi[]`

### zakazka
`id` (ID z E-ZAK), `subjekt_id`, `nazev`, `druh` (stavebni / dodavky / sluzby), `rezim` (VZMR / zjednodušené podlimitní / …), `predpokladana_hodnota`, `stav`, `datum_zahajeni`, `datum_zadani`, `vitez_ico`, `vysoutezena_cena`, `url`, `projekt_ids[]`

### smlouva
`id` (ID verze z registru smluv), `subjekt_id`, `protistrana_ico`, `predmet`, `hodnota_bez_dph`, `hodnota_s_dph`, `dph_dopocteno` (bool), `datum_uzavreni`, `typ` (smlouva / dodatek), `navazuje_na` (u dodatku), `zakazka_id`, `projekt_ids[]`, `url`

### castka
Jednotný zápis peněz kvůli rozlišení druhů.
`hodnota`, `mena`, `s_dph` (bool / null = neuvedeno), `druh` (odhad / rozpocet_schvaleny / rozpocet_upraveny / predpokladana_hodnota / vysoutezena / smluvni / dodatek / zaplaceno / dotace_prislib / dotace_prijata), `datum`, `zdroj`

### projekt
Ručně spravovaný soubor `data/projekty/<slug>.yaml`.
`id`, `nazev`, `oblast` (investice / sport / kultura / social / skolstvi / doprava / zivotni_prostredi / …), `sprm_opatreni[]`, `stav` (namet / priprava / rozhodnuto / soutez / realizace / dokonceno / zastaveno), `popis`, `castky[]`, `udalosti[]`, `usneseni_ids[]`, `zakazka_ids[]`, `smlouva_ids[]`, `parcely[]`, `plan` [{`krok`, `planovano`, `skutecnost`}], `jistota_vazeb` (doloženo / naše propojení)

### udalost
Krok časové osy projektu. `datum`, `typ` (zamer / usneseni / soutez / smlouva / zahajeni / dodatek / dokonceni / kolaudace / jine), `popis`, `zdroj`, `jistota`

### sprm_opatreni
Ze Strategického plánu 2021–2030. `id`, `oblast`, `cil`, `nazev`, `stav_dle_trebonaci` (z endpointu `/projekty`)

### parcela
`katastralni_uzemi`, `cislo`, `ruian_id`, `geometrie` (z ČÚZK)

## Zásady
- Surová data (`raw/`) se neupravují; vše odvozené je reprodukovatelné skriptem.
- Každé pole odvozené AI má příznak a stav ověření.
- Osobní údaje fyzických osob se do `data/` nezapisují (anonymizace už v extrakci).
