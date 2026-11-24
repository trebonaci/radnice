// Mapa používá stejné karty a doklady jako seznam projektů.
const GIS_STATES = {
  priprava: { label: "Připravuje se", color: "#8a3c00" },
  probiha: { label: "Probíhá", color: "#004bb3" },
  hotovo: { label: "Dokončeno", color: "#14623d" },
};
const GIS_SERVICE = { label: "Změny v místech a službách", color: "#790b88" };
// okruh stejný jako na ostatních stránkách (FO a okruhChips v sablona.html; je v adrese #mapa/<okruh>, 23. 11. 2026)
const gisFilters = { q: "", state: "", view: "map", selected: "" };
let closeGis;
let leafletAssets;

function loadLeaflet() {
  if (leafletAssets) return leafletAssets;
  // Leaflet 1.9.4 přibalený k webu (web/site/leaflet, licence BSD-2) – bez načítání z cizího CDN
  const base = "leaflet/leaflet.";
  const css = document.createElement("link");
  css.rel = "stylesheet";
  css.href = base + "css";
  css.integrity = "sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=";
  const script = document.createElement("script");
  script.src = base + "js";
  script.integrity = "sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=";
  leafletAssets = Promise.all([css,script].map(tag => new Promise((resolve,reject) => {
    tag.crossOrigin = "anonymous";
    tag.onload = resolve;
    tag.onerror = reject;
    document.head.append(tag);
  }))).then(() => window.L).catch(error => {
    css.remove();
    script.remove();
    leafletAssets = null;
    throw error;
  });
  return leafletAssets;
}

function gisProjects() {
  const geo = new Map(GIS.map(item => [item.typ + "/" + item.id, item]));
  function entry(p, type, changes = [], okruh = p.okruh) {
    const id = type + "/" + p.id;
    const loc = geo.get(id);
    const state = p.faze === "dokonceno" ? "hotovo" : p.faze === "probiha" ? "probiha" : "priprava";
    const topic = OBLAST[p.oblast] ? p.oblast : "jine";
    const places = (loc?.misto || []).filter(place => place.bod || place.linie?.length);
    return {
      id, p, type, state: type === "misto" ? "sluzby" : state, changes, places, geometry: loc?.geometrie,
      topic,
      topicLabel: OBLAST[topic],
      okruh: OKN[okruh] ? okruh : "rozvoj_sprava",
      approx: places.some(place => place.jistota !== "dolozeno"),
      text: bezDia([p.nazev,p.popis,OBLAST[topic],OKN[okruh]?.nazev,...changes.map(change => change.text),...places.map(place => place.nazev)].filter(Boolean).join(" ")),
    };
  }
  const services = M.flatMap(place => {
    const changes = ZM.filter(change => change.misto_id === place.id);
    return changes.length ? [entry(place,"misto",changes)] : [];
  });
  const unlocated = ZM.filter(change => !M.some(place => place.id === change.misto_id)).map(change =>
    entry({id:change.id,nazev:change.kdo || change.text,oblast:change.oblast},"misto",[change],change.okruh));
  return [...P.map(p => entry(p,"investice")), ...zPol().map(p => entry(p,"zasobnik")), ...services, ...unlocated]
    .sort((a,b) => a.p.nazev.localeCompare(b.p.nazev,"cs"));
}

function gisKpi(projects) {
  const n = t => projects.filter(p => p.type === "investice" && p.state === t).length;
  const karta = (l, v, s) => '<div class="kpi"><span>' + l + '</span><b>' + v + '</b><small>' + s + '</small></div>';
  return '<div class="kpis ak-kpi">' +
    karta("Celkem v mapě", projects.filter(p => p.geometry).length,
          "z " + projects.length + " sledovaných akcí a míst") +
    karta("Staví se", n("probiha"), "stavba podle dokladů probíhá") +
    karta("V přípravě", n("priprava"), "projektuje se nebo běží výběrové řízení") +
    karta("Dokončeno", n("hotovo"), "stavba podle dokladů skončila") + '</div>';
}
function gisHtml(projects) {
  return '<section><span class="eyebrow">Prostorová data města</span><h1 class="st" tabindex="-1">Mapa staveb, oprav a služeb</h1>' +
    '<p class="gis-intro">Najděte stavby, opravy a změny v místních službách podle ulice nebo okruhu.</p>' +
    gisKpi(projects) +
    '<div class="gis-controls">' +
    '<label>Hledat<input data-gis-query type="search" placeholder="Ulice, místo nebo název akce" value="' + esc(gisFilters.q) + '"></label>' +
    '<label>Co zobrazit<select data-gis-state><option value="">Vše</option><option value="stavby"' + (gisFilters.state==="stavby"?' selected':'') + '>Všechny stavby a opravy</option>' +
    Object.entries(GIS_STATES).map(([k,s]) => '<option value="' + k + '"' + (gisFilters.state===k?' selected':'') + '>' + s.label + '</option>').join("") +
    '<option value="sluzby"' + (gisFilters.state==="sluzby"?' selected':'') + '>Změny v místech a službách</option>' +
    '</select></label><div role="group" aria-label="Zobrazení">' +
    '<button type="button" data-gis-view="map">Mapa</button><button type="button" data-gis-view="list">Seznam</button></div></div>' +
    okruhChips("mapa") +
    '<p class="gis-summary" data-gis-summary aria-live="polite"></p>' +
    '<div class="gis-layout"><div class="gis-map-frame"><div class="gis-canvas" role="region" aria-label="Interaktivní mapa Třeboně"></div>' +
    '<p class="gis-status pozn" role="status"></p><div class="gis-tools"><button type="button" class="gis-reset">Ukázat celý výběr</button>' +
    '<ul class="gis-key" aria-label="Legenda mapy">' +
    Object.values(GIS_STATES).map(s => '<li><i aria-hidden="true" style="--gis-color:' + s.color + '"></i>' + s.label + '</li>').join("") +
    '<li><i class="gis-service" aria-hidden="true" style="--gis-color:' + GIS_SERVICE.color + '"></i>' + GIS_SERVICE.label + '</li>' +
    '</ul></div><p class="pozn">Přerušovaná značka označuje přibližnou polohu. Čára ukazuje ulici či trasu, rozsah prací ověřte v dokladech.</p></div>' +
    '<div class="gis-panel"><section class="gis-overlap" tabindex="-1" aria-label="Akce v okolí vybraného bodu"></section>' +
    '<section class="gis-card" tabindex="-1" aria-label="Vybraná akce"></section>' +
    '<section class="gis-results"><h2>Výsledky</h2><div class="gis-list"></div></section></div></div></section>';
}

function gisSymbol(entry) {
  return entry.type === "misto" ? GIS_SERVICE : GIS_STATES[entry.state];
}

function gisRow(entry) {
  const situation = !entry.geometry ? "Poloha není doložena" : entry.approx ? "Přibližná poloha" : "Poloha v mapě";
  return '<li><button type="button" class="gis-row" data-gis-project="' + esc(entry.id) + '" aria-pressed="' +
    (gisFilters.selected===entry.id) + '"><strong>' + esc(rozepis(entry.p.nazev)) + '</strong><small>' +
    gisSymbol(entry).label + ' · ' + situation + '</small></button></li>';
}

function gisCard(entry) {
  const { p, type, approx, geometry, places } = entry;
  if (type === "misto") {
    const place = M.find(item => item.id === p.id);
    return '<h2>' + esc(p.nazev) + '</h2><p class="pozn">' + esc(OKN[entry.okruh].nazev) + '</p>' +
      '<ul class="zm">' + entry.changes.map(change => zmRadek(change,false)).join("") + '</ul>' +
      '<p class="pozn">' + (geometry ? 'Značka ukazuje adresu místa nebo sídlo služby.' : 'Změna je dostupná v seznamu bez značky na mapě.') + '</p>' +
      (place ? '<a class="gis-detail" href="#misto-' + esc(place.id) + '">Místo a související akce →</a>' : '');
  }
  let amount, priceLabel, href;
  if (type === "investice") {
    [priceLabel,amount] = hlavni(p);
    href = "#" + p.id;
  } else {
    const preparation = p.cena_pripravy?.smlouvy;
    if (preparation) {
      amount = [
        preparation.s_dph == null ? "" : kc(preparation.s_dph) + " s DPH",
        preparation.bez_dph == null ? "" : kc(preparation.bez_dph) + " bez DPH",
      ].filter(Boolean).join(" + ");
    }
    priceLabel = "smlouvy na přípravu";
    href = "#priprava-" + p.id;
  }
  const sources = [...new Set(places.map(place => place.zdroj).filter(Boolean))].join(" · ");
  return '<h2>' + esc(rozepis(p.nazev)) + '</h2><p class="pozn">' +
    esc((type === "investice" && stavText(p)) || gisSymbol(entry).label) + ' · ' + esc(OKN[entry.okruh].nazev) + '</p>' +
    (amount ? '<p><b>' + esc(amount) + '</b> · ' + esc(priceLabel) + '</p>' : '') +
    '<p class="pozn">' + (!geometry ? "Polohu zatím nemáme doloženou." :
      (approx ? "Přibližná poloha" : "Doložená poloha") + (sources ? " · " + esc(sources) : "") +
      (places.some(place => place.druh === "ulice") ? ". Čára může zahrnovat i úsek ulice mimo stavbu." : ".")) +
    '</p>' + places.filter(place => place.druh === 'usek' && place.zdroj_url?.startsWith('https://')).map(place =>
      '<p><a href="' + esc(place.zdroj_url) + '">' + esc(place.nazev || 'Doklad k rozsahu úseku') + '</a></p>'
    ).join('') + '<a class="gis-detail" href="' + esc(href) + '">' + (type === "investice" ? "Detail a doklady" : "Příprava a doklady") + ' →</a>';
}

function gisNearPoint(L, map, layer, point) {
  if (layer.getLatLng) return map.latLngToLayerPoint(layer.getLatLng()).distanceTo(point) <= 16;
  if (layer.getLayers) return layer.getLayers().some(child => gisNearPoint(L,map,child,point));
  function nearLine(line) {
    if (Array.isArray(line[0])) return line.some(nearLine);
    return line.some((vertex,i) => i > 0 && L.LineUtil.pointToSegmentDistance(
      point, map.latLngToLayerPoint(line[i-1]), map.latLngToLayerPoint(vertex),
    ) <= 8);
  }
  return layer.getLatLngs ? nearLine(layer.getLatLngs()) : false;
}

function openGis(el) {
  const projects = gisProjects();
  const predchozi = document.body.dataset.str;
  zobraz(el,gisHtml(projects),"mapa","Mapa staveb, oprav a služeb");
  posun2(predchozi,"mapa");
  const layout = el.querySelector(".gis-layout");
  const frame = el.querySelector(".gis-map-frame");
  const canvas = el.querySelector(".gis-canvas");
  const message = el.querySelector(".gis-status");
  const reset = el.querySelector(".gis-reset");
  const result = el.querySelector(".gis-list");
  const card = el.querySelector(".gis-card");
  const overlap = el.querySelector(".gis-overlap");
  const summary = el.querySelector("[data-gis-summary]");
  let map, layers, L, pending, disposed;
  const shapes = new Map();
  let filtered = [];

  closeGis = () => {
    disposed = true;
    if (map) map.remove();
  };

  function showPanel(panel) {
    panel.focus({preventScroll:true});
    if (matchMedia("(max-width:760px)").matches) panel.scrollIntoView({block:"nearest"});
  }

  // Výchozí výřez drží Třeboňsko; vzdálené body (např. rybník mimo území města) do něj nezahrnuje,
  // pokud je v mapě i něco blíž. Na vzdálený bod se mapa přiblíží po jeho výběru.
  const OKOLI = [[48.94,14.68],[49.07,14.87]];
  function fit() {
    const okoli = L.latLngBounds(OKOLI), blizko = L.latLngBounds([]);
    layers.eachLayer(l => { const b = l.getBounds(); if (b.isValid() && okoli.contains(b.getCenter())) blizko.extend(b); });
    const bounds = blizko.isValid() ? blizko : layers.getBounds();
    if (bounds.isValid()) map.fitBounds(bounds,{padding:[28,28],maxZoom:16,animate:false});
    else map.setView([49.004,14.772],13,{animate:false});
  }

  function select(entry, fromList) {
    overlap.innerHTML = "";
    gisFilters.selected = entry.id;
    card.innerHTML = gisCard(entry);
    result.querySelectorAll("[data-gis-project]").forEach(b =>
      b.setAttribute("aria-pressed",String(b.dataset.gisProject === entry.id)));
    emphasize();
    const shape = shapes.get(entry.id);
    if (fromList && map && gisFilters.view === "map" && shape?.getBounds().isValid()) {
      map.fitBounds(shape.getBounds(),{padding:[35,35],maxZoom:17,animate:false});
    }
    showPanel(card);
  }

  function choose(event, entry) {
    if (!event.latlng) return select(entry,false);
    const point = map.latLngToLayerPoint(event.latlng);
    const nearby = filtered.filter(p => p.id === entry.id ||
      (shapes.has(p.id) && gisNearPoint(L,map,shapes.get(p.id),point)));
    if (nearby.length === 1) return select(entry,false);
    overlap.innerHTML = '<h2>Akce na tomto místě</h2><ul>' + nearby.map(gisRow).join("") + '</ul>';
    showPanel(overlap);
  }

  function emphasize() {
    for (const [id,shape] of shapes) {
      const current = id === gisFilters.selected;
      shape.setStyle({weight:current ? 9 : 6});
      shape.eachLayer(function mark(layer) {
        const pin = layer.getElement?.()?.querySelector(".gis-pin");
        pin?.classList.toggle("selected",current);
        layer.eachLayer?.(mark);
      });
    }
  }

  function redrawMap() {
    if (!layers) return;
    shapes.clear();
    layers.clearLayers();
    for (const entry of filtered) {
      if (!entry.geometry) continue;
      const color = gisSymbol(entry).color;
      const iconSize = entry.approx ? 22 : 16;
      const shape = L.geoJSON(entry.geometry,{
        style: {color,weight:6,opacity:1,dashArray:entry.approx ? "7 6" : null,className:"gis-path"},
        pointToLayer: (_,latlng) => L.marker(latlng,{
          title:entry.p.nazev + ' · ' + gisSymbol(entry).label,
          alt:entry.p.nazev + ' · ' + gisSymbol(entry).label,
          icon:L.divIcon({
            className:"gis-marker",iconSize:[iconSize,iconSize],
            html:'<span aria-hidden="true" class="gis-pin' + (entry.approx?' approx':'') + (entry.type==="misto"?' gis-service':'') + '" style="--gis-color:' + color + '"></span>',
          }),
        }),
      }).addTo(layers);
      shape.on("click",event => choose(event,entry));
      shapes.set(entry.id,shape);
    }
    emphasize();
  }

  async function ensureMap() {
    if (map || pending) return;
    pending = true;
    message.textContent = "Načítáme mapu…";
    reset.disabled = true;
    try {
      L = await loadLeaflet();
      if (disposed || gisFilters.view !== "map") return;
      map = L.map(canvas,{scrollWheelZoom:false, attributionControl:false,zoomControl:false});
      L.control.zoom({zoomInTitle:'Přiblížit',zoomOutTitle:'Oddálit'}).addTo(map);
      L.control.attribution({prefix:false}).addTo(map);
      // podklad: OpenStreetMap (rozhodnutí Ondřeje 23. 11. 2026 – ČÚZK ZTM byla špatně čitelná), mírně odbarvený
      // (třída gis-osm v mapa.css), aby barevné značky vynikly; letecký snímek dál z ČÚZK.
      // Dlaždice tile.openstreetmap.org: povolené při malém provozu s viditelnou atribucí (Tile Usage Policy).
      const osm = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom:19, className:"gis-osm",
        attribution:'© <a href="https://www.openstreetmap.org/copyright">přispěvatelé OpenStreetMap</a>',
      });
      const ortofoto = L.tileLayer("https://ags.cuzk.gov.cz/arcgis1/rest/services/ORTOFOTO_WM/MapServer/tile/{z}/{y}/{x}", {
        maxZoom:19, attribution:'© <a href="https://geoportal.cuzk.gov.cz">ČÚZK</a> – Ortofoto ČR',
      });
      const podklady = {"Mapa": osm, "Letecký snímek": ortofoto};
      const tiles = podklady["Mapa"].addTo(map);
      L.control.layers(podklady, null, {position:"topright", collapsed:false}).addTo(map);
      for (const vrstva of Object.values(podklady))
        vrstva.on("tileerror",() => { message.textContent = "Část podkladové mapy se nepodařilo načíst. Značky a seznam jsou dál k dispozici."; });
      layers = L.featureGroup().addTo(map);
      redrawMap();
      if (gisFilters.q || gisFilters.state || FO.okruh) fit();
      else map.setView([49.004,14.772],14,{animate:false});
      emphasize();
      message.textContent = "";
      reset.disabled = false;
    } catch {
      if (disposed) return;
      if (map) map.remove();
      map = layers = null;
      canvas.hidden = true;
      message.textContent = "Mapu se nepodařilo načíst. Akce a doklady najdete v seznamu níže.";
    } finally {
      pending = false;
    }
  }

  function refresh() {
    const words = koreny(gisFilters.q);
    const state = gisFilters.state;
    filtered = projects.filter(p => (!state || p.state === state || (state === "stavby" && p.type !== "misto")) &&
      (!FO.okruh || p.okruh === FO.okruh) && words.every(word => p.text.includes(word)));
    const mapped = filtered.filter(p => p.geometry);
    const missing = filtered.filter(p => !p.geometry);
    summary.textContent = filtered.length ?
      pl(filtered.length,"výsledek","výsledky","výsledků") + " · v mapě " + mapped.length + " · bez polohy " + missing.length :
      "Výběru neodpovídá žádný záznam.";
    // výsledky po okruzích ve stejném pořadí jako na ostatních stránkách; v okruhu nejdřív akce se značkou
    result.innerHTML = OK.map(o => {
      const v = filtered.filter(p => p.okruh === o.id);
      if (!v.length) return "";
      const bez = v.filter(p => !p.geometry).length;
      return '<details class="gis-okruh o-' + o.id + '"><summary>' + esc(o.nazev) + ' <small>' +
        v.length + (bez ? ' · bez polohy ' + bez : '') + '</small></summary><ul>' +
        [...v.filter(p => p.geometry), ...v.filter(p => !p.geometry)].map(gisRow).join("") + '</ul></details>';
    }).join("");
    if (!filtered.some(p => p.id === gisFilters.selected)) {
      gisFilters.selected = "";
      card.innerHTML = "";
    } else card.innerHTML = gisCard(filtered.find(p => p.id === gisFilters.selected));
    overlap.innerHTML = "";
    redrawMap();
  }

  el.querySelector("[data-gis-query]").oninput = e => { gisFilters.q = e.target.value; refresh(); };
  el.querySelector("[data-gis-state]").onchange = e => { gisFilters.state = e.target.value; refresh(); if (map) fit(); };
  for (const panel of [result,overlap]) {
    panel.onclick = e => {
      const button = e.target.closest("[data-gis-project]");
      if (button) select(filtered.find(p => p.id === button.dataset.gisProject),panel === result);
    };
  }
  reset.onclick = fit;

  const views = el.querySelectorAll("[data-gis-view]");
  function setView(view) {
    gisFilters.view = view;
    frame.hidden = view === "list";
    layout.classList.toggle("is-list",frame.hidden);
    views.forEach(b => b.setAttribute("aria-pressed",String(b.dataset.gisView === view)));
    if (frame.hidden) {
      overlap.innerHTML = "";
    } else {
      canvas.hidden = false;
      if (map) map.invalidateSize();
      else ensureMap();
    }
  }
  views.forEach(b => b.onclick = () => setView(b.dataset.gisView));
  refresh();
  setView(gisFilters.view);
}
