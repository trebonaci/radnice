# Přehled dění na radnici – modul pro trebonaci-theme (#177, #187)

Stránka podle designových pravidel `docs/DESIGN-PREHLED-RADNICE.md`. Data čte v prohlížeči z JSON (nezávisle na WP Super Cache); čísla jen zobrazuje, počítá je pipeline (`pipeline/prehled.py`, `pipeline/ukazatele.py`).

**Data se nenahrávají ručně do WordPressu.** `web/build.py` vystaví `prehled.json`, `ukazatele.json` a `beh.json` do `_site/data/` na radnice.trebonaci.cz (Cloudflare Pages, CORS) a denní běh je automaticky aktualizuje. Stránka `/radnice/` je čte z `https://radnice.trebonaci.cz/data/` (filtr `trb_radnice_data_base` umožní zdroj přepnout).

**Zveřejnit až po „schváleno ke zveřejnění“ (Ondřej).**

## Soubory (cesty uvnitř šablony `trebonaci-theme`)
| Soubor v tomto repozitáři | Kam v šabloně |
|---|---|
| `web/radnice/page-radnice-prehled.php` | `page-radnice-prehled.php` |
| `web/radnice/css/pages/radnice-prehled.css` | `css/pages/radnice-prehled.css` |
| `web/radnice/js/radnice-prehled.js` | `js/radnice-prehled.js` |
| `data/prehled.json`, `data/ukazatele.json`, `data/beh.json` | servíruje radnice.trebonaci.cz/data/ (automaticky, netřeba nahrávat) |

## Napojení v `inc/enqueue.php` (jen pro tuto šablonu)
1. `trebonaci_css_files()` – za `'map-chrome'` přidat:
   `'radnice-prehled' => 'css/pages/radnice-prehled.css',`
2. `trebonaci_page_css()` – před `return`:
   ```php
   if (is_page_template('page-radnice-prehled.php')) {
       $css[] = 'radnice-prehled';
   }
   ```
3. `trebonaci_enqueue()` – před `wp_enqueue_script('trebonaci-main', …)`:
   ```php
   if (is_page_template('page-radnice-prehled.php')) {
       wp_enqueue_script('trebonaci-radnice-prehled', $theme . '/js/radnice-prehled.js', [],
           file_exists($dir . '/js/radnice-prehled.js') ? filemtime($dir . '/js/radnice-prehled.js') : '1.0', true);
   }
   ```

## Nasazení (ručně, FTP)
1. Nahrát tři soubory šablony a upravený `inc/enqueue.php`.
2. JSON se nenahrávají – stránka je čte z radnice.trebonaci.cz/data/ (zveřejnění webu radnice = posun větve `verejne`, schvaluje Ondřej).
3. WordPress: nová stránka „Co se děje na radnici“, šablona **Přehled dění na radnici**; položku menu přidat v administraci.
4. Vyprázdnit WP Super Cache (wp-admin → Nastavení → WP Super Cache → Delete Cache).

## Kontrola před předáním (pravidla §8)
Desktop i mobil, klávesnice a focus, stav bez výsledků (filtr, který nic nenajde), dlouhé titulky, položka bez volitelného údaje (bez dalšího kroku), CSS se nenačítá na jiných stránkách, odkazy na zdroje.

## Náhled bez WordPressu
`python -m web.nahled nahled.html --sablona <cesta k trebonaci-theme>` – použije skutečné tokeny, layout a hero šablony; hlavička a patička webu v náhledu chybí.
