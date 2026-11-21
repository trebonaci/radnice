/* Datový přehled radnice Třeboň (trebonaci/radnice #177). Čte ukazatele.json a vykreslí bloky.
   Čísla jen zobrazuje, nic nepočítá (počty a součty dělá pipeline/ukazatele.py). */
(function () {
  "use strict";
  var el = document.getElementById("trb-radnice");
  if (!el) return;
  var obsah = el.querySelector(".trb-radnice__obsah");

  function esc(t) { return String(t == null ? "" : t).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function cislo(n) { return Math.round(n).toLocaleString("cs-CZ").replace(/ /g, " "); }
  function kc(n) {
    if (n >= 1e6) return (n / 1e6).toLocaleString("cs-CZ", { maximumFractionDigits: 1 }) + " mil. Kč";
    if (n >= 1e3) return (n / 1e3).toLocaleString("cs-CZ", { maximumFractionDigits: 0 }) + " tis. Kč";
    return cislo(n) + " Kč";
  }
  function datum(d) { return d ? d.split("-").reverse().map(function (x) { return +x; }).join(". ") : ""; }
  function obdobi(u) { var o = u.obdobi || {}; return o.od && o.do ? (o.od === o.do ? datum(o.od) : datum(o.od) + " – " + datum(o.do)) : ""; }
  function hodnota(u, v) { return u.jednotka === "Kč" ? kc(v) : cislo(v); }

  function sloupce(u, rada, popisek) {
    var max = Math.max.apply(null, rada.map(function (r) { return r.hodnota; }).concat([1]));
    return '<ul class="trb-radnice__sloupce">' + rada.map(function (r) {
      var pct = Math.max(1.5, r.hodnota / max * 100);
      return '<li title="' + esc(r.nazev + ": " + hodnota(u, r.hodnota)) + '"><span class="trb-radnice__nazev">' + esc(r.nazev) +
        (popisek ? '<small>' + esc(popisek(r)) + "</small>" : "") + '</span><span class="trb-radnice__osa"><span class="trb-radnice__sloupec" style="width:' +
        pct.toFixed(1) + '%"></span></span><span class="trb-radnice__hodnota">' + hodnota(u, r.hodnota) + "</span></li>";
    }).join("") + "</ul>";
  }
  function zdroje(u) {
    return '<p class="trb-radnice__zdroj">' + esc(u.definice) + (u.srovnatelnost ? " " + esc(u.srovnatelnost) : "") +
      " <br>Zdroj: " + (u.zdroj || []).map(function (z) { return '<a href="' + esc(z.url) + '" rel="noopener" target="_blank">' + esc(z.nazev) + "</a>"; }).join(", ") +
      (obdobi(u) ? " · období " + obdobi(u) : "") + "</p>";
  }
  function blok(u, titul, telo) {
    return '<section class="trb-radnice__blok" id="' + esc(u.id) + '"><h2>' + esc(titul || u.nazev) + "</h2>" + telo + zdroje(u) + "</section>";
  }
  function velke(cisla) {
    return '<div class="trb-radnice__cisla">' + cisla.map(function (c) {
      return '<div class="trb-radnice__cislo"><b>' + c[0] + "</b><span>" + esc(c[1]) + "</span></div>";
    }).join("") + "</div>";
  }

  var BLOKY = {
    "jednani": function (u) {
      return blok(u, "Jednání", velke(u.hodnota.map(function (r) { return [cislo(r.hodnota), r.nazev]; })));
    },
    "usneseni-oblasti": function (u) {
      return blok(u, "O čem se rozhodovalo",
        velke([[cislo(u.celkem), "usnesení celkem"], [cislo(u.neprijato), "nepřijato"]]) + sloupce(u, u.hodnota));
    },
    "investice-rozpocet": function (u) {
      return blok(u, u.nazev, velke([[kc(u.po_zmenach), "po rozpočtových změnách"], [kc(u.schvaleny), "schválený rozpočet"]]) +
        sloupce(u, u.hodnota, function (r) { return r.hodnota === r.schvaleny ? "beze změny" : "schváleno " + kc(r.schvaleny); }));
    },
    "investicni-akce": function (u) {
      return blok(u, "Investiční akce", velke(u.hodnota.map(function (r) { return [cislo(r.hodnota), r.nazev]; })
        .concat([[cislo(u.zasobnik), "v zásobníku (připravuje se)"]])));
    },
    "smlouvy-organizace": function (u) {
      return blok(u, "Smlouvy podle organizací", sloupce(u, u.hodnota, function (r) {
        return Object.keys(r.podle_let).map(function (k) { return k + ": " + r.podle_let[k]; }).join(" · ");
      }));
    },
    "zakazky-organizace": function (u) {
      return blok(u, "Veřejné zakázky", sloupce(u, u.hodnota, function (r) {
        var s = r.podle_stavu || {}; return (s["zrušen"] ? s["zrušen"] + " zrušených" : "");
      }));
    },
    "dotace-oblasti": function (u) {
      return blok(u, u.nazev, sloupce(u, u.hodnota, function (r) { return r.pocet + (r.pocet === 1 ? " dotace" : r.pocet < 5 ? " dotace" : " dotací"); }));
    }
  };
  var PORADI = ["jednani", "usneseni-oblasti", "investice-rozpocet", "investicni-akce", "smlouvy-organizace", "zakazky-organizace", "dotace-oblasti"];

  function vykresli(data) {
    var po = {};
    data.forEach(function (u) { po[u.id] = u; });
    obsah.innerHTML = PORADI.filter(function (id) { return po[id]; }).map(function (id) { return BLOKY[id](po[id]); }).join("");
  }
  if (window.TRB_RADNICE_DATA) { vykresli(window.TRB_RADNICE_DATA); return; }
  fetch(el.getAttribute("data-src"), { cache: "no-cache" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(vykresli)
    .catch(function () { obsah.innerHTML = '<p class="trb-radnice__nacitani">Data se nepodařilo načíst. Zkuste stránku obnovit.</p>'; });
})();
