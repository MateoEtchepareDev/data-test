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
      Dash.fetchJSON("/analytics/ventas-por-provincia"),
      fetch("data/geo/provincias.json", { cache: "reload" }),
    ]);

    if (destacadaEl) destacadaEl.classList.remove("is-error");

    resultados
      .then(async ([api, ventasApi, geo]) => {
        const top = api.status === "fulfilled" ? api.value : null;
        const apiFallido = api.status === "rejected";
        const ventasPorProvincia = new Map();
        if (ventasApi.status === "fulfilled") {
          const rows = Array.isArray(ventasApi.value) ? ventasApi.value : [];
          rows.forEach((row) => {
            if (row && row.provincia) {
              ventasPorProvincia.set(normalizeNombre(row.provincia), row.ventas);
            }
          });
        }

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

        let seleccion = top && top.provincia ? normalizeNombre(top.provincia) : null;

        function colorDeFeature(feature) {
          const name = feature && feature.properties && feature.properties.name;
          const n = normalizeNombre(name);
          if (seleccion && n === seleccion) {
            return { color: "#ffffff", weight: 1.6, fillColor: "#c2410c", fillOpacity: 0.9 };
          }
          if (ventasPorProvincia.has(n)) {
            return { color: "#b45309", weight: 1, fillColor: "rgba(194, 65, 12, 0.18)", fillOpacity: 1 };
          }
          return { color: "#d6d3d1", weight: 0.8, fillColor: "#f6f3f0", fillOpacity: 0.75 };
        }

        geoLayer.setStyle(colorDeFeature);

        geoLayer.eachLayer((layer) => {
          const name = layer.feature && layer.feature.properties && layer.feature.properties.name;
          const n = normalizeNombre(name);
          const el = layer.getElement && layer.getElement();
          if (el) el.dataset.ventasProvincia = n;

          if (!ventasPorProvincia.has(n)) {
            if (el) el.style.pointerEvents = "none";
            return;
          }

          const texto = `${name} — ${Dash.formatearMoneda(ventasPorProvincia.get(n))}`;
          if (seleccion && n === seleccion) layer.bringToFront();
          layer.bindTooltip(texto, {
            permanent: false,
            direction: "center",
            opacity: 1,
          });

          layer.on("click", () => {
            seleccion = n;
            geoLayer.setStyle(colorDeFeature);
            layer.bringToFront();
            if (destacadaEl) {
              destacadaEl.classList.remove("is-error");
              destacadaEl.textContent = texto;
            }
          });
        });

        const marco = top && top.ventas != null ? ` — ${Dash.formatearMoneda(top.ventas)}` : "";
        if (destacadaEl) {
          if (apiFallido) {
            Dash.notifyError();
            destacadaEl.textContent = "API no disponible";
            destacadaEl.classList.add("is-error");
          } else if (seleccion) {
            destacadaEl.textContent = `${top.provincia}${marco}`;
          } else {
            destacadaEl.textContent = "—";
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