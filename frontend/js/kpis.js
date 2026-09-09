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

      const lista = document.getElementById("kpi-ticket").querySelector(".kpi__list");
      lista.innerHTML = "";
      tickets.forEach((row) => {
        const li = document.createElement("li");
        li.textContent = `${row.nombre_sucursal}: ${Dash.formatearMoneda(row.ticket_promedio)}`;
        lista.appendChild(li);
      });

      const tbody = document.querySelector("#top-productos tbody");
      tbody.innerHTML = "";
      topProductos.forEach((row, i) => {
        const tr = document.createElement("tr");
        const rank = document.createElement("td");
        rank.textContent = i + 1;
        const nombre = document.createElement("td");
        nombre.textContent = row.nombre_producto;
        const ventasCell = document.createElement("td");
        ventasCell.className = "num";
        ventasCell.textContent = Dash.formatearMoneda(row.ventas);
        tr.append(rank, nombre, ventasCell);
        tbody.appendChild(tr);
      });
    } catch (error) {
      Dash.mostrarError(document.getElementById("kpi-ventas").querySelector(".kpi__value"), error.message);
    }
  }

  Dash.registrar(render);
})();