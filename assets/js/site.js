(function () {
  "use strict";
  document.documentElement.classList.add("js");
  /* "New" badges made at build time (Events menu item, home New-event line): hide them once the event is no longer new or has ended. */
  var todayPT = new Date().toLocaleDateString("en-CA", { timeZone: "America/Vancouver" });
  document.querySelectorAll("[data-new-until]").forEach(function (n) {
    var ends = n.getAttribute("data-new-ends");
    if (todayPT >= n.getAttribute("data-new-until") || (ends && new Date(ends).getTime() < Date.now())) n.remove();
  });
  /* Upcoming-event banner above the home hero (events_cal.home_banner, 4 Oct 2026): always the next public event that has
     not ended, soonest first; "New" badge while it is new; "+N more" link. Re-picked from the embedded list on every visit
     (so it never sits on an event that has ended), then refreshed from get_public_events. Hidden only when nothing is upcoming. */
  (function () {
    var box = document.getElementById("nextev"), dn = document.getElementById("nextev-data");
    if (!box || !dn) return;
    var D; try { D = JSON.parse(dn.textContent); } catch (x) { return; }
    var FR = D.lang === "fr", TZ = "America/Vancouver", T = D.txt, NEW = {};
    D.u.forEach(function (e) { NEW[e.i] = e.n; });
    function plusDays(ymd, n) { var d = new Date(ymd + "T12:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); }
    function when(s) {
      var o = {}; new Intl.DateTimeFormat(FR ? "fr-CA" : "en-CA", { timeZone: TZ, weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit", hour12: !FR })
        .formatToParts(new Date(s)).forEach(function (p) { o[p.type] = p.value; });
      return FR ? o.weekday + " " + o.day + " " + o.month + ", " + Number(o.hour) + "\u00a0h\u00a0" + o.minute
                : o.weekday + ", " + o.month.replace(".", "") + " " + o.day + ", " + o.hour + ":" + o.minute + "\u00a0" + String(o.dayPeriod || "").replace(/\./g, "").toLowerCase();
    }
    function mk(tag, cls, txt, href) { var n = document.createElement(tag); if (cls) n.className = cls; if (txt != null) n.textContent = txt; if (href) n.href = href; return n; }
    function render(list) {
      var now = Date.now(), up = list.filter(function (e) { return new Date(e.e).getTime() > now; })
        .sort(function (a, b) { return a.s < b.s ? -1 : a.s > b.s ? 1 : a.i - b.i; });
      var p = box.querySelector("p");
      if (!up.length) { box.hidden = true; return; }
      var e = up[0], more = up.length - 1, nw = e.n && todayPT < e.n;
      p.textContent = "";
      p.append(mk("span", "nextb", new Date(e.s).getTime() <= now ? T.now : T.next), " ", mk("a", null, e.t, D.url + "?e=" + e.i));
      if (nw) p.append(" ", mk("span", "newb", T.badge));
      p.append(" ", mk("span", "nextev-when", "· " + when(e.s) + (e.l ? " · " + e.l : "")));
      if (more) { var m = mk("span", "newev-more", "· "); m.append(mk("a", null, (more === 1 ? T.more_up_one : T.more_up).replace("{n}", more), D.url)); p.append(" ", m); }
      box.hidden = false;
    }
    render(D.u);
    if (!window.fetch) return;
    fetch(D.api + "/rest/v1/rpc/get_public_events", { method: "POST", headers: { "Content-Type": "application/json", apikey: D.key }, body: "{}" })
      .then(function (r) { if (!r.ok) throw r.status; return r.json(); })
      .then(function (rows) {
        if (!Array.isArray(rows)) return;
        render(rows.map(function (r) {
          var t = String((FR && r.title_fr) || r.title || "").split("|").map(function (x) { return x.trim(); }).join(" — ");
          var pl = String((FR && r.location_name_fr) || r.location_name || "").split(",")[0].trim();
          if (pl && t.toLowerCase().indexOf(pl.toLowerCase()) >= 0) pl = "";
          // added after this build: 'New' for the usual number of days from the build day
          return { i: r.id, t: t, l: pl, s: r.starts_at, e: r.ends_at, n: r.id in NEW ? NEW[r.id] : plusDays(D.today, D.days) };
        }));
      })["catch"](function () {});  // offline / blocked: keep the built list
  })();
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
