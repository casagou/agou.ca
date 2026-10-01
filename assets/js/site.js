(function () {
  "use strict";
  document.documentElement.classList.add("js");
  /* "New" badges made at build time (Events menu item, home New-event line): hide them once the event is no longer new or has ended. */
  var todayPT = new Date().toLocaleDateString("en-CA", { timeZone: "America/Vancouver" });
  document.querySelectorAll("[data-new-until]").forEach(function (n) {
    var ends = n.getAttribute("data-new-ends");
    if (todayPT >= n.getAttribute("data-new-until") || (ends && new Date(ends).getTime() < Date.now())) n.remove();
  });
  /* Read more / Show less: content is visible without JS; JS collapses it and shows the toggle button. */
  document.querySelectorAll(".rm-toggle").forEach(function (b) {
    var r = document.getElementById(b.getAttribute("aria-controls"));
    if (!r) return;
    function set(open) {
      b.setAttribute("aria-expanded", String(open));
      b.textContent = open ? b.getAttribute("data-less") : b.getAttribute("data-more");
      r.hidden = !open;
    }
    b.hidden = false; set(false);
    b.addEventListener("click", function () { set(b.getAttribute("aria-expanded") !== "true"); }); // focus stays on the button
  });
  var btn = document.getElementById("menu-btn"), nav = document.getElementById("site-nav");
  if (!btn || !nav) return;
  function set(open) {
    btn.setAttribute("aria-expanded", String(open));
    btn.querySelector(".lbl").textContent = open ? btn.getAttribute("data-close") : btn.getAttribute("data-open");
    document.body.classList.toggle("menu-open", open);
  }
  btn.addEventListener("click", function () { set(btn.getAttribute("aria-expanded") !== "true"); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && btn.getAttribute("aria-expanded") === "true") { set(false); btn.focus(); } });
  window.matchMedia("(min-width: 1024px)").addEventListener("change", function (m) { if (m.matches) set(false); });
  // an in-page link in the open menu (or any nav link) closes it
  nav.addEventListener("click", function (e) { if (e.target.closest("a") && btn.getAttribute("aria-expanded") === "true") set(false); });
})();
