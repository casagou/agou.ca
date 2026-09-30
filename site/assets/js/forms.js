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
  var C = CFG.common || { err_title: "", tick: "" };
  /* Errors: a summary (each item links to its field) plus a message under each field (aria-invalid + aria-describedby). */
  function clearErrs(form) {
    form.querySelectorAll(".ferr").forEach(function (x) { x.remove(); });
    form.querySelectorAll("[aria-invalid]").forEach(function (x) {
      x.removeAttribute("aria-invalid");
      var d = x.getAttribute("data-desc"); if (d) x.setAttribute("aria-describedby", d); else x.removeAttribute("aria-describedby");
    });
  }
  function fieldErr(inp, text) {
    var id = inp.id + "-err";
    if (!inp.hasAttribute("data-desc")) inp.setAttribute("data-desc", inp.getAttribute("aria-describedby") || "");
    inp.setAttribute("aria-invalid", "true");
    inp.setAttribute("aria-describedby", ((inp.getAttribute("data-desc") || "") + " " + id).trim());
    var p = document.createElement("p"); p.className = "ferr"; p.id = id;
    var ic = document.createElement("span"); ic.className = "ferr-ic"; ic.setAttribute("aria-hidden", "true"); ic.textContent = "!";
    p.append(ic, document.createTextNode(text));
    var anchor = inp.type === "checkbox" || inp.type === "radio" ? inp.closest(".cb") : inp;
    anchor.after(p);
    var off = function () { clearOne(inp); inp.removeEventListener("input", off); inp.removeEventListener("change", off); };
    inp.addEventListener("input", off); inp.addEventListener("change", off);
  }
  function clearOne(inp) {
    var e = document.getElementById(inp.id + "-err"); if (e) e.remove();
    inp.removeAttribute("aria-invalid");
    var d = inp.getAttribute("data-desc"); if (d) inp.setAttribute("aria-describedby", d); else inp.removeAttribute("aria-describedby");
  }
  // list: [[fieldId, message], ...]
  function fail(form, msg, list) {
    clearErrs(form);
    msg.className = "msg err"; msg.textContent = "";
    var h = document.createElement("p"); h.className = "msg-t"; h.textContent = C.err_title; msg.append(h);
    var ul = document.createElement("ul");
    list.forEach(function (it) {
      var inp = document.getElementById(it[0]); if (!inp) return;
      fieldErr(inp, it[1]);
      var li = document.createElement("li"), a = document.createElement("a");
      a.href = "#" + it[0]; a.textContent = it[1];
      a.addEventListener("click", function (ev) { ev.preventDefault(); inp.focus(); inp.scrollIntoView({ block: "center" }); });
      li.append(a); ul.append(li);
    });
    msg.append(ul); msg.focus();
  }
  function ok(form) { clearErrs(form); }
  function lock(form, btn) { form.querySelectorAll("input,textarea,select,button").forEach(function (x) { x.disabled = true; }); btn.textContent = T.sent; }

  /* ---------- Volunteer (rpc submit_volunteer_signup) ---------- */
  if (CFG.form === "volunteer") {
    $("f").addEventListener("submit", function (e) {
      e.preventDefault();
      if (v("website")) { show("ok", T.thanks); return; } // bot
      var errs = [];
      var P = T.err_prefix;
      if (!v("first_name")) errs.push(["first_name", P + T.err_first]);
      if (!v("last_name")) errs.push(["last_name", P + T.err_last]);
      if (!EMAIL.test(v("email"))) errs.push(["email", P + T.err_email]);
      if (v("phone").replace(/\D/g, "").length < 7) errs.push(["phone", P + T.err_phone]);
      if (!$("consent").checked) errs.push(["consent", C.tick + T.err_consent]);
      if (errs.length) { fail($("f"), $("msg"), errs); return; }
      ok($("f")); $("msg").className = "msg"; $("msg").textContent = "";
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
      var P = T.err_prefix;
      if (v("full_name").length < 2) errs.push(["full_name", P + T.err_name]);
      if (v("street_address").length < 4) errs.push(["street_address", P + T.err_street]);
      if (v("phone").replace(/\D/g, "").length < 7) errs.push(["phone", P + T.err_phone]);
      if (v("email") && !EMAIL.test(v("email"))) errs.push(["email", P + T.err_email]);
      if (!$("consent").checked) errs.push(["consent", C.tick + T.err_consent]);
      if (errs.length) { fail($("f"), $("msg"), errs); return; }
      ok($("f")); $("msg").className = "msg"; $("msg").textContent = "";
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
      var errs = [], A = T.err_add, K = T.err_tick;
      if (!v("first_name")) errs.push(["first_name", A + T.err_first]);
      if (!v("last_name")) errs.push(["last_name", A + T.err_last]);
      if (!EMAIL.test(v("email"))) errs.push(["email", A + T.err_email]);
      if (v("phone").replace(/\D/g, "").length < 7) errs.push(["phone", A + T.err_phone]);
      if (v("street_address").length < 3) errs.push(["street_address", A + T.err_street]);
      if (!v("city")) errs.push(["city", A + T.err_city]);
      if (!PC.test(v("postal_code"))) errs.push(["postal_code", A + T.err_postal]);
      if (!$("permission").checked) errs.push(["permission", K + T.tick_permission]);
      if (!$("consent").checked) errs.push(["consent", K + T.tick_consent]);
      if (errs.length) { fail($("f"), $("msg"), errs); return; }
      ok($("f")); $("msg").className = "msg"; $("msg").textContent = "";
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
    var dayFull = function (s) { var p = parts(s); return FR ? cap(p.weekday) + " " + p.day + " " + p.month : p.weekday + ", " + p.month + " " + p.day; }; // "Sunday, October 4" / "Dimanche 4 octobre"
    var cap = function (s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; };
    var NB = "\u00a0";
    // "11:15 am – 12:30 pm" (same day) or "Oct 4, 11:15 am – Oct 5, 1:00 am"
    function timeRange(e) {
      var same = ymd(e.starts_at) === ymd(e.ends_at);
      return (same ? "" : dayShort(e.starts_at) + ", ") + clock(e.starts_at).replace(/ /g, NB) + " – " + (same ? "" : dayShort(e.ends_at) + ", ") + clock(e.ends_at).replace(/ /g, NB);
    }
    function timeLine(e) { return dayShort(e.starts_at) + " · " + timeRange(e); }
    // Title as written in the campaign app, with "|" shown as an em dash: "Coffee with Joachim — North Park"
    var evTitle = function (e) { return String(e.title || "").replace(/\s*\|\s*/g, NB + "— ").trim(); }; // the dash stays with the words before it
    function tile(s, cls) { // "SUN / 4 / OCT" block (decorative: the full date is also in the text next to it)
      var o = {}; new Intl.DateTimeFormat(LOC, { timeZone: TZ, weekday: "short", day: "numeric", month: "short" }).formatToParts(new Date(s)).forEach(function (p) { o[p.type] = p.value; });
      var up = function (x) { return String(x || "").replace(/\./g, "").toUpperCase(); };
      return el("span", { class: "dtile" + (cls ? " " + cls : ""), "aria-hidden": "true" },
        el("span", { class: "dt-wd", text: up(o.weekday) }), el("span", { class: "dt-d", text: o.day }), el("span", { class: "dt-m", text: up(o.month) }));
    }
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
    var whereText = function (e) { return [venue(e), e.address].filter(Boolean).join(", "); }; // calendar LOCATION: venue + street address, so calendar apps find the right place
    // Maps. With lat/lng (campaign_events, migration 41) every link goes to the exact pin. Without them, the street
    // address alone is searched. The old link searched "location_name, address" as free text, and Google answered with a
    // list of guesses (other markets, the other Bubby Rose's), not a pin.
    var hasPin = function (e) { return typeof e.lat === "number" && typeof e.lng === "number"; };
    var ll = function (e) { return e.lat.toFixed(6) + "," + e.lng.toFixed(6); };
    function venue(e) { // "Fernwood Square, on the public sidewalk outside Little June" -> "Little June"
      var s = String(e.location_name || ""), m = /\b(?:outside|beside|at)\s+(?:the\s+(?=[A-Z][a-z]+\s+[A-Z]))?(.+)$/.exec(s);
      return ((m ? m[1] : s.split(",")[0]) || "").replace(/\s*\(.*?\)\s*$/, "").trim();
    }
    var mapUrl = function (e) {
      if (hasPin(e)) return "https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(ll(e));
      return e.address ? "https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(e.address) : "";
    };
    var dirUrl = function (e) {
      if (hasPin(e)) return "https://www.google.com/maps/dir/?api=1&destination=" + encodeURIComponent(ll(e));
      return e.address ? "https://www.google.com/maps/dir/?api=1&destination=" + encodeURIComponent(e.address) : "";
    };
    var appleUrl = function (e) {
      var q = venue(e) || e.address || "";
      if (hasPin(e)) return "https://maps.apple.com/?ll=" + ll(e) + "&q=" + encodeURIComponent(q);
      return e.address ? "https://maps.apple.com/?q=" + encodeURIComponent(e.address) : "";
    };
    function mapImg(e) { // static OSM map made by tools/make_event_maps.py; only if it was drawn for this exact pin
      var m = (CFG.maps || {})[String(e.id)];
      if (!m || !hasPin(e) || Math.abs(m.lat - e.lat) > 1e-6 || Math.abs(m.lng - e.lng) > 1e-6) return null;
      var b = "/assets/img/events/event-" + e.id + "-", q = "?v=" + m.v;
      var img = el("img", { src: b + "phone-2x.png" + q, srcset: b + "phone-2x.png" + q + " 2x, " + b + "phone-3x.png" + q + " 3x",
        width: "358", height: "224", alt: T.map_alt.replace("{v}", venue(e) || e.location_name || ""), loading: "lazy", decoding: "async" });
      var pic = el("picture", null, el("source", { media: "(min-width: 700px)", srcset: b + "desk-2x.png" + q + " 2x", width: "640", height: "320" }), img);
      return el("figure", { class: "evmap" },
        el("a", { href: mapUrl(e), target: "_blank", rel: "noopener noreferrer", "aria-label": T.map_open }, pic),
        el("figcaption", null, el("a", { href: "https://www.openstreetmap.org/copyright", target: "_blank", rel: "noopener noreferrer", text: "© OpenStreetMap contributors" })));
    }
    // The description repeats the practical facts that are now shown above it; those paragraphs are left out.
    var REPEAT = /^\s*(?:\*\*)?(?:where to find me|when|where|rsvp is optional|où me trouver|quand|où)\b/i;
    function spotLine(e) {
      var m = /(?:^|\n)\s*(?:\*\*)?Where to find me:?(?:\*\*)?\s*([^\n]+)/i.exec(String(e.description || ""));
      return m ? m[1].trim() : [e.location_name, e.address].filter(Boolean).join(", ");
    }
    function bodyText(e) {
      return String(e.description || "").replace(/\r\n?/g, "\n").split(/\n\s*\n/).filter(function (b) { return b.trim() && !REPEAT.test(b); })
        .map(function (b) { // long paragraphs: at most two sentences each
          if (b.length < 240 || /^\s*[-*•]\s/m.test(b)) return b;
          var ss = b.match(/[^.!?]+[.!?]+["”’)]*\s*|[^.!?]+$/g) || [b], out = [];
          for (var i = 0; i < ss.length; i += 2) out.push(ss.slice(i, i + 2).join("").trim());
          return out.join("\n\n");
        }).join("\n\n");
    }
    var eventUrl = function (e) { return LIVE + "?e=" + e.id; };
    var utc = function (s) { return new Date(s).toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, ""); };
    var icsEsc = function (s) { return String(s || "").replace(/\\/g, "\\\\").replace(/\n/g, "\\n").replace(/([,;])/g, "\\$1"); };
    function icsFold(line) { var out = []; while (line.length > 74) { out.push(line.slice(0, 74)); line = " " + line.slice(74); } out.push(line); return out.join("\r\n"); }
    function downloadIcs(e) {
      var desc = plain(e.description) + (e.description ? "\n\n" : "") + eventUrl(e);
      var ics = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//agou.ca//Events//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "BEGIN:VEVENT",
        "UID:event-" + e.id + "@agou.ca", "DTSTAMP:" + utc(new Date()), "DTSTART:" + utc(e.starts_at), "DTEND:" + utc(e.ends_at),
        "SUMMARY:" + icsEsc(evTitle(e)), whereText(e) ? "LOCATION:" + icsEsc(whereText(e)) : null, "DESCRIPTION:" + icsEsc(desc), "URL:" + eventUrl(e),
        "END:VEVENT", "END:VCALENDAR"].filter(Boolean).map(icsFold).join("\r\n") + "\r\n";
      var a = el("a", { href: URL.createObjectURL(new Blob([ics], { type: "text/calendar;charset=utf-8" })), download: "agou-event-" + e.id + ".ics" });
      document.body.append(a); a.click(); setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
    }
    function googleCal(e) {
      var q = new URLSearchParams({ action: "TEMPLATE", text: evTitle(e), dates: utc(e.starts_at) + "/" + utc(e.ends_at), ctz: TZ,
        details: (plain(e.description) ? plain(e.description).slice(0, 1200) + "\n\n" : "") + eventUrl(e), location: whereText(e) });
      return "https://calendar.google.com/calendar/render?" + q.toString();
    }
    function renderList() {
      var box = $("list"); box.textContent = "";
      if (!EVENTS.length) { box.append(el("p", { class: "note", text: T.empty })); return; }
      var now = Date.now(), up = function (e) { return new Date(e.ends_at).getTime() >= now; };
      var list = EVENTS.slice().sort(function (a, b) { return (up(b) - up(a)) || (new Date(a.starts_at) - new Date(b.starts_at)) || (a.id - b.id); });
      var ul = el("ul", { class: "evlist" });
      list.forEach(function (e) {
        var a = el("a", { href: "?e=" + e.id, text: evTitle(e) });
        a.addEventListener("click", function (ev) { if (ev.metaKey || ev.ctrlKey || ev.shiftKey) return; ev.preventDefault(); history.pushState({ e: e.id }, "", "?e=" + e.id); route(); window.scrollTo(0, 0); });
        var du = dirUrl(e), past = !up(e);
        ul.append(el("li", { class: "evc" + (past ? " past" : "") }, tile(e.starts_at),
          el("div", { class: "evc-body" },
            el("h3", null, a),
            el("p", { class: "evc-when" }, el("span", { class: "vh", text: dayFull(e.starts_at) + ", " }), timeRange(e), past ? el("span", { class: "evc-ended", text: " · " + T.ended }) : null),
            e.neighbourhood ? el("p", { class: "evc-nb", text: e.neighbourhood }) : null,
            du && !past ? el("p", { class: "readlink evc-dir" }, el("a", { href: du, target: "_blank", rel: "noopener noreferrer", text: T.directions_short + " ↗" })) : null)));
      });
      box.append(ul);
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
        location: Object.assign({ "@type": "Place", name: venue(e) || e.location_name || e.address || T.riding, address: e.address || e.location_name || "Victoria, BC" },
          hasPin(e) ? { geo: { "@type": "GeoCoordinates", latitude: e.lat, longitude: e.lng } } : {}),
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
        el("h2", { text: T.rsvp }), el("p", { class: "opt", text: evTitle(e) + " · " + timeLine(e) }),
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
        var errs = [], P = T.err_prefix;
        if (!v("first_name")) errs.push(["first_name", P + T.err_first]);
        if (!v("last_name")) errs.push(["last_name", P + T.err_last]);
        if (!EMAIL.test(v("email"))) errs.push(["email", P + T.err_email]);
        if (v("phone") && v("phone").replace(/\D/g, "").length < 7) errs.push(["phone", P + T.err_phone]);
        if (!$("consent").checked) errs.push(["consent", C.tick + T.err_consent]);
        if (errs.length) { fail(f, msg, errs); return; }
        ok(f); msg.className = "msg"; msg.textContent = "";
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
      setMeta(evTitle(e) + " – " + cap(dayLong(e.starts_at)) + " – Joachim Agou", (spotLine(e) || plain(e.description)).slice(0, 160), eventUrl(e));
      jsonLd([e]);
      var past = new Date(e.ends_at).getTime() < Date.now();
      // 1. what and when: date tile + title + time range and neighbourhood
      box.append(backLink(), el("header", { class: "evhead" }, tile(e.starts_at, "big"),
        el("div", null, el("h2", { class: "evtitle", text: evTitle(e) }),
          el("p", { class: "evwhen" }, el("span", { class: "vh", text: dayFull(e.starts_at) + ", " }), timeRange(e),
            e.neighbourhood && evTitle(e).indexOf(e.neighbourhood) < 0 ? el("span", { class: "evnb", text: " · " + e.neighbourhood }) : null,
            past ? el("span", { text: " · " + T.ended }) : null))));
      // 2. where to find him, then the actions: directions (primary), calendar (secondary), Apple Maps (text link)
      var spot = spotLine(e);
      if (spot) box.append(el("p", { class: "evspot" }, el("strong", { text: T.find_me + " " }), spot));
      var acts = el("div", { class: "actions evacts" }), du = dirUrl(e), au = appleUrl(e);
      if (du) acts.append(el("a", { href: du, target: "_blank", rel: "noopener noreferrer", class: "btn primary", text: T.directions }));
      var calBtn = el("button", { type: "button", class: "btn sec", "aria-expanded": "false", "aria-haspopup": "true", text: T.add_cal });
      var menu = el("div", { class: "calmenu", hidden: "" });
      var ics = el("button", { type: "button", text: T.ics });
      ics.addEventListener("click", function () { downloadIcs(e); menu.hidden = true; calBtn.setAttribute("aria-expanded", "false"); });
      menu.append(el("a", { href: googleCal(e), target: "_blank", rel: "noopener noreferrer", text: T.gcal }), ics);
      calBtn.addEventListener("click", function () { menu.hidden = !menu.hidden; calBtn.setAttribute("aria-expanded", String(!menu.hidden)); });
      if (!past) acts.append(el("div", { class: "cal" }, calBtn, menu));
      box.append(acts);
      if (au) box.append(el("p", { class: "readlink evapple" }, el("a", { href: au, target: "_blank", rel: "noopener noreferrer", text: T.apple + " ↗" })));
      var fig = mapImg(e); if (fig) box.append(fig);
      // 3. the facts, once, in one tidy block
      var facts = el("dl", { class: "evfacts" },
        el("dt", { text: T.when }), el("dd", { text: dayFull(e.starts_at) + ", " + timeRange(e).replace(new RegExp(NB, "g"), " ") + " " + T.pacific }));
      var addr = e.address ? e.address.replace(/,\s*(Victoria),\s*BC$/i, ", $1") : "";
      var place = venue(e) || e.location_name || "";
      if (place || addr) facts.append(el("dt", { text: T.where }), el("dd", null, place, place && addr ? el("br") : null, addr || null));
      box.append(facts);
      // 4. the welcome, in short paragraphs
      var txt = bodyText(e);
      if (txt) box.append(renderMd(txt));
      // 5. RSVP: optional and quiet
      if (e.signup_url && /^https?:\/\//i.test(e.signup_url)) box.append(el("p", { class: "readlink" }, el("a", { href: e.signup_url, target: "_blank", rel: "noopener noreferrer", text: T.signup })));
      if (e.rsvp_open) {
        var rsvpBtn = el("button", { type: "button", class: "linkbtn", "aria-expanded": "false", "aria-controls": "rsvp", text: T.rsvp_link });
        box.append(el("div", { class: "evrsvp" }, el("p", { text: T.rsvp_quiet }), rsvpBtn));
        var f = rsvpForm(e); box.append(f);
        rsvpBtn.addEventListener("click", function () { f.hidden = false; rsvpBtn.setAttribute("aria-expanded", "true"); f.scrollIntoView({ behavior: RM ? "auto" : "smooth", block: "start" }); setTimeout(function () { if ($("first_name")) $("first_name").focus({ preventScroll: true }); }, 300); });
      }
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
