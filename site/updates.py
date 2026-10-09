"""'Updates' / « Nouvelles » (6 Oct 2026, Joachim via Provincial Campaign Ops; first built as 'On the campaign trail').

Each entry mirrors one of Joachim's daily social posts (Instagram, Facebook, X), added by hand: site/data/updates.json
("entries"; format in README "Updates"). Photos Joachim provides go in site/data/updates/ (JPEG). tools/make_updates.py (or any
local build with Pillow) strips their metadata and writes assets/img/updates/<stem>-<width>.{webp,jpg} (4:3, sRGB, no
EXIF/GPS) plus assets/img/updates/index.json; commit those files (the CI build has no Pillow and only checks them).
No embeds, no third-party scripts: titles, text, photos and plain links to the posts.

With zero entries nothing of it is built: no home section, no follow buttons, no /updates/ page, no link (build.py puts
"updates" in HIDDEN). Staging, while there are no real entries, shows the SAMPLE entries from data/updates-samples.json
(existing licensed Victoria photos) when site.json updates.samples_on_staging is true; live never does (build check).
"""
import hashlib, html, json, pathlib, re, sys
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "data" / "updates"            # originals (JPEG, metadata stripped by make_images)
OUT = ROOT / "assets" / "img" / "updates"  # web sizes (committed)
MANIFEST = OUT / "index.json"
WIDTHS = (320, 640, 960, 1280)
ASPECT = (4, 3)
Q = {"webp": 72, "jpg": 78}
MAX_SRC = 2400                 # px, long edge of the stripped original kept in the (public) repo
LIM = {"title": 90, "body": 280, "place": 60, "alt": 160}
MAX_IMAGES = 4
PAGE_SUFFIX = " – Joachim Agou"  # permalink <title> suffix: short, so up to 55 characters of the entry title fit in 70
HOME_BODY = {"photo": 110, "text": 200}  # home strip excerpt length (characters): under a photo, and on a navy text card
PLATFORMS = {"instagram": ("Instagram", ("instagram.com",)), "facebook": ("Facebook", ("facebook.com", "fb.com", "fb.watch")),
             "x": ("X", ("x.com", "twitter.com"))}
MON = {"en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
       "fr": ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juill.", "août", "sept.", "oct.", "nov.", "déc."]}
MONTHS = {"en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
          "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]}
RULES = r"\bJoa\b|the candidate|le candidat|Thales|\bACTW\b|(?i:lawn signs? (?:are |is )?free|free lawn sign|pancartes? gratuites?)"
esc = lambda s: html.escape(s, quote=True)
STATE = {"entries": [], "sample": False}


# ---------------- data ----------------
def _read(name):
    f = ROOT / "data" / name
    return json.loads(f.read_text()).get("entries", []) if f.exists() else []


def images(e):
    """The entry's photos as dicts {file|vic, focus, alt_en, alt_fr}; 'image' (one file name) still works."""
    raw = list(e.get("images") or []) + ([e["image"]] if e.get("image") else [])
    return [({"file": x} if isinstance(x, str) else dict(x)) for x in raw]


def link_ok(platform, url):
    if platform not in PLATFORMS: return f"platform must be one of {', '.join(PLATFORMS)}"
    u = urlsplit(str(url))
    if u.scheme != "https" or not u.hostname: return "url must start with https://"
    host = u.hostname.lower()
    if not any(host == d or host.endswith("." + d) for d in PLATFORMS[platform][1]):
        return f"url host {host} is not {' / '.join(PLATFORMS[platform][1])}"
    return ""


def _real_date(d):
    import datetime
    try: datetime.date.fromisoformat(d); return True
    except ValueError: return False


def validate(entries, where):
    errs = []
    for i, e in enumerate(entries):
        tag = f"{where} entry {i + 1}"
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(e.get("date", ""))) or not _real_date(e["date"]): errs.append(f"{tag}: date is required, a real YYYY-MM-DD date")
        if not str(e.get("title_en", "")).strip(): errs.append(f"{tag}: title_en is required")
        unknown = set(e) - {"date", "slug", "title_en", "title_fr", "body_en", "body_fr", "links", "images", "image", "place", "place_fr", "alt_en", "alt_fr", "sample", "_note"}
        if e.get("slug") is not None and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(e["slug"])) or len(str(e.get("slug") or "")) > 60:
            errs.append(f"{tag}: slug must be lowercase ASCII letters, digits and single hyphens (max 60), without the date")
        if unknown: errs.append(f"{tag}: unknown field(s) {', '.join(sorted(unknown))}")
        for k, lim in (("title_en", "title"), ("title_fr", "title"), ("body_en", "body"), ("body_fr", "body"), ("place", "place"), ("place_fr", "place"), ("alt_en", "alt"), ("alt_fr", "alt")):
            v = str(e.get(k) or "")
            if len(v) > LIM[lim]: errs.append(f"{tag}: {k} is {len(v)} characters (max {LIM[lim]})")
            if re.search(RULES, v): errs.append(f"{tag}: {k} breaks a site rule (Joa / the candidate / Thales / ACTW / 'free' lawn signs)")
        links = e.get("links") or []
        if not isinstance(links, list): errs.append(f"{tag}: links must be a list"); links = []
        for j, l in enumerate(links):
            bad = link_ok(str((l or {}).get("platform", "")).lower(), (l or {}).get("url", "")) if isinstance(l, dict) else "must be {\"platform\": ..., \"url\": ...}"
            if bad: errs.append(f"{tag}: links[{j + 1}] {bad}")
        ims = images(e)
        if len(ims) > MAX_IMAGES: errs.append(f"{tag}: {len(ims)} photos (max {MAX_IMAGES})")
        for j, im in enumerate(ims):
            t2 = f"{tag}: photo {j + 1}"
            if e.get("sample"):
                if not im.get("vic"): errs.append(f"{t2}: a sample photo needs 'vic' (a site.json victoria_photos id)")
            else:
                f = str(im.get("file", ""))
                if not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.jpe?g", f): errs.append(f"{t2}: file must be a lowercase .jpg name (letters, digits, hyphens) in data/updates/")
                elif not (SRC / f).exists(): errs.append(f"{t2}: data/updates/{f} not found")
            fo = im.get("focus")
            if fo is not None and not (isinstance(fo, list) and len(fo) == 2 and all(isinstance(x, (int, float)) and 0 <= x <= 1 for x in fo)):
                errs.append(f"{t2}: focus must be [x, y], fractions 0-1 (crop centre)")
            for k in ("alt_en", "alt_fr"):
                if len(str(im.get(k) or "")) > LIM["alt"]: errs.append(f"{t2}: {k} is too long (max {LIM['alt']})")
                if re.search(RULES, str(im.get(k) or "")): errs.append(f"{t2}: {k} breaks a site rule (Joa / the candidate / Thales / ACTW / 'free' lawn signs)")
    return errs


def stem(im):
    return ("sample-" + im["vic"]) if im.get("vic") else re.sub(r"\.jpe?g$", "", im["file"])


def load(env, site, vic_photos):
    """Entries to show in this build, newest first (same date: later in the file first). Each gets a stable anchor id."""
    real = _read("updates.json")
    errs = validate(real, "data/updates.json")
    entries, sample = real, False
    if not real and env == "staging" and site.get("updates", {}).get("samples_on_staging"):
        entries, sample = _read("updates-samples.json"), True
        errs += validate(entries, "data/updates-samples.json")
        errs += [f"data/updates-samples.json: unknown victoria photo {im['vic']!r}" for e in entries for im in images(e) if im.get("vic") not in vic_photos]
    if errs: sys.exit("updates:\n  " + "\n  ".join(errs))
    slugs = {}
    for e in entries:  # permalink /updates/<date>-<slug>/ (slug field, else from title_en); must be unique
        e["_slug"] = f"{e['date']}-{e.get('slug') or slugify(e['title_en'])}"
        slugs.setdefault(e["_slug"], []).append(e["title_en"])
    dup = [k for k, v in slugs.items() if len(v) > 1]
    if dup: sys.exit("updates: two entries share a permalink (" + ", ".join(dup) + "); give one of them a different 'slug'")
    entries = [e for _, e in sorted(enumerate(entries), key=lambda ie: (ie[1]["date"], ie[0]), reverse=True)]
    STATE["entries"], STATE["sample"] = entries, sample
    return entries


def slugify(t):
    """ASCII, lowercase, hyphens; at most 50 characters, cut at a hyphen."""
    import unicodedata
    a = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower().replace("'", "").replace("’", "")
    a = re.sub(r"[^a-z0-9]+", "-", a).strip("-") or "update"
    return a if len(a) <= 50 else a[:50].rsplit("-", 1)[0]


def all_images(entries):
    return [im for e in entries for im in images(e)]


# ---------------- images ----------------
def _sha(b): return hashlib.sha256(b).hexdigest()[:16]


def jpeg_has_metadata(path):
    """True if the JPEG has an APP1 (EXIF/XMP, where GPS lives) or APP13 (IPTC) segment. No Pillow needed (CI)."""
    b = path.read_bytes(); i = 2
    if b[:2] != b"\xff\xd8": return True
    while i + 4 <= len(b) and b[i] == 0xFF:
        m = b[i + 1]
        if m in (0xD9, 0xDA): break
        if m in (0xE1, 0xED): return True
        i += 2 + int.from_bytes(b[i + 2:i + 4], "big")
    return False


def _key(im, vic_photos):
    if im.get("vic"):
        P = vic_photos[im["vic"]]
        return _sha(json.dumps([P.get("source_url"), P.get("blur"), im.get("focus")]).encode())
    return _sha((SRC / im["file"]).read_bytes() + json.dumps(im.get("focus")).encode())


def _crop(im, focus):
    W, H = im.size; aw, ah = ASPECT
    cw, ch = (W, round(W * ah / aw)) if W * ah / aw <= H else (round(H * aw / ah), H)
    fx, fy = focus or (0.5, 0.5)
    x = min(max(round(fx * W - cw / 2), 0), W - cw); y = min(max(round(fy * H - ch / 2), 0), H - ch)
    return im.crop((x, y, x + cw, y + ch))


def _sample_source(im, vic_photos):
    """SAMPLE photos only: the licensed Commons original of a site.json victoria_photos id, with its 'blur' boxes applied."""
    sys.path.insert(0, str(ROOT / "tools"))
    import make_vic_photos as mv
    P = vic_photos[im["vic"]]; orig = pathlib.Path("/tmp/vic-photos-orig"); orig.mkdir(exist_ok=True)
    return mv.blur(mv.original(im["vic"], P["source_url"], orig), P.get("blur"))


def make_images(ims, vic_photos, force=False):
    """Strip metadata from originals and write the web sizes for every photo whose outputs are missing or stale."""
    from PIL import Image, ImageCms, ImageOps
    import io
    man = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    OUT.mkdir(parents=True, exist_ok=True); done = []
    for im in ims:
        s = stem(im)
        if not im.get("vic"):
            src = SRC / im["file"]
            if jpeg_has_metadata(src):  # phone photos carry GPS: re-save the original without any metadata (orientation applied)
                p = ImageOps.exif_transpose(Image.open(src)); icc = p.info.get("icc_profile")
                if icc: p = ImageCms.profileToProfile(p, ImageCms.ImageCmsProfile(io.BytesIO(icc)), ImageCms.createProfile("sRGB"), outputMode="RGB")
                p = p.convert("RGB"); p.thumbnail((MAX_SRC, MAX_SRC), Image.LANCZOS)
                p.save(src, "JPEG", quality=92, optimize=True, progressive=True)
                print(f"updates: stripped metadata from data/updates/{im['file']}")
        key = _key(im, vic_photos); have = man.get(s, {})
        if not force and have.get("key") == key and all((OUT / f"{s}-{w}.{x}").exists() for w in have.get("widths", []) for x in Q):
            continue
        p = _sample_source(im, vic_photos) if im.get("vic") else ImageOps.exif_transpose(Image.open(SRC / im["file"])).convert("RGB")
        p = _crop(p, im.get("focus"))
        widths = [w for w in WIDTHS if w <= p.size[0]] or [p.size[0]]
        for old in OUT.glob(f"{s}-*"): old.unlink()
        for w in widths:
            r = p.resize((w, round(w * ASPECT[1] / ASPECT[0])), Image.LANCZOS)
            r.save(OUT / f"{s}-{w}.webp", "WEBP", quality=Q["webp"], method=6)
            r.save(OUT / f"{s}-{w}.jpg", "JPEG", quality=Q["jpg"], optimize=True, progressive=True)
        man[s] = {"key": key, "widths": widths}; done.append(s)
        MANIFEST.write_text(json.dumps(dict(sorted(man.items())), indent=1) + "\n")  # after each photo: an interrupted run keeps its work
    MANIFEST.write_text(json.dumps(dict(sorted(man.items())), indent=1) + "\n")
    return done


def ensure_images(entries, vic_photos):
    """Build step: web sizes must exist and match their photo. With Pillow (local) stale ones are regenerated;
    without it (CI) the build stops and says to run tools/make_updates.py and commit."""
    man = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    stale = []
    for im in all_images(entries):
        s = stem(im); have = man.get(s)
        if not im.get("vic") and jpeg_has_metadata(SRC / im["file"]): stale.append(f"data/updates/{im['file']} still has EXIF/GPS metadata"); continue
        if not have or not all((OUT / f"{s}-{w}.{x}").exists() for w in have["widths"] for x in Q): stale.append(f"{s}: web sizes missing"); continue
        if not im.get("vic") and have["key"] != _key(im, vic_photos): stale.append(f"{s}: photo or focus changed")
    if not stale: return
    try:
        import PIL  # noqa: F401
    except ImportError:
        sys.exit("updates: " + "; ".join(stale) + ". Run tools/make_updates.py locally (needs Pillow) and commit data/updates/ and assets/img/updates/.")
    make_images(all_images(entries), vic_photos)


# ---------------- rendering ----------------
def pick(e, k, lang):
    return str((e.get(f"{k}_fr") or e.get(f"{k}_en") or "") if lang == "fr" else (e.get(f"{k}_en") or "")).strip()


def title(e, lang, T):
    return (T["sample_tag"] if e.get("sample") else "") + pick(e, "title", lang)


def place(e, lang):
    return str(((e.get("place_fr") or e.get("place")) if lang == "fr" else e.get("place")) or "").strip()


def short_date(d, lang, year=None):
    y, m, dd = map(int, d.split("-")); yr = "" if year in (None, y) else f" {y}"
    if lang == "fr": return f"{'1er' if dd == 1 else dd}\u00a0{MON['fr'][m - 1]}{yr}"  # no-break space: « 5 oct. » never splits
    return f"{MON['en'][m - 1]}\u00a0{dd}" + (f", {y}" if yr else "")


def long_date(d, lang):
    y, m, dd = map(int, d.split("-"))
    if lang == "fr": return f"{'1er' if dd == 1 else dd}\u00a0{MONTHS['fr'][m - 1]} {y}"
    return f"{MONTHS['en'][m - 1]}\u00a0{dd}, {y}"


def clip(s, n):
    """Shorten to n characters at a word boundary, with an ellipsis (never mid-word, no dangling punctuation)."""
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) <= n: return s
    cut = s[:n - 1].rsplit(" ", 1)[0] if " " in s[:n - 1] else s[:n - 1]
    return cut.rstrip(" ,;:–—-.") + "…"


def alt(e, im, k, n, lang):
    a = pick(im, "alt", lang) or pick(e, "alt", lang)
    return a or pick(e, "title", lang) + (f" ({k}/{n})" if n > 1 else "")


def web_sizes(im):
    return json.loads(MANIFEST.read_text())[stem(im)]["widths"]


def picture(B, im, sizes, alt_text, eager=False):
    s = stem(im); widths = web_sizes(im)
    f = lambda w, x: f"/assets/img/updates/{s}-{w}.{x}"
    ss = lambda x: ", ".join(f"{f(w, x)} {w}w" for w in widths)
    W = widths[-1]; H = round(W * ASPECT[1] / ASPECT[0])
    if im.get("vic") and im["vic"] not in B.PAGE_STATE["vic_used"]: B.PAGE_STATE["vic_used"].append(im["vic"])  # licence credit in the footer
    load = 'fetchpriority="high"' if eager else 'loading="lazy"'
    return (f'<picture><source type="image/webp" srcset="{ss("webp")}" sizes="{sizes}">'
            f'<img src="{f(widths[min(1, len(widths) - 1)], "jpg")}" srcset="{ss("jpg")}" sizes="{sizes}" width="{W}" height="{H}" alt="{esc(alt_text)}" {load} decoding="async"></picture>')


def follow(B, lang):
    T = B.UI[lang]["updates"]
    items = "".join(f'<li><a href="{esc(u)}" rel="me noopener">{B.ICONS[n]}<span>{esc(n)}</span></a></li>' for n, u in B.SITE["updates"]["follow"].items())
    return f'<div class="upd-follow"><h3>{esc(T["follow"])}</h3><ul class="social" aria-label="{esc(T["follow"])}">{items}</ul></div>'


def _sample_note(B, lang):
    return f'<p class="draft-tag">{esc(B.UI[lang]["updates"]["sample_note"])}</p>' if STATE["sample"] else ""


def meta(e, lang, short=True, year=None):
    d = short_date(e["date"], lang, year) if short else long_date(e["date"], lang)
    p = place(e, lang)
    return f'<time datetime="{e["date"]}">{esc(d)}</time>' + (f' · {esc(p)}' if p else "")


def key(e): return "u:" + e["_slug"]


def permalink(B, lang, e): return B.url(lang, key(e))


def body_html(e, lang):
    b = pick(e, "body", lang)
    return f'<p class="upd-body">{"<br>".join(esc(x) for x in b.split(chr(10)))}</p>' if b else ""


def photos_html(B, e, lang, eager=False):
    ims = images(e); n = len(ims)
    if not n: return ""
    grid = "".join(f'<li>{picture(B, im, photo_sizes(n, k), alt(e, im, k + 1, n, lang), eager and k == 0)}</li>' for k, im in enumerate(ims))
    return f'<ul class="upd-photos n{n}">{grid}</ul>'


def photo_sizes(n, k):
    """Photo layouts (site.css .upd-photos.nN; reading column max 720px): 1 = one photo; 2 = side by side;
    3 = one large + two small (phones: large on top, two small side by side under it); 4 = 2x2."""
    if n == 1: return "(min-width: 760px) 720px, calc(100vw - 36px)"
    if n == 3: return ("(min-width: 760px) 476px, (min-width: 600px) calc((100vw - 48px) * 2 / 3), calc(100vw - 36px)" if k == 0
                       else "(min-width: 760px) 234px, (min-width: 600px) calc((100vw - 48px) / 3), calc((100vw - 48px) / 2)")
    return "(min-width: 760px) 354px, calc((100vw - 48px) / 2)"


def home_section(B, lang):
    """Home strip under the priorities: the latest entries (site.json updates.home_max) as cards (first photo, or a navy
    text card for text-only posts), each with date, title, the start of the text and 'Read more' to its permalink."""
    E = STATE["entries"]
    if not E: return ""
    T = B.UI[lang]["updates"]; n = min(len(E), int(B.SITE["updates"].get("home_max", 4))); yr = int(E[0]["date"][:4])
    cap = {1: 360, 2: 600, 3: 840}.get(n, 1084)  # row width cap from 800px (site.css .upd-list.nN)
    sizes = f"(min-width: 1120px) {(cap - 16 * (n - 1)) // n}px, (min-width: 800px) min({(cap - 16 * (n - 1)) // n}px, calc((100vw - 36px - {16 * (n - 1)}px) / {n})), {80 if n == 1 else 72}vw"
    cards = []
    for e in E[:n]:
        ims = images(e); b = pick(e, "body", lang)
        ex = clip(b, HOME_BODY["photo"] if ims else HOME_BODY["text"]) if b else ""
        media = (f'<div class="upd-media">{picture(B, ims[0], sizes, alt(e, ims[0], 1, len(ims), lang))}'
                 + (f'<span class="upd-more" aria-hidden="true">+{len(ims) - 1}</span>' if len(ims) > 1 else "") + "</div>") if ims else ""
        cards.append(f'<li class="upd-card{"" if ims else " upd-textcard"}">{media}<div class="upd-cb"><p class="upd-m">{meta(e, lang, True, yr)}</p>'
                     f'<h3 class="upd-t">{esc(title(e, lang, T))}</h3>' + (f'<p class="upd-ex">{esc(ex)}</p>' if ex else "")
                     + f'<p class="readlink"><a href="{permalink(B, lang, e)}">{esc(T["read_more"])}<span class="vh">: {esc(pick(e, "title", lang))}</span> <span aria-hidden="true">→</span></a></p></div></li>')
    return (f'<section class="block updates" aria-labelledby="updates">{_sample_note(B, lang)}<h2 id="updates">{esc(T["title"])}</h2>'
            f'<div class="upd-strip" role="region" aria-labelledby="updates" tabindex="0"><ul class="upd-list n{n}">{"".join(cards)}</ul></div>'
            f'<p class="pagelink"><a href="{B.url(lang, "updates")}">{esc(T["see_all"])} <span aria-hidden="true">→</span></a></p>{follow(B, lang)}</section>')


SKIP_URLS = set()  # build.py: links left out (hidden personal social accounts)


def links_html(e, T):
    out = []
    for l in e.get("links") or []:
        if l["url"].rstrip("/").lower() in SKIP_URLS: continue
        name = PLATFORMS[l["platform"].lower()][0]
        out.append(f'<li><a class="btn sec" href="{esc(l["url"])}" target="_blank" rel="noopener">{esc(T["see_on"].format(platform=name))} <span aria-hidden="true">↗</span><span class="vh"> {esc(T["new_tab"])}</span></a></li>')
    return f'<ul class="upd-links">{"".join(out)}</ul>' if out else ""


def rss_link(B, lang):
    T = B.UI[lang]["updates"]
    return f'<link rel="alternate" type="application/rss+xml" title="{esc(T["feed_title"])}" href="{B.url(lang, "updates")}feed.xml">\n'


def page(B, lang, pg, env):
    """/updates/: the feed, newest first; each title links to its permalink."""
    E = STATE["entries"]
    if not E: sys.exit("updates: /updates/ was built with no entries (it must be in HIDDEN)")
    T = B.UI[lang]["updates"]; arts = []
    for e in E:
        cls = "upd-entry" + ("" if images(e) else " upd-textcard")
        arts.append(f'<article class="{cls}" id="{e["_slug"]}" aria-labelledby="{e["_slug"]}-t"><p class="upd-m">{meta(e, lang, False)}</p>'
                    f'<h2 id="{e["_slug"]}-t"><a href="{permalink(B, lang, e)}">{esc(title(e, lang, T))}</a></h2>'
                    f'{body_html(e, lang)}{photos_html(B, e, lang)}{links_html(e, T)}</article>')
    body = (f'<section class="block updates updates-all" aria-labelledby="updates-h">{_sample_note(B, lang)}<p class="vh" id="updates-h">{esc(T["title"])}</p>'
            f'<p class="upd-intro">{esc(T["intro"])}</p><div class="upd-feed">{"".join(arts)}</div>{follow(B, lang)}'
            f'<p class="upd-rss"><a href="{B.url(lang, "updates")}feed.xml" type="application/rss+xml">{esc(T["rss"])}</a></p></section>')
    main = (f'<div class="page-head"><div class="wrap"><h1>{esc(T["title"])}</h1></div></div>'
            f'<div class="wrap content updates-content">{body}{B.updated_for(lang, "updates")}</div>')
    return B.shell(lang, pg, f'{T["title"]} – Joachim Agou', T["intro"], main, env, extra_head=rss_link(B, lang))


def page_suffix(e, lang):
    """PAGE_SUFFIX, or on a French page whose title is the English one (no title_fr) « – Nouvelles – Joachim Agou », so EN and FR titles stay unique."""
    return " – Nouvelles" + PAGE_SUFFIX if lang == "fr" and pick(e, "title", "fr") == pick(e, "title", "en") else PAGE_SUFFIX


def page_title(B, e, lang):
    """<title> without suffix: the entry title cut to fit 70 characters with page_suffix(); the date is added if two entries share a title."""
    T = B.UI[lang]["updates"]; suf = page_suffix(e, lang); t = title(e, lang, T)
    if sum(1 for x in STATE["entries"] if title(x, lang, T) == t) > 1: t = f"{t} ({short_date(e['date'], lang)})"
    return clip(t, 70 - len(suf))


def page_desc(B, e, lang):
    """meta description (100-170 characters): the text, else the title, plus a plain line about the campaign when short.
    A French page that would repeat the English description (no body_fr) starts with the French campaign line instead."""
    T = B.UI[lang]["updates"]; b = pick(e, "body", lang) or pick(e, "title", lang)
    d = clip(b, 165)
    if len(d) < 100: d = clip(f"{d.rstrip('.…')}. {T['desc_tail']} ({long_date(e['date'], lang)})", 170)
    if len(d) < 100: d = clip(f"{d} {T['intro']}", 170)
    if lang == "fr" and d == page_desc(B, e, "en"): d = clip(f"{T['desc_tail']} {b}", 170)
    return d


def permalink_page(B, lang, pg, env):
    """/updates/<date>-<slug>/: one update, with its own title, description, Open Graph image and canonical URL."""
    e = pg["_entry"]; T = B.UI[lang]["updates"]; ims = images(e)
    allp = B.url(lang, "updates")
    if ims:
        w = web_sizes(ims[0])[-1]
        pg["og"] = {"path": f"/assets/img/updates/{stem(ims[0])}-{w}.jpg", "w": w, "h": round(w * ASPECT[1] / ASPECT[0]),
                    "alt": alt(e, ims[0], 1, len(ims), lang), "type": "image/jpeg", "og_type": "article"}
    else:
        pg["og"] = {"og_type": "article"}
    art = (f'<article class="upd-entry upd-single{"" if ims else " upd-textcard"}" aria-labelledby="pg-title"><p class="upd-m">{meta(e, lang, False)}</p>'
           f'{body_html(e, lang)}{photos_html(B, e, lang, eager=True)}{links_html(e, T)}</article>')
    body = (f'<section class="block updates updates-one" aria-labelledby="pg-title">{_sample_note(B, lang)}'
            f'<p class="upd-back"><a href="{allp}">{esc(T["all"])}</a></p>{art}'
            f'<p class="pagelink upd-allbottom"><a href="{allp}">{esc(T["all"])} <span aria-hidden="true">→</span></a></p>{follow(B, lang)}</section>')
    main = (f'<div class="page-head"><div class="wrap"><p class="upd-kicker"><a href="{allp}">{esc(T["title"])}</a></p><h1 id="pg-title">{esc(title(e, lang, T))}</h1></div></div>'
            f'<div class="wrap content updates-content">{body}{B.updated_for(lang, key(e))}</div>')
    head = rss_link(B, lang) + f'<meta property="article:published_time" content="{e["date"]}">\n'
    return B.shell(lang, pg, page_title(B, e, lang) + page_suffix(e, lang), page_desc(B, e, lang), main, env, extra_head=head)


def register(B):
    """Add one page per entry (key u:<slug>, /updates/<slug>/) so build.py builds, checks and lists it in the sitemap."""
    kids = []
    for e in STATE["entries"]:
        k = key(e)
        p = {"key": k, "slug": f"updates/{e['_slug']}/", "nav": {"en": pick(e, "title", "en"), "fr": pick(e, "title", "fr")}, "_entry": e}
        B.PAGES.append(p); B.BYKEY[k] = p; kids.append(k)
        B.SITE["updated"][k] = e["date"]
    B.BYKEY["updates"]["children"] = kids  # breadcrumbs: Home > Updates > entry (updates is not in the menu, so no submenu)


def feed_xml(B, lang, env):
    """RSS 2.0 (/updates/feed.xml, /fr/updates/feed.xml): every entry, newest first, plain text and the first photo."""
    T = B.UI[lang]["updates"]; origin = B.LIVE if env == "live" else B.STAGING_ORIGIN
    x = lambda s: html.escape(s, quote=False)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]; mons = MON["en"]
    import datetime
    items = []
    for e in STATE["entries"]:
        d = datetime.date.fromisoformat(e["date"]); link = B.LIVE + permalink(B, lang, e)
        pub = f"{days[d.weekday()]}, {d.day:02d} {mons[d.month - 1]} {d.year} 12:00:00 -0700"
        ims = images(e); desc = pick(e, "body", lang) or pick(e, "title", lang)
        enc = ""
        if ims:
            w = web_sizes(ims[0])[-1]; f = f"{origin}/assets/img/updates/{stem(ims[0])}-{w}.jpg"
            size = (B.ROOT / "assets/img/updates" / f"{stem(ims[0])}-{w}.jpg").stat().st_size
            enc = f'\n      <enclosure url="{x(f)}" length="{size}" type="image/jpeg"/>'
        items.append(f"    <item>\n      <title>{x(title(e, lang, T))}</title>\n      <link>{x(link)}</link>\n      <guid isPermaLink=\"true\">{x(link)}</guid>\n"
                     f"      <pubDate>{pub}</pubDate>\n      <description>{x(desc)}</description>{enc}\n    </item>")
    home = B.LIVE + B.url(lang, "updates")
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n  <channel>\n'
            f'    <title>{x(T["feed_title"])}</title>\n    <link>{x(home)}</link>\n    <description>{x(T["intro"])}</description>\n'
            f'    <language>{lang}-CA</language>\n    <atom:link href="{x(home)}feed.xml" rel="self" type="application/rss+xml"/>\n'
            + "\n".join(items) + "\n  </channel>\n</rss>\n")


def write_feeds(B, dist, env):
    if not STATE["entries"]: return
    for l in B.LANGS:
        (dist / B.url(l, "updates").lstrip("/") / "feed.xml").write_text(feed_xml(B, l, env))


# ---------------- build guard ----------------
def check(B, dist, env):
    import xml.etree.ElementTree as ET
    errs = []; E = STATE["entries"]; on = bool(E)
    errs += [f"data: {x}" for x in validate([{k: v for k, v in e.items() if not k.startswith("_")} for e in E], "shown")]
    if len({e["_slug"] for e in E}) != len(E): errs.append("updates: permalinks are not unique")
    for l in B.LANGS:
        hp = dist / B.url(l, "home").lstrip("/") / "index.html"; ht = hp.read_text()
        up = dist / B.url(l, "updates").lstrip("/") / "index.html"; fd = up.parent / "feed.xml"
        sec = re.search(r'<section class="block updates".*?</section>', ht, re.S)
        if on:
            if not sec: errs.append(f"{hp.relative_to(dist)}: updates has entries but the home section is missing")
            else:
                k = len(re.findall(r'<li class="upd-card', sec.group(0)))
                if k == 0 or k != min(len(E), int(B.SITE["updates"].get("home_max", 4))): errs.append(f"{hp.relative_to(dist)}: updates section shows {k} cards (empty or wrong count)")
                if len(re.findall(r'class="readlink"><a href="(?:/fr)?/updates/\d{4}-\d{2}-\d{2}-', sec.group(0))) != k: errs.append(f"{hp.relative_to(dist)}: a home update card has no Read more link to its permalink")
                if 'class="upd-follow"' not in sec.group(0): errs.append(f"{hp.relative_to(dist)}: updates section lost its follow buttons")
            if not up.exists(): errs.append(f"{up.relative_to(dist)}: /updates/ page missing"); continue
            ut = up.read_text()
            if len(re.findall(r'<article class="upd-entry', ut)) != len(E): errs.append(f"{up.relative_to(dist)}: does not list every update")
            if 'type="application/rss+xml"' not in ut: errs.append(f"{up.relative_to(dist)}: no RSS alternate link")
            for e in E:
                pp = dist / permalink(B, l, e).lstrip("/") / "index.html"
                if not pp.exists(): errs.append(f"{pp.relative_to(dist)}: permalink page missing"); continue
                pt = pp.read_text()
                if f'href="{permalink(B, l, e)}"' not in ut: errs.append(f"{up.relative_to(dist)}: feed title does not link to {permalink(B, l, e)}")
                if f'href="{B.url(l, "updates")}"' not in pt: errs.append(f"{pp.relative_to(dist)}: no 'All updates' link")
                if 'property="og:type" content="article"' not in pt: errs.append(f"{pp.relative_to(dist)}: og:type is not article")
                if images(e) and f'/assets/img/updates/{stem(images(e)[0])}-' not in re.search(r'<meta property="og:image" content="([^"]+)"', pt).group(1): errs.append(f"{pp.relative_to(dist)}: og:image is not the first photo")
            for m in re.finditer(r'<a [^>]*class="btn sec" href="([^"]+)"[^>]*>', ut):
                if 'target="_blank"' not in m.group(0) or 'rel="noopener"' not in m.group(0): errs.append(f"{up.relative_to(dist)}: post link {m.group(1)} must open in a new tab with rel=noopener")
            if not fd.exists(): errs.append(f"{fd.relative_to(dist)}: RSS feed missing")
            else:
                try:
                    items = ET.parse(fd).getroot().findall("./channel/item")
                    if len(items) != len(E): errs.append(f"{fd.relative_to(dist)}: {len(items)} items, {len(E)} entries")
                except ET.ParseError as ex: errs.append(f"{fd.relative_to(dist)}: not valid XML ({ex})")
            sm = (dist / "sitemap.xml").read_text()
            errs += [f"sitemap.xml: missing {permalink(B, l, e)}" for e in E if B.LIVE + permalink(B, l, e) not in sm]
        else:
            if sec or 'class="upd-follow"' in ht or 'id="updates"' in ht: errs.append(f"{hp.relative_to(dist)}: updates section rendered with no entries")
            if up.parent.exists(): errs.append(f"{up.parent.relative_to(dist)}/: /updates/ built with no entries")
    for f in sorted(dist.rglob("*.html")):  # no embeds or third-party scripts from the social platforms
        t = f.read_text()
        if re.search(r'<(script|iframe)[^>]+src="https?://[^"]*(instagram|facebook|fbcdn|twitter|x\.com|twimg)', t): errs.append(f"{f.relative_to(dist)}: embeds a social-media script or iframe")
    if not on:
        if "/updates/" in (dist / "sitemap.xml").read_text(): errs.append("sitemap.xml lists /updates/ with no entries")
        errs += [f"{f.relative_to(dist)}: links to /updates/ with no entries" for f in sorted(dist.rglob("*.html")) if re.search(r'href="(/fr)?/updates/', f.read_text())]
    if env == "live" or not STATE["sample"]:  # SAMPLE entries: staging only, never shipped
        note = esc(B.UI["en"]["updates"]["sample_note"]); tags = (B.UI["en"]["updates"]["sample_tag"].strip(), B.UI["fr"]["updates"]["sample_tag"].strip())
        for f in sorted([*dist.rglob("*.html"), *dist.rglob("feed.xml")]):
            t = f.read_text()
            if "/assets/img/updates/sample-" in t or note in t or any(tg in t for tg in tags): errs.append(f"{f.relative_to(dist)}: shows an updates SAMPLE")
        d = dist / "assets/img/updates"
        errs += [f"{f.relative_to(dist)}: SAMPLE photo file shipped" for f in d.glob("sample-*")] if d.exists() else []
    if env == "live" and STATE["sample"]: errs.append("updates: SAMPLE entries loaded in a live build")
    return errs


def prune_dist(dist):
    """Ship only the web sizes of the photos shown in this build (never samples on live, nothing at all with zero entries)."""
    d = dist / "assets" / "img" / "updates"
    if not d.exists(): return
    keep = {stem(im) for im in all_images(STATE["entries"])}
    for f in d.iterdir():
        m = re.match(r"(.+)-\d+\.(webp|jpg)$", f.name)
        if not m or m.group(1) not in keep: f.unlink()
    if not any(d.iterdir()): d.rmdir()
