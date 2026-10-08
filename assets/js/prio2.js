/* Priorities summary-first layout (prio_layout.py): details stay reachable.
   - a link to a promise, a section or anything inside a closed <details> opens it (on load and on hash change);
   - printing opens every <details>, then puts them back;
   - Ctrl+F / Cmd+F opens every <details>, so the browser's find also sees their text (Chrome and Edge already search closed details);
   - "Open all details" / "Close all details"; the section bar marks the section being read. */
(function () {
  var root = document.querySelector(".prio2"); if (!root) return;
  var all = [].slice.call(root.querySelectorAll("details"));
  var btn = root.querySelector(".p2-all");
  function setAll(open) { all.forEach(function (d) { d.open = open; }); if (btn) btn.textContent = open ? btn.dataset.close : btn.dataset.open; }
  if (btn) { btn.hidden = false; btn.addEventListener("click", function () { setAll(btn.textContent === btn.dataset.open); }); }
  function openFor(hash) {
    if (!hash || hash.length < 2) return;
    var t; try { t = document.getElementById(decodeURIComponent(hash.slice(1))); } catch (e) { return; }
    if (!t) return;
    var opened = false;
    for (var p = t; p && p !== root; p = p.parentElement) if (p.tagName === "DETAILS" && !p.open) { p.open = true; opened = true; }
    if (t.tagName === "DETAILS" && !t.open) { t.open = true; opened = true; }
    if (t.classList.contains("pc")) { var d = t.querySelector("details"); if (d && !d.open) { d.open = true; opened = true; } }
    if (opened) t.scrollIntoView();
  }
  openFor(location.hash);
  window.addEventListener("hashchange", function () { openFor(location.hash); });
  root.addEventListener("click", function (e) { var a = e.target.closest && e.target.closest('a[href^="#"]'); if (a && a.getAttribute("href") === location.hash) openFor(location.hash); });
  var before = null;
  window.addEventListener("beforeprint", function () { before = all.map(function (d) { return d.open; }); all.forEach(function (d) { d.open = true; }); });
  window.addEventListener("afterprint", function () { if (before) all.forEach(function (d, i) { d.open = before[i]; }); before = null; });
  document.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && !e.altKey && (e.key === "f" || e.key === "F")) setAll(true);
  });
  var nav = root.querySelector(".pnav");
  if (nav && "IntersectionObserver" in window) {
    var links = {}; [].forEach.call(nav.querySelectorAll('a[href^="#"]'), function (a) { links[a.getAttribute("href").slice(1)] = a; });
    var secs = [].slice.call(root.querySelectorAll("section.block[aria-labelledby]")).filter(function (s) { return links[s.getAttribute("aria-labelledby")]; });
    var cur = null;
    function mark(id) {
      if (id === cur) return; cur = id;
      for (var k in links) links[k].removeAttribute("aria-current");
      var a = links[id]; if (!a) return; a.setAttribute("aria-current", "true");
      var ul = nav.querySelector("ul"), l = a.parentElement.offsetLeft, w = a.parentElement.offsetWidth;
      if (l < ul.scrollLeft || l + w > ul.scrollLeft + ul.clientWidth) ul.scrollTo({ left: Math.max(0, l - 24), behavior: "smooth" });
    }
    var vis = {};
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { vis[e.target.getAttribute("aria-labelledby")] = e.isIntersecting; });
      var id = null; secs.some(function (s) { var k = s.getAttribute("aria-labelledby"); if (vis[k]) { id = k; return true; } return false; });
      mark(id || "glance");
    }, { rootMargin: "-140px 0px -55% 0px" });
    secs.forEach(function (s) { io.observe(s); });
  }
})();
