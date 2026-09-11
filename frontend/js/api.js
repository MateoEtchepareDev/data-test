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
  const refreshHooks = [];
  let erroresDelCiclo = 0;

  function mostrarError(container, mensaje) {
    if (!container) return;
    container.textContent = mensaje;
    container.classList.add("is-error");
  }

  function mostrarErrorPanel(container, mensaje) {
    if (!container) return;
    let err = container.querySelector(".chart-error");
    if (!err) {
      err = document.createElement("p");
      err.className = "chart-error";
      container.appendChild(err);
    }
    err.textContent = mensaje;
    container.classList.add("is-error");
  }

  function registrar(fn) {
    loaders.push(fn);
  }

  function notifyError() {
    erroresDelCiclo += 1;
  }

  function onRefresh(fn) {
    refreshHooks.push(fn);
  }

  function setRefreshing(active) {
    const btn = document.getElementById("btn-refresh");
    if (btn) {
      btn.disabled = active;
      btn.textContent = active ? "Actualizando…" : "Actualizar datos";
      btn.classList.toggle("is-loading", active);
    }
  }

  function showApiAlert(mensaje) {
    const el = document.getElementById("api-alert");
    if (!el) return;
    if (mensaje) {
      el.textContent = mensaje;
      el.hidden = false;
    } else {
      el.hidden = true;
      el.textContent = "";
    }
  }

  async function refresh() {
    setRefreshing(true);
    erroresDelCiclo = 0;
    try {
      const results = await Promise.allSettled(loaders.map((fn) => fn()));
      const errores = results.reduce((acum, r, i) => {
        if (r.status === "rejected") acum.push(loaders[i]?.name || i);
        return acum;
      }, []);
      if (erroresDelCiclo > 0 || errores.length > 0) {
        showApiAlert("No se pudieron cargar algunos datos");
      } else {
        showApiAlert(null);
      }
      refreshHooks.forEach((fn) => { try { fn(errores); } catch (_ignored) {} });
    } finally {
      setRefreshing(false);
    }
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
    onRefresh,
    refresh,
    formatearMoneda,
    formatearEntero,
    mostrarError,
    mostrarErrorPanel,
    notifyError,
  };
})();