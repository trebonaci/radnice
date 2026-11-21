# Datový přehled radnice – modul pro trebonaci-theme (#177)

Stránka čte `ukazatele.json` v prohlížeči (nezávisle na WP Super Cache, ZADANI.md kap. 6). Čísla jen zobrazuje; počítá je `pipeline/ukazatele.py`.

**Zveřejnit až po „schváleno ke zveřejnění“ (Ondřej).**

## Instalace (ručně, FTP na Vedos)
1. Do složky šablony `wp-content/themes/trebonaci-theme/`:
   - `page-radnice.php` do kořene šablony,
   - `radnice.css` a `radnice.js` do podsložky `radnice/`.
2. `data/ukazatele.json` z repozitáře do `wp-content/uploads/radnice/ukazatele.json`.
3. Ve WordPressu: nová stránka (např. „Co se děje na radnici“), šablona stránky **Přehled radnice**, publikovat.
4. Vyprázdnit cache: wp-admin → Nastavení → WP Super Cache → Delete Cache.

Při aktualizaci dat stačí znovu nahrát `ukazatele.json` (stránka ho načítá bez cache).

## Před nasazením ověřit v šabloně
- Názvy tokenů v `css/01-tokens.css`: modul používá `--text`, `--muted`, `--primary`, `--bg-soft`, `--border`, `--surface` s náhradními hodnotami. Kde se jmenují jinak, upravit první řádek `radnice.css` (pravidla `PRAVIDLA-STYLU.md`: žádné pevné barvy mimo náhradní hodnoty).
- Zda `get_header()` / `get_footer()` šablony obalují obsah vlastním kontejnerem (pak odebrat `max-width` z `.trb-radnice`).

## Náhled bez WordPressu
`python -m web.nahled nahled.html` – jedna stránka s vloženými daty.
