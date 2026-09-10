(function () {
  let chart = null;

  function ppi() {
    return window.devicePixelRatio * (window.DASH_SCALE || 1);
  }

  async function render() {
    const datos = await Dash.fetchJSON("/analytics/margen-por-categoria");
    const etiquetas = datos.map((d) => d.categoria);
    const valores = datos.map((d) => d.margen);
    const colores = etiquetas.map((_, i) =>
      i === 0 ? "#c2410c" : "rgba(194, 65, 12, 0.32)"
    );

    const ctx = document.getElementById("chart-barras");
    if (chart) chart.destroy();
    chart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: etiquetas,
        datasets: [{
          label: "Margen bruto ($)",
          data: valores,
          backgroundColor: colores,
          borderRadius: 6,
          barThickness: 22,
          maxBarThickness: 26,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        devicePixelRatio: ppi(),
        indexAxis: "y",
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#292524",
            padding: 10,
            cornerRadius: 8,
            displayColors: false,
            titleFont: { size: 12 },
            bodyFont: { size: 12 },
            callbacks: { label: (c) => Dash.formatearMoneda(c.parsed.x) },
          },
        },
        scales: {
          x: {
            beginAtZero: true,
            border: { display: false },
            grid: { color: "rgba(41, 37, 36, 0.07)" },
            ticks: {
              color: "#78716c",
              font: { size: 11 },
              maxTicksLimit: 5,
              callback: (v) => (v >= 1000 ? (v / 1000).toFixed(0) + "k" : v),
            },
          },
          y: {
            grid: { display: false },
            border: { display: false },
            ticks: { color: "#292524", font: { size: 12, weight: "600" } },
          },
        },
      },
    });
  }

  Dash.registrar(render);
})();