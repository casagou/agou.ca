"""Events calendar (October 2026 month view) and 'New' events for agou.ca (build.py imports this).

- Events come from the same public rpc as the list (get_public_events), fetched at build time for the static parts
  (Events menu badge, home 'New event' line); the page itself still loads them live in forms.js, so the calendar chips stay in sync.
- data/events-added.json records when each event id was first added (seeded from campaign_events.created_at; new ids get the build time
  as added_at) and when it last changed meaningfully (changed_at: title, title_fr, start or end changed between builds).
- An event is new for site.json events_new_hours hours (default 48; 2 days since 4 Oct 2026, was 7 days) from the later of
  added_at (or, for records without it, 00:00 Pacific on the added date) and changed_at. until = that + hours (exclusive, exact time).
- Key dates: site.json key_dates (Elections BC only, each with an elections.bc.ca source).
- site.json events_calendar_live = false: live builds leave all of this out.
See README 'Events calendar' and 'New events'."""
import calendar, datetime, html, json, pathlib, sys, urllib.request
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent
TZ = ZoneInfo("America/Vancouver")
ADDED = ROOT / "data/events-added.json"
SUPABASE_URL = "https://qhyttuzmysookdgxymrl.supabase.co"
SUPABASE_KEY = "sb_publishable_yJEI3Tmfk2bnZanIF-W1gQ_tgBwW-N7"  # public key (same as forms.js): can only call get_public_events / submit_* rpcs
esc = lambda s: html.escape(str(s), quote=True)
MONTHS = {"en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
          "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]}
DAYS = {"en": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        "fr": ["dimanche", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"]}
DAYS_ABBR = {"en": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"], "fr": ["dim.", "lun.", "mar.", "mer.", "jeu.", "ven.", "sam."]}
_STATE = {"events": None, "fetched": False}


def today():
    return datetime.datetime.now(TZ).date()


def day_label(d, lang):
    """'Saturday, October 3' / 'samedi 3 octobre' ('1er' for the first)."""
    wd = DAYS[lang][(d.weekday() + 1) % 7]
    if lang == "fr":
        return f"{wd} {'1er' if d.day == 1 else d.day} {MONTHS['fr'][d.month - 1]}"
    return f"{wd}, {MONTHS['en'][d.month - 1]} {d.day}"


def events():
    """Public events with their 'added' date. Fetches get_public_events once per build; records ids it has not seen
    (added = build day) in data/events-added.json. Offline: falls back to the file's own copy of title/start/end."""
    if _STATE["events"] is not None: return _STATE["events"]
    store = json.loads(ADDED.read_text())
    live = None
    try:
        req = urllib.request.Request(SUPABASE_URL + "/rest/v1/rpc/get_public_events", data=b"{}", method="POST",
                                     headers={"apikey": SUPABASE_KEY, "Content-Type": "application/json"})
        live = json.loads(urllib.request.urlopen(req, timeout=10).read())
    except Exception as ex:
        print(f"WARNING: get_public_events not reachable ({ex.__class__.__name__}); using data/events-added.json for the 'New' badges")
    changed = False
    _STATE["live"] = live
    if live is not None:
        for e in live:
            k = str(e["id"]); rec = store["events"].get(k)
            snap = {"title": e["title"], "starts_at": e["starts_at"], "ends_at": e["ends_at"]}
            if e.get("title_fr"): snap["title_fr"] = e["title_fr"]  # migration 46; the French home banner uses it
            if rec is None:
                store["events"][k] = {"added": today().isoformat(), "added_at": now_iso(), **snap}; changed = True
                print(f"events: new event id {k} ({e['title']}) recorded as added {now_iso()} in data/events-added.json (commit it)")
            elif any(rec.get(f) != v for f, v in snap.items()):
                # meaningful change (title / title_fr / start / end differ from the last build): 'New' again from now.
                # A field the record never stored (e.g. title_fr before migration 46) is filled in silently.
                if any(f in rec and rec[f] != v for f, v in snap.items()):
                    rec["changed_at"] = now_iso()
                    print(f"events: event id {k} ({e['title']}) changed; recorded changed_at {rec['changed_at']} (commit it)")
                rec.update(snap); changed = True
        if changed: ADDED.write_text(json.dumps(store, ensure_ascii=False, indent=2) + "\n")
        ids = {str(e["id"]) for e in live}
    else:
        ids = set(store["events"])
    out = []
    for k, r in store["events"].items():
        if k not in ids: continue
        out.append({"id": int(k), "title": r["title"], "title_fr": r.get("title_fr") or "", "starts_at": r["starts_at"], "ends_at": r["ends_at"],
                    "added": datetime.date.fromisoformat(r["added"]), "since": since_of(r)})
    out.sort(key=lambda e: (e["starts_at"], e["id"]))
    _STATE["events"] = out
    return out


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _ts(s):
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))


def since_of(r):
    """When the event became 'new': the later of added_at (else 00:00 Pacific on the added date) and changed_at."""
    a = _ts(r["added_at"]) if r.get("added_at") else datetime.datetime.combine(datetime.date.fromisoformat(r["added"]), datetime.time(0), TZ)
    return max(a, _ts(r["changed_at"])) if r.get("changed_at") else a


def new_hours(site):
    return int(site.get("events_new_hours", 48))


def until(e, site):
    """Exact UTC time the event stops being 'new'."""
    return (e["since"] + datetime.timedelta(hours=new_hours(site))).astimezone(datetime.timezone.utc)


def until_iso(e, site):
    return until(e, site).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_map(site):
    """{event id: ISO UTC time} = when the event stops being new. forms.js / site.js show 'New' while Date.now() < that time."""
    return {str(e["id"]): until_iso(e, site) for e in events()}


def new_upcoming(site):
    now = datetime.datetime.now(datetime.timezone.utc)
    return [e for e in events() if until(e, site) > now and datetime.datetime.fromisoformat(e["ends_at"]) >= now]


def title_of(e, lang="en"):
    t = (lang == "fr" and e.get("title_fr")) or e["title"]  # French site: title_fr, else the English title
    return " — ".join(p.strip() for p in t.split("|"))


def nav_badge(lang, site, ui):
    """Badge after 'Events' in the main menu (desktop and mobile), while an upcoming event is new. site.js removes it once expired."""
    nu = new_upcoming(site)
    if not nu: return ""
    T = ui[lang]["new_events"]
    last_until = until_iso(max(nu, key=lambda e: until(e, site)), site)
    last_end = max(e["ends_at"] for e in nu)
    return (f' <span class="newb nav-new" data-new-until="{last_until}" data-new-ends="{esc(last_end)}">'
            f'<span class="vh">{esc(T["nav_sr"])}</span><span aria-hidden="true">{esc(T["badge"])}</span></span>')


ABBR_MON = {"en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
            "fr": ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]}


def short_when(iso, lang):
    """'Sun, Oct 4, 9:30 am' / 'dim. 4 oct., 9 h 30' (Pacific time; no line break inside the time). Same format as site.js (home banner)."""
    t = datetime.datetime.fromisoformat(iso).astimezone(TZ); wd = DAYS_ABBR[lang][(t.weekday() + 1) % 7]
    if lang == "fr": return f"{wd} {t.day} {ABBR_MON['fr'][t.month - 1]}, {t.hour}\u00a0h\u00a0{t.minute:02d}"
    h = t.hour % 12 or 12
    return f"{wd}, {ABBR_MON['en'][t.month - 1]} {t.day}, {h}:{t.minute:02d}\u00a0{'am' if t.hour < 12 else 'pm'}"


def short_place(title, loc):
    """First part of the location ('Cook St & Caledonia Ave'), left out when the title already names it."""
    p = (loc or "").split(",")[0].strip()
    return "" if not p or p.lower() in title.lower() else p


def upcoming(lang, site):
    """Every public event that has not ended yet, soonest first, localized for the home banner:
    {i: id, t: title, l: short place, s: starts_at, e: ends_at, n: ISO UTC time it stops being 'New'}.
    Uses the build-time get_public_events (title_fr / location_name_fr on French, else English); offline: data/events-added.json."""
    now = datetime.datetime.now(datetime.timezone.utc)
    nu = {e["id"]: until_iso(e, site) for e in events()}
    src = _STATE.get("live")
    if src is None: src = [{"id": e["id"], "title": e["title"], "title_fr": e["title_fr"], "starts_at": e["starts_at"], "ends_at": e["ends_at"]} for e in events()]
    out = []
    for e in src:
        if datetime.datetime.fromisoformat(e["ends_at"]) <= now: continue
        t = title_of({"title": e["title"], "title_fr": e.get("title_fr") or ""}, lang)
        loc = (lang == "fr" and e.get("location_name_fr")) or e.get("location_name") or ""
        out.append({"i": e["id"], "t": t, "l": short_place(t, loc), "s": e["starts_at"], "e": e["ends_at"], "n": nu.get(e["id"], "")})
    out.sort(key=lambda x: (x["s"], x["i"]))
    return out


def home_banner(lang, site, ui, events_url):
    """Upcoming-event banner above the home hero (replaces the 'New event' line, 4 Oct 2026): ALWAYS the next public event
    that has not ended (soonest first), 'New' badge while it is new, '+N more' link to the Events page.
    Built static (works without JS); site.js re-picks the next event from the embedded list on every visit and refreshes it
    from get_public_events, so it never goes stale between builds. Hidden only when there is no upcoming event.
    Guard: build.py check() fails if events are upcoming and a home page has no banner."""
    up = upcoming(lang, site)
    T = ui[lang]["new_events"]
    data = {"u": up, "url": events_url, "built": now_iso(), "hours": new_hours(site), "lang": lang,
            "txt": {k: T[k] for k in ("next", "now", "badge", "more_up_one", "more_up")}, "api": SUPABASE_URL, "key": SUPABASE_KEY}
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    inner = ""
    if up:
        e = up[0]; now = datetime.datetime.now(datetime.timezone.utc)
        live = datetime.datetime.fromisoformat(e["s"]) <= now
        more = len(up) - 1
        inner = (f'<span class="nextb">{esc(T["now"] if live else T["next"])}</span> <a href="{events_url}?e={e["i"]}">{esc(e["t"])}</a>'
                 + (f' <span class="newb">{esc(T["badge"])}</span>' if e["n"] and now < _ts(e["n"]) else "")
                 + f' <span class="nextev-when">· {esc(short_when(e["s"], lang))}' + (f' · {esc(e["l"])}' if e["l"] else "") + "</span>"
                 + (f' <span class="newev-more">· <a href="{events_url}">{esc((T["more_up_one"] if more == 1 else T["more_up"]).replace("{n}", str(more)))}</a></span>' if more else ""))
    return (f'<div class="newev nextev" id="nextev"{"" if up else " hidden"}><div class="wrap"><p>{inner}</p></div>'
            f'<script type="application/json" id="nextev-data">{js}</script></div>')


def key_dates(site):
    out = []
    for k in site.get("key_dates", []):
        if not k.get("sources") or not all(s.startswith("https://elections.bc.ca/") for s in k["sources"]):
            sys.exit(f"site.json key_dates {k.get('start')}: every key date needs an elections.bc.ca source")
        a = datetime.date.fromisoformat(k["start"]); b = datetime.date.fromisoformat(k.get("end", k["start"]))
        if b < a: sys.exit(f"site.json key_dates {k['start']}: end before start")
        out.append({**k, "a": a, "b": b})
    return out


def calendar_html(lang, site, ui):
    """Static month grid (table) with the key dates; forms.js adds the event chips into each day (data-date) and the agenda.
    Without JS the grid, key dates and agenda still show (the list needs JS anyway)."""
    T = ui[lang]["events"]
    y, m = map(int, site["calendar_month"].split("-"))
    kds = key_dates(site)
    src_name = {"https://elections.bc.ca/2026-provincial-election/": T["src2"], "https://elections.bc.ca/2026-provincial-election/ways-to-vote/": T["src3"]}
    def kd_on(d): return [k for k in kds if k["a"] <= d <= k["b"]]
    cal = calendar.Calendar(firstweekday=0)  # Monday first (Joachim, 1 Oct 2026); blank cells before the 1st come from the real weekday
    order = [1, 2, 3, 4, 5, 6, 0]  # DAYS / DAYS_ABBR are Sunday-first lists: Mon … Sun
    head = "".join(f'<th scope="col"{" class=\"we\"" if i in (6, 0) else ""}><abbr title="{esc(DAYS[lang][i])}">{esc(DAYS_ABBR[lang][i])}</abbr></th>' for i in order)
    rows = []
    for week in cal.monthdatescalendar(y, m):
        cells = []
        for d in week:
            if d.month != m:
                cells.append(f'<td class="out{" we" if d.weekday() >= 5 else ""}" aria-hidden="true"></td>'); continue
            ks = kd_on(d); iso = d.isoformat(); we = " we" if d.weekday() >= 5 else ""  # Sat/Sun from the date, not the column
            items = "".join(f'<li class="it kd"><span class="mk" aria-hidden="true">◆</span><span class="tx">{esc(k[lang]["short"])}</span></li>' for k in ks)
            num = (f'<a class="dn dn-link" href="#ag-{iso}"><span class="vh">{esc(day_label(d, lang))}</span><span aria-hidden="true">{d.day}</span></a>' if ks else "")
            cells.append(f'<td class="day{we}{" has-kd" if ks else ""}" data-date="{iso}">'
                         f'<span class="dn dn-txt"><span class="vh">{esc(day_label(d, lang))}</span><span aria-hidden="true">{d.day}</span></span>{num}'
                         f'<ul class="items">{items}</ul></td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    month_name = MONTHS[lang][m - 1]
    agenda = "".join(
        f'<li class="ag-day" id="ag-{d.isoformat()}" data-date="{d.isoformat()}"><p class="ag-d">{esc(day_label(d, lang)[:1].upper() + day_label(d, lang)[1:])}</p><ul>'
        + "".join(f'<li class="it kd"><span class="mk" aria-hidden="true">◆</span> {esc(k[lang]["short"])}</li>' for k in kd_on(d)) + "</ul></li>"
        for d in (datetime.date(y, m, i) for i in range(1, calendar.monthrange(y, m)[1] + 1)) if kd_on(d))
    def range_label(k):
        if k["a"] == k["b"]: return day_label(k["a"], lang)
        if lang == "fr": return f"du {day_label(k['a'], 'fr')} au {day_label(k['b'], 'fr')}"
        return f"{day_label(k['a'], 'en')} to {day_label(k['b'], 'en')}"
    keys = ""
    for k in kds:
        rl = range_label(k); rl = rl[:1].upper() + rl[1:]
        srcs = " · ".join(f'<a href="{esc(s)}" rel="noopener">{esc(src_name.get(s, s))}</a>' for s in k["sources"])
        keys += (f'<li><p class="kd-when"><span class="mk" aria-hidden="true">◆</span> {esc(rl)}</p><p>{esc(k[lang]["long"])}</p>'
                 f'<p class="kd-src">{esc(T["src"])}{" :" if lang == "fr" else ":"} {srcs}</p></li>')
    checked = datetime.date.fromisoformat(site["key_dates_checked"])
    note = T["key_note"].replace("{d}", (day_label(checked, "en").split(", ")[1] + f", {checked.year}") if lang == "en" else f"{day_label(checked, 'fr')} {checked.year}")
    return (f'<section id="calView" class="calview" aria-labelledby="cal-h">'
            f'<h2 id="cal-h">{esc(T["cal_h"])}</h2>'
            f'<ul class="cal-legend"><li><span class="mk kd" aria-hidden="true">◆</span> {esc(T["legend_key"])}</li>'
            f'<li><span class="mk cev" aria-hidden="true">●</span> {esc(T["legend_ev"])}</li>'
            f'<li><span class="newb" aria-hidden="true">{esc(ui[lang]["new_events"]["badge"])}</span> {esc(T["legend_new"])}</li></ul>'
            f'<div class="cal-wrap"><table class="mcal"><caption class="vh">{esc(T["cal_caption"])}</caption><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            f'<p class="cal-after" hidden>{esc(T["after_oct"])}</p>'
            f'<div class="agenda-box"><h3>{esc(T["agenda_h"])}</h3><p class="note ag-note">{esc(T["agenda_note"])}</p><ol class="agenda">{agenda}</ol></div>'
            f'<div class="keydates-cal"><h3>{esc(T["key_h"])}</h3><ul class="kd-list">{keys}</ul><p class="note">{esc(note)}</p></div>'
            f'</section>')
