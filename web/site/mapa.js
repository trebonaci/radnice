// Mapa používá stejné karty a doklady jako seznam projektů.
const GIS_STATES = {
  priprava: { label: "Připravuje se", color: "#795305" },
  probiha: { label: "Probíhá", color: "#006684" },
  hotovo: { label: "Dokončeno", color: "#386125" },
};
const GIS_TOPICS = [
  ["prostor", "Doprava a veřejný prostor", ["doprava","zelen","voda_odpady","energie","zivotni_prostredi"]],
  ["pece", "Bydlení a péče", ["bydleni","socialni","zdravotnictvi"]],
  ["skoly", "Školy a školky", ["skolstvi"]],
  ["volny-cas", "Sport, kultura a spolky", ["sport","kultura","komunity_spolky"]],
  ["firmy", "Městské společnosti", ["lazne","lazne_spolecnosti"]],
  ["rozvoj", "Rozvoj a správa města", ["uzemni_plan","majetek","rozpocet","sprava","urad","zakazky"]],
];
const gisFilters = { q: "", state: "", topic: "", view: "map", selected: "" };
let closeGis;
let leafletAssets;

function loadLeaflet() {
  if (leafletAssets) return leafletAssets;
  const base = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.";
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
  function entry(p, type) {
    const id = type + "/" + p.id;
    const loc = geo.get(id);
    const state = p.faze === "dokonceno" ? "hotovo" : p.faze === "probiha" ? "probiha" : "priprava";
    const topic = GIS_TOPICS.find(([, , areas]) => areas.includes(p.oblast));
    const places = (loc?.misto || []).filter(place => place.bod || place.linie?.length);
    return {
      id, p, type, state, places, geometry: loc?.geometrie,
      topic: topic?.[0] || "ostatni",
      topicLabel: topic?.[1] || OBLAST[p.oblast] || "Ostatní",
      approx: places.some(place => place.jistota !== "dolozeno"),
      text: bezDia([p.nazev,p.popis,topic?.[1],...places.map(place => place.nazev)].filter(Boolean).join(" ")),
    };
  }
  return [...P.map(p => entry(p,"investice")), ...zPol().map(p => entry(p,"zasobnik"))]
    .sort((a,b) => a.p.nazev.localeCompare(b.p.nazev,"cs"));
}

function gisHtml(projects) {
  const topics = [...GIS_TOPICS,["ostatni","Ostatní"]].filter(([key]) => projects.some(p => p.topic === key));
  return '<section><h1 class="st" tabindex="-1">Mapa staveb a oprav</h1>' +
    '<p class="gis-intro">Najděte stavby, opravy a připravované projekty podle ulice nebo tématu.</p>' +
    '<div class="gis-controls">' +
    '<label>Hledat<input data-gis-query type="search" placeholder="Ulice, místo nebo název projektu" value="' + esc(gisFilters.q) + '"></label>' +
    '<label>Stav<select data-gis-state><option value="">Všechny stavy</option>' +
    Object.entries(GIS_STATES).map(([k,s]) => '<option value="' + k + '"' + (gisFilters.state===k?' selected':'') + '>' + s.label + '</option>').join("") +
    '</select></label><label>Téma<select data-gis-topic><option value="">Všechna témata</option>' +
    topics.map(([k,label]) => '<option value="' + k + '"' + (gisFilters.topic===k?' selected':'') + '>' + label + '</option>').join("") +
    '</select></label><div role="group" aria-label="Zobrazení">' +
    '<button type="button" data-gis-view="map">Mapa</button><button type="button" data-gis-view="list">Seznam</button></div></div>' +
    '<p class="gis-summary" data-gis-summary aria-live="polite"></p>' +
    '<div class="gis-layout"><div class="gis-map-frame"><div class="gis-canvas" role="region" aria-label="Interaktivní mapa Třeboně"></div>' +
    '<p class="gis-status pozn" role="status"></p><div class="gis-tools"><button type="button" class="gis-reset">Ukázat celý výběr</button>' +
    '<ul class="gis-key" aria-label="Stav projektů">' +
    Object.values(GIS_STATES).map(s => '<li><i aria-hidden="true" style="--gis-color:' + s.color + '"></i>' + s.label + '</li>').join("") +
    '</ul></div><p class="pozn">Přerušovaná značka označuje přibližnou polohu. Čára ukazuje ulici či trasu, rozsah prací ověřte v dokladech.</p></div>' +
    '<div class="gis-panel"><section class="gis-overlap" tabindex="-1" aria-label="Projekty v okolí vybraného bodu"></section>' +
    '<section class="gis-card" tabindex="-1" aria-label="Vybraný projekt"></section>' +
    '<section class="gis-results"><h2>Projekty ve výběru</h2><div class="gis-list"></div></section></div></div></section>';
}

function gisRow(entry) {
  const situation = !entry.geometry ? "Poloha není doložena" : entry.approx ? "Přibližná poloha" : "Poloha v mapě";
  return '<li><button type="button" class="gis-row" data-gis-project="' + esc(entry.id) + '" aria-pressed="' +
    (gisFilters.selected===entry.id) + '"><strong>' + esc(rozepis(entry.p.nazev)) + '</strong><small>' +
    GIS_STATES[entry.state].label + ' · ' + situation + '</small></button></li>';
}

function gisCard(entry) {
  const { p, type, approx, geometry, places } = entry;
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
    esc((type === "investice" && stavText(p)) || GIS_STATES[entry.state].label) + ' · ' + esc(entry.topicLabel) + '</p>' +
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
  zobraz(el,gisHtml(projects),"mapa","Mapa staveb a oprav");
  window.scrollTo(0,0);
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

  function fit() {
    const bounds = layers.getBounds();
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
    overlap.innerHTML = '<h2>Projekty na tomto místě</h2><ul>' + nearby.map(gisRow).join("") + '</ul>';
    showPanel(overlap);
  }

  function emphasize() {
    for (const [id,shape] of shapes) {
      const current = id === gisFilters.selected;
      shape.setStyle({weight:current ? 8 : 5});
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
      const color = GIS_STATES[entry.state].color;
      const shape = L.geoJSON(entry.geometry,{
        style: {color,weight:5,opacity:.91,dashArray:entry.approx ? "7 6" : null,className:"gis-path"},
        pointToLayer: (_,latlng) => L.marker(latlng,{
          title:entry.p.nazev + ' · ' + GIS_STATES[entry.state].label,
          alt:entry.p.nazev + ' · ' + GIS_STATES[entry.state].label,
          icon:L.divIcon({
            className:"gis-marker",iconSize:[16,16],
            html:'<span aria-hidden="true" class="gis-pin' + (entry.approx?' approx':'') + '" style="--gis-color:' + color + '"></span>',
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
      const tiles = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",{
        maxZoom:19, attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }).addTo(map);
      tiles.on("tileerror",() => { message.textContent = "Část podkladové mapy se nepodařilo načíst. Polohy projektů a seznam jsou dál k dispozici."; });
      layers = L.featureGroup().addTo(map);
      redrawMap();
      if (gisFilters.q || gisFilters.state || gisFilters.topic) fit();
      else map.setView([49.004,14.772],14,{animate:false});
      emphasize();
      message.textContent = "";
      reset.disabled = false;
    } catch {
      if (disposed) return;
      if (map) map.remove();
      map = layers = null;
      canvas.hidden = true;
      message.textContent = "Mapu se nepodařilo načíst. Projekty a doklady najdete v seznamu níže.";
    } finally {
      pending = false;
    }
  }

  function refresh() {
    const words = koreny(gisFilters.q);
    filtered = projects.filter(p => (!gisFilters.state || p.state === gisFilters.state) &&
      (!gisFilters.topic || p.topic === gisFilters.topic) && words.every(word => p.text.includes(word)));
    const mapped = filtered.filter(p => p.geometry);
    const missing = filtered.filter(p => !p.geometry);
    summary.textContent = filtered.length ?
      pl(filtered.length,"projekt","projekty","projektů") + " · v mapě " + mapped.length + " · bez polohy " + missing.length :
      "Výběru neodpovídá žádný projekt.";
    result.innerHTML = (mapped.length ? '<ul>' + mapped.map(gisRow).join("") + '</ul>' : '') +
      (missing.length ? '<h3>Projekty bez doložené polohy</h3><ul>' + missing.map(gisRow).join("") + '</ul>' : '');
    if (!filtered.some(p => p.id === gisFilters.selected)) {
      gisFilters.selected = "";
      card.innerHTML = "";
    } else card.innerHTML = gisCard(filtered.find(p => p.id === gisFilters.selected));
    overlap.innerHTML = "";
    redrawMap();
  }

  el.querySelector("[data-gis-query]").oninput = e => { gisFilters.q = e.target.value; refresh(); };
  el.querySelector("[data-gis-state]").onchange = e => { gisFilters.state = e.target.value; refresh(); if (map) fit(); };
  el.querySelector("[data-gis-topic]").onchange = e => { gisFilters.topic = e.target.value; refresh(); if (map) fit(); };
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
