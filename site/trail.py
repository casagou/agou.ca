"""'On the campaign trail' (6 Oct 2026, approved by Joachim via Provincial Campaign Ops).

Entries: site/data/trail.json ("entries", one object per photo; see README "Campaign trail"). Photos Joachim provides go in
site/data/trail/ (JPEG). tools/make_trail.py (or any local build with Pillow) strips their metadata and writes the web sizes to
assets/img/trail/<stem>-<width>.{webp,jpg} (4:3, sRGB, no EXIF/GPS) plus assets/img/trail/index.json; commit those files.

With zero entries the feature does not exist on the built site: no home section, no follow buttons, no /trail/ page, no link
(build.py puts "trail" in HIDDEN). Staging, while there are no real entries, shows the clearly labelled SAMPLE entries from
data/trail-samples.json (existing licensed Victoria photos) when site.json trail.samples_on_staging is true; live never does.
"""
import hashlib, html, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "data" / "trail"            # originals (JPEG, metadata stripped by make_images)
OUT = ROOT / "assets" / "img" / "trail"  # web sizes (committed; CI has no Pillow)
MANIFEST = OUT / "index.json"
WIDTHS = (320, 640, 960, 1280)
ASPECT = (4, 3)
Q = {"webp": 72, "jpg": 78}
MAX_SRC = 2400  # px, long edge of the stripped original kept in the repo
MON = {"en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
       "fr": ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juill.", "août", "sept.", "oct.", "nov.", "déc."]}
esc = lambda s: html.escape(s, quote=True)
STATE = {"entries": [], "sample": False}


# ---------------- data ----------------
def _read(name):
    f = ROOT / "data" / name
    return json.loads(f.read_text()).get("entries", []) if f.exists() else []


def validate(entries, where):
    errs = []
    for i, e in enumerate(entries):
        tag = f"{where} entry {i + 1}"
        for k in ("date", "caption_en"):
            if not str(e.get(k, "")).strip(): errs.append(f"{tag}: '{k}' is required")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(e.get("date", ""))): errs.append(f"{tag}: date must be YYYY-MM-DD")
        if e.get("sample"):
            if not e.get("vic"): errs.append(f"{tag}: a sample needs 'vic' (a site.json victoria_photos id)")
        else:
            img = str(e.get("image", ""))
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.jpe?g", img): errs.append(f"{tag}: image must be a lowercase .jpg file name (letters, digits, hyphens) in data/trail/")
            elif not (SRC / img).exists(): errs.append(f"{tag}: data/trail/{img} not found")
        for k in ("caption_en", "caption_fr", "place", "place_fr"):
            v = str(e.get(k) or "")
            if re.search(r"\bJoa\b|the candidate|le candidat|Thales|\bACTW\b", v): errs.append(f"{tag}: {k} breaks a site rule (Joa / the candidate / Thales / ACTW)")
            if len(v) > 90: errs.append(f"{tag}: {k} is {len(v)} characters (keep it to one short line, max 90)")
        if e.get("focus") is not None and not (isinstance(e["focus"], list) and len(e["focus"]) == 2 and all(0 <= x <= 1 for x in e["focus"])):
            errs.append(f"{tag}: focus must be [x, y], fractions 0-1 (crop centre)")
    return errs


def stem(e):
    return ("sample-" + e["vic"]) if e.get("sample") else re.sub(r"\.jpe?g$", "", e["image"])


def load(env, site, vic_photos):
    """Entries to show in this build, newest first (same date: later in the file first)."""
    real = _read("trail.json")
    errs = validate(real, "data/trail.json")
    entries, sample = real, False
    if not real and env == "staging" and site.get("trail", {}).get("samples_on_staging"):
        entries, sample = _read("trail-samples.json"), True
        errs += validate(entries, "data/trail-samples.json")
        errs += [f"data/trail-samples.json: unknown victoria photo {e['vic']!r}" for e in entries if e.get("vic") not in vic_photos]
    if errs: sys.exit("campaign trail:\n  " + "\n  ".join(errs))
    entries = [e for _, e in sorted(enumerate(entries), key=lambda ie: (ie[1]["date"], ie[0]), reverse=True)]
    STATE["entries"], STATE["sample"] = entries, sample
    return entries


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


def _crop(im, focus):
    W, H = im.size; aw, ah = ASPECT
    cw, ch = (W, round(W * ah / aw)) if W * ah / aw <= H else (round(H * aw / ah), H)
    fx, fy = focus or (0.5, 0.5)
    x = min(max(round(fx * W - cw / 2), 0), W - cw); y = min(max(round(fy * H - ch / 2), 0), H - ch)
    return im.crop((x, y, x + cw, y + ch))


def _sample_source(e, vic_photos):
    """SAMPLE entries only: the licensed Commons original of a site.json victoria_photos id, with its 'blur' boxes applied."""
    sys.path.insert(0, str(ROOT / "tools"))
    import make_vic_photos as mv
    P = vic_photos[e["vic"]]; orig = pathlib.Path("/tmp/vic-photos-orig"); orig.mkdir(exist_ok=True)
    return mv.blur(mv.original(e["vic"], P["source_url"], orig), P.get("blur"))


def make_images(entries, vic_photos, force=False):
    """Strip metadata from originals and write the web sizes for every entry whose outputs are missing or stale."""
    from PIL import Image, ImageCms, ImageOps
    import io
    man = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    OUT.mkdir(parents=True, exist_ok=True); done = []
    for e in entries:
        s = stem(e)
        if e.get("sample"):
            key = _sha(json.dumps([vic_photos[e["vic"]].get("source_url"), vic_photos[e["vic"]].get("blur"), e.get("focus")]).encode())
        else:
            src = SRC / e["image"]
            if jpeg_has_metadata(src):  # phone photos carry GPS: re-save the original without any metadata (orientation applied)
                im = ImageOps.exif_transpose(Image.open(src))
                icc = im.info.get("icc_profile")
                if icc: im = ImageCms.profileToProfile(im, ImageCms.ImageCmsProfile(io.BytesIO(icc)), ImageCms.createProfile("sRGB"), outputMode="RGB")
                im = im.convert("RGB"); im.thumbnail((MAX_SRC, MAX_SRC), Image.LANCZOS)
                im.save(src, "JPEG", quality=92, optimize=True, progressive=True)
                print(f"trail: stripped metadata from data/trail/{e['image']}")
            key = _sha(src.read_bytes() + json.dumps(e.get("focus")).encode())
        have = man.get(s, {})
        if not force and have.get("key") == key and all((OUT / f"{s}-{w}.{x}").exists() for w in have.get("widths", []) for x in Q):
            continue
        if e.get("sample"): im = _sample_source(e, vic_photos)
        else:
            im = Image.open(SRC / e["image"]); im = ImageOps.exif_transpose(im).convert("RGB")
        im = _crop(im, e.get("focus"))
        widths = [w for w in WIDTHS if w <= im.size[0]] or [im.size[0]]
        for old in OUT.glob(f"{s}-*"): old.unlink()
        for w in widths:
            r = im.resize((w, round(w * ASPECT[1] / ASPECT[0])), Image.LANCZOS)
            r.save(OUT / f"{s}-{w}.webp", "WEBP", quality=Q["webp"], method=6)
            r.save(OUT / f"{s}-{w}.jpg", "JPEG", quality=Q["jpg"], optimize=True, progressive=True)
        man[s] = {"key": key, "widths": widths}; done.append(s)
        MANIFEST.write_text(json.dumps(dict(sorted(man.items())), indent=1) + "\n")  # after each photo, so an interrupted run keeps what it made
    MANIFEST.write_text(json.dumps(dict(sorted(man.items())), indent=1) + "\n")
    return done


def ensure_images(entries, vic_photos):
    """Build step: outputs must exist and match their source. With Pillow (local) stale ones are regenerated;
    without it (CI) the build stops and says to run tools/make_trail.py and commit."""
    man = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    stale = []
    for e in entries:
        s = stem(e); have = man.get(s)
        if not e.get("sample") and jpeg_has_metadata(SRC / e["image"]): stale.append(f"data/trail/{e['image']} still has EXIF/GPS metadata"); continue
        if not have or not all((OUT / f"{s}-{w}.{x}").exists() for w in have["widths"] for x in Q): stale.append(f"{s}: web sizes missing"); continue
        if not e.get("sample") and have["key"] != _sha((SRC / e["image"]).read_bytes() + json.dumps(e.get("focus")).encode()): stale.append(f"{s}: photo or focus changed")
    if not stale: return
    try:
        import PIL  # noqa: F401
    except ImportError:
        sys.exit("campaign trail: " + "; ".join(stale) + ". Run tools/make_trail.py locally (needs Pillow) and commit data/trail/ and assets/img/trail/.")
    make_images(entries, vic_photos)


# ---------------- rendering ----------------
def caption(e, lang):
    c = (e.get("caption_fr") or e["caption_en"]) if lang == "fr" else e["caption_en"]
    return c.strip()


def place(e, lang):
    return ((e.get("place_fr") or e.get("place")) if lang == "fr" else e.get("place")) or ""


def date_txt(d, lang, year=None):
    y, m, dd = map(int, d.split("-"))
    yr = "" if year in (None, y) else f" {y}"
    if lang == "fr": return f"{'1er' if dd == 1 else dd} {MON['fr'][m - 1]}{yr}"
    return f"{MON['en'][m - 1]} {dd}" + (f", {y}" if yr else "")


def line(e, lang, year, sample_tag):
    """One short caption line: caption, the place if the caption does not already name it, and the date."""
    c = caption(e, lang); p = place(e, lang)
    if p and p.lower() not in c.lower(): c = f"{c}, {p}"
    return (sample_tag if e.get("sample") else "") + f"{c}, {date_txt(e['date'], lang, year)}"


def picture(B, e, lang, sizes, alt):
    s = stem(e); widths = json.loads(MANIFEST.read_text())[s]["widths"]
    f = lambda w, x: f"/assets/img/trail/{s}-{w}.{x}"
    ss = lambda x: ", ".join(f"{f(w, x)} {w}w" for w in widths)
    W = widths[-1]; H = round(W * ASPECT[1] / ASPECT[0])
    if e.get("sample") and e["vic"] not in B.PAGE_STATE["vic_used"]: B.PAGE_STATE["vic_used"].append(e["vic"])  # licence credit in the footer
    return (f'<picture><source type="image/webp" srcset="{ss("webp")}" sizes="{sizes}">'
            f'<img src="{f(widths[min(1, len(widths) - 1)], "jpg")}" srcset="{ss("jpg")}" sizes="{sizes}" width="{W}" height="{H}" alt="{esc(alt)}" loading="lazy" decoding="async"></picture>')


def follow(B, lang):
    T = B.UI[lang]["trail"]
    items = "".join(f'<li><a href="{esc(u)}" rel="me noopener">{B.ICONS[n]}<span>{esc(n)}</span></a></li>' for n, u in B.SITE["trail"]["follow"].items())
    return f'<div class="trail-follow"><h3>{esc(T["follow"])}</h3><ul class="social" aria-label="{esc(T["follow"])}">{items}</ul></div>'


def _sample_note(B, lang):
    return f'<p class="draft-tag">{esc(B.UI[lang]["trail"]["sample_note"])}</p>' if STATE["sample"] else ""


def home_section(B, lang):
    """Home strip under the priorities: the most recent entries (site.json trail.home_max), See all, Follow the campaign."""
    E = STATE["entries"]
    if not E: return ""
    T = B.UI[lang]["trail"]; n = min(len(E), int(B.SITE["trail"].get("home_max", 6))); yr = int(E[0]["date"][:4])
    cap = {1: 360, 2: 600, 3: 840}.get(n, 1084)  # row width cap from 800px (site.css .trail-list.nN)
    sizes = f"(min-width: 1120px) {(cap - 12 * (n - 1)) // n}px, (min-width: 800px) min({(cap - 12 * (n - 1)) // n}px, calc((100vw - 36px - {12 * (n - 1)}px) / {n})), {80 if n == 1 else 62}vw"
    lis = "".join(f'<li><figure>{picture(B, e, lang, sizes, caption(e, lang))}<figcaption>{esc(line(e, lang, yr, T["sample_tag"]))}</figcaption></figure></li>' for e in E[:n])
    return (f'<section class="block trail" aria-labelledby="campaign-trail">{_sample_note(B, lang)}<h2 id="campaign-trail">{esc(T["title"])}</h2>'
            f'<div class="trail-strip" role="region" aria-labelledby="campaign-trail" tabindex="0"><ul class="trail-list n{n}">{lis}</ul></div>'
            f'<p class="pagelink"><a href="{B.url(lang, "trail")}">{esc(T["see_all"])} <span aria-hidden="true">→</span></a></p>{follow(B, lang)}</section>')


def page(B, lang, pg, env):
    E = STATE["entries"]
    if not E: sys.exit("campaign trail: /trail/ was built with no entries (it must be in HIDDEN)")
    T = B.UI[lang]["trail"]; yr = int(E[0]["date"][:4])
    sizes = "(min-width: 840px) 382px, (min-width: 600px) calc((100vw - 56px) / 2), calc(100vw - 36px)"
    lis = "".join(f'<li><figure>{picture(B, e, lang, sizes, caption(e, lang))}<figcaption>{esc(line(e, lang, yr, T["sample_tag"]))}</figcaption></figure></li>' for e in E)
    body = (f'<section class="block trail trail-all" aria-labelledby="trail-h">{_sample_note(B, lang)}<p class="vh" id="trail-h">{esc(T["title"])}</p>'
            f'<p>{esc(T["intro"])}</p><ul class="trail-grid">{lis}</ul>{follow(B, lang)}</section>')
    main = (f'<div class="page-head"><div class="wrap"><h1>{esc(T["title"])}</h1></div></div>'
            f'<div class="wrap content trail-content">{body}{B.updated_for(lang, "trail")}</div>')
    return B.shell(lang, pg, f'{T["title"]} – Joachim Agou', T["intro"], main, env)


# ---------------- build guard ----------------
def check(B, dist, env):
    errs = []; on = bool(STATE["entries"])
    for l in B.LANGS:
        hp = dist / B.url(l, "home").lstrip("/") / "index.html"; ht = hp.read_text()
        tp = dist / B.url(l, "trail").lstrip("/") / "index.html"
        sec = re.search(r'<section class="block trail".*?</section>', ht, re.S)
        if on:
            if not sec: errs.append(f"{hp.relative_to(dist)}: campaign trail has entries but the home section is missing")
            else:
                k = len(re.findall(r"<li><figure><picture>", sec.group(0)))
                if k == 0 or k != min(len(STATE["entries"]), int(B.SITE["trail"].get("home_max", 6))): errs.append(f"{hp.relative_to(dist)}: campaign trail section shows {k} entries (empty or wrong count)")
                if 'class="trail-follow"' not in sec.group(0): errs.append(f"{hp.relative_to(dist)}: campaign trail section lost its Follow the campaign buttons")
            if not tp.exists() or len(re.findall(r"<li><figure><picture>", tp.read_text())) != len(STATE["entries"]):
                errs.append(f"{tp.relative_to(dist)}: missing or not listing every campaign trail entry")
        else:
            if sec or 'class="trail-follow"' in ht or 'id="campaign-trail"' in ht: errs.append(f"{hp.relative_to(dist)}: campaign trail section rendered with no entries")
            if tp.exists(): errs.append(f"{tp.relative_to(dist)}: /trail/ page built with no entries")
    if not on:
        if "/trail/" in (dist / "sitemap.xml").read_text(): errs.append("sitemap.xml lists /trail/ with no entries")
        errs += [f"{f.relative_to(dist)}: links to /trail/ with no entries" for f in sorted(dist.rglob("*.html")) if re.search(r'href="(/fr)?/trail/"', f.read_text())]
    if env == "live" or not STATE["sample"]:  # SAMPLE entries: staging only, never shipped
        errs += [f"{f.relative_to(dist)}: shows a campaign trail SAMPLE" for f in sorted(dist.rglob("*.html")) if "/assets/img/trail/sample-" in f.read_text() or 'class="draft-tag">' + esc(B.UI["en"]["trail"]["sample_note"]) in f.read_text()]
        errs += [f"{f.relative_to(dist)}: SAMPLE photo file shipped" for f in (dist / "assets/img/trail").glob("sample-*")] if (dist / "assets/img/trail").exists() else []
    return errs


def prune_dist(dist):
    """Ship only the web sizes of the entries shown in this build (never samples on live, nothing at all with zero entries)."""
    d = dist / "assets" / "img" / "trail"
    if not d.exists(): return
    keep = {stem(e) for e in STATE["entries"]}
    for f in d.iterdir():
        m = re.match(r"(.+)-\d+\.(webp|jpg)$", f.name)
        if not m or m.group(1) not in keep: f.unlink()
    if not any(d.iterdir()): d.rmdir()
