(function () {
  Chart.defaults.animation = false;
  Chart.defaults.transitions.active = { animation: { duration: 0 } };

  const MESES = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
  ];

  let chart = null;

  function render() {
    return Dash.fetchJSON("/analytics/evolucion-mensual")
      .then((datos) => {
        const etiquetas = datos.map((d) => MESES[d.mes - 1]);
        const valores = datos.map((d) => d.ventas);

        const ctx = document.getElementById("chart-lineas");
        const box = ctx && ctx.closest(".chart-box");
        if (box) {
          box.classList.remove("is-error");
          const err = box.querySelector(".chart-error");
          if (err) err.remove();
        }

        if (chart) chart.destroy();
        chart = new Chart(ctx, {
          type: "line",
          data: {
            labels: etiquetas,
            datasets: [{
              label: "Ventas ($)",
              data: valores,
              borderColor: "#c2410c",
              backgroundColor: "rgba(194, 65, 12, 0.1)",
              borderWidth: 2,
              fill: "origin",
              tension: 0.35,
              pointRadius: 3,
              pointBackgroundColor: "#ffffff",
              pointBorderColor: "#c2410c",
              pointBorderWidth: 2,
              pointHoverRadius: 5,
            }],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            devicePixelRatio: window.devicePixelRatio || 1,
            interaction: { mode: "index", intersect: false },
            plugins: {
              legend: { display: false },
              tooltip: {
                backgroundColor: "#292524",
                padding: 10,
                cornerRadius: 8,
                displayColors: false,
                titleFont: { size: 12 },
                bodyFont: { size: 12 },
                callbacks: { label: (c) => Dash.formatearMoneda(c.parsed.y) },
              },
            },
            scales: {
              x: {
                grid: { display: false },
                border: { display: false },
                ticks: { color: "#78716c", font: { size: 11 } },
              },
              y: {
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
            },
          },
        });
      })
      .catch((error) => {
        Dash.notifyError();
        const ctx = document.getElementById("chart-lineas");
        const box = ctx && ctx.closest(".chart-box");
        if (box) Dash.mostrarErrorPanel(box, "No se pudo cargar el gráfico");
      });
  }

  Dash.registrar(render);
})();