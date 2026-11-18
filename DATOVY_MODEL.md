# Datový model (verze 0.3)

Sjednoceno z návrhu Clauda, návrhu Codexu (PR #1) a zjištění z pilotu zápisů.

## Zásady

- Formát JSON v `data/`, jeden soubor na typ entity; ručně spravované projekty jako `data/projekty/<slug>.yaml`. Stabilní ID, vazby přes ID. Názvy polí česky bez diakritiky.
- Oddělujeme dlouhodobý **projekt**, jednotlivé **události**, **zdrojové dokumenty**, **částky** a **ukazatele přehledu**. Usnesení, zakázka ani smlouva samy o sobě nejsou projektem.
- **Každé pole navržené AI** má vedle sebe příznak `<pole>_ai: true` a údaj je doložen citací (`citace`). Platí pro téma, kategorie, shrnutí i navržené vazby.
- **Stav ověření** (`overeni`) u každého záznamu, který prošel AI: `navrh` → `overeno_kodem` (citace doslova ve zdroji) → `zkontrolovano` (nezávislý kontrolor proti originálu) → `schvaleno` (Ondřej). Automatické ověření citace nenahrazuje kontrolu kontextu.
- **Jistota vazby** (`jistota`): `dolozeno` / `nase_propojeni` / `nevime`. Není to pravděpodobnost a není to povolení ke zveřejnění.
- Neznámá hodnota je `null`, nikdy nula.
- Automatická shoda názvů vytváří jen návrh vazby; potvrdit ji lze přímým identifikátorem nebo ruční kontrolou.
- Surová data (`raw/`) se neupravují; vše odvozené je reprodukovatelné skriptem.
- Osobní údaje fyzických osob, které nejsou volenými zástupci, se do `data/` nezapisují (anonymizace při sestavení). Členy komisí neuvádíme; podnikatele (fyzické osoby) anonymizujeme vždy.

## Entity

### subjekt
`id` (IČO), `nazev`, `typ` (mesto / sro / prispevkova / jina), `rozsah` (smlouvy / zakazky / oboje / nezarazeno), `ezak_profil`. Seznam v `config/subjekty.yaml`.

### dokument
Zdrojový soubor nebo záznam (manifest v `raw/manifest.json`).
`dokument_id`, `typ` (zapis_rada / zapis_zm / smlouva / zakazka / rozpocet / csu / monitor / sprm / jine), `nazev`, `vydavatel`, `url`, `stranka_zdroje`, `datum_dokumentu`, `vyveseno`, `stazeno`, `sha256`, `pocet_stran`, `metoda_textu` (html / textove_pdf / ocr / rucni_prepis / dataset), `omezeni`

### citace
Vnořená struktura: `dokument_id`, `strany[]` nebo jiný lokátor (bod, ID smlouvy), `text` (doslovný úryvek).

### jednani
`id` = `<organ>-<datum>` (např. `rm-2026-11-04`), `organ` (rada / zastupitelstvo), `druh` (radne / ustavujici / mimoradne), `cislo` (v rámci období), `datum`, `obdobi`, `pritomno_na_zacatku`, `clenu`, `pritomnost_zmeny[]` {`cas`, `udalost`, `osoba`}, `dokument`, `body[]`

### bod_programu (vnořený v jednání)
`cislo`, `nazev`, `strana`, `text` (jen u bodů bez usnesení, zobrazuje se v detailu), `nazev_anonymizovan`, `text_anonymizovan`

### usneseni
`id` = `<organ>-<rok>-j<jednání>-u<číslo>` (např. `rm-2026-j1-u7` pro „RM č. 7/2026-1“), `cislo` (původní označení), `jednani_id`, `bod`, `vysledek` (schvaleno / neschvaleno / vzato_na_vedomi / odlozeno / neuvedeno), `text` (+ `text_anonymizovan`), `tema` + `tema_ai`, `kategorie[]` + `kategorie_ai` (číselník `config/kategorie.yaml`), `shrnuti` + `shrnuti_ai`, `citace`, `castky[]`, `parcely[]`, `subjekty_ico[]`, `projekt_ids[]`, `overeni`, `poznamka`

### hlasovani
`typ` (usneseni / protinavrh / volba_kandidata), `usneseni_id` (u protinávrhu null), `cast` (I., II. – jen u usnesení s více hlasováními), `predmet` (text protinávrhu / jméno kandidáta), `pro`, `proti`, `zdrzel`, `hlasu_celkem`, `vysledek` (u protinávrhu), `jmenovite` (null = zdroj neuvádí; jinak [{`osoba_id`, `hlas`}]), `jednani_id`, `bod`, `strana`

### osoba
Jen volení zástupci. `id`, `jmeno`, `klub`, `obdobi[]`, `funkce[]`

### zakazka
`id` (ID z E-ZAK), `subjekt_id`, `nazev`, `druh` (stavebni / dodavky / sluzby), `rezim`, `stav`, `datum_zahajeni`, `datum_zadani`, `vitez_ico`, `castky[]`, `url`, `projekt_ids[]` + `jistota`

### smlouva
`id` (ID verze z registru smluv), `subjekt_id`, `protistrana_ico` (u fyzických osob null), `predmet`, `castky[]`, `datum_uzavreni`, `typ` (smlouva / dodatek), `navazuje_na`, `zakazka_id` + `jistota`, `projekt_ids[]` + `jistota`, `url`

### castka
`hodnota`, `mena`, `jednotka` (Kč, Kč/m2/rok…), `s_dph` (true / false / null = neuvedeno), `druh` (odhad / rozpocet_schvaleny / rozpocet_upraveny / rozpoctove_opatreni / predpokladana_hodnota / vysoutezena / smluvni / dodatek / zaplaceno / najemne_sazba / dar_prijaty / dar_poskytnuty / dotace_pozadovana / dotace_priznana / jine), `obdobi`, `k_datu`, `citace`, `poznamka`. Částky různých druhů se nesčítají ani přímo neporovnávají.

### projekt
Ručně spravovaný soubor `data/projekty/<slug>.yaml`.
`id`, `nazev`, `popis`, `oblast` (investice / sport / kultura / socialni / skolstvi / doprava / zivotni_prostredi / sprava / …), `druh` (investicni / neinvesticni / smiseny), `stav` (pripravuje_se / schvaleno / soutezi_se / smluvne_zajisteno / probiha / dokonceno / pozastaveno / zruseno / nevime) + `stav_k_datu` (redakční stav, ne úřední), `sprm_opatreni[]`, `vlastnik_subjekt_id`, `castky[]`, `udalost_ids[]`, `parcely[]`, `plan` [{`krok`, `planovano`, `skutecnost`}], `aktualizovano`

### udalost
Jeden ověřitelný krok projektu nebo téma, které zatím nemá potvrzenou vazbu na projekt.
`id`, `projekt_id` (null, není-li vazba potvrzena) + `jistota`, `datum` + `druh_data`, `typ` (projednano / navrzeno / doporuceno / rozhodnuto / soutez_vyhlasena / smlouva_uzavrena / dodatek / zahajeni / prubezna_informace / dokonceni / jine), `nazev`, `co_rika_zdroj`, `shrnuti` + `shrnuti_ai`, `vysledek`, `zdroje` (usnesení, smlouvy, zakázky – ID), `citace[]`, `overeni`

### ukazatel (datový přehled)
`id`, `nazev`, `hodnota` (číslo nebo řada), `jednotka`, `obdobi`, `definice`, `vypocet` (skript), `zdroj`, `zkontrolovano`, `srovnatelnost`

### sprm_opatreni
Ze Strategického plánu 2021–2030. Zdroj: existující WordPress evidence `trebonaci_projekt` na trebonaci.cz (endpoint `/projekty`). Před rozšířením se její pole zmapují; druhý katalog SPRM nevytvářet bez rozhodnutí.

### podnet
Z mapy na trebonaci.cz. **Jen omezený veřejný výstup**: `id`, `typ` (prani / zavada), `stav`, `poloha`, `kategorie`, `datum`, upravený popis. Bez jména podatele, kontaktů a diskuse (současný endpoint `/podnety` je vrací, proto se přímo nepoužije). Vazba na projekt/usnesení s `jistota`; občanský návrh se vizuálně odlišuje od projektu, který město připravuje.

### parcela
`katastralni_uzemi`, `cislo`, `cast` (bool), `ruian_id`, `geometrie`, `citace`
