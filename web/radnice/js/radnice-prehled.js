/* Přehled dění na radnici (trebonaci/radnice #177, #187).
   Čte prehled.json, ukazatele.json a beh.json; nic nepočítá, jen zobrazuje a filtruje.
   Počty a součty dělá pipeline (pipeline/prehled.py, pipeline/ukazatele.py). */
(function () {
  "use strict";
  var root = document.querySelector(".trb-radnice-prehled");
  if (!root) return;
  var NA_STRANKU = 20;
  var $ = function (sel) { return root.querySelector(sel); };

  function esc(t) {
    return String(t == null ? "" : t).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function datum(d) {
    if (!d) return "";
    var c = d.slice(0, 10).split("-");
    return +c[2] + ". " + +c[1] + ". " + c[0];
  }
  function cislo(n) { return Math.round(n).toLocaleString("cs-CZ"); }
  function kc(n) {
    if (n >= 1e6) return (n / 1e6).toLocaleString("cs-CZ", { maximumFractionDigits: 1 }) + " mil. Kč";
    if (n >= 1e3) return (n / 1e3).toLocaleString("cs-CZ", { maximumFractionDigits: 0 }) + " tis. Kč";
    return cislo(n) + " Kč";
  }
  var JISTOTA = {
    doloze: "doloženo", doloženo: "doloženo",
    nase_propojeni: "naše propojení: stav odhadujeme z dokladů, město ho takto neoznámilo",
    nevime: "nevíme"
  };
  function nacti(url) {
    return fetch(url, { cache: "no-cache" }).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    });
  }

  /* ---------- položky ---------- */
  function odkazZdroje(z) {
    if (!z || !z.url) return "";
    var typ = z.pdf ? " (PDF" + (z.strana ? ", str. " + z.strana : "") + ")" : "";
    return '<a class="trb-radnice-zdroj" href="' + esc(z.url) + '" target="_blank" rel="noopener">' +
      esc(z.nazev) + typ + '<span class="trb-radnice-sr"> – otevře se v novém okně</span></a>';
  }
  function polozka(p) {
    var meta = esc(p.typ) + (p.oblast_nazev ? " · " + esc(p.oblast_nazev) : "");
    var krok = p.posledni_udalost ? '<p class="trb-radnice-krok">Poslední krok: ' + esc(p.posledni_udalost) + "</p>" : "";
    var dalsi = p.dalsi_krok ? '<p class="trb-radnice-krok">Další krok: ' + esc(p.dalsi_krok) + "</p>" : "";
    var ai = p.text_ai ? '<p class="trb-radnice-ai">Shrnutí připravila AI z usnesení, citace je ověřená proti zápisu.</p>' : "";
    return '<li><article class="trb-radnice-karta">' +
      '<p class="trb-radnice-meta">' + meta + "</p>" +
      '<p class="trb-radnice-stav trb-radnice-stav--' + esc(p.stav) + '">' + esc(p.stav_nazev) +
        (p.stav_jistota ? ' <span class="trb-radnice-jistota">(' + esc(JISTOTA[p.stav_jistota] || p.stav_jistota) + ")</span>" : "") + "</p>" +
      '<h3 class="trb-radnice-titulek">' + esc(p.titulek) + "</h3>" +
      '<p class="trb-radnice-shrnuti">' + esc(p.shrnuti) + "</p>" + krok +
      '<p class="trb-radnice-datum"><time datetime="' + esc(p.datum) + '">' + datum(p.datum) + "</time></p>" +
      '<p class="trb-radnice-odkaz">Zdroj: ' + odkazZdroje(p.zdroj) + "</p>" + dalsi + ai +
      "</article></li>";
  }

  var vsechny = [], zobrazeno = NA_STRANKU;
  var form = $("[data-trb-radnice-filtry]");

  function vybrane() {
    var oblast = form.elements.oblast.value;
    var stavy = Array.prototype.filter.call(form.querySelectorAll("input[name=stav]"), function (i) { return i.checked; })
      .map(function (i) { return i.value; });
    return vsechny.filter(function (p) {
      return (!oblast || p.oblast_nazev === oblast) && (!stavy.length || stavy.indexOf(p.stav) >= 0);
    });
  }
  function vykresli() {
    var v = vybrane();
    var ukaz = v.slice(0, zobrazeno);
    $("[data-trb-radnice-polozky]").innerHTML = ukaz.map(polozka).join("");
    var pocet = $("[data-trb-radnice-pocet]");
    if (!v.length) {
      pocet.innerHTML = "Žádná položka neodpovídá filtrům. <button type=\"button\" class=\"trb-radnice-odkaz-tlacitko\" data-trb-radnice-reset>Zrušit filtry</button>";
      pocet.querySelector("[data-trb-radnice-reset]").addEventListener("click", function () { form.reset(); zmena(); });
    } else {
      pocet.textContent = v.length === vsechny.length ? "Zobrazeno " + ukaz.length + " z " + v.length + " položek"
        : "Filtru odpovídá " + v.length + " z " + vsechny.length + " položek (zobrazeno " + ukaz.length + ")";
    }
    $("[data-trb-radnice-dalsi]").hidden = v.length <= zobrazeno;
  }
  function zmena() { zobrazeno = NA_STRANKU; vykresli(); }

  function filtry(data) {
    var oblasti = {}, stavy = {};
    data.forEach(function (p) {
      oblasti[p.oblast_nazev] = (oblasti[p.oblast_nazev] || 0) + 1;
      stavy[p.stav] = stavy[p.stav] || { nazev: p.stav_nazev, popis: p.stav_popis, pocet: 0 };
      stavy[p.stav].pocet++;
    });
    form.elements.oblast.insertAdjacentHTML("beforeend", Object.keys(oblasti).sort(function (a, b) { return a.localeCompare(b, "cs"); })
      .map(function (o) { return '<option value="' + esc(o) + '">' + esc(o) + " (" + oblasti[o] + ")</option>"; }).join(""));
    var poradi = ["rozhodnuto", "vzato_na_vedomi", "navrzeno", "projednava_se", "planuje_se", "realizuje_se", "dokonceno"];
    var pouzite = poradi.filter(function (s) { return stavy[s]; });
    $("[data-trb-radnice-stavy]").innerHTML = pouzite.map(function (s) {
      return '<label class="trb-radnice-volba"><input type="checkbox" name="stav" value="' + s + '"> <span>' +
        esc(stavy[s].nazev) + " (" + stavy[s].pocet + ")</span></label>";
    }).join("");
    $("[data-trb-radnice-legenda]").innerHTML = pouzite.map(function (s) {
      return '<div><dt><span class="trb-radnice-stav trb-radnice-stav--' + s + '">' + esc(stavy[s].nazev) + "</span></dt><dd>" +
        esc(stavy[s].popis) + "</dd></div>";
    }).join("") + "<div><dt>Jak jistý je stav</dt><dd>U investic je stav našim odhadem z dokladů (štítek „naše propojení“), pokud není uvedeno „doloženo“.</dd></div>";
    form.hidden = false;
    form.addEventListener("change", zmena);
    form.addEventListener("reset", function () { setTimeout(zmena, 0); });
    $("[data-trb-radnice-dalsi]").addEventListener("click", function () { zobrazeno += NA_STRANKU; vykresli(); });
  }

  /* ---------- V číslech (ukazatele) ---------- */
  function hodnota(u, v) { return u.jednotka === "Kč" ? kc(v) : cislo(v); }
  function sloupce(u, rada) {
    var max = Math.max.apply(null, rada.map(function (r) { return r.hodnota; }).concat([1]));
    return '<ul class="trb-radnice-sloupce">' + rada.map(function (r) {
      return '<li><span class="trb-radnice-sloupce-nazev">' + esc(r.nazev) + '</span><span class="trb-radnice-sloupce-osa" aria-hidden="true"><span style="width:' +
        Math.max(1.5, r.hodnota / max * 100).toFixed(1) + '%"></span></span><span class="trb-radnice-sloupce-hodnota">' + hodnota(u, r.hodnota) + "</span></li>";
    }).join("") + "</ul>";
  }
  function zdrojeUkazatele(u) {
    var o = u.obdobi || {};
    var obd = o.od && o.do ? (o.od === o.do ? datum(o.od) : datum(o.od) + " – " + datum(o.do)) : "";
    return '<p class="trb-radnice-poznamka">' + esc(u.definice) + (u.srovnatelnost ? " " + esc(u.srovnatelnost) : "") +
      (obd ? " Období: " + obd + "." : "") + " Zdroj: " + (u.zdroj || []).map(function (z) {
        return '<a href="' + esc(z.url) + '" target="_blank" rel="noopener">' + esc(z.nazev) + "</a>";
      }).join(", ") + ".</p>";
  }
  var UKAZATELE = {
    "usneseni-oblasti": function (u) { return sloupce(u, u.hodnota.slice(0, 8)); },
    "investice-rozpocet": function (u) {
      return '<p class="trb-radnice-velke"><strong>' + kc(u.po_zmenach) + "</strong> po rozpočtových změnách (schváleno " + kc(u.schvaleny) + ")</p>" + sloupce(u, u.hodnota);
    },
    "smlouvy-organizace": function (u) { return sloupce(u, u.hodnota); },
    "dotace-oblasti": function (u) { return sloupce(u, u.hodnota); }
  };
  function ukazatele(data) {
    var html = data.filter(function (u) { return UKAZATELE[u.id]; }).map(function (u) {
      return '<section class="trb-radnice-ukazatel"><h3>' + esc(u.nazev) + "</h3>" + UKAZATELE[u.id](u) + zdrojeUkazatele(u) + "</section>";
    }).join("");
    if (html) { $("[data-trb-radnice-ukazatele]").innerHTML = html; $("[data-trb-radnice-cisla]").hidden = false; }
  }

  /* ---------- start ---------- */
  function start(prehled, uk, beh) {
    vsechny = prehled;
    filtry(prehled);
    vykresli();
    if (uk) ukazatele(uk);
    if (beh && beh.zacatek) {
      $("[data-trb-radnice-aktualizace]").innerHTML = "Přehled naposledy aktualizován <time datetime=\"" + esc(beh.zacatek) + "\">" + datum(beh.zacatek) + "</time>.";
    }
  }
  if (window.TRB_RADNICE_DATA) {
    var d = window.TRB_RADNICE_DATA;
    start(d.prehled, d.ukazatele, d.beh);
    return;
  }
  Promise.all([nacti(root.getAttribute("data-prehled")),
    nacti(root.getAttribute("data-ukazatele")).catch(function () { return null; }),
    nacti(root.getAttribute("data-beh")).catch(function () { return null; })])
    .then(function (r) { start(r[0], r[1], r[2]); })
    .catch(function () { $("[data-trb-radnice-pocet]").textContent = "Data se nepodařilo načíst. Zkuste stránku obnovit."; });
})();
