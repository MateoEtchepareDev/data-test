(function () {
  let chart = null;

  async function render() {
    const datos = await Dash.fetchJSON("/analytics/margen-por-categoria");
    const etiquetas = datos.map((d) => d.categoria);
    const valores = datos.map((d) => d.margen);

    const ctx = document.getElementById("chart-barras");
    if (chart) chart.destroy();
    chart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: etiquetas,
        datasets: [{
          label: "Margen bruto ($)",
          data: valores,
          backgroundColor: etiquetas.map((_, i) =>
            i === 0 ? "#b4692e" : "rgba(180, 105, 46, 0.45)"
          ),
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { callback: (v) => "$" + v.toLocaleString("es-AR") },
          },
        },
      },
    });
  }

  Dash.registrar(render);
})();