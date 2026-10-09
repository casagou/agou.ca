#!/usr/bin/env python3
"""Word-for-word check: every line of Notion text (notion-raw/*.txt) must appear verbatim in the built page,
and every external link in Notion must be an href on that page. Lines removed on purpose (exclusions.json) are
listed separately. Usage: python3 tools/diffcheck.py [dist]"""
import re, sys, json, pathlib, html
from html.parser import HTMLParser
ROOT = pathlib.Path(__file__).resolve().parent.parent
dist = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist"
SITE = json.loads((ROOT / "site.json").read_text())
EXCL = json.loads((ROOT / "exclusions.json").read_text())["rules"]
# Party links (2 Oct 2026): build.py PARTY_MD rewrites these Notion lines on staging (and on live once site.json party_links_live is true)
sys.path.insert(0, str(ROOT)); _argv = sys.argv; sys.argv = ["build.py"]
import build as _build  # noqa: E402
sys.argv = _argv
PARTY_ON = _build.PARTY_ON("staging" if "--live" not in sys.argv else "live")
PARTY_MD = _build.PARTY_MD
# Staging drafts (staging-drafts.json): a draft that is on for this env (always on staging; on live only with its site.json live_flag)
# rewrites the Notion lines named in its 'find' texts on purpose. Finds shorter than 12 characters never excuse a line.
DENV = "staging" if "--live" not in sys.argv else "live"
DRAFT_FINDS = {}
for _n, _d in _build.DRAFTS.items():
    if not _build.DRAFT_ON(_n, DENV): continue
    for _pk, _eds in _d["edits"].items():
        for _f, _r in _eds:
            DRAFT_FINDS.setdefault(_pk.replace("/", "-"), []).append((_n, _f, _r))
# No-party version (site.json no_party_v1, 8 Oct 2026): no_party.py removes or rewrites party text on purpose. The excused lines
# and links are exactly the ones that differ between read() with the flag off and on (PARTY links are off in that version).
import no_party as _np  # noqa: E402
NP = _np.NP_ON(DENV, SITE)
# Events / Get involved hidden (site.json hide_events_getinvolved_v1, Joachim 8 Oct 2026 6:00 PM PT): build.py HIDE_EG_EDITS drop their home / FAQ sections
HEG = bool(SITE.get("hide_events_getinvolved_v1")) and (DENV == "staging" or bool(SITE.get("hide_events_getinvolved_v1_live")))
NP_GONE, NP_LINKS = {}, {}
if NP or HEG:
    PARTY_ON = PARTY_ON and not NP
    _build.DRAFT_ENV["env"] = DENV
    _LNK = r"\]\((https?://[^)\s]+)\)"
    for _raw in sorted((ROOT / "notion-raw").glob("*.txt")):
        _lang, _key = _raw.stem.split("-", 1)
        _np.ON["on"] = False; _build.HIDE_EG["on"] = False; _b = _build.read(_lang, _key)
        _np.ON["on"] = NP; _build.HIDE_EG["on"] = HEG; _a = _build.read(_lang, _key)
        if _b is None: continue
        _al = set(_a.split("\n"))
        NP_GONE[_raw.stem] = [l for l in _b.split("\n") if l not in _al]
        NP_LINKS[_raw.stem] = set(re.findall(_LNK, _b)) - set(re.findall(_LNK, _a))
    _np.ON["on"] = False; _build.HIDE_EG["on"] = False
BLOCK = {"p", "li", "h1", "h2", "h3", "figcaption", "summary", "div", "section", "br", "td", "a"}

class T(HTMLParser):
    def __init__(s): super().__init__(); s.buf = []; s.skip = 0; s.hrefs = []
    def handle_starttag(s, t, a):
        if t in ("script", "style"): s.skip += 1
        if t == "a": s.hrefs.append(dict(a).get("href", ""))
        if t in BLOCK and t != "a": s.buf.append("\n")
    def handle_endtag(s, t):
        if t in ("script", "style"): s.skip -= 1
        if t in BLOCK and t != "a": s.buf.append("\n")
    def handle_data(s, d):
        if not s.skip: s.buf.append(d)

def page_text(path):
    t = T(); t.feed(path.read_text())
    txt = re.sub(r"[ \t\u00a0]+", " ", "".join(t.buf))
    return re.sub(r"\s+", " ", txt), t.hrefs

def plain(line):
    s = line.strip()
    if not s or s == "---" or s.startswith(("<callout", "</callout", "<details", "</details", "<table_of_contents", "<pdf")): return None
    s = re.sub(r"</?summary>", "", s); s = re.sub(r"</?span[^>]*>", "", s)
    m = re.match(r'<page url="[^"]+">(.*)</page>', s)
    if m: return m.group(1)
    m = re.match(r"!\[(.*)\]\(", s)
    if m: return m.group(1)
    s = re.sub(r'<mention-page url="[^"]+"/>', "", s)
    s = re.sub(r"^#+ ", "", s); s = re.sub(r"^- ", "", s)
    s = re.sub(r"\s*\{color=\"[a-z_]+\"\}", "", s)
    s = re.sub(r"^\[\*\*→\s*", "[**", s)  # leading arrow on Notion call-to-action lines is presentational (site buttons have no leading arrow)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = s.replace("**", "").replace("\\$", "$").replace("\\[", "[").replace("\\]", "]")
    s = re.sub(r"(?<!\w)\*|\*(?!\w)", "", s)
    return re.sub(r"\s+", " ", s).strip()

TARGET = {"home": "", "about": "about/", "priorities": "priorities/", "media": "media/", "faq": "faq/"}
removed_lines = set()
for r in EXCL:
    for l in r["find"].split("\n"):
        p = plain(l)
        if p: removed_lines.add((r["page"], p))
total = 0; problems = []; excluded = []
# site.json nominations_closed (30 Sep 2026): the home nominator callout, the "Become a nominator" section and the
# "75 nominators" source are left out on purpose (build.py); Notion still has them
NOM_HEADS = {"Become a nominator", "Appuyer ma candidature", "Signer mon formulaire de mise en candidature"}  # Notion heading (FR renamed by exclusions.json)
def nominate_lines(name, text):
    if not SITE.get("nominations_closed") or not name.endswith("-home"): return set()
    out = set(); lang = name[:2]; ls = text.split("\n")
    i = next((k for k, l in enumerate(ls) if l.startswith("## ") and plain(l) in NOM_HEADS), None)
    if i is not None:
        j = next((k for k in range(i + 1, len(ls)) if ls[k].startswith("## ")), len(ls))
        out |= {plain(l) for l in ls[i:j] if plain(l)}
    c0 = next((k for k, l in enumerate(ls) if l.strip().startswith("<callout")), None)
    if c0 is not None:
        c1 = next(k for k in range(c0, len(ls)) if ls[k].strip().startswith("</callout"))
        out |= {plain(l) for l in ls[c0:c1 + 1] if plain(l)}
    return out
for raw in sorted((ROOT / "notion-raw").glob("*.txt")):
    name = raw.stem; lang, key = name.split("-", 1)
    text = raw.read_text()
    lines = text.split("\n")
    if "---" in lines[:6]: lines = lines[lines.index("---") + 1:]
    body = "\n".join(lines)
    m = re.search(r"\n---\n## (Contact|Coordonnées)|\n---\n(?=\*(Authorized|Autorisé) )", body)
    main_part, contact = (body[:m.start()], body[m.end():]) if m else (body, "")
    page = dist / ("fr/" if lang == "fr" else "") / TARGET[key] / "index.html"
    ptxt, hrefs = page_text(page)
    for l in main_part.split("\n"):
        p = plain(l)
        if not p: continue
        total += 1
        if p in ptxt: continue
        if p in nominate_lines(name, text):
            excluded.append(f"{name}: {p[:110]!r}  -> nominations complete (site.json nominations_closed)"); continue
        if p.startswith(("Sources", "Sources (en anglais)")) and SITE.get("nominations_closed") and re.sub(r"\s*·\s*(75 nominators|75 signataires)[^·]*$", "", p) in ptxt:
            excluded.append(f"{name}: hero sources without the '75 nominators' source  -> nominations complete (site.json nominations_closed)"); continue
        mi = re.match(r"!\[.*\]\((\S+?)(\?[^)]*)?\)$", l.strip())
        if mi and SITE["images"].get(mi.group(1).rsplit("/", 1)[-1]) == "riding-map" and 'class="map-card"' in page.read_text():
            excluded.append(f"{name}: riding map image -> replaced by the site's own map card (tools/make_map.py), same boundary, with its own alt text and attribution"); continue
        # excluded on purpose? (whole line, or the line with the excluded part removed)
        hit = [r for r in EXCL if r["page"] in (name, "*") and any(plain(fl) and (plain(fl) in p or p == plain(fl)) for fl in r["find"].split("\n"))]
        if not hit and PARTY_ON:
            pm = [f for f, _ in PARTY_MD.get((lang, key), []) for fl in f.split("\n") if plain(fl) and plain(fl) in p]
            if pm:
                excluded.append(f"{name}: {p[:110]!r}  -> party links (2 Oct 2026): rewritten by build.py PARTY_MD"); continue
        if not hit:
            dm = [n_ for n_, f_, _ in DRAFT_FINDS.get(name, []) for fl in f_.split("\n") if plain(fl) and len(plain(fl)) >= 12 and plain(fl) in p]
            if dm:
                excluded.append(f"{name}: {p[:110]!r}  -> staging draft {dm[0]} (staging-drafts.json, live only with site.json {_build.DRAFTS[dm[0]]['live_flag']})"); continue
        if not hit and (NP or HEG) and any(p in (plain(g) or "\x00") for g in NP_GONE.get(name, [])):
            excluded.append(f"{name}: {p[:110]!r}  -> no-party version / hidden Events + Get involved (no_party.py, build.py HIDE_EG_EDITS)"); continue
        if hit:
            excluded.append(f"{name}: {p[:110]!r}  -> {hit[0]['why']}")
        else:
            problems.append(f"{name} ({page.relative_to(dist)}): NOT FOUND: {p[:140]!r}")
    for u in re.findall(r"\]\((https?://[^)\s]+)\)", main_part):
        if "notion.com" in u or "agou.ca" in u or "prod-files-secure" in u: continue
        if u not in hrefs:
            if any(r["page"] in (name, "*") and u in r["find"] and u not in r["replace"] for r in EXCL):
                excluded.append(f"{name}: link {u} replaced on purpose (exclusions.json)"); continue
            if u in NP_LINKS.get(name, set()):
                excluded.append(f"{name}: link {u} removed on purpose (no-party version)"); continue
            dl = [n_ for n_, f_, r_ in DRAFT_FINDS.get(name, []) if u in f_ and u not in r_]
            if dl:
                excluded.append(f"{name}: link {u} replaced on purpose (staging draft {dl[0]})"); continue
            problems.append(f"{name}: link missing on page: {u}")
    # contact block (every page footer)
    for l in contact.split("\n"):
        p = plain(l)
        if p == "Instagram · X · Facebook":  # shown as three labelled buttons; check the links instead
            for u in re.findall(r"\((https://[^)]+)\)", l):
                if u not in hrefs: problems.append(f"{name}: social link missing: {u}")
            continue
        if p and p not in ptxt:
            hit = [r for r in EXCL if r["page"] == f"{name}:contact" and plain(r["find"]) and plain(r["find"]) in p]
            if hit: excluded.append(f"{name}: contact {p[:80]!r}  -> {hit[0]['why']}"); continue
            problems.append(f"{name}: contact line not in footer: {p[:100]!r}")
print(f"Checked {total} Notion lines.")
print("Intentional differences (exclusions.json):"); print("\n".join("  " + e for e in excluded) or "  none")
print("Unexpected differences:"); print("\n".join("  " + p for p in problems) or "  none")
sys.exit(1 if problems else 0)
