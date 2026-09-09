const DashAPI = (function () {
  const API_BASE = window.API_BASE || "http://127.0.0.1:5000";

  async function fetchJSON(path) {
    const resp = await fetch(API_BASE + path, { cache: "reload" });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw new Error(body.error || `Error HTTP ${resp.status}`);
    }
    return resp.json();
  }

  return { API_BASE, fetchJSON };
})();

const Dash = (function () {
  const loaders = [];

  function mostrarError(container, mensaje) {
    if (!container) return;
    container.textContent = mensaje;
    container.classList.add("is-error");
  }

  function registrar(fn) {
    loaders.push(fn);
  }

  async function refresh() {
    await Promise.allSettled(loaders.map((fn) => fn()));
  }

  function formatearMoneda(value) {
    if (value === null || value === undefined) return "—";
    return "$" + value.toLocaleString("es-AR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  function formatearEntero(value) {
    if (value === null || value === undefined) return "—";
    return value.toLocaleString("es-AR");
  }

  return {
    API_BASE: DashAPI.API_BASE,
    fetchJSON: DashAPI.fetchJSON,
    registrar,
    refresh,
    formatearMoneda,
    formatearEntero,
    mostrarError,
  };
})();