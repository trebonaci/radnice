<?php
/**
 * Template Name: Přehled dění na radnici
 * Template Post Type: page
 *
 * Datový přehled radnice Třeboň (repozitář trebonaci/radnice, #177, #187).
 * Data se načítají v prohlížeči z JSON v uploads/radnice/ (nezávisle na WP Super Cache).
 * Styl: css/pages/radnice-prehled.css (enqueue jen na této šabloně, viz inc/enqueue.php),
 * skript: js/radnice-prehled.js. Designová pravidla: DESIGNOVA-PRAVIDLA-PREHLED-RADNICE.md.
 */
defined('ABSPATH') || exit;
$trb_radnice_uploads = wp_upload_dir();
$trb_radnice_data = trailingslashit($trb_radnice_uploads['baseurl']) . 'radnice/';
get_header();
?>
<main class="trb-radnice-prehled"
      data-prehled="<?php echo esc_url($trb_radnice_data . 'prehled.json'); ?>"
      data-ukazatele="<?php echo esc_url($trb_radnice_data . 'ukazatele.json'); ?>"
      data-beh="<?php echo esc_url($trb_radnice_data . 'beh.json'); ?>">
    <header class="page-hero"><div class="container">
        <div class="clanek-breadcrumb">Třeboňáci · Přehled radnice</div>
        <h1><?php the_title(); ?></h1>
        <p>Co rada a zastupitelstvo rozhodly, co se v Třeboni staví a co se připravuje. Každá položka odkazuje na veřejný zdroj.</p>
    </div></header>

    <div class="container trb-radnice-obsah">
        <section class="trb-radnice-uvod" aria-labelledby="trb-radnice-uvod-nadpis">
            <h2 id="trb-radnice-uvod-nadpis">Co přehled zahrnuje</h2>
            <p>Změny pro občany z usnesení rady a zastupitelstva (od září 2026), investiční akce města a městských společností a projekty, ke kterým město zadalo studii nebo projektovou dokumentaci. Data se stahují automaticky každý den ze zápisů z jednání, registru smluv, profilů zadavatelů a rozpočtu města.</p>
            <p class="trb-radnice-aktualizace" data-trb-radnice-aktualizace></p>
            <dl class="trb-radnice-legenda" data-trb-radnice-legenda aria-label="Co znamenají štítky stavu"></dl>
        </section>

        <section class="trb-radnice-seznam" aria-labelledby="trb-radnice-seznam-nadpis">
            <h2 id="trb-radnice-seznam-nadpis">Co se děje</h2>
            <form class="trb-radnice-filtry" data-trb-radnice-filtry role="search" aria-label="Filtrovat přehled" hidden>
                <label class="trb-radnice-filtr">
                    <span>Oblast</span>
                    <select name="oblast"><option value="">Všechny oblasti</option></select>
                </label>
                <fieldset class="trb-radnice-filtr">
                    <legend>Stav</legend>
                    <div class="trb-radnice-stavy" data-trb-radnice-stavy></div>
                </fieldset>
                <button type="reset" class="trb-radnice-zrusit">Zrušit filtry</button>
            </form>
            <p class="trb-radnice-pocet" data-trb-radnice-pocet aria-live="polite">Načítám data…</p>
            <ol class="trb-radnice-polozky" data-trb-radnice-polozky></ol>
            <button type="button" class="trb-radnice-dalsi" data-trb-radnice-dalsi hidden>Zobrazit další</button>
        </section>

        <section class="trb-radnice-cisla" aria-labelledby="trb-radnice-cisla-nadpis" data-trb-radnice-cisla hidden>
            <h2 id="trb-radnice-cisla-nadpis">V číslech</h2>
            <div data-trb-radnice-ukazatele></div>
        </section>

        <p class="trb-radnice-pata">Nejde o web Města Třeboň. Data pocházejí z veřejných zdrojů uvedených u každého údaje. Přehled připravují Třeboňáci; shrnutí usnesení připravuje AI a jeho citace se strojově ověřuje proti zápisu.</p>
    </div>
</main>
<?php get_footer(); ?>
