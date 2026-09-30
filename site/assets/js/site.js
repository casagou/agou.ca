(function () {
  "use strict";
  var btn = document.getElementById("menu-btn"), nav = document.getElementById("site-nav");
  if (!btn || !nav) return;
  document.documentElement.classList.add("js");
  function set(open) {
    btn.setAttribute("aria-expanded", String(open));
    btn.querySelector(".lbl").textContent = open ? btn.getAttribute("data-close") : btn.getAttribute("data-open");
    document.body.classList.toggle("menu-open", open);
  }
  btn.addEventListener("click", function () { set(btn.getAttribute("aria-expanded") !== "true"); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && btn.getAttribute("aria-expanded") === "true") { set(false); btn.focus(); } });
  window.matchMedia("(min-width: 1024px)").addEventListener("change", function (m) { if (m.matches) set(false); });
})();
