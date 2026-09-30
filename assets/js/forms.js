/* agou.ca forms. Supabase calls are identical to the original pages (same RPCs, same parameters). */
(function () {
  "use strict";
  var SUPABASE_URL = "https://qhyttuzmysookdgxymrl.supabase.co";
  var SUPABASE_KEY = "sb_publishable_yJEI3Tmfk2bnZanIF-W1gQ_tgBwW-N7"; // public key: can only call the submit_* / get_public_events RPCs (RLS: cannot read tables)
  var cfgEl = document.getElementById("form-config");
  if (!cfgEl) return;
  var CFG = JSON.parse(cfgEl.textContent);
  var T = CFG.text;
  var $ = function (id) { return document.getElementById(id); };
  var v = function (id) { var e = $(id); return e ? e.value.trim() : ""; };
  var EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
  function rpc(name, body) {
    return fetch(SUPABASE_URL + "/rest/v1/rpc/" + name, {
      method: "POST",
      headers: { "Content-Type": "application/json", apikey: SUPABASE_KEY },
      body: JSON.stringify(body)
    }).then(function (r) { if (!r.ok) return r.text().then(function (t) { throw new Error(t); }); return r; });
  }
  function show(kind, text) { var m = $("msg"); m.className = "msg " + kind; m.textContent = text; if (kind === "err") m.focus(); }
  function lock(form, btn) { form.querySelectorAll("input,textarea,select,button").forEach(function (x) { x.disabled = true; }); btn.textContent = T.sent; }

  /* ---------- Volunteer (rpc submit_volunteer_signup) ---------- */
  if (CFG.form === "volunteer") {
    $("f").addEventListener("submit", function (e) {
      e.preventDefault();
      if (v("website")) { show("ok", T.thanks); return; } // bot
      var errs = [];
      if (!v("first_name")) errs.push(T.err_first);
      if (!v("last_name")) errs.push(T.err_last);
      if (!EMAIL.test(v("email"))) errs.push(T.err_email);
      if (v("phone").replace(/\D/g, "").length < 7) errs.push(T.err_phone);
      if (!$("consent").checked) errs.push(T.err_consent);
      if (errs.length) { show("err", T.err_prefix + errs.join(", ") + "."); return; }
      var btn = $("btn"); btn.disabled = true; btn.textContent = T.sending;
      rpc("submit_volunteer_signup", {
        p_first_name: v("first_name"), p_last_name: v("last_name"), p_email: v("email"),
        p_phone: v("phone"), p_address: v("address"),
        p_consent: true, p_consent_text: T.consent, p_website: v("website")
      }).then(function () { lock($("f"), btn); show("ok", T.thanks); })
        .catch(function () { btn.disabled = false; btn.textContent = T.button; show("err", T.err_send); });
    });
  }

  /* ---------- Nominate (rpc submit_nominator_signup) ---------- */
  if (CFG.form === "nominate") {
    $("f").addEventListener("submit", function (e) {
      e.preventDefault();
      if (v("website")) return; // bot
      var errs = [];
      if (v("full_name").length < 2) errs.push(T.err_name);
      if (v("street_address").length < 4) errs.push(T.err_street);
      if (v("phone").replace(/\D/g, "").length < 7) errs.push(T.err_phone);
      if (v("email") && !EMAIL.test(v("email"))) errs.push(T.err_email);
      if (!$("consent").checked) errs.push(T.err_consent);
      if (errs.length) { show("err", T.err_prefix + errs.join(", ") + "."); return; }
      var btn = $("btn"); btn.disabled = true; btn.textContent = T.sending;
      rpc("submit_nominator_signup", {
        p_full_name: v("full_name"), p_street_address: v("street_address"), p_phone: v("phone"),
        p_email: v("email"), p_best_time: v("best_time"),
        p_sessions: Array.prototype.map.call(document.querySelectorAll("input[name=session]:checked"), function (x) { return x.value; }),
        p_consent: true, p_consent_text: T.consent
      }).then(function () { lock($("f"), btn); show("ok", T.thanks); })
        .catch(function () { btn.disabled = false; btn.textContent = T.button; show("err", T.err_send); });
    });
  }

  /* ---------- Lawn sign (rpc submit_lawn_sign_request) ---------- */
  if (CFG.form === "lawnsign") {
    var PC = /^[A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d$/;
    $("postal_code").addEventListener("blur", function () {
      var s = this.value.replace(/[^A-Za-z0-9]/g, "").toUpperCase();
      if (s.length === 6) this.value = s.slice(0, 3) + " " + s.slice(3);
    });
    $("f").addEventListener("submit", function (e) {
      e.preventDefault();
      if (v("website")) { show("ok", T.thanks); return; } // bot
      var errs = [], ticks = [];
      if (!v("first_name")) errs.push(T.err_first);
      if (!v("last_name")) errs.push(T.err_last);
      if (!EMAIL.test(v("email"))) errs.push(T.err_email);
      if (v("phone").replace(/\D/g, "").length < 7) errs.push(T.err_phone);
      if (v("street_address").length < 3) errs.push(T.err_street);
      if (!v("city")) errs.push(T.err_city);
      if (!PC.test(v("postal_code"))) errs.push(T.err_postal);
      if (!$("permission").checked) ticks.push(T.tick_permission);
      if (!$("consent").checked) ticks.push(T.tick_consent);
      if (errs.length || ticks.length) {
        show("err", [errs.length ? T.err_add + errs.join(", ") + "." : "", ticks.length ? T.err_tick + ticks.join(T.and) + "." : ""].filter(Boolean).join(" "));
        return;
      }
      var pl = document.querySelector('input[name="placement"]:checked');
      var btn = $("btn"); btn.disabled = true; btn.textContent = T.sending;
      rpc("submit_lawn_sign_request", {
        p_first_name: v("first_name"), p_last_name: v("last_name"), p_email: v("email"), p_phone: v("phone"),
        p_street_address: v("street_address"), p_unit: v("unit"), p_city: v("city"), p_postal_code: v("postal_code"),
        p_large_sign: $("large_sign").checked, p_placement: pl ? pl.value : null, p_has_permission: true,
        p_delivery_notes: v("delivery_notes"), p_consent: true, p_consent_text: T.consent, p_website: v("website")
      }).then(function () { lock($("f"), btn); show("ok", T.thanks); })
        .catch(function () { btn.disabled = false; btn.textContent = T.button; show("err", T.err_send); });
    });
  }

  /* ---------- Events (rpc get_public_events, submit_event_rsvp) ---------- */
  if (CFG.form === "events") {
    var TZ = "America/Vancouver", LOC = T.locale, FR = LOC.indexOf("fr") === 0;
    var LIVE = CFG.live_url; // canonical live URL of this page, e.g. https://agou.ca/events/
    var el = function (tag, attrs) {
      var e = document.createElement(tag), kids = Array.prototype.slice.call(arguments, 2);
      for (var k in attrs || {}) { if (k === "text") e.textContent = attrs[k]; else if (k === "class") e.className = attrs[k]; else e.setAttribute(k, attrs[k]); }
      kids.flat().forEach(function (c) { if (c != null) e.append(c); }); return e;
    };
    var EVENTS = null, RM = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
    function parts(s) { var o = {}; new Intl.DateTimeFormat(LOC, { timeZone: TZ, weekday: "long", month: "long", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit", hour12: !FR }).formatToParts(new Date(s)).forEach(function (p) { o[p.type] = p.value; }); return o; }
    var ymd = function (s) { return new Date(s).toLocaleDateString("en-CA", { timeZone: TZ }); };
    var dayLong = function (s) { var p = parts(s); return FR ? p.weekday + " " + p.day + " " + p.month : p.weekday + " " + p.month + " " + p.day; };
    var dayShort = function (s) { var p = parts(s); return FR ? p.day + " " + p.month : p.month + " " + p.day; };
    var clock = function (s) { var p = parts(s); return FR ? p.hour + " h " + p.minute : p.hour + ":" + p.minute + " " + String(p.dayPeriod || "").toLowerCase(); };
    function timeLine(e) { return dayShort(e.starts_at) + " @ " + clock(e.starts_at) + " - " + (ymd(e.starts_at) === ymd(e.ends_at) ? "" : dayShort(e.ends_at) + " @ ") + clock(e.ends_at); }
    function heading(e) { var d = dayLong(e.starts_at); if (FR) d = d.charAt(0).toUpperCase() + d.slice(1); return d + " | " + T.riding + " | " + e.title; }
    function inline(text) {
      var out = [], re = /\*\*([^*]+)\*\*|(https?:\/\/[^\s<>"]+[^\s<>".,;:!?)])/g, last = 0, m;
      while ((m = re.exec(text))) {
        if (m.index > last) out.push(document.createTextNode(text.slice(last, m.index)));
        if (m[1] != null) out.push(el("strong", { text: m[1] }));
        else out.push(el("a", { href: m[2], rel: "noopener noreferrer", target: "_blank", text: m[2] }));
        last = re.lastIndex;
      }
      if (last < text.length) out.push(document.createTextNode(text.slice(last)));
      return out;
    }
    function renderMd(src) {
      var box = el("div", { class: "desc" });
      String(src || "").replace(/\r\n?/g, "\n").split(/\n\s*\n/).forEach(function (block) {
        var lines = block.split("\n").map(function (l) { return l.trimEnd(); }).filter(function (l) { return l.trim(); });
        var ul = null, p = null;
        lines.forEach(function (l) {
          var b = /^\s*(?:[-*•])\s+(.*)$/.exec(l);
          if (b) { p = null; if (!ul) { ul = el("ul"); box.append(ul); } ul.append(el("li", null, inline(b[1]))); }
          else { ul = null; if (!p) { p = el("p"); box.append(p); } else p.append(el("br")); p.append.apply(p, inline(l.trim())); }
        });
      });
      return box;
    }
    var plain = function (s) { return String(s || "").replace(/\*\*([^*]+)\*\*/g, "$1").replace(/^\s*[-*•]\s+/gm, "").replace(/\s+/g, " ").trim(); };
    function excerpt(s) { var t = plain(s); return t.length > 200 ? t.slice(0, 200).replace(/\s+\S*$/, "") + "…" : t; }
    var whereText = function (e) { return [e.location_name, e.address].filter(Boolean).join(", "); };
    var mapUrl = function (e) { return whereText(e) ? "https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(whereText(e)) : ""; };
    var eventUrl = function (e) { return LIVE + "?e=" + e.id; };
    var utc = function (s) { return new Date(s).toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, ""); };
    var icsEsc = function (s) { return String(s || "").replace(/\\/g, "\\\\").replace(/\n/g, "\\n").replace(/([,;])/g, "\\$1"); };
    function icsFold(line) { var out = []; while (line.length > 74) { out.push(line.slice(0, 74)); line = " " + line.slice(74); } out.push(line); return out.join("\r\n"); }
    function downloadIcs(e) {
      var desc = plain(e.description) + (e.description ? "\n\n" : "") + eventUrl(e);
      var ics = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//agou.ca//Events//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "BEGIN:VEVENT",
        "UID:event-" + e.id + "@agou.ca", "DTSTAMP:" + utc(new Date()), "DTSTART:" + utc(e.starts_at), "DTEND:" + utc(e.ends_at),
        "SUMMARY:" + icsEsc(e.title), whereText(e) ? "LOCATION:" + icsEsc(whereText(e)) : null, "DESCRIPTION:" + icsEsc(desc), "URL:" + eventUrl(e),
        "END:VEVENT", "END:VCALENDAR"].filter(Boolean).map(icsFold).join("\r\n") + "\r\n";
      var a = el("a", { href: URL.createObjectURL(new Blob([ics], { type: "text/calendar;charset=utf-8" })), download: "agou-event-" + e.id + ".ics" });
      document.body.append(a); a.click(); setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
    }
    function googleCal(e) {
      var q = new URLSearchParams({ action: "TEMPLATE", text: e.title, dates: utc(e.starts_at) + "/" + utc(e.ends_at), ctz: TZ,
        details: (plain(e.description) ? plain(e.description).slice(0, 1200) + "\n\n" : "") + eventUrl(e), location: whereText(e) });
      return "https://calendar.google.com/calendar/render?" + q.toString();
    }
    function renderList() {
      var box = $("list"); box.textContent = "";
      if (!EVENTS.length) { box.append(el("p", { class: "note", text: T.empty })); return; }
      EVENTS.forEach(function (e) {
        var a = el("a", { href: "?e=" + e.id, text: heading(e) });
        a.addEventListener("click", function (ev) { if (ev.metaKey || ev.ctrlKey || ev.shiftKey) return; ev.preventDefault(); history.pushState({ e: e.id }, "", "?e=" + e.id); route(); window.scrollTo(0, 0); });
        var ex = excerpt(e.description);
        box.append(el("section", { class: "ev" }, el("h3", null, a), ex ? el("p", { class: "ex", text: ex }) : null, el("span", { class: "badge", text: timeLine(e) })));
      });
    }
    var baseTitle = document.title, baseDesc = (document.querySelector('meta[name="description"]') || {}).content || "";
    function setMeta(title, desc, url) {
      document.title = title;
      var set = function (sel, attr, val) { var m = document.querySelector(sel); if (m) m.setAttribute(attr, val); };
      set('meta[name="description"]', "content", desc); set('meta[property="og:title"]', "content", title);
      set('meta[property="og:description"]', "content", desc); set('meta[property="og:url"]', "content", url); set('link[rel="canonical"]', "href", url);
    }
    function jsonLd(list) {
      var s = $("ld"); if (!s) { s = el("script", { id: "ld", type: "application/ld+json" }); document.head.append(s); }
      s.textContent = JSON.stringify(list.map(function (e) { return { "@context": "https://schema.org", "@type": "Event", name: e.title, startDate: e.starts_at, endDate: e.ends_at,
        eventStatus: "https://schema.org/EventScheduled", eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
        location: { "@type": "Place", name: e.location_name || e.address || T.riding, address: e.address || e.location_name || "Victoria, BC" },
        description: plain(e.description).slice(0, 500), url: eventUrl(e), organizer: { "@type": "Organization", name: "Joachim Agou campaign", url: LIVE } }; }));
    }
    function backLink() {
      var a = el("a", { href: "./", class: "back", text: T.all });
      a.addEventListener("click", function (ev) { ev.preventDefault(); history.pushState({}, "", location.pathname); route(); window.scrollTo(0, 0); });
      return a;
    }
    function field(id, label, type, attrs, opt) {
      var inp = el("input", Object.assign({ id: id, name: id, type: type }, attrs));
      return [el("label", { class: "f", for: id }, label, opt ? el("span", { class: "opt", text: T.optional }) : null), inp];
    }
    function rsvpForm(e) {
      var guests = el("select", { id: "guests", name: "guests" });
      for (var i = 0; i <= 10; i++) guests.append(el("option", { value: String(i), text: i === 0 ? T.just_me : "+" + i + (i === 1 ? T.guest : T.guests_pl) }));
      var btn = el("button", { id: "btn", type: "submit", class: "btn primary block", text: T.button });
      var msg = el("div", { id: "msg", class: "msg", role: "status", "aria-live": "polite", tabindex: "-1" });
      var f = el("form", { id: "rsvp", class: "card form", novalidate: "", hidden: "" },
        el("h2", { text: T.rsvp }), el("p", { class: "opt", text: e.title + " · " + timeLine(e) }),
        el("div", { class: "row" }, el("div", null, field("first_name", T.first_name, "text", { autocomplete: "given-name", autocapitalize: "words", required: "", maxlength: "80" })),
          el("div", null, field("last_name", T.last_name, "text", { autocomplete: "family-name", autocapitalize: "words", required: "", maxlength: "80" }))),
        field("email", T.email, "email", { autocomplete: "email", autocapitalize: "off", spellcheck: "false", required: "", maxlength: "200", inputmode: "email" }),
        field("phone", T.phone, "tel", { autocomplete: "tel", maxlength: "30", inputmode: "tel" }, true),
        el("label", { class: "f", for: "guests" }, T.guests), guests,
        el("div", { class: "cb" }, el("input", { id: "consent", type: "checkbox", required: "" }), el("label", { for: "consent", text: T.consent })),
        el("div", { class: "hp", "aria-hidden": "true" }, el("label", null, T.honeypot + " ", el("input", { id: "website", type: "text", tabindex: "-1", autocomplete: "off" }))),
        btn, msg);
      var showm = function (k, t) { msg.className = "msg " + k; msg.textContent = t; if (k === "err") msg.focus(); };
      f.addEventListener("submit", function (ev) {
        ev.preventDefault();
        var done = function () { var t = el("div", { class: "msg ok", role: "status", tabindex: "-1", text: T.thanks }); f.replaceWith(t); t.focus(); };
        if (v("website")) { done(); return; } // bot
        var errs = [];
        if (!v("first_name")) errs.push(T.err_first);
        if (!v("last_name")) errs.push(T.err_last);
        if (!EMAIL.test(v("email"))) errs.push(T.err_email);
        if (v("phone") && v("phone").replace(/\D/g, "").length < 7) errs.push(T.err_phone);
        if (!$("consent").checked) errs.push(T.err_consent);
        if (errs.length) { showm("err", T.err_prefix + errs.join(", ") + "."); return; }
        btn.disabled = true; btn.textContent = T.sending;
        rpc("submit_event_rsvp", { p_event_id: e.id, p_first_name: v("first_name"), p_last_name: v("last_name"), p_email: v("email"),
          p_phone: v("phone") || null, p_guests: +$("guests").value, p_consent: true, p_consent_text: T.consent, p_website: v("website") })
          .then(done)
          .catch(function (err) { btn.disabled = false; btn.textContent = T.button; showm("err", /not open for RSVPs/.test(String(err && err.message)) ? T.rsvpClosed : T.rsvpErr); });
      });
      return f;
    }
    function renderDetail(id) {
      var box = $("detailView"); box.textContent = "";
      var e = EVENTS.find(function (x) { return String(x.id) === String(id); });
      if (!e) { box.append(backLink(), el("p", { class: "note", text: T.gone })); setMeta(baseTitle, baseDesc, LIVE); return; }
      setMeta(e.title + " – " + dayLong(e.starts_at) + " – Joachim Agou", (plain(e.description) || heading(e)).slice(0, 160), eventUrl(e));
      jsonLd([e]);
      var where = whereText(e), mu = mapUrl(e);
      box.append(backLink(), el("h2", { class: "evtitle", text: heading(e) }), el("span", { class: "badge", text: timeLine(e) }));
      if (e.description) box.append(el("div", { class: "card" }, renderMd(e.description)));
      var info = el("div", { class: "card" }, el("div", { class: "when" }, el("b", { text: T.when }),
        el("p", { text: dayLong(e.starts_at) + ", " + clock(e.starts_at) + " – " + (ymd(e.starts_at) === ymd(e.ends_at) ? "" : dayLong(e.ends_at) + ", ") + clock(e.ends_at) + " " + T.pacific })));
      if (where) info.append(el("div", { class: "where" }, el("b", { text: T.where }),
        e.location_name ? el("p", { text: e.location_name }) : null, e.address ? el("p", { text: e.address }) : null,
        mu ? el("p", null, el("a", { href: mu, target: "_blank", rel: "noopener noreferrer", class: "more", text: T.maps })) : null));
      box.append(info);
      var acts = el("div", { class: "actions" }), rsvpBtn = null;
      if (e.rsvp_open) { rsvpBtn = el("button", { type: "button", class: "btn primary", "aria-expanded": "false", "aria-controls": "rsvp", text: T.rsvp }); acts.append(rsvpBtn); }
      var calBtn = el("button", { type: "button", class: "btn sec", "aria-expanded": "false", "aria-haspopup": "true", text: T.add_cal });
      var menu = el("div", { class: "calmenu", hidden: "" });
      var ics = el("button", { type: "button", text: T.ics });
      ics.addEventListener("click", function () { downloadIcs(e); menu.hidden = true; calBtn.setAttribute("aria-expanded", "false"); });
      menu.append(el("a", { href: googleCal(e), target: "_blank", rel: "noopener noreferrer", text: T.gcal }), ics);
      calBtn.addEventListener("click", function () { menu.hidden = !menu.hidden; calBtn.setAttribute("aria-expanded", String(!menu.hidden)); });
      acts.append(el("div", { class: "cal" }, calBtn, menu));
      if (e.signup_url && /^https?:\/\//i.test(e.signup_url)) acts.append(el("a", { href: e.signup_url, target: "_blank", rel: "noopener noreferrer", class: "btn sec", text: T.signup }));
      box.append(acts);
      if (rsvpBtn) { var f = rsvpForm(e); box.append(f); rsvpBtn.addEventListener("click", function () { f.hidden = false; rsvpBtn.setAttribute("aria-expanded", "true"); f.scrollIntoView({ behavior: RM ? "auto" : "smooth", block: "start" }); setTimeout(function () { if ($("first_name")) $("first_name").focus({ preventScroll: true }); }, 300); }); }
    }
    function currentId() { var q = new URLSearchParams(location.search).get("e"); if (q) return q; var h = location.hash.replace(/^#/, ""); return /^\d+$/.test(h) ? h : null; }
    function updateLangLink() { var a = document.querySelector("a[data-lang-switch]"); if (a) { var id = currentId(); a.href = a.getAttribute("data-base") + (id ? "?e=" + id : ""); } }
    function route() {
      if (!EVENTS) return;
      var id = currentId();
      $("listView").hidden = !!id; $("detailView").hidden = !id;
      document.querySelectorAll("[data-hide-on-detail]").forEach(function (n) { n.hidden = !!id; });
      updateLangLink();
      if (id) renderDetail(id);
      else { setMeta(baseTitle, baseDesc, LIVE); renderList(); jsonLd(EVENTS); }
    }
    window.addEventListener("popstate", route);
    window.addEventListener("hashchange", route);
    document.addEventListener("click", function (ev) { var m = document.querySelector(".calmenu"); if (m && !m.hidden && !ev.target.closest(".cal")) { m.hidden = true; var b = document.querySelector(".cal > .btn"); if (b) b.setAttribute("aria-expanded", "false"); } });
    rpc("get_public_events", {}).then(function (r) { return r.json(); }).then(function (data) { EVENTS = data; route(); })
      .catch(function () { $("list").textContent = ""; $("list").append(el("p", { class: "note", text: T.loadErr })); if (currentId()) $("listView").hidden = false; });
  }
})();
