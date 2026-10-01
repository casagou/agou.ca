"""Events calendar (October 2026 month view) and 'New' events for agou.ca (build.py imports this).

- Events come from the same public rpc as the list (get_public_events), fetched at build time for the static parts
  (Events menu badge, home 'New event' line); the page itself still loads them live in forms.js, so the calendar chips stay in sync.
- data/events-added.json records when each event id was first added (seeded from campaign_events.created_at; new ids get the build day).
- An event is new for site.json events_new_days days (default 7) from that date: until = added + days (exclusive, Pacific time).
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
    if live is not None:
        for e in live:
            k = str(e["id"]); rec = store["events"].get(k)
            snap = {"title": e["title"], "starts_at": e["starts_at"], "ends_at": e["ends_at"]}
            if rec is None:
                store["events"][k] = {"added": today().isoformat(), **snap}; changed = True
                print(f"events: new event id {k} ({e['title']}) recorded as added {today()} in data/events-added.json (commit it)")
            elif any(rec.get(f) != v for f, v in snap.items()):
                rec.update(snap); changed = True
        if changed: ADDED.write_text(json.dumps(store, ensure_ascii=False, indent=2) + "\n")
        ids = {str(e["id"]) for e in live}
    else:
        ids = set(store["events"])
    out = []
    for k, r in store["events"].items():
        if k not in ids: continue
        out.append({"id": int(k), "title": r["title"], "starts_at": r["starts_at"], "ends_at": r["ends_at"],
                    "added": datetime.date.fromisoformat(r["added"])})
    out.sort(key=lambda e: (e["starts_at"], e["id"]))
    _STATE["events"] = out
    return out


def new_days(site):
    return int(site.get("events_new_days", 7))


def until(e, site):
    return e["added"] + datetime.timedelta(days=new_days(site))


def new_map(site):
    """{event id: 'YYYY-MM-DD'} = first day the event is no longer new (Pacific time). forms.js shows 'New' while today < that day."""
    return {str(e["id"]): until(e, site).isoformat() for e in events()}


def new_upcoming(site):
    now = datetime.datetime.now(datetime.timezone.utc); t = today()
    return [e for e in events() if until(e, site) > t and datetime.datetime.fromisoformat(e["ends_at"]) >= now]


def title_of(e):
    return " — ".join(p.strip() for p in e["title"].split("|"))


def nav_badge(lang, site, ui):
    """Badge after 'Events' in the main menu (desktop and mobile), while an upcoming event is new. site.js removes it once expired."""
    nu = new_upcoming(site)
    if not nu: return ""
    T = ui[lang]["new_events"]
    last_until = max(until(e, site) for e in nu).isoformat()
    last_end = max(e["ends_at"] for e in nu)
    return (f' <span class="newb nav-new" data-new-until="{last_until}" data-new-ends="{esc(last_end)}">'
            f'<span class="vh">{esc(T["nav_sr"])}</span><span aria-hidden="true">{esc(T["badge"])}</span></span>')


def home_line(lang, site, ui, events_url):
    """'New event: <title>, <date>' above the home hero: the most recently added upcoming event (+ how many more are new).
    Static: site.js hides it when that event ends or stops being new; the next build picks the next one."""
    nu = new_upcoming(site)
    if not nu: return ""
    T = ui[lang]["new_events"]
    e = sorted(nu, key=lambda x: (-x["added"].toordinal(), x["starts_at"]))[0]  # the most recently added, then the soonest
    d = datetime.datetime.fromisoformat(e["starts_at"]).astimezone(TZ).date()
    more = len(nu) - 1
    more_html = ""
    if more:
        txt = T["more_one"] if more == 1 else T["more"].replace("{n}", str(more))
        more_html = f' <span class="newev-more">· <a href="{events_url}">{esc(txt)}</a></span>'
    return (f'<div class="newev" data-new-until="{until(e, site).isoformat()}" data-new-ends="{esc(e["ends_at"])}"><div class="wrap"><p>'
            f'<span class="newb">{esc(T["line"])}</span> <a href="{events_url}?e={e["id"]}">{esc(title_of(e))}, {esc(day_label(d, lang))}</a>{more_html}</p></div></div>')


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
    cal = calendar.Calendar(firstweekday=6)  # Sunday first (Canadian convention)
    head = "".join(f'<th scope="col"><abbr title="{esc(DAYS[lang][i])}">{esc(DAYS_ABBR[lang][i])}</abbr></th>' for i in range(7))
    rows = []
    for week in cal.monthdatescalendar(y, m):
        cells = []
        for d in week:
            if d.month != m:
                cells.append('<td class="out" aria-hidden="true"></td>'); continue
            ks = kd_on(d); iso = d.isoformat()
            items = "".join(f'<li class="it kd"><span class="mk" aria-hidden="true">◆</span><span class="tx">{esc(k[lang]["short"])}</span></li>' for k in ks)
            num = (f'<a class="dn dn-link" href="#ag-{iso}"><span class="vh">{esc(day_label(d, lang))}</span><span aria-hidden="true">{d.day}</span></a>' if ks else "")
            cells.append(f'<td class="day{" has-kd" if ks else ""}" data-date="{iso}">'
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
