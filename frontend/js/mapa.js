(function () {
  let map = null;
  let geoLayer = null;

  const ARG_BOUNDS = [
    [-55.2, -73.6],
    [-21.8, -53.6],
  ];

  const panel = document.getElementById("mapa");
  const destacadaEl = document.getElementById("map-destacada");

  function normalizeNombre(value) {
    return String(value || "")
      .trim()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  function mostrarError(mensaje) {
    if (destacadaEl) {
      destacadaEl.textContent = mensaje;
      destacadaEl.classList.add("is-error");
    }
  }

  function ajustarTamano() {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (map) map.invalidateSize();
      });
    });
  }

  function render() {
    const resultados = Promise.allSettled([
      Dash.fetchJSON("/analytics/provincia-mayor-volumen"),
      fetch("data/geo/provincias.json", { cache: "reload" }),
    ]);

    if (destacadaEl) destacadaEl.classList.remove("is-error");

    resultados
      .then(async ([api, geo]) => {
        const top = api.status === "fulfilled" ? api.value : null;
        const apiFallido = api.status === "rejected";
        let geojson = null;

        if (geo.status === "rejected" || !geo.value.ok) {
          throw new Error("No se pudo cargar el GeoJSON de provincias.");
        }
        try {
          geojson = await geo.value.json();
        } catch (e) {
          throw new Error("El GeoJSON de provincias no es válido.");
        }

        if (!map) {
          map = L.map(panel, {
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

          if (window.ResizeObserver && panel) {
            new ResizeObserver(() => {
              if (map) map.invalidateSize();
            }).observe(panel);
          }
        }

        if (!geoLayer) {
          geoLayer = L.geoJSON([]).addTo(map);
        }
        geoLayer.clearLayers();
        geoLayer.addData(geojson);

        const destacada = top && top.provincia ? top.provincia : null;
        const target = normalizeNombre(destacada);

        geoLayer.setStyle((feature) => {
          const name = feature.properties && feature.properties.name;
          const esDestacada = target && normalizeNombre(name) === target;
          return {
            color: "#ffffff",
            weight: esDestacada ? 1.6 : 0.8,
            fillColor: esDestacada ? "#c2410c" : "#f6f3f0",
            fillOpacity: esDestacada ? 0.9 : 0.75,
          };
        });

        const marco = top && top.ventas ? ` — ${Dash.formatearMoneda(top.ventas)}` : "";
        geoLayer.eachLayer((layer) => {
          const name = layer.feature && layer.feature.properties && layer.feature.properties.name;
          const esDestacada = !!target && normalizeNombre(name) === target;
          if (esDestacada) layer.bringToFront();
          layer.bindTooltip(name + (esDestacada ? marco : ""), {
            permanent: false,
            direction: "center",
            opacity: 1,
          });
        });

        if (destacadaEl) {
          if (apiFallido) {
            Dash.notifyError();
            destacadaEl.textContent = "API no disponible";
            destacadaEl.classList.add("is-error");
          } else {
            destacadaEl.textContent = destacada ? `${destacada}${marco}` : "—";
          }
        }

        ajustarTamano();
      })
      .catch((error) => {
        Dash.notifyError();
        mostrarError("No se pudo cargar el mapa");
        console.warn("mapa:", error && error.message ? error.message : error);
      });
  }

  window.addEventListener("resize", () => {
    if (map) map.invalidateSize();
  });

  Dash.registrar(render);
})();