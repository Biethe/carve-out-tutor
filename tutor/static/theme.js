// Picks the theme before the page paints (no flash), and wires the theme buttons.
// A saved choice wins; otherwise follow the system's light/dark setting.
(function () {
  var root = document.documentElement;
  var system = matchMedia("(prefers-color-scheme: dark)");
  var saved = null;
  try { saved = localStorage.getItem("theme"); } catch (e) {}
  root.dataset.theme = saved || (system.matches ? "night" : "paper");

  function mark() {
    document.querySelectorAll("[data-theme-choice]").forEach(function (b) {
      b.setAttribute("aria-checked", String(b.dataset.themeChoice === root.dataset.theme));
    });
  }

  function set(name) {
    root.dataset.theme = name;
    try { localStorage.setItem("theme", name); } catch (e) {}
    mark();
    dispatchEvent(new CustomEvent("themechange"));
  }

  system.addEventListener("change", function (e) {
    var chosen = null;
    try { chosen = localStorage.getItem("theme"); } catch (err) {}
    if (!chosen) { root.dataset.theme = e.matches ? "night" : "paper"; mark(); }
  });

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-theme-choice]").forEach(function (b) {
      b.addEventListener("click", function () { set(b.dataset.themeChoice); });
    });
    mark();
  });
})();
