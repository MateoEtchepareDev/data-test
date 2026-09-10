(function () {
  let map = null;
  let geoLayer = null;

  const ARG_BOUNDS = [
    [-55.2, -73.6],
    [-21.8, -53.6],
  ];

  async function render() {
    const [top, resp] = await Promise.all([
      Dash.fetchJSON("/analytics/provincia-mayor-volumen"),
      fetch("data/geo/provincias.json", { cache: "reload" }),
    ]);
    if (!resp.ok) throw new Error("No se pudo cargar el GeoJSON de provincias");
    const geojson = await resp.json();

    if (!map) {
      map = L.map("mapa", {
        scrollWheelZoom: false,
        zoomControl: true,
        minZoom: 3,
        maxZoom: 10,
      }).setView([-38.4, -63.5], 4);
      map.setMaxBounds(ARG_BOUNDS);
      L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap &copy; CARTO",
      }).addTo(map);
    }

    const destacada = top && top.provincia ? top.provincia : null;

    if (!geoLayer) {
      geoLayer = L.geoJSON(geojson).addTo(map);
    } else {
      geoLayer.clearLayers();
      geoLayer.addData(geojson);
    }

    geoLayer.setStyle((feature) => {
      const esDestacada = feature.properties.name === destacada;
      return {
        color: "#ffffff",
        weight: esDestacada ? 1.6 : 0.8,
        fillColor: esDestacada ? "#c2410c" : "#f6f3f0",
        fillOpacity: esDestacada ? 0.9 : 0.75,
      };
    });
    geoLayer.eachLayer((layer) => {
      const nombre = layer.feature.properties.name;
      const esDestacada = nombre === destacada;
      if (esDestacada) layer.bringToFront();
      layer.bindTooltip(
        nombre + (esDestacada && top ? ` — ${Dash.formatearMoneda(top.ventas)}` : ""),
        { permanent: false, direction: "center", opacity: 1 }
      );
    });
  }

  Dash.registrar(render);
})();