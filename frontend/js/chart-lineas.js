(function () {
  const MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
  ];

  let chart = null;

  async function render() {
    const datos = await Dash.fetchJSON("/analytics/evolucion-mensual");
    const etiquetas = datos.map((d) => MESES[d.mes - 1]);
    const valores = datos.map((d) => d.ventas);

    const ctx = document.getElementById("chart-lineas");
    if (chart) chart.destroy();
    chart = new Chart(ctx, {
      type: "line",
      data: {
        labels: etiquetas,
        datasets: [{
          label: "Ventas ($)",
          data: valores,
          borderColor: "#7c4a21",
          backgroundColor: "rgba(124, 74, 33, 0.12)",
          fill: true,
          tension: 0.3,
          pointRadius: 3,
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