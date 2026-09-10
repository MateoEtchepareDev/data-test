(function () {
  const DESIGN_W = 1366;
  const DESIGN_H = 768;
  const stage = document.getElementById("stage");

  function apply() {
    const w = window.innerWidth;
    const h = window.innerHeight;
    const scale = Math.min(w / DESIGN_W, h / DESIGN_H);
    window.DASH_SCALE = scale;
    if (stage) {
      stage.style.transform = "scale(" + scale + ")";
      stage.style.left = Math.max(0, Math.round((w - DESIGN_W * scale) / 2)) + "px";
      stage.style.top = Math.max(0, Math.round((h - DESIGN_H * scale) / 2)) + "px";
    }
  }

  window.addEventListener("resize", apply);
  apply();
})();