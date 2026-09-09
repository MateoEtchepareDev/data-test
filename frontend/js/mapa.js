(function () {
  let map = null;
  let geoLayer = null;

  async function render() {
    const top = await Dash.fetchJSON("/analytics/provincia-mayor-volumen");
    const resp = await fetch("data/geo/provincias.json", { cache: "reload" });
    if (!resp.ok) throw new Error("No se pudo cargar el GeoJSON de provincias");
    const geojson = await resp.json();

    if (!map) {
      map = L.map("mapa").setView([-38.4, -63.5], 4);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 18,
        attribution: "&copy; OpenStreetMap",
      }).addTo(map);
    }

    const destacada = top && top.provincia ? top.provincia : null;

    if (!geoLayer) {
      geoLayer = L.geoJSON(geojson).addTo(map);
    } else {
      geoLayer.clearLayers();
      geoLayer.addData(geojson);
    }

    geoLayer.setStyle((feature) => ({
      color: "#ffffff",
      weight: 1,
      fillColor: feature.properties.name === destacada ? "#b4692e" : "#e8d5bb",
      fillOpacity: feature.properties.name === destacada ? 0.85 : 0.5,
    }));
    geoLayer.eachLayer((layer) => {
      const nombre = layer.feature.properties.name;
      const esDestacada = nombre === destacada;
      if (esDestacada) layer.bringToFront();
      layer.bindTooltip(
        nombre + (esDestacada && top ? ` — ${Dash.formatearMoneda(top.ventas)}` : ""),
        { permanent: false, direction: "center" }
      );
    });
  }

  Dash.registrar(render);
})();