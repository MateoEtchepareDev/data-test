(function () {
  async function render() {
    try {
      const [ventas, cantidad, margen, tickets, topProductos] = await Promise.all([
        Dash.fetchJSON("/kpis/ventas-totales"),
        Dash.fetchJSON("/kpis/cantidad-vendida"),
        Dash.fetchJSON("/kpis/margen-bruto"),
        Dash.fetchJSON("/kpis/ticket-promedio"),
        Dash.fetchJSON("/analytics/top-productos"),
      ]);

      document.getElementById("kpi-ventas").querySelector(".kpi__value").textContent =
        Dash.formatearMoneda(ventas.ventas_totales);
      document.getElementById("kpi-cantidad").querySelector(".kpi__value").textContent =
        Dash.formatearEntero(cantidad.cantidad_vendida);
      document.getElementById("kpi-margen").querySelector(".kpi__value").textContent =
        Dash.formatearMoneda(margen.margen_bruto);

      const grid = document.getElementById("kpi-ticket").querySelector(".kpi__grid");
      grid.innerHTML = "";
      tickets.forEach((row) => {
        const chip = document.createElement("div");
        chip.className = "chip";
        const name = document.createElement("span");
        name.className = "chip__name";
        name.textContent = row.nombre_sucursal;
        const val = document.createElement("span");
        val.className = "chip__val";
        val.textContent = Dash.formatearMoneda(row.ticket_promedio);
        chip.append(name, val);
        grid.appendChild(chip);
      });

      const box = document.getElementById("top-productos");
      box.innerHTML = "";
      const max = topProductos.length ? topProductos[0].ventas : 0;
      topProductos.forEach((row, i) => {
        const div = document.createElement("div");
        div.className = "bar-row";

        const rank = document.createElement("span");
        rank.className = "bar-row__rank";
        rank.textContent = i + 1;

        const name = document.createElement("span");
        name.className = "bar-row__name";
        name.textContent = row.nombre_producto;

        const track = document.createElement("span");
        track.className = "bar-row__track";
        const fill = document.createElement("span");
        fill.className = "bar-row__fill";
        fill.style.width = max ? (row.ventas / max) * 100 + "%" : "0%";
        track.appendChild(fill);

        const val = document.createElement("span");
        val.className = "bar-row__value";
        val.textContent = Dash.formatearMoneda(row.ventas);

        div.append(rank, name, track, val);
        box.appendChild(div);
      });
    } catch (error) {
      Dash.notifyError();
      Dash.mostrarError(document.getElementById("kpi-ventas").querySelector(".kpi__value"), error.message);
    }
  }

  Dash.registrar(render);
})();