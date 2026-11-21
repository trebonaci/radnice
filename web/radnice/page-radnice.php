<?php
/**
 * Template Name: Přehled radnice
 *
 * Datový přehled radnice Třeboň (repozitář trebonaci/radnice, #177).
 * Data se načítají v prohlížeči z JSON v uploads (nezávisle na WP Super Cache, ZADANI.md kap. 6).
 * Soubory: radnice/radnice.css, radnice/radnice.js v šabloně; uploads/radnice/ukazatele.json.
 */
$radnice_ver = '2026-11-21';
wp_enqueue_style('trb-radnice', get_template_directory_uri() . '/radnice/radnice.css', array(), $radnice_ver);
wp_enqueue_script('trb-radnice', get_template_directory_uri() . '/radnice/radnice.js', array(), $radnice_ver, true);
$uploads = wp_upload_dir();
get_header();
?>
<main class="trb-radnice" id="trb-radnice"
      data-src="<?php echo esc_url($uploads['baseurl'] . '/radnice/ukazatele.json'); ?>">
  <header class="trb-radnice__hlava">
    <span class="trb-radnice__stitek">Přehled radnice</span>
    <h1><?php the_title(); ?></h1>
    <p class="trb-radnice__lead">Co rada a zastupitelstvo projednávají, jaké smlouvy a zakázky město a jeho organizace uzavírají a kam jdou investice. Čísla počítá kód z veřejných zdrojů uvedených u každého údaje.</p>
  </header>
  <div class="trb-radnice__obsah" aria-live="polite"><p class="trb-radnice__nacitani">Načítám data…</p></div>
  <p class="trb-radnice__pata">Nejde o web Města Třeboň. Data pocházejí z veřejných zdrojů uvedených u každého údaje.</p>
</main>
<?php get_footer();
