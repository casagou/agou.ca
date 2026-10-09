#!/usr/bin/env python3
"""Static build for agou.ca.  python3 build.py --env staging|live  ->  dist/

Content comes from content/<lang>/*.md (made from Notion by tools/notion2md.py).
Interface/form wording comes from ui.json. Page list, photo slots and social links from site.json.
No framework, no dependencies (Python 3 standard library only)."""
import argparse, html, json, re, shutil, pathlib, sys
import scorecard  # /scorecard/ page (scorecard.py, scorecard.json, content/<lang>/scorecard.md)
import province  # /province/ page (province.py, content/<lang>/province.md; not from Notion)
import updates  # "Updates" / « Nouvelles » (updates.py, data/updates.json; hidden everywhere while it has no entries)
import no_party  # no-party version (site.json no_party_v1, 8 Oct 2026); see no_party.py
import prio_layout  # Priorities summary-first layout (staging only until site.json priorities_layout_v2_live)
import events_cal  # Events calendar + 'New' events (events_cal.py; staging only until site.json events_calendar_live)

ROOT = pathlib.Path(__file__).resolve().parent
SITE = json.loads((ROOT / "site.json").read_text())
UI = json.loads((ROOT / "ui.json").read_text())
SEO = json.loads((ROOT / "seo.json").read_text())  # titles, descriptions, og:image per page and language (see seo.json _doc)
STAGING_ORIGIN = "https://agou-staging.pages.dev"  # og:image host on staging builds, so shared staging links preview the new image
PAGES = SITE["pages"]
BYKEY = {p["key"]: p for p in PAGES}
LIVE = SITE["live_origin"]
LANGS = ["en", "fr"]
CAL_ON = lambda env: env == "staging" or bool(SITE.get("events_calendar_live"))
VOL_WARM = lambda env: env == "staging" or bool(SITE.get("volunteer_warm_live"))  # warmer /volunteer/ (welcome note, help + availability checkboxes); staging only until Joachim approves  # calendar view, New badges, menu badge, home New-event line
VIC = SITE.get("victoria_photos", {})  # real Victoria photos (Wikimedia Commons; tools/make_vic_photos.py); staging only until site.json victoria_photos_live
VIC_ON = lambda env: env == "staging" or bool(SITE.get("victoria_photos_live"))
BLANK_GIF = "data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="  # 1x1 transparent: <source> for "not on this screen"
VIC_VARIANTS = {"strip": (3, 1, (480, 800, 1200)), "tile": (4, 3, (240, 360, 480)), "thumb": (1, 1, (80, 160, 240))}  # same as tools/make_vic_photos.py
NOMINATIONS_CLOSED = bool(SITE.get("nominations_closed"))  # site.json: nominations complete (Joachim, 30 Sep 2026); see README "Nominations closed"
# Party links (Joachim, 2 Oct 2026 12:28 AM PT): volunteering, lawn signs and donations go through the Conservative Party of BC (site.json "party").
# Staging always; live only when site.json party_links_live is true. See README "Party links".
PARTY_ON = lambda env: env == "staging" or bool(SITE.get("party_links_live"))
# Volunteer shifts on the Events page (migration 48): staging always; live only when site.json volunteer_shifts_live is true.
# Live and staging share one database, so this flag is what keeps shifts off agou.ca until Joachim approves. See README "Volunteer shifts".
SHIFTS_ON = lambda env: CAL_ON(env) and (env == "staging" or bool(SITE.get("volunteer_shifts_live")))
PRIO2_ON = lambda env: env == "staging" or bool(SITE.get("priorities_layout_v2_live"))  # Priorities summary-first layout (prio_layout.py; 7 Oct 2026, staging only until Joachim approves)
PRIO2_STATE = {}  # EN decisions (which card texts stay visible), reused for FR
PARTY = {"on": False}
# Staging drafts (4 Oct 2026): staging-drafts.json holds exact find/replace text edits that show on staging only,
# and on live only once site.json[<draft live_flag>] is true. Applied in read(). See README "Staging drafts".
DRAFTS = json.loads((ROOT / "staging-drafts.json").read_text())["drafts"] if (ROOT / "staging-drafts.json").exists() else {}
DRAFT_ENV = {"env": None}
DRAFT_ON = lambda name, env: env == "staging" or bool(SITE.get(DRAFTS[name]["live_flag"]))
PARTY_MOVED = ("volunteer", "lawn-sign", "donate")
_PU = lambda k: SITE["party"]["urls"][k]
PARTY_MD = {  # (lang, file): exact replacements in the Notion text when party links are on (each must match once)
    ("en", "home"): [
        ("[**→ Sign up to volunteer**](/volunteer/)", "Sign-up and lawn-sign requests are on the Conservative Party of BC's website.\n[**→ Sign up to volunteer**](/volunteer/)"),
        ("Online donations are coming soon. To contribute now, contact my financial agent, Bert Chen, at [bert@bertchen.ca](mailto:bert@bertchen.ca) or [778-996-9910](tel:+17789969910). He'll explain how to give and issue your tax receipt.",
         "Donations to my campaign go through the Conservative Party of BC's secure donation page. Questions? Contact my financial agent, Bert Chen, at [bert@bertchen.ca](mailto:bert@bertchen.ca) or [778-996-9910](tel:+17789969910)."),
        ("Only individuals who are Canadian citizens or permanent residents living in B.C. can contribute.\n", "Only individuals who are Canadian citizens or permanent residents living in B.C. can contribute.\n[**→ Donate on the party's website**](/donate/)\n"),
    ],
    ("fr", "home"): [
        ("[**→ Inscrivez-vous comme bénévole**](/fr/volunteer/)", "L'inscription des bénévoles et les demandes de pancarte se font sur le site du Parti conservateur de la C.-B. (en anglais).\n[**→ Inscrivez-vous comme bénévole**](/fr/volunteer/)"),
        ("Les dons en ligne seront bientôt possibles. Pour contribuer dès maintenant, communiquez avec mon agent financier, Bert Chen, à [bert@bertchen.ca](mailto:bert@bertchen.ca) ou au [778-996-9910](tel:+17789969910). Il vous expliquera comment donner et vous remettra votre reçu fiscal.",
         "Les dons à ma campagne se font sur la page de dons sécurisée du Parti conservateur de la C.-B. (en anglais). Des questions? Communiquez avec mon agent financier, Bert Chen, à [bert@bertchen.ca](mailto:bert@bertchen.ca) ou au [778-996-9910](tel:+17789969910)."),
        ("et vivant en C.-B. peuvent contribuer.\n", "et vivant en C.-B. peuvent contribuer.\n[**→ Faire un don sur le site du parti**](/fr/donate/)\n"),
    ],
    ("en", "faq"): [
        ("[Sign up to volunteer](/volunteer/)", "Sign-up is on the Conservative Party of BC's website: [Sign up to volunteer](/volunteer/)"),
        ("[Request a lawn sign](/lawn-sign/)", "Requests go through the Conservative Party of BC's lawn-sign form: [Request a lawn sign](/lawn-sign/)"),
        ("Online donations are coming soon. To contribute now, contact my financial agent, Bert Chen, at [bert@bertchen.ca](mailto:bert@bertchen.ca) or [778-996-9910](tel:+17789969910).",
         "Donate online through the Conservative Party of BC's secure donation page: [Donate](/donate/). Questions? Contact my financial agent, Bert Chen, at [bert@bertchen.ca](mailto:bert@bertchen.ca) or [778-996-9910](tel:+17789969910)."),
    ],
    ("fr", "faq"): [
        ("[Inscrivez-vous comme bénévole](/fr/volunteer/)", "L'inscription se fait sur le site du Parti conservateur de la C.-B. (en anglais) : [Inscrivez-vous comme bénévole](/fr/volunteer/)"),
        ("[Demander une pancarte](/fr/lawn-sign/)", "Les demandes se font sur le formulaire du Parti conservateur de la C.-B. (en anglais) : [Demander une pancarte](/fr/lawn-sign/)"),
        ("Les dons en ligne seront bientôt possibles. Pour contribuer dès maintenant, communiquez avec mon agent financier, Bert Chen, à [bert@bertchen.ca](mailto:bert@bertchen.ca) ou au [778-996-9910](tel:+17789969910).",
         "Faites un don en ligne sur la page de dons sécurisée du Parti conservateur de la C.-B. (en anglais) : [Faire un don](/fr/donate/). Des questions? Communiquez avec mon agent financier, Bert Chen, à [bert@bertchen.ca](mailto:bert@bertchen.ca) ou au [778-996-9910](tel:+17789969910)."),
    ],
}


def party_rewrite(h, lang):
    """Party links on: every link to our volunteer / lawn-sign / donate pages goes to the party's page instead
    (same tab, rel=noopener as for other external links; hreflang=en on French pages). The language switcher keeps our bridge pages."""
    def sub(m):
        attrs, key = m.group(1) + m.group(4), m.group(3)
        if 'class="lang"' in attrs: return m.group(0)
        attrs = attrs.replace(' aria-current="page"', "")
        extra = "" if "rel=" in attrs else ' rel="noopener"'
        if lang == "fr" and "hreflang=" not in attrs: extra += ' hreflang="en"'
        return f'<a {m.group(1)}href="{esc(_PU(key))}"{m.group(4).replace(" aria-current=\"page\"", "")}{extra}>'
    h = re.sub(r'<a ([^>]*?)href="(/fr)?/(volunteer|lawn-sign|donate)/"([^>]*)>', sub, h)
    if lang == "fr":  # other links to the party's (English-only) site, e.g. its privacy policy
        h = re.sub(r'<a ((?![^>]*hreflang=)[^>]*href="https://conservativebc\.ca/[^"]*"[^>]*)>', r'<a \1 hreflang="en">', h)
    return h


def party_page(lang, page, env):
    """/volunteer/, /lawn-sign/, /donate/ when party links are on: a short page that explains the step and links out (no form)."""
    key = page["key"]; P = UI[lang]["party"]; T = P[key]
    btn = f'<p class="cta-line"><a class="btn primary" href="{esc(_PU(key))}" rel="noopener"{" hreflang=\"en\"" if lang == "fr" else ""}>{esc(T["btn"])} <span aria-hidden="true">↗</span></a></p>'
    parts = [f'<p>{esc(T["lead"])}</p>', f'<p>{esc(T["what"])}</p>', btn, f'<p class="note">{esc(T.get("note") or P["note_ref"])}</p>']
    if key == "lawn-sign": parts.append(f'<p class="note">{esc(T["shared"])}</p>')
    shifts_note = ""
    if key == "volunteer" and SHIFTS_ON(env) and "events" not in HIDDEN and (env == "staging" or SITE.get("volunteer_shifts_note_live")):
        # 5 Oct 2026: optional door-knocking shifts (Events page, ?show=shifts); staging only until site.json volunteer_shifts_note_live
        draft = f'<p class="draft-tag">{esc(UI[lang]["volunteer"]["draft_tag"])}</p>' if env == "staging" and not SITE.get("volunteer_shifts_note_live") else ""
        shifts_note = (f'<section class="block vshifts" aria-labelledby="vshifts">{draft}<h2 id="vshifts">{esc(T["shifts_h"])}</h2>'
                       f'<p>{esc(T["shifts_p1"])}</p><p>{esc(T["shifts_p2"])}</p>'
                       f'<p class="pagelink"><a href="{url(lang, "events")}?show=shifts">{esc(T["shifts_link"])} →</a></p></section>')
    if key == "donate":
        parts.append(f'<p>{esc(T["questions"])} <a href="mailto:bert@bertchen.ca">bert@bertchen.ca</a> {esc(P["or"])} <a href="tel:+17789969910">778-996-9910</a>.</p>')
    body = f'<section class="block lead">{"".join(parts)}</section>' + shifts_note
    main = f'<div class="page-head"><div class="wrap"><h1>{esc(T["h1"])}</h1></div></div><div class="wrap content">{body}{updated_for(lang, key)}</div>'
    return shell(lang, page, f'{T["h1"]} – Joachim Agou – Victoria–Beacon Hill', T["lead"], main, env)
HIDE_EG = {"on": False, "keys": ("events", "get-involved", "volunteer", "lawn-sign", "nominate")}  # site.json hide_events_getinvolved_v1(_live)
HIDE_EG_EDITS = {  # copy that only points to the hidden pages (Joachim 8 Oct 2026 6:00 PM PT)
    "en/home": [("dropsec", "## Volunteer"), ("dropsec", "## Events")],
    "fr/home": [("dropsec", "## Bénévolat"), ("dropsec", "## Événements")],
    "en/faq": [("dropsec", "## Get involved")],
    "fr/faq": [("dropsec", "## S'impliquer")],
}
HIDDEN = set()  # page keys left out of this build (see site.json publish_faq_live); filled in __main__
MEDIAKIT = {"on": True, "env": "staging", "errs": {}}  # media-kit PDFs (site.json media_kit / publish_media_kit_live); set in __main__
IMG = {  # local image name -> (files by width, width, height)
    "joachim-agou-speaking": ({800: "joachim-agou-speaking-800.jpg", 1600: "joachim-agou-speaking-1600.jpg"}, 1600, 1000),
    # headshot (Joachim, 30 Sep 2026): tools/make_headshot.py, no metadata; a .webp twin of each JPG is served first
    "joachim-agou-headshot": ({400: "joachim-agou-headshot-400.jpg", 800: "joachim-agou-headshot-800.jpg", 1200: "joachim-agou-headshot-1200.jpg"}, 1200, 1200),
}
# headshot background options (30 Sep 2026, staging only until Joachim picks): site.json headshot_background = "a"/"b"/"c" (or null = original photo)
HS_BG = SITE.get("headshot_background")
if HS_BG:
    if HS_BG not in SITE["headshot_backgrounds"]: sys.exit(f"site.json headshot_background {HS_BG!r}: not in headshot_backgrounds")
    IMG["joachim-agou-headshot"] = ({w: f"joachim-agou-headshot-bg-{HS_BG}-{w}.jpg" for w in (400, 800, 1200)}, 1200, 1200)
HS_SECOND = SITE.get("headshot_background_second")  # second headshot (B, Dallas Road): About photo + second download on Media; never on a page that already shows the main one twice
if HS_SECOND and HS_SECOND not in SITE["headshot_backgrounds"]: sys.exit(f"site.json headshot_background_second {HS_SECOND!r}: not in headshot_backgrounds")
HS_USED = [v for v in (HS_BG, HS_SECOND) if v]  # background options that ship (files + footer credits)
def hs_files(bg):
    return {w: (f"joachim-agou-headshot-bg-{bg}-{w}.jpg" if bg else f"joachim-agou-headshot-{w}.jpg") for w in (400, 800, 1200)}
HEADSHOT_ALT = "Joachim Agou"  # plain alt text, EN and FR (photo slots and the Media page)
esc = lambda s: html.escape(s, quote=True)


def url(lang, key):
    return ("/fr/" if lang == "fr" else "/") + BYKEY[key]["slug"]


def slugify(s):
    s = re.sub(r"[^\w\s-]", "", s.lower(), flags=re.U)
    return re.sub(r"[\s_]+", "-", s).strip("-")


# ---------------- inline markdown ----------------
def inline(t, ctx):
    out, i = [], 0
    pat = re.compile(r"<span color=\"red\">(.+?)</span>|(?<!\\)\[((?:[^\[\]]|\[[^\]]*\])*)\]\(([^)\s]+)\)|\*\*(.+?)\*\*|(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])")
    for m in pat.finditer(t):
        out.append(esc(unesc(t[i:m.start()])))
        if m.group(1) is not None:  # Notion red text = an open draft note ("[TO COMPLETE: ...]"); shown highlighted on staging, blocks a live build
            out.append(f'<mark class="todo">{inline(m.group(1), ctx)}</mark>')
        elif m.group(2) is not None:
            href = m.group(3)
            if ctx.get("self") and href.rstrip("/") == ctx["self"].rstrip("/"):
                href = ctx.get("self_anchor", "#main")
            ext = href.startswith("http")
            out.append(f'<a href="{esc(href)}"{" rel=\"noopener\"" if ext else ""}>{inline(m.group(2), ctx)}</a>')
        elif m.group(4) is not None:
            out.append(f"<strong>{inline(m.group(4), ctx)}</strong>")
        else:
            out.append(f"<em>{inline(m.group(5), ctx)}</em>")
        i = m.end()
    out.append(esc(unesc(t[i:])))
    return "".join(out)


def unesc(s):
    return s.replace("\\$", "$").replace("\\[", "[").replace("\\]", "]")


PAGE_STATE = {"hero_map": False, "vic_used": []}  # set while building the home page when the hero already shows the riding map


def map_card(lang, eager=False):
    """The riding map (tools/make_map.py): self-hosted PNGs, phone and desktop art direction, 2x/3x. Light card + caption."""
    M = UI[lang]["map"]; f = lambda v, s: f"/assets/img/riding-map-{lang}-{v}-{s}x.png"
    load = 'fetchpriority="high"' if eager else 'loading="lazy"'
    return (f'<figure class="map-card"><picture>'
            f'<source media="(max-width: 599px)" srcset="{f("phone", 2)} 680w, {f("phone", 3)} 1020w" sizes="calc(100vw - 40px)" width="680" height="510">'
            f'<img src="{f("desk", 2)}" srcset="{f("desk", 2)} 1040w, {f("desk", 3)} 1560w" sizes="(min-width: 800px) 560px, calc(100vw - 40px)" width="1040" height="780" alt="{esc(M["alt"])}" {load} decoding="async">'
            f'</picture><figcaption><p class="map-q">{esc(M["title"])}</p>'
            f'<p class="map-link"><a href="https://wheretovote.elections.bc.ca/" rel="noopener">{esc(M["link"])} <span aria-hidden="true">↗</span></a></p>'
            f'<p class="map-attr">{esc(M["attribution"])}</p></figcaption></figure>')


def picture(name, alt, lang, caption=True, eager=False):
    fname = pathlib.PurePosixPath(name).name
    local = SITE["images"].get(fname, name)
    if local == "riding-map":  # Notion's riding map image -> the site's own map (once per page)
        return "" if PAGE_STATE["hero_map"] else map_card(lang)
    if local not in IMG:
        sys.exit(f"Image {name!r} is not mapped to a local file. Download it into assets/img and add it to site.json 'images' and IMG in build.py.")
    files, w, h = IMG[local]
    srcset = ", ".join(f"/assets/img/{f} {wd}w" for wd, f in sorted(files.items()))
    big = files[max(files)]
    img = (f'<img src="/assets/img/{big}" srcset="{srcset}" sizes="(min-width: 900px) 820px, 100vw" '
           f'width="{w}" height="{h}" alt="{esc(alt)}" {"" if eager else "loading=\"lazy\" "}decoding="async">')
    cap = f"<figcaption>{esc(alt)}</figcaption>" if caption else ""
    return f'<figure class="fig"><a href="/assets/img/{big}" class="figlink">{img}</a>{cap}</figure>'


def headshot(sizes, eager=False, link=False, caption=False, bg="main"):
    """The headshot as <picture>: WebP first, JPEG fallback, 400/800/1200w; explicit width/height (no layout shift);
    lazy unless eager (above the fold). link=True wraps it in a link to the 1200px JPEG (Media page download)."""
    files, w, h = IMG["joachim-agou-headshot"]
    if bg != "main": files = hs_files(bg)
    for f in files.values():
        for ext in (".jpg", ".webp"):
            if not (ROOT / "assets/img" / f.replace(".jpg", ext)).exists(): sys.exit(f"headshot file missing: assets/img/{f.replace('.jpg', ext)} (run tools/make_headshot.py)")
    srcset = lambda ext: ", ".join(f"/assets/img/{f.replace('.jpg', ext)} {wd}w" for wd, f in sorted(files.items()))
    big = files[max(files)]
    img = (f'<picture><source type="image/webp" srcset="{srcset(".webp")}" sizes="{sizes}">'
           f'<img src="/assets/img/{files[800]}" srcset="{srcset(".jpg")}" sizes="{sizes}" width="{w}" height="{h}" alt="{esc(HEADSHOT_ALT)}" '
           f'{"fetchpriority=\"high\"" if eager else "loading=\"lazy\""} decoding="async"></picture>')
    if link: img = f'<a href="/assets/img/{big}" class="figlink">{img}</a>'
    cap = f"<figcaption>{esc(HEADSHOT_ALT)}</figcaption>" if caption else ""
    return f'<figure class="fig headshot">{img}{cap}</figure>'


def vic_picture(pid, var, lang, sizes, cls="vphoto", min_width=None):
    """A Victoria photo (site.json victoria_photos) as <picture>: AVIF, then WebP, JPEG fallback; width/height set (no layout
    shift); always lazy (none of them is above the fold on a phone). The photo's credit goes in this page's footer.
    min_width: show it only from that viewport width; below it the first <source> picks a 1x1 data: GIF, so phones download
    nothing (the CSS hides the tile there too)."""
    P = VIC["photos"][pid]; aw, ah, widths = VIC_VARIANTS[var]
    if var not in P["focus"]: sys.exit(f"victoria_photos: {pid} has no {var!r} crop (add it to focus, run tools/make_vic_photos.py)")
    f = lambda w, ext: f"/assets/img/vic/{pid}-{var}-{w}.{ext}"
    for w in widths:
        for ext in ("avif", "webp", "jpg"):
            if not (ROOT / f(w, ext).lstrip("/")).exists(): sys.exit(f"victoria photo missing: {f(w, ext)} (run tools/make_vic_photos.py)")
    ss = lambda ext: ", ".join(f"{f(w, ext)} {w}w" for w in widths)
    W = widths[-1]; H = round(W * ah / aw)
    if pid not in PAGE_STATE["vic_used"]: PAGE_STATE["vic_used"].append(pid)
    skip = f'<source media="(max-width: {min_width - 0.02}px)" srcset="{BLANK_GIF}">' if min_width else ""
    return (f'<picture class="{cls}">{skip}<source type="image/avif" srcset="{ss("avif")}" sizes="{sizes}"><source type="image/webp" srcset="{ss("webp")}" sizes="{sizes}">'
            f'<img src="{f(widths[1], "jpg")}" srcset="{ss("jpg")}" sizes="{sizes}" width="{W}" height="{H}" alt="{esc(P["alt"][lang])}" loading="lazy" decoding="async"></picture>')


def vic_strip(pid, lang, cls="vstrip"):
    return f'<figure class="{cls}">{vic_picture(pid, "strip", lang, "(min-width: 860px) 800px, calc(100vw - 40px)")}</figure>'


def vic_credits(lang):
    """Footer credit for each Victoria photo on this page (CC BY / CC BY-SA: title, author, licence, and that it was cropped,
    or cropped with passers-by blurred when the photo has 'blur'). A public-domain photo has no licence link (licence_url "")."""
    V = UI[lang]["vic"]; out = []
    for pid in PAGE_STATE["vic_used"]:
        P = VIC["photos"][pid]; colon = " :" if lang == "fr" else ":"
        lic = (f'<a href="{esc(P["licence_url"])}" rel="license">{esc(P["licence"])}</a>' if P.get("licence_url") else esc(P["licence"]))
        out.append(f'<p class="credit">{esc(V["credit_prefix"])} ({esc(P["place"][lang])}){colon} <a href="{esc(P["source_url"])}">{esc(P["title"])}</a>, '
                   f'{esc(P["author"])}, {lic}{esc(V["cropped_blurred"] if P.get("blur") else V["cropped"])}.</p>')
    return "".join(out)


VBAND_DESKTOP = 768  # px: from here the home band shows victoria_photos.home_desktop too (one row of 6, full content width)

def vic_band(lang, env="staging"):
    """Home: small neighbourhood photos under the hero, each linking to the riding map section. Phones: the 3 'home' tiles
    (unchanged). With home_band6_live (always on staging), from 768px: one row of 6 equal tiles across the content width
    ('home' + 'home_desktop', ul.six); the extra 3 are hidden and never downloaded below 768px (vic_picture min_width).
    Without it (live until Joachim approves): exactly the previous 3-tile band."""
    V = UI[lang]["vic"]; target = "#riding-map"
    six = bool(VIC.get("home_desktop")) and (env == "staging" or bool(SITE.get("home_band6_live")))
    sizes = (f"(min-width: 1120px) 171px, (min-width: {VBAND_DESKTOP}px) calc((100vw - 96px) / 6), calc((100vw - 64px) / 3)" if six
             else "(min-width: 800px) 240px, calc((100vw - 64px) / 3)")
    tile = lambda pid, extra: (f'<li{" class=\"vband-d\"" if extra else ""}><a href="{target}">'
                               f'{vic_picture(pid, "tile", lang, sizes, min_width=VBAND_DESKTOP if extra else None)}'
                               f'<span class="vband-l">{esc(VIC["photos"][pid]["place"][lang])}</span></a></li>')
    tiles = "".join(tile(pid, False) for pid in VIC["home"]) + ("".join(tile(pid, True) for pid in VIC["home_desktop"]) if six else "")
    return (f'<section class="vband" aria-label="{esc(V["band_label"])}"><div class="wrap"><ul{" class=\"six\"" if six else ""}>{tiles}</ul>'
            f'<p class="vband-map"><a href="{target}">{esc(V["band_map"])} <span aria-hidden="true">↓</span></a></p></div></section>')


def vic_priorities(body, lang):
    """Priorities: a slim photo strip under each numbered priority heading and under 'Also for this riding'."""
    for k, pid in VIC["priorities"].items():
        if k == "also":
            pat = r'<h2 id="[^"]+">(?:Also for this riding|D(?:\'|’|&#x27;)autres priorités pour la circonscription)</h2>'
        else:
            pat = rf'<h2 id="[^"]+">{re.escape(k)}\. [^<]*</h2>'
        m = re.search(pat, body)
        if not m: sys.exit(f"priorities ({lang}): heading for victoria_photos.priorities[{k!r}] not found (Notion heading changed?)")
        body = body[:m.end()] + vic_strip(pid, lang) + body[m.end():]
    return body


def vic_events_cfg(lang):
    """Events: forms.js shows a small venue photo on each list card, matched only against the public event data
    (get_public_events): address first, then neighbourhood."""
    E = VIC["events"]; ids = [i for i in dict.fromkeys(list(E["address"].values()) + list(E["neighbourhood"].values())) if i]  # null = venue with no licensed photo of its block: no photo, no neighbourhood fallback
    for pid in ids:
        if pid not in PAGE_STATE["vic_used"]: PAGE_STATE["vic_used"].append(pid)
        if "thumb" not in VIC["photos"][pid]["focus"]: sys.exit(f"victoria_photos: {pid} needs a 'thumb' crop for the events page")
    return {"base": "/assets/img/vic/", "widths": list(VIC_VARIANTS["thumb"][2]), "address": {k: v for k, v in E["address"].items()},
            "neighbourhood": {k: v for k, v in E["neighbourhood"].items()}, "alt": {pid: VIC["photos"][pid]["alt"][lang] for pid in ids}}


# ---------------- block markdown (Notion subset) ----------------
def render(md, lang, ctx, toc_levels=("h2",)):
    lines = md.split("\n")
    out, heads = [], []
    i = 0
    list_open = False
    section_open = False
    last_h2 = 0

    def close_list():
        nonlocal list_open
        if list_open:
            out.append("</ul>"); list_open = False

    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s:
            i += 1; continue
        if s.startswith("## "):
            close_list()
            if section_open: out.append("</section>")
            t = s[3:].strip(); hid = slugify(re.sub(r"\*", "", t)); heads.append((hid, t))
            out.append(f'<section class="block" aria-labelledby="{hid}"><h2 id="{hid}">{inline(t, ctx)}</h2>')
            last_h2 = len(out); section_open = True; i += 1; continue
        if s.startswith("### "):
            close_list(); t = s[4:].strip(); out.append(f'<h3 id="{slugify(t)}">{inline(t, ctx)}</h3>'); i += 1; continue
        if s.startswith("<callout"):
            close_list(); j = i + 1; inner = []
            while not lines[j].strip().startswith("</callout>"):
                inner.append(lines[j][1:] if lines[j].startswith("\t") else lines[j]); j += 1
            body = render("\n".join(inner), lang, ctx)[0]
            out.append(f'<div class="callout">{body}</div>'); i = j + 1; continue
        if s.startswith("<details>"):
            close_list(); j = i + 1
            summ = re.sub(r"</?summary>", "", lines[j].strip()); j += 1; inner = []
            while not lines[j].strip().startswith("</details>"):
                inner.append(lines[j][1:] if lines[j].startswith("\t") else lines[j]); j += 1
            body = render("\n".join(inner), lang, ctx)[0]
            out.append(f'<details class="more-details"><summary>{inline(summ, ctx)}</summary><div class="details-body">{body}</div></details>'); i = j + 1; continue
        if s == "<table_of_contents/>":
            close_list(); out.append("<!--TOC-->"); i += 1; continue
        if s == "<more/>":  # Priorities: explicit 'Read more' split (collapse() keeps everything above it visible)
            close_list(); out.append("<!--MORE-->"); i += 1; continue
        if s.startswith("<draft>"):
            close_list(); out.append(f'<div class="draft" role="note">{esc(re.sub(r"</?draft>", "", s))}</div>'); i += 1; continue
        if s.startswith("<placeholder>"):
            close_list(); key = re.sub(r"</?placeholder>", "", s).strip().lower()
            if key == "mediakit" and MEDIAKIT["on"]:
                out.append(mediakit_block(lang)); i += 1; continue
            txt = UI[lang].get("placeholder_" + key) or UI["en"].get("placeholder_" + key)
            out.append(f'<div class="placeholder" role="note"><strong>[Placeholder]</strong> {esc(txt)}</div>'); i += 1; continue
        m = re.match(r'<page url="([^"]+)">(.*)</page>', s)
        if m:
            close_list(); out.append(f'<p class="pagelink"><a href="{esc(m.group(1))}">{esc(m.group(2))} <span aria-hidden="true">→</span></a></p>'); i += 1; continue
        m = re.match(r"!\[(.*)\]\((\S+)\)$", s)
        if m:
            close_list(); out.append(picture(m.group(2), m.group(1), lang))
            if SITE["images"].get(pathlib.PurePosixPath(m.group(2).split("?")[0]).name) in SITE.get("more_photos_after", []):
                out.append(f'<p class="readlink"><a href="{esc(SITE["social"]["campaign"]["Instagram"])}" rel="noopener">{esc(UI[lang]["more_photos"])} <span aria-hidden="true">↗</span></a></p>')
            i += 1; continue
        if s == "---":
            close_list(); out.append("<hr>"); i += 1; continue
        if re.match(r"^- ", s) and not ln.startswith("\t"):
            if not list_open: out.append("<ul>"); list_open = True
            item = inline(s[2:], ctx)
            j = i + 1; extra = []
            while j < len(lines) and lines[j].startswith("\t") and lines[j].strip():
                extra.append(f'<span class="sub">{inline(lines[j].strip(), ctx)}</span>'); j += 1
            out.append(f"<li>{item}{''.join(extra)}</li>"); i = j; continue
        close_list()
        s2 = re.sub(r'<mention-page url="([^"]+)"/>', lambda mm: f'[{mention_title(mm.group(1))}]({mm.group(1)})', s)
        mr = re.match(r"^\[\*\*→\s*(.*?)\*\*\]\((/(?:fr/)?(?:faq|about|priorities|media)/)\)$", s2)
        if mr:  # a reading/navigation link, not an action: text link with one trailing arrow
            out.append(f'<p class="pagelink"><a href="{esc(mr.group(2))}">{inline(mr.group(1), ctx)} <span aria-hidden="true">→</span></a></p>'); i += 1; continue
        if re.match(r"^\[\*\*→", s2):
            kind = "primary" if not any('class="btn primary"' in o for o in out[last_h2:]) else "sec"
            a = re.sub(r"^<a ", f'<a class="btn {kind}" ', inline(re.sub(r"^\[\*\*→\s*", "[**", s2), ctx))
            out.append(f'<p class="cta-line">{a}</p>'); i += 1; continue
        out.append(f"<p>{inline(s2, ctx)}</p>"); i += 1
    close_list()
    if section_open: out.append("</section>")
    htmls = "\n".join(out)
    if "<!--TOC-->" in htmls:
        pos = htmls.index("<!--TOC-->")
        after = [h for h in heads if f'id="{h[0]}"' in htmls[pos:]]
        toc = '<nav class="toc" aria-label="' + esc(UI[lang]["toc"]) + '"><ul>' + "".join(f'<li><a href="#{h}">{inline(t, ctx)}</a></li>' for h, t in after) + "</ul></nav>"
        htmls = htmls.replace("<!--TOC-->", toc)
    return htmls, heads


COLLAPSE_EN = {}  # (page, section index) -> number of children the English page keeps visible (French review: same split in FR)


def collapse(html, lang, keep_chars=320, min_hidden=300, page=None):
    """Presentation only: in each <section class="block">, keep the first children visible (about keep_chars of text),
    put the rest in a region toggled by a 'Read more' button. Without JS the region stays visible (the button is hidden).
    Trailing call-to-action / page links stay visible. Text is unchanged (diffcheck still sees every line)."""
    U = UI[lang]; lines = html.split("\n"); out = []; i = 0; n = 0; sec = -1
    while i < len(lines):
        ln = lines[i]
        if not ln.startswith('<section class="block"'):
            out.append(ln); i += 1; continue
        j = i + 1; kids = []; sec += 1
        bal = lambda s: len(re.findall(r"<(div|details|figure|ul|nav|picture)\b", s)) - len(re.findall(r"</(div|details|figure|ul|nav|picture)>", s))
        while j < len(lines) and lines[j] != "</section>":
            k = j; chunk = [lines[j]]
            while bal("\n".join(chunk)) > 0 and k + 1 < len(lines):
                k += 1; chunk.append(lines[k])
            kids.append("\n".join(chunk)); j = k + 1
        tail = []
        while kids and re.match(r'<p class="(cta-line|pagelink)"', kids[-1]):
            tail.insert(0, kids.pop())
        txt = lambda h: len(re.sub(r"<[^>]+>", "", h))
        vis = []; explicit = "<!--MORE-->" in kids
        if explicit:  # <more/> marker: everything above it stays visible (main actions, 'What changes for you', 'How you'll know'); the rest goes behind 'Read more'
            k_ = kids.index("<!--MORE-->"); vis, kids = kids[:k_], kids[k_ + 1:]
            if "<!--MORE-->" in kids: sys.exit(f"collapse: more than one <more/> marker in one section ({ln[:80]})")
        en_n = COLLAPSE_EN.get((page, sec)) if lang == "fr" and page else None
        if not explicit and en_n:  # French: keep visible the same paragraphs as the English page (French text runs longer)
            while kids and len(vis) < en_n:
                vis.append(kids.pop(0))
        while not explicit and not en_n and kids and (not vis or sum(map(txt, vis)) < keep_chars):
            vis.append(kids.pop(0))
        if lang == "en" and page and not explicit:
            COLLAPSE_EN[(page, sec)] = len(vis)
        if kids and (explicit or sum(map(txt, kids)) >= min_hidden) and not any("<details" in k or "<nav" in k for k in kids):
            n += 1; rid = f"rm-{slugify(re.sub(r'<[^>]+>', '', ln))[:40]}-{n}"
            vis += [f'<div class="rm-more" id="{rid}">' + "\n".join(kids) + "</div>",
                    f'<p class="rm"><button type="button" class="rm-toggle" aria-expanded="true" aria-controls="{rid}" data-more="{esc(U["read_more"])}" data-less="{esc(U["show_less"])}" hidden>{esc(U["show_less"])}</button></p>']
        else:
            vis += kids
        out += [ln] + vis + tail + (["</section>"] if j < len(lines) else [])
        i = j + 1
    return "\n".join(out)


def mention_title(u):
    for p in PAGES:
        for l in LANGS:
            if url(l, p["key"]) == u: return p["nav"][l]
    return u


def read(lang, key):
    if PARTY["on"] and key == "privacy" and (ROOT / "content" / lang / "privacy-party.md").exists():
        key = "privacy-party"
    p = ROOT / "content" / lang / f"{key}.md"
    t = p.read_text() if p.exists() else None
    if t is not None and PARTY["on"]:
        for a_, b_ in PARTY_MD.get((lang, key), []):
            if t.count(a_) != 1: sys.exit(f"party links: {lang}/{key}.md: text to replace not found once (Notion text changed?): {a_[:80]!r}")
            t = t.replace(a_, b_)
    if t is not None and DRAFT_ENV["env"]:
        for name_, d_ in DRAFTS.items():
            if not DRAFT_ON(name_, DRAFT_ENV["env"]): continue
            for a_, b_ in d_["edits"].get(f"{lang}/{key}", []):
                if t.count(a_) != 1: sys.exit(f"staging draft {name_}: {lang}/{key}.md: text to replace not found once (live text changed? redo the draft): {a_[:80]!r}")
                t = t.replace(a_, b_)
    t = no_party.apply(t, lang, key)
    if key == "media" and t is not None and not MEDIAKIT["on"]:  # Joachim 8 Oct 2026 7:15 PM PT: no PDF -> no 'Media kit (PDF)' section or placeholder
        parts = re.split(r"(?m)^(?=## )", t)
        keep = [p_ for p_ in parts if not (p_.startswith("## ") and "<placeholder>MEDIAKIT</placeholder>" in p_)]
        if len(keep) != len(parts) - 1: sys.exit(f"media: {lang}/{key}: expected exactly one '## …' section holding <placeholder>MEDIAKIT</placeholder>")
        t = "".join(keep)
    if HIDE_EG["on"] and t is not None and f"{lang}/{key}" in HIDE_EG_EDITS:
        t = no_party.apply_ops(t, HIDE_EG_EDITS[f"{lang}/{key}"], f"hide_events_getinvolved {lang}/{key}")
    return t


def page_drafts(lang, key, md):
    """Staging drafts scoped to one page built from a home section (edits keyed '<lang>/<page key>', e.g. 'en/how-to-vote'):
    applied to that page's section text only, so the home page keeps the Notion text. Same rules as read(): exact find, once."""
    if not DRAFT_ENV["env"]: return md
    for name_, d_ in DRAFTS.items():
        if not DRAFT_ON(name_, DRAFT_ENV["env"]): continue
        for a_, b_ in d_["edits"].get(f"{lang}/{key}", []):
            if md.count(a_) != 1: sys.exit(f"staging draft {name_}: {lang}/{key} (home section): text to replace not found once (Notion text changed? redo the draft): {a_[:80]!r}")
            md = md.replace(a_, b_)
    return no_party.apply(md, lang, key)


def draft_updated(lang, key):
    """'Last updated' date of the drafts that change this page (draft 'updated' field), when they apply to this build."""
    if not DRAFT_ENV["env"]: return None
    ds = [d_.get("updated") for n_, d_ in DRAFTS.items() if DRAFT_ON(n_, DRAFT_ENV["env"]) and f"{lang}/{key}" in d_["edits"]]
    return max([d for d in ds if d], default=None)


HTV_V2 = lambda env: "how_to_vote_v2" in DRAFTS and DRAFT_ON("how_to_vote_v2", env)  # How to vote v2 (6 Oct 2026, staging until Joachim approves)


def section(md, title):
    m = re.search(r"^## " + re.escape(title) + r"\s*$", md, re.M)
    if not m: sys.exit(f"Section '## {title}' not found in home page content.")
    rest = md[m.end():]
    n = re.search(r"^## ", rest, re.M)
    return rest[: n.start()] if n else rest


# ---------------- forms (static HTML; logic in assets/js/forms.js) ----------------
def f_input(id_, label, typ="text", attrs="", opt=None, hint=None):
    o = f' <span class="opt">{esc(opt)}</span>' if opt else ""
    h = f' <span class="opt">{esc(hint)}</span>' if hint else ""
    return f'<label class="f" for="{id_}">{esc(label)}{h}{o}</label><input id="{id_}" name="{id_}" type="{typ}" {attrs}>'


def honeypot(T):
    return f'<div class="hp" aria-hidden="true"><label>{esc(T["honeypot"])} <input id="website" type="text" tabindex="-1" autocomplete="off"></label></div>'


def vol_checks(T, key, name):  # volunteer help / availability checkboxes (optional; values are the database keys)
    cbs = "".join(f'<div class="cb"><input type="checkbox" name="{name}" id="{name}_{v}" value="{esc(v)}"><label for="{name}_{v}">{esc(l)}</label></div>' for v, l in T[key])
    return f'<fieldset class="vchecks"><legend>{esc(T[key + "_legend"])} <span class="opt">{esc(T["optional"])}</span></legend><p class="hint">{esc(T[key + "_hint"])}</p>{cbs}</fieldset>'


def form_html(kind, lang, warm=False):
    T = UI[lang][kind] if kind != "events" else UI[lang]["events"]
    if kind == "volunteer":
        body = (f'<div class="row"><div>{f_input("first_name", T["first_name"], attrs="autocomplete=\"given-name\" autocapitalize=\"words\" required maxlength=\"80\"")}</div>'
                f'<div>{f_input("last_name", T["last_name"], attrs="autocomplete=\"family-name\" autocapitalize=\"words\" required maxlength=\"80\"")}</div></div>'
                + f_input("email", T["email"], "email", 'autocomplete="email" autocapitalize="off" spellcheck="false" required maxlength="200" inputmode="email"')
                + f_input("phone", T["phone"], "tel", 'autocomplete="tel" required maxlength="30" inputmode="tel"')
                + f_input("address", T["address"], "text", f'autocomplete="street-address" maxlength="200" placeholder="{esc(T["address_ph"])}"', opt=T["optional"])
                + (vol_checks(T, "help", "help") + vol_checks(T, "avail", "avail") if warm else "")
                + f'<div class="cb"><input id="consent" type="checkbox" required><label for="consent">{esc(T["consent"])}</label></div>')
    elif kind == "nominate":
        sess = "".join(f'<div class="cb"><input type="checkbox" name="session" id="s{i}" value="{esc(v)}"><label for="s{i}">{esc(l)}</label></div>' for i, (v, l) in enumerate(T["sessions"]))
        body = (f_input("full_name", T["full_name"], attrs='autocomplete="name" required maxlength="120"')
                + f_input("street_address", T["street_address"], attrs=f'autocomplete="street-address" required maxlength="200" placeholder="{esc(T["street_ph"])}"', hint=T["street_hint"])
                + f_input("phone", T["phone"], "tel", 'autocomplete="tel" required maxlength="30" inputmode="tel"')
                + f_input("email", T["email"], "email", 'autocomplete="email" maxlength="200" inputmode="email" autocapitalize="off" spellcheck="false"', opt=T["optional"])
                + f_input("best_time", T["best_time"], attrs=f'maxlength="200" placeholder="{esc(T["best_time_ph"])}"')
                + f'<fieldset><legend>{esc(T["sessions_legend"])}</legend><p class="hint">{esc(T["sessions_hint"])}</p>{sess}</fieldset>'
                + f'<div class="cb"><input id="consent" type="checkbox" required><label for="consent">{esc(T["consent"])}</label></div>')
    elif kind == "lawnsign":
        pl = "".join(f'<div class="cb"><input id="pl{i}" type="radio" name="placement" value="{esc(v)}"><label for="pl{i}">{esc(l)}</label></div>' for i, (v, l) in enumerate(T["placements"]))
        body = (f'<div class="row"><div>{f_input("first_name", T["first_name"], attrs="autocomplete=\"given-name\" autocapitalize=\"words\" required maxlength=\"80\"")}</div>'
                f'<div>{f_input("last_name", T["last_name"], attrs="autocomplete=\"family-name\" autocapitalize=\"words\" required maxlength=\"80\"")}</div></div>'
                + f_input("email", T["email"], "email", 'autocomplete="email" autocapitalize="off" spellcheck="false" required maxlength="200" inputmode="email"')
                + f_input("phone", T["phone"], "tel", 'autocomplete="tel" required maxlength="30" inputmode="tel"')
                + f'<div class="row"><div>{f_input("street_address", T["street_address"], attrs=f"autocomplete=\"address-line1\" autocapitalize=\"words\" required maxlength=\"200\" placeholder=\"{esc(T["street_ph"])}\"")}</div>'
                f'<div class="sm">{f_input("unit", T["unit"], attrs=f"autocomplete=\"address-line2\" maxlength=\"20\" placeholder=\"{esc(T["unit_ph"])}\"", opt=T["optional"])}</div></div>'
                f'<div class="row"><div>{f_input("city", T["city"], attrs="autocomplete=\"address-level2\" autocapitalize=\"words\" required maxlength=\"80\" value=\"Victoria\"")}</div>'
                f'<div class="sm">{f_input("postal_code", T["postal_code"], attrs="autocomplete=\"postal-code\" autocapitalize=\"characters\" spellcheck=\"false\" required maxlength=\"7\" placeholder=\"V8V 1A1\"")}</div></div>'
                + f'<fieldset><legend>{esc(T["placement_legend"])} <span class="opt">{esc(T["optional"])}</span></legend>{pl}</fieldset>'
                + f'<div class="cb"><input id="large_sign" type="checkbox"><label for="large_sign">{esc(T["large"])}</label></div>'
                + f'<label class="f" for="delivery_notes">{esc(T["notes"])} <span class="opt">{esc(T["optional"])}</span></label><textarea id="delivery_notes" name="delivery_notes" maxlength="500" rows="3" autocomplete="off" placeholder="{esc(T["notes_ph"])}"></textarea>'
                + f'<div class="cb req"><input id="permission" type="checkbox" required><label for="permission">{esc(T["permission"])}</label></div>'
                + f'<div class="cb"><input id="consent" type="checkbox" required><label for="consent">{esc(T["consent"])}</label></div>')
    call = f'<p class="vcall">{esc(T["call"])}</p>' if warm else ""
    btn = call + f'<button id="btn" class="btn primary block" type="submit">{esc(T["button"])}</button><div id="msg" class="msg" role="status" aria-live="polite" tabindex="-1"></div>'
    return f'<form id="f" class="card form" novalidate>{body}{honeypot(T)}{btn}</form>'


def form_block(kind, lang, warm=False):
    T = UI[lang][kind]
    intro = f'<p>{esc(T["intro"])}</p>' + (f'<p>{esc(T["delivery"])}</p>' if kind == "lawnsign" else "")
    # warm volunteer page: no second "Volunteer…" heading (the page h1 already says it); the form keeps its accessible name
    head = (f'<h2 id="form-title" class="vh">{esc(T["title"])}</h2>' if warm else f'<h2 id="form-title">{esc(T["title"])}</h2>')
    return (f'<section class="block formblock" id="form" aria-labelledby="form-title">{head}'
            f'<p class="sub">{esc(T["sub"])}</p><div class="intro">{intro}</div>{form_html(kind, lang, warm)}'
            f'<p class="privacy-note"><a href="{url(lang, "privacy")}">{esc(BYKEY["privacy"]["nav"][lang])}</a></p></section>')


# ---------------- page shell ----------------
ICONS = {
    "Instagram": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M12 2.2c3.2 0 3.6 0 4.8.1 1.2.1 1.8.2 2.2.4.6.2 1 .5 1.4.9.4.4.7.8.9 1.4.2.4.4 1.1.4 2.2.1 1.3.1 1.6.1 4.8s0 3.6-.1 4.8c-.1 1.2-.2 1.8-.4 2.2-.2.6-.5 1-.9 1.4-.4.4-.8.7-1.4.9-.4.2-1.1.4-2.2.4-1.3.1-1.6.1-4.8.1s-3.6 0-4.8-.1c-1.2-.1-1.8-.2-2.2-.4-.6-.2-1-.5-1.4-.9-.4-.4-.7-.8-.9-1.4-.2-.4-.4-1.1-.4-2.2C2.2 15.6 2.2 15.2 2.2 12s0-3.6.1-4.8c.1-1.2.2-1.8.4-2.2.2-.6.5-1 .9-1.4.4-.4.8-.7 1.4-.9.4-.2 1.1-.4 2.2-.4C8.4 2.2 8.8 2.2 12 2.2zm0 1.8c-3.1 0-3.5 0-4.7.1-1.1.1-1.7.2-2.1.4-.5.2-.9.4-1.3.8-.4.4-.6.8-.8 1.3-.2.4-.3 1-.4 2.1C2.6 8.9 2.6 9.3 2.6 12s0 3.1.1 4.3c.1 1.1.2 1.7.4 2.1.2.5.4.9.8 1.3.4.4.8.6 1.3.8.4.2 1 .3 2.1.4 1.2.1 1.6.1 4.7.1s3.5 0 4.7-.1c1.1-.1 1.7-.2 2.1-.4.5-.2.9-.4 1.3-.8.4-.4.6-.8.8-1.3.2-.4.3-1 .4-2.1.1-1.2.1-1.6.1-4.3s0-3.1-.1-4.3c-.1-1.1-.2-1.7-.4-2.1-.2-.5-.4-.9-.8-1.3-.4-.4-.8-.6-1.3-.8-.4-.2-1-.3-2.1-.4C15.5 4 15.1 4 12 4zm0 3.1a4.9 4.9 0 110 9.8 4.9 4.9 0 010-9.8zm0 8a3.1 3.1 0 100-6.2 3.1 3.1 0 000 6.2zm5.1-8.3a1.1 1.1 0 110-2.3 1.1 1.1 0 010 2.3z"/></svg>',
    "X": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M18.2 2.3h3.4l-7.4 8.4 8.7 11.5h-6.8l-5.3-7-6.1 7H1.3l7.9-9L.9 2.3h7l4.8 6.4 5.5-6.4zm-1.2 17.9h1.9L7.1 4.2H5.1l11.9 16z"/></svg>',
    "Facebook": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M22 12a10 10 0 10-11.6 9.9v-7H7.9V12h2.5V9.8c0-2.5 1.5-3.9 3.8-3.9 1.1 0 2.2.2 2.2.2v2.5h-1.3c-1.2 0-1.6.8-1.6 1.6V12h2.8l-.4 2.9h-2.3v7A10 10 0 0022 12z"/></svg>',
}


def social_links(cls, lang):
    """Campaign: Facebook · Instagram, then Personal: Instagram · Facebook · X (site.json social; Joachim, 2 Oct 2026)."""
    G = UI[lang]["social_groups"]; colon = "\u00a0:" if lang == "fr" else ":"
    rows = []
    for g in ("campaign", "personal"):
        lab = G[g]
        items = "".join(f'<li><a href="{esc(u)}" rel="me noopener"><span class="vh">{esc(lab)} </span>{ICONS[n]}<span>{n}</span></a></li>' for n, u in SITE["social"][g].items())
        rows.append(f'<div class="soc-row"><span class="soc-glabel" aria-hidden="true">{esc(lab)}{colon}</span><ul class="{cls}" aria-label="{esc(lab)}">{items}</ul></div>')
    return "".join(rows)


def footer(lang, ctx):
    U = UI[lang]
    md = read(lang, "_contact")
    lines = [l for l in md.split("\n") if l.strip() and not re.match(r"^\*(Authorized|Autorisé) by|^\*(Authorized|Autorisé) par", l.strip())]
    # split: contact lines (email/phone + socials) | financial agent box | other
    fa_i = next(i for i, l in enumerate(lines) if l.startswith("**"))
    contact = lines[:fa_i]; fa = lines[fa_i:fa_i + 3]; rest = lines[fa_i + 3:]
    contact_html = "".join(f"<p>{inline(l, ctx)}</p>" for l in contact if "instagram.com" not in l)
    fa_html = f'<div class="fa-box"><p class="fa-title">{inline(fa[0], ctx)}</p>' + "".join(f"<p>{inline(l, ctx)}</p>" for l in fa[1:]) + "</div>"
    skip = {url(lang, k) for k in SITE["footer_nav"]} | hidden_urls()
    rest = [l for l in rest if not re.match(r'<page url="([^"]+)">', l.strip()) or re.match(r'<page url="([^"]+)">', l.strip()).group(1) not in skip]
    rest = [re.sub(r'^<page url="([^"]+)">(.*)</page>$', r"[\2](\1)", l.strip()) for l in rest]
    rest_html = "".join(f"<p>{inline(re.sub(r'<mention-page url=\"([^\"]+)\"/>', lambda m: f'[{mention_title(m.group(1))}]({m.group(1)})', l), ctx)}</p>" for l in rest)
    nav = "".join(f'<li><a href="{url(lang, k)}">{esc(BYKEY[k]["nav"][lang])}</a></li>' for k in SITE["footer_nav"])
    contact_h = "Contact" if lang == "en" else "Coordonnées"
    auth_en = "Authorized by Bert Chen, financial agent, bert@bertchen.ca, 778-996-9910."
    auth = f'<p class="auth">{auth_en}</p>' if lang == "en" else f'<p class="auth">Autorisé par Bert Chen, agent financier, bert@bertchen.ca, 778-996-9910.</p><p class="auth" lang="en">{auth_en}</p>'
    return (f'<footer class="site-footer"><div class="wrap fgrid">'
            f'<section aria-labelledby="fc"><h2 id="fc">{contact_h}</h2>{contact_html}<p class="soc-label">{esc(U["social_label"])}</p>{social_links("social", lang)}{rest_html}</section>'
            f'<section aria-label="{esc(fa[0].strip("*"))}">{fa_html}</section>'
            f'<nav aria-label="{esc(U["footer_nav"])}"><ul class="fnav">{nav}</ul></nav>'
            f'</div><div class="wrap">{auth}{bg_credit(lang)}{vic_credits(lang)}</div></footer>')


def bg_credit(lang):
    """Attribution the background photo's licence requires (CC BY / CC BY-SA): small footer line on every page that can show the headshot."""
    return "".join(credit_line(SITE["headshot_backgrounds"][v], lang) for v in HS_USED)


def credit_line(c, lang):
    return (f'<p class="credit">{esc(c["credit_prefix"][lang])} <a href="{esc(c["source_url"])}">{esc(c["title"])}</a>, '
            f'{esc(c["author"])}, <a href="{esc(c["licence_url"])}" rel="license">{esc(c["licence"])}</a>{esc(c["credit_suffix"][lang])}</p>')


def shell(lang, page, title, desc, main_html, env, extra_head="", robots_override=None):
    U = UI[lang]; key = page["key"]; other = "fr" if lang == "en" else "en"
    path = url(lang, key); opath = url(other, key)
    canonical = LIVE + path
    robots = "noindex, nofollow" if env == "staging" else (robots_override or ("noindex" if page.get("robots") == "noindex" else "index, follow"))
    # search/social metadata (seo.json): every real page gets its own title and description; the 404 page keeps its own
    meta = SEO["pages"].get(key, {}).get(lang) if robots_override is None else None
    if meta:
        title = meta.get("home_title") or meta["title"] + SEO["suffix"][lang]
        desc = meta["desc"]
    OG = dict(SEO["og_image"]); OG["alt"] = dict(OG["alt"]); OG["type"] = "image/jpeg" if OG[lang].endswith(".jpg") else "image/png"
    og_img = f'{LIVE if env == "live" else STAGING_ORIGIN}/assets/img/{OG[lang]}'
    og_type = "profile" if key == "about" else "website"
    po = page.get("og") or {}  # a page's own share image/type (Updates permalinks: first photo, og:type article)
    if po.get("path"):
        og_img = f'{LIVE if env == "live" else STAGING_ORIGIN}{po["path"]}'; OG["width"], OG["height"], OG["alt"][lang], OG["type"] = po["w"], po["h"], po["alt"], po["type"]
    og_type = po.get("og_type", og_type)
    if robots_override is None:
        alt_links = (f'<link rel="canonical" href="{canonical}">\n'
                     + "".join(f'<link rel="alternate" hreflang="{h}" href="{LIVE + url(l, key)}">\n' for h, l in (("en-CA", "en"), ("fr-CA", "fr"), ("x-default", "en"))))
        og_url = f'<meta property="og:url" content="{canonical}">\n'
    else:  # 404: no canonical, alternates or og:url (it is not a page of its own)
        alt_links = ""; og_url = ""
    extra_head = json_ld(lang, key, title, desc, canonical, env) + extra_head if robots_override is None else extra_head
    def cur(k):
        return ' aria-current="page"' if k == key else ""
    items = []
    for k in SITE["main_nav"]:
        if k in HIDDEN: continue
        p = BYKEY[k]
        kids = p.get("children") or []
        sub = ""
        if kids:
            sub = '<ul class="subnav">' + "".join(f'<li><a href="{url(lang, c)}"{cur(c)}>{esc(BYKEY[c]["nav"][lang])}</a></li>' for c in kids) + "</ul>"
        active = ' class="active"' if key in kids else ""
        badge = events_cal.nav_badge(lang, SITE, UI) if k == "events" and CAL_ON(env) else ""
        items.append(f'<li{" class=\"has-sub\"" if kids else ""}><a href="{url(lang, k)}"{cur(k)}{active}>{esc(p.get("nav_short", p["nav"])[lang])}{badge}</a>{sub}</li>')
    navs = ("" if "volunteer" in HIDDEN else f'<li class="nav-cta"><a class="btn primary" href="{url(lang, "volunteer")}">{esc(U["cta_volunteer"])}</a></li>') + "".join(items)
    staging = f'<div class="staging" role="note">{esc(U["staging"])}</div>' if env == "staging" else ""
    evbase = f' data-lang-switch data-base="{opath}"' if key == "events" else ""
    cta_v = url(lang, "volunteer"); cta_d = url(lang, "donate")
    return f"""<!doctype html>
<html lang="{lang}-CA">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="robots" content="{robots}">
{alt_links}<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{esc(U['site_name'])}">
<meta property="og:locale" content="{'en_CA' if lang == 'en' else 'fr_CA'}">
<meta property="og:locale:alternate" content="{'fr_CA' if lang == 'en' else 'en_CA'}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
{og_url}<meta property="og:image" content="{og_img}">
<meta property="og:image:type" content="{OG['type']}">
<meta property="og:image:width" content="{OG['width']}"><meta property="og:image:height" content="{OG['height']}">
<meta property="og:image:alt" content="{esc(OG['alt'][lang])}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{og_img}">
<meta name="twitter:image:alt" content="{esc(OG['alt'][lang])}">
<meta name="theme-color" content="#123a6d">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/assets/img/favicon.svg?v=joa" type="image/svg+xml">
<link rel="icon" href="/assets/img/favicon-32.png?v=joa" type="image/png" sizes="32x32">
<link rel="icon" href="/assets/img/favicon-16.png?v=joa" type="image/png" sizes="16x16">
<link rel="apple-touch-icon" href="/assets/img/apple-touch-icon.png?v=joa">
<link rel="manifest" href="{'/fr/' if lang == 'fr' else '/'}site.webmanifest">
<link rel="stylesheet" href="/assets/css/site.css?v={BUILD_ID}">
{extra_head}</head>
<body class="page-{key}">
{staging}<a class="skip" href="#main">{esc(U['skip'])}</a>
<header class="site-header">
 <div class="wrap bar">
  <a class="brand" href="{url(lang, 'home')}"><span class="brand-name">Joachim Agou</span><span class="brand-sub">{esc(U['brand_sub'])}</span></a>
  <div class="tools">
   <a class="lang" href="{opath}" hreflang="{other}-CA" lang="{other}"{evbase} aria-label="{esc(U['lang_other_label'])}"><span class="lang-long">{esc(U['lang_other'])}</span><span class="lang-short" aria-hidden="true">{U['lang_other_short']}</span></a>
{"" if "volunteer" in HIDDEN else f'   <a class="btn primary hdr-cta" href="{cta_v}">{esc(U["cta_volunteer"])}</a>'}
{f'   <a class="btn donate hdr-cta" href="{cta_d}">{esc(U["cta_donate"])}</a>' if SITE.get("promote_donate") else ""}
   <button id="menu-btn" class="menu-btn" type="button" aria-expanded="false" aria-controls="site-nav" data-open="{esc(U['menu'])}" data-close="{esc(U['close'])}"><span class="burger" aria-hidden="true"></span><span class="lbl">{esc(U['menu'])}</span></button>
  </div>
 </div>
 <nav id="site-nav" class="site-nav" aria-label="{'Main' if lang == 'en' else 'Principal'}"><ul class="wrap">{navs}</ul></nav>
</header>
<main id="main" tabindex="-1">
{main_html}
</main>
{footer(lang, {"self": path})}
<script src="/assets/js/site.js?v={BUILD_ID}" defer></script>
</body>
</html>
"""


def json_ld(lang, key, title, desc, canonical, env):
    """schema.org JSON-LD: Person + WebSite on the home page; BreadcrumbList on the others (events add Event items in forms.js)."""
    home = LIVE + url(lang, "home")
    person = {"@type": "Person", "@id": LIVE + "/#joachim", "name": "Joachim Agou", "url": home,
              "image": LIVE + "/assets/img/" + IMG["joachim-agou-headshot"][0][1200], "knowsLanguage": ["en", "fr"],
              "sameAs": [u for g in ("campaign", "personal") for u in SITE["social"][g].values()],
              "description": SEO["pages"]["home"][lang]["desc"]}
    if key == "home":
        graph = [person, {"@type": "WebSite", "@id": LIVE + "/#website", "name": UI[lang]["site_name"], "url": home,
                          "inLanguage": f"{lang}-CA", "publisher": {"@id": LIVE + "/#joachim"}}]
    else:
        crumbs = [(BYKEY["home"]["nav"][lang], home)]
        parent = next((p["key"] for p in PAGES if key in (p.get("children") or [])), None)
        if parent: crumbs.append((BYKEY[parent]["nav"][lang], LIVE + url(lang, parent)))
        crumbs.append((UI[lang]["nominations_closed"]["title"] if key == "nominate" and NOMINATIONS_CLOSED else BYKEY[key]["nav"][lang], canonical))
        graph = [{"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": i, "name": n, "item": u} for i, (n, u) in enumerate(crumbs, 1)]}]
    data = {"@context": "https://schema.org", "@graph": graph}
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"


def updated_date(lang, key):
    return re.search(r'datetime="([^"]+)"', updated_for(lang, key)).group(1)


def sitemap():
    """All indexable pages, each with its en-CA / fr-CA / x-default alternates and lastmod (the page's 'Last updated' date)."""
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for p in PAGES:
        if p.get("robots") == "noindex": continue
        for l in LANGS:
            alts = "".join(f'\n    <xhtml:link rel="alternate" hreflang="{h}" href="{LIVE + url(al, p["key"])}"/>' for h, al in (("en-CA", "en"), ("fr-CA", "fr"), ("x-default", "en")))
            out.append(f'  <url>\n    <loc>{LIVE + url(l, p["key"])}</loc>\n    <lastmod>{updated_date(l, p["key"])}</lastmod>{alts}\n  </url>')
    return "\n".join(out + ["</urlset>"]) + "\n"


def seo_check(dist, env):
    """Every page: one title, description, canonical, hreflang trio, og and twitter tags; no duplicates across pages."""
    errs = []; seen = {"title": {}, "description": {}, "canonical": {}}
    need = ["og:title", "og:description", "og:url", "og:type", "og:locale", "og:locale:alternate", "og:site_name", "og:image", "og:image:width", "og:image:height", "og:image:alt"]
    for f in sorted(dist.rglob("*.html")):
        rel = str(f.relative_to(dist)); t = f.read_text(); head = t[:t.index("</head>")]
        is404 = rel == "404.html"
        def one(pat, what):
            m = re.findall(pat, head)
            if len(m) != 1: errs.append(f"{rel}: {len(m)} × {what}")
            return html.unescape(m[0]) if m else ""
        title = one(r"<title>(.*?)</title>", "<title>")
        desc = one(r'<meta name="description" content="([^"]*)"', "meta description")
        for p in need:
            if p == "og:url" and is404: continue
            one(rf'<meta property="{re.escape(p)}" content="([^"]*)"', p)
        for n in ("twitter:card", "twitter:title", "twitter:description", "twitter:image"): one(rf'<meta name="{n}" content="([^"]*)"', n)
        if 'name="twitter:card" content="summary_large_image"' not in head: errs.append(f"{rel}: twitter:card is not summary_large_image")
        if not re.search(r'<html lang="(en|fr)-CA">', t): errs.append(f"{rel}: html lang missing")
        robots = one(r'<meta name="robots" content="([^"]*)"', "meta robots")
        if env == "staging" and "noindex" not in robots: errs.append(f"{rel}: staging page is indexable")
        if env == "live" and not is404 and "noindex" in robots and f.parent.name not in {p["slug"].strip("/") for p in PAGES if p.get("robots") == "noindex"}:
            errs.append(f"{rel}: live page is noindex")
        img = re.search(r'<meta property="og:image" content="https?://[^/]+(/[^"]+)"', head)
        if img and not (dist / img.group(1).lstrip("/")).exists(): errs.append(f"{rel}: og:image file {img.group(1)} missing")
        for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S):
            try: json.loads(m)
            except ValueError as e: errs.append(f"{rel}: invalid JSON-LD ({e})")
        if is404: continue
        canon = one(r'<link rel="canonical" href="([^"]*)">', "canonical")
        want = LIVE + "/" + rel[:-len("index.html")]
        if canon != want: errs.append(f"{rel}: canonical {canon} != {want}")
        hl = re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)">', head)
        if sorted(h for h, _ in hl) != ["en-CA", "fr-CA", "x-default"]: errs.append(f"{rel}: hreflang set {hl}")
        if not 100 <= len(desc) <= 170: errs.append(f"{rel}: description is {len(desc)} characters (100–170)")
        if len(title) > 70: errs.append(f"{rel}: title is {len(title)} characters (max 70)")
        for k, v in (("title", title), ("description", desc), ("canonical", canon)):
            if v in seen[k]: errs.append(f"{rel}: same {k} as {seen[k][v]}")
            seen[k][v] = rel
    return errs


def first_text(md, n=155):
    for l in md.split("\n"):
        s = l.strip()
        if s and not s.startswith(("#", "<", "!", "- ", "[", "|")) and len(s) > 40:
            t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s); t = re.sub(r"[*\\]", "", t)
            return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"
    return ""


def photo_slot(slot, lang, cls):
    f = SITE["photos"].get(slot)
    if f == "joachim-agou-headshot-second":  # About: the second headshot (B), so About and home differ
        if not HS_SECOND: sys.exit(f"photo slot {slot}: joachim-agou-headshot-second needs site.json headshot_background_second")
        return f'<div class="{cls} has-photo">{headshot("(min-width: 800px) 280px, 200px", eager=True, bg=HS_SECOND)}</div>'
    if f == "joachim-agou-headshot":  # hero: above the fold on desktop, so not lazy; About: top of the page, also not lazy
        sizes = "(min-width: 800px) 400px, 260px" if slot == "hero" else "(min-width: 800px) 280px, 200px"
        return f'<div class="{cls} has-photo">{headshot(sizes, eager=True)}</div>'
    if f:
        if f in IMG:
            return f'<div class="{cls} has-photo">{picture(f, UI[lang]["photo_alt"], lang, caption=False, eager=slot == "hero")}</div>'
        return f'<div class="{cls} has-photo"><img src="/assets/img/photos/{esc(f)}" alt="{esc("Joachim Agou")}" decoding="async"></div>'
    if slot != "hero":
        return f'<!-- photo slot "{slot}": empty (see README, Photo slots) -->'
    # empty hero photo slot: the riding map card (the home page then skips the same map further down)
    PAGE_STATE["hero_map"] = True
    return f'<div class="{cls} hero-map" data-photo-slot="{slot}">{map_card(lang, eager=True)}</div>'


def event_maps():
    """assets/img/events/index.json (tools/make_event_maps.py): {event id: {lat, lng, v}}. The events page shows a map
    only when the event's lat/lng from get_public_events still match, so a moved pin never shows an old map."""
    f = ROOT / "assets/img/events/index.json"
    return json.loads(f.read_text()) if f.exists() else {}

def build_page(lang, page, env):
    key = page["key"]; U = UI[lang]
    PAGE_STATE["vic_used"] = []; vic = VIC_ON(env) and bool(VIC)
    if key == "scorecard":  # /scorecard/: own layout, see scorecard.py
        return scorecard.scorecard_page(sys.modules[__name__], lang, page, env)
    if key == "province":  # /province/: own layout, see province.py
        return province.page(sys.modules[__name__], lang, page, env)
    if key == "updates":  # /updates/: the feed of Joachim's updates, newest first (updates.py); only built when there are entries
        return updates.page(sys.modules[__name__], lang, page, env)
    if key.startswith("u:"):  # /updates/<date>-<slug>/: one update (permalink page)
        return updates.permalink_page(sys.modules[__name__], lang, page, env)
    if PARTY["on"] and key in PARTY_MOVED:
        return party_page(lang, page, env)
    self_path = url(lang, key)
    ctx = {"self": self_path, "self_anchor": "#form" if page.get("form") in ("volunteer", "nominate", "lawnsign") else "#events-list"}
    home = read(lang, "home")
    if key == "home":
        md = drop_hidden_sections(home, lang)
        if NOMINATIONS_CLOSED:  # no "Become a nominator" section (its riding map comes back as the map section below)
            md = drop_section(md, page_section_title("nominate", lang))
        top, rest = md.split("\n## ", 1)
        rest = "## " + rest
        tl = [l for l in top.split("\n") if l.strip()]
        sub, tagline = tl[0], tl[1]
        # hero: status line, tagline, short intro paragraph(s), the nominator callout, then an optional "Sources:" line
        c0 = next(k for k, l in enumerate(tl) if l.strip().startswith("<callout"))
        c1 = next(k for k, l in enumerate(tl) if l.strip().startswith("</callout>"))
        intro = "".join(f'<p class="hero-intro">{inline(l.strip(), ctx)}</p>' for l in tl[2:c0])
        callout = "\n".join(tl[c0:c1 + 1])
        src_lines = tl[c1 + 1:]
        if NOMINATIONS_CLOSED:  # the "75 nominators, nominations close…" source was only there for the callout
            src_lines = [re.sub(r"\s*·\s*\[75 (?:nominators|signataires)[^\]]*\]\([^)]*\)", "", l) for l in src_lines]
        hero_src = "".join(f'<p class="hero-src">{inline(l.strip(), ctx)}</p>' for l in src_lines)
        # Follow along section goes before Donate
        donate_h = page_section_title("donate", lang)
        follow = f'<section class="block follow" aria-labelledby="follow"><h2 id="follow">{esc(U["follow_title"])}</h2><p>{esc(U["follow_text"])}</p>{social_links("social big", lang)}</section>'
        PAGE_STATE["hero_map"] = False
        hero_media = photo_slot("hero", lang, "hero-photo")
        body, _ = render(rest, lang, {"self": self_path})
        if "scorecard" not in HIDDEN:  # "See the scorecard" under the home priorities section
            pl = f'<p class="pagelink"><a href="{url(lang, "priorities")}">'
            j = body.find(pl)
            if j < 0: sys.exit("home: priorities page link not found (needed to place the scorecard link)")
            j = body.index("</p>", j) + 4
            body = body[:j] + scorecard.home_link(sys.modules[__name__], lang) + body[j:]
        PAGE_STATE["hero_map"] = False
        body = body.replace(f'<section class="block" aria-labelledby="{slugify(donate_h)}">', follow + f'\n<section class="block" aria-labelledby="{slugify(donate_h)}">', 1)
        # the callout's link is the page's main action: a primary button (same wording)
        hero_callout = re.sub(r'<a href="([^"]+)">', r'<a class="btn primary hero-cta" href="\1">', render(callout, lang, {"self": self_path})[0], count=1)
        if NOMINATIONS_CLOSED:  # the nominator callout is gone; Volunteer is the hero's main action (same label as the header button)
            hero_callout = "" if "volunteer" in HIDDEN else f'<p class="hero-actions"><a class="btn primary hero-cta" href="{url(lang, "volunteer")}">{esc(U["cta_volunteer"])}</a></p>'
            body = body.replace(f'<section class="block" aria-labelledby="{slugify(donate_h)}">', map_block(lang) + f'\n<section class="block" aria-labelledby="{slugify(donate_h)}">', 1)
        hero = (f'<div class="hero"><div class="wrap hero-grid"><div class="hero-text">'
                f'<h1>{esc(U["home_title"])}</h1><p class="hero-sub">{inline(sub, ctx)}</p><p class="tagline">{inline(tagline, ctx)}</p><p class="lockup">{esc(U["lockup"])}</p>'
                f'{intro}{hero_callout}</div>{hero_media}</div>'
                + (f'<div class="wrap">{hero_src}</div>' if hero_src else "") + '</div>')
        newev = "" if "events" in HIDDEN else events_cal.home_banner(lang, SITE, UI, url(lang, "events"))  # always on (4 Oct 2026): next upcoming event; hidden only when none
        main = newev + hero + shortcuts(lang) + (vic_band(lang, env) if vic else "") + home_layout(collapse(body, lang, page="home"), lang, updates.home_section(sys.modules[__name__], lang)) + f'<div class="wrap home-foot">{updated_for(lang, "home")}</div>'
        title = f"Joachim Agou – Victoria–Beacon Hill" if lang == "en" else "Joachim Agou – Victoria–Beacon Hill (français)"
        desc = re.sub(r"[*]", "", sub) + ". " + re.sub(r"[*]", "", tagline)
        return shell(lang, page, title, desc, main, env)
    h1 = None; md = None; extra = ""
    if key == "get-involved":
        h1 = page["title"][lang]; md = ""
    elif key == "contact":
        md = "\n".join(l for l in read(lang, "_contact").split("\n") if not re.match(r"^\*(Authorized|Autorisé)", l.strip())
                        and not any(f'<page url="{u}"' in l for u in hidden_urls()))
    elif key == "privacy":
        md = read(lang, "privacy")
    elif page.get("section"):
        h1 = page["section"][lang]; md = page_drafts(lang, key, section(home, h1))
    elif key == "lawn-sign":
        h1 = U["lawnsign"]["title"]; md = ""
    elif key == "media" and lang == "fr" and not read("fr", "media") and MEDIAKIT["on"]:
        h1 = "Médias"
        md = f"<placeholder>MEDIAKIT</placeholder>\n<page url=\"/media/\">{U['mediakit']['page_link']}</page>"
    elif key == "media" and lang == "fr" and not read("fr", "media"):
        h1 = "Médias"
        md = f"<placeholder>FR_MEDIA</placeholder>\n[Media (English)](/media/)"
    else:
        md = read(lang, key); h1 = NOTION_TITLES[key][lang]
    if page.get("title"):
        h1 = page["title"][lang]
    body, heads = render(md, lang, ctx) if md else ("", [])
    if key == "media" and lang in ("en", "fr") and SITE["photos"].get("media") == "joachim-agou-headshot":  # headshot first under Photos (not from Notion), linked to the 1200px JPEG
        sp = '<figure class="fig"><a href="/assets/img/joachim-agou-speaking-'
        if sp not in body: sys.exit("media: Photos image not found (needed to place the headshot)")
        hs = headshot("(min-width: 800px) 400px, 100vw", link=True, caption=True)
        if HS_SECOND:  # two downloadable headshots side by side: main (C) and second (B)
            hs = f'<div class="headshot-pair">{hs}{headshot("(min-width: 800px) 400px, 100vw", link=True, caption=True, bg=HS_SECOND)}</div>'
        body = body.replace(sp, hs + sp, 1)
    if key == "priorities":
        body = collapse(body, lang)
    if key == "priorities" and "province" not in HIDDEN:  # "Who controls what? See what the Province actually controls →"
        body = province.line(sys.modules[__name__], lang, "prio") + body
    if key == "priorities" and "scorecard" not in HIDDEN:
        body = scorecard.priorities_link(sys.modules[__name__], lang) + scorecard.priorities_related(sys.modules[__name__], lang, body)
    for new_, olds_ in SITE.get("anchor_aliases", {}).get(f"{lang}/{key}", {}).items():  # old anchors after a heading rename (site.json anchor_aliases)
        tag_ = f'<h2 id="{new_}">'
        if tag_ in body:
            body = body.replace(tag_, "".join(f'<span id="{esc(o_)}" class="anchor-alias"></span>' for o_ in olds_ if f'id="{o_}"' not in body) + tag_, 1)
    if key == "faq" and heads:
        idx = "".join(f'<li><a href="#{h}">{inline(t_, ctx)}</a></li>' for h, t_ in heads)
        body = (f'<div class="faq-layout"><nav class="faq-index" aria-label="{esc(U["faq_index"])}"><p class="faq-index-t" aria-hidden="true">{esc(U["faq_index"])}</p><ul>{idx}</ul></nav>'
                f'<div class="faq-main">{body}</div></div>')
    if key == "get-involved":
        body = hub(lang, home)
    if key in ("how-to-vote", "donate", "volunteer", "events", "nominate") and body and not body.lstrip().startswith("<section"):
        body = f'<section class="block lead">{body}</section>'
    if key == "how-to-vote" and HTV_V2(env):  # v2: the draft text carries every fact with its Elections BC source, so no separate key-dates box
        for must in ("722 Johnson Street", "1-800-661-8683", "elections.bc.ca"):
            if must not in body: sys.exit(f"how-to-vote v2: {must!r} missing from the page (staging-drafts.json how_to_vote_v2)")
        body = re.sub(r"<p>(Sources? ?:)", r'<p class="vote-src">\1', body) + map_block(lang)
    elif key == "how-to-vote":
        V = U["vote"]
        facts = "".join(f'<li>{esc(t)} <a class="srclink" href="{esc(u_)}" rel="noopener">{esc(V["src_link"])}</a></li>' for t, u_ in V["facts"])
        links = "".join(f'<li><a href="{esc(u_)}" rel="noopener">{esc(t)}</a></li>' for t, u_ in V["links"])
        body = (f'<section class="block keydates" aria-labelledby="kd"><h2 id="kd">{esc(V["title"])}</h2><p class="src">{esc(V["source"])}</p><ul class="facts">{facts}</ul>'
                f'<h3>{esc(V["links_title"])}</h3><ul class="links">{links}</ul></section>' + body + map_block(lang))
    if key in ("how-to-vote", "get-involved") and "faq" not in HIDDEN:
        body += faq_block(lang)
    if key == "about":
        body = photo_slot("about-portrait", lang, "about-photo") + body
    if key == "nominate" and NOMINATIONS_CLOSED:  # URL kept so old links work: thank-you note only, no form (noindex, out of nav and sitemap)
        h1 = U["nominations_closed"]["title"]
        body = (f'<section class="block lead"><p>{esc(U["nominations_closed"]["text"])}</p>'
                f'<p><a class="btn primary" href="{url(lang, "volunteer")}">{esc(U["cta_volunteer"])}</a></p></section>')
    warm = key == "volunteer" and VOL_WARM(env)
    if warm:  # welcome note on top; "Sign up" button (#form) dropped; lawn sign link moved below the form
        VT = U["volunteer"]
        body = re.sub(r'<p class="cta-line"><a class="btn[^"]*" href="#form">.*?</p>\s*', "", body)
        body = re.sub(r'\s*<p class="cta-line"><a class="btn[^"]*" href="[^"]*lawn-sign/">.*?</p>', "", body)
        if "#form" in body or "lawn-sign/" in body: sys.exit("volunteer page: could not remove the Sign up / lawn sign buttons from the lead (Notion text changed?)")
        draft = f'<p class="draft-tag">{esc(VT["draft_tag"])}</p>' if env == "staging" and not SITE.get("volunteer_welcome_approved") else ""
        welcome = (f'<section class="block vwelcome">{draft}<div class="vw-in">{headshot("112px", eager=True, bg=HS_SECOND)}'
                   f'<blockquote class="vw-note"><p>{esc(VT["welcome"])}</p><footer>– {esc(VT["welcome_sign"])}</footer></blockquote></div></section>')
        body = body.replace('</section>', f'<p class="vreassure">{esc(VT["reassure"])}</p>'
                            f'<p class="vnext" id="vnext" hidden data-events="{url(lang, "events")}"></p></section>', 1)
        # Joachim (1 Oct 2026): the lead's "Every hour helps." / "Chaque heure compte." duplicated the reassurance line
        # ("…even two hours helps."), so the warm page drops that sentence and keeps "Knock on doors, make calls, …".
        # Home and Get involved keep the full Notion line.
        body = re.sub(r'\s*(?:Every hour helps|Chaque heure compte)\.', "", body, count=1)
        if re.search(r"Every hour helps|Chaque heure compte", body): sys.exit("volunteer page: 'Every hour helps' / 'Chaque heure compte' still in the lead (removed 1 Oct 2026)")
        body = welcome + (vic_strip(VIC["volunteer"], lang, "vstrip vstrip-vol") if vic else "") + body
    if key == "volunteer" and vic and not warm:
        body = vic_strip(VIC["volunteer"], lang, "vstrip vstrip-vol") + body
    if page.get("form") in ("volunteer", "nominate", "lawnsign") and not (key == "nominate" and NOMINATIONS_CLOSED):
        body += form_block(page["form"], lang, warm)
        if warm:
            body += (f'<section class="block vlawn"><h2>{esc(VT["lawnsign_t"])}</h2>'
                     f'<p class="cta-line"><a class="btn sec" href="{url(lang, "lawn-sign")}"><strong>{esc(VT["lawnsign_btn"])}</strong></a></p></section>')
        extra = f'<script id="form-config" type="application/json">{json.dumps({"form": page["form"], "warm": warm, **({"hide": sorted(events_cal.HIDE)} if events_cal.HIDE else {}), "text": {k: v for k, v in UI[lang][page["form"]].items() if k != "draft_tag"}, "common": UI[lang]["form_common"]}, ensure_ascii=False).replace("</", "<\\/")}</script>\n<script src="/assets/js/forms.js?v={BUILD_ID}" defer></script>\n'
    if page.get("form") == "events":
        T = U["events"]
        cal = CAL_ON(env)
        toggle = (f'<div class="viewtoggle" role="group" aria-label="{esc(T["view"])}" hidden><button type="button" data-view="list" aria-pressed="true">{esc(T["view_list"])}</button>'
                  f'<button type="button" data-view="calendar" aria-pressed="false">{esc(T["view_cal"])}</button></div>') if cal else ""
        shifts = SHIFTS_ON(env); ST = U["shifts"]
        if shifts:  # Public events / Volunteer shifts / Both (forms.js; ?show=public|shifts, default both)
            toggle += (f'<div class="evfilter" role="group" aria-label="{esc(ST["filter"])}" hidden><span class="evfilter-l" aria-hidden="true">{esc(ST["filter"])}</span>'
                       f'<button type="button" data-show="public" aria-pressed="false">{esc(ST["f_public"])}</button>'
                       f'<button type="button" data-show="shifts" aria-pressed="false"><span class="mk sev" aria-hidden="true">■</span> {esc(ST["f_shifts"])}</button>'
                       f'<button type="button" data-show="both" aria-pressed="true">{esc(ST["f_both"])}</button></div>')
        calv = events_cal.calendar_html(lang, SITE, UI, shifts=shifts) if cal else ""
        body = f'<div data-hide-on-detail>{body}</div><section class="block" id="events-list" aria-live="polite">{toggle}<div id="listView"><div id="list"><p class="note">{esc(T["loading"])}</p></div></div>{calv}<article id="detailView" class="detail" hidden></article></section>'
        cfg = {"form": "events", "live_url": LIVE + self_path, "text": T, "common": U["form_common"], "maps": event_maps()}
        if events_cal.HIDE: cfg["hide"] = sorted(events_cal.HIDE)  # no_party_v1: events left out of this build
        if vic: cfg["vic"] = vic_events_cfg(lang)
        if cal: cfg.update({"cal": SITE["calendar_month"], "new_until": events_cal.new_map(SITE), "new_label": UI[lang]["new_events"]["badge"]})
        if shifts: cfg.update({"shifts": True, "shift_text": {k: v for k, v in ST.items() if not k.startswith("_")}})
        extra = f'<script id="form-config" type="application/json">{json.dumps(cfg, ensure_ascii=False).replace("</", "<\\/")}</script>\n<script src="/assets/js/forms.js?v={BUILD_ID}" defer></script>\n'
    lock = f'<p class="lockup">{esc(U["lockup"])}</p>' if key == "priorities" else ""  # two-line lockup: home, Priorities, Scorecard only
    if key == "priorities":
        rid = slugify(U["lockup_block"])
        m_ = re.search(rf'<h2 id="{re.escape(rid)}">.*?</h2>', body)
        if not m_: sys.exit(f"priorities: '{U['lockup_block']}' section not found (needed for the lockup)")
        body = body[:m_.end()] + f'<p class="lockup lockup-block">{esc(U["lockup"])}</p>' + body[m_.end():]
        if vic: body = vic_priorities(body, lang)
        if PRIO2_ON(env):
            classic_ = body
            body = prio_layout.transform(body, lang, slugify, PRIO2_STATE)
            probs_ = prio_layout.coverage(classic_, body, lang)
            if probs_: sys.exit(f"priorities ({lang}) summary-first layout: text or links from the classic page are missing:\n  " + "\n  ".join(probs_))
            extra = (extra or "") + f'<script src="/assets/js/prio2.js?v={BUILD_ID}" defer></script>\n'
    main = f'<div class="page-head"><div class="wrap"><h1>{esc(h1)}</h1>{lock}</div></div><div class="wrap content">{body}{updated_for(lang, key)}</div>'
    desc = first_text(md) if md else U["lawnsign"]["intro"] if key == "lawn-sign" else ""
    if key == "lawn-sign": desc = U["lawnsign"]["intro"]
    title = f"{h1} – Joachim Agou – Victoria–Beacon Hill"
    out = shell(lang, page, title, desc, main, env)
    if key == "priorities" and PRIO2_ON(env):
        out = out.replace("</head>", f'<link rel="stylesheet" href="/assets/css/prio2.css?v={BUILD_ID}">\n</head>', 1)
    return out.replace("</body>", extra + "</body>", 1) if extra else out


def shortcuts(lang):
    """Compact row of section shortcuts under the home hero (existing pages)."""
    items = "".join(f'<li><a href="{url(lang, k)}">{esc(BYKEY[k]["nav"][lang])}</a></li>' for k in ("priorities", "get-involved", "events", "how-to-vote") if k not in HIDDEN)
    return f'<nav class="shortcuts" aria-label="{esc(UI[lang]["shortcuts_label"])}"><div class="wrap"><ul>{items}</ul></div></nav>'


def home_layout(body, lang, upd_html=""):
    """Home: open reading sections, one pale-blue band with the ways to help as cards, then Events and Follow along side by side.
    upd_html ("Updates", updates.py; empty with no entries) goes right under the priorities section."""
    parts = re.split(r"\n?(?=<section class=\"block)", body)
    secs = [s for s in parts if s.strip()]
    sid = lambda s: re.search(r'aria-labelledby="([^"]+)"', s).group(1)
    by = {sid(s): s for s in secs}
    pick = lambda k: slugify(page_section_title(k, lang))
    help_ids = [i for i in (pick("nominate"), pick("volunteer"), pick("donate")) if i in by]
    side_ids = [i for i in (pick("events"), "follow") if i in by]
    order = [sid(s) for s in secs]
    first = [i for i in order[:2]] + [i for i in order[2:] if i == "riding-map"]  # nominations closed: the riding map follows About and Priorities
    rest = [i for i in order if i not in first + help_ids + side_ids]
    card = lambda s: s.replace('<section class="block"', '<section class="block card-sec"', 1)
    if upd_html:
        if f'href="{url(lang, "priorities")}"' not in by[order[1]]: sys.exit("home: the second section is not the priorities section (needed to place Updates)")
        by[order[1]] += "\n" + upd_html
    h = f'<div class="wrap home">' + "\n".join(by[i] for i in first) + "</div>"
    if help_ids:
        h += f'<div class="band band-sky"><div class="wrap"><div class="grid-help">' + "\n".join(card(by[i]) for i in help_ids) + "</div></div></div>"
    h += f'<div class="wrap home">'
    if side_ids:
        h += '<div class="grid-2">' + "\n".join(by[i] for i in side_ids) + "</div>"
    h += "\n".join(by[i] for i in rest) + "</div>"
    return h


def pdf_kb(name):
    return max(1, round((ROOT / "assets" / "media" / name).stat().st_size / 1024))


def mediakit_block(lang):
    """Media kit download links (rule in RESYNC.md: Notion's PDF attachments become <placeholder>MEDIAKIT</placeholder>, rendered here)."""
    T = UI[lang]["mediakit"]; K = SITE["media_kit"]; other = T["other_lang"]
    main_f, other_f = K[lang], K[other]
    h = (f'<div class="mediakit"><p class="cta-line"><a class="btn primary" href="/assets/media/{main_f}" type="application/pdf" hreflang="{lang}">'
         f'<strong>{esc(T["main"].format(kb=pdf_kb(main_f)))}</strong></a></p>'
         f'<p class="mk-other"><a href="/assets/media/{other_f}" type="application/pdf" hreflang="{other}" lang="{other}">{esc(T["other"].format(kb=pdf_kb(other_f)))}</a></p>')
    errs = sorted({w.split(":")[0] for es in MEDIAKIT["errs"].values() for w in es})
    if MEDIAKIT["env"] == "staging" and errs:
        h += f'<div class="draft" role="note">{esc(T["staging_note"].format(errs="; ".join(errs)))}</div>'
    return h + "</div>"


def pdf_check(dist):
    """Run the same content checks on the text of every PDF in dist/ (needs pdftotext from poppler-utils)."""
    import subprocess
    import hashlib
    res = {}
    approved = SITE.get("media_kit_approved", {})
    for f in sorted(dist.rglob("*.pdf")):
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        if h in approved:
            print(f"PDF approved as-is (sha256 {h[:12]}…, scan skipped): {f.relative_to(dist)}"); res[f] = []; continue
        try:
            txt = subprocess.check_output(["pdftotext", "-enc", "UTF-8", str(f), "-"], text=True)
            meta = subprocess.check_output(["pdfinfo", "-enc", "UTF-8", str(f)], text=True)
        except (OSError, subprocess.CalledProcessError) as e:
            res[f] = [f"cannot read PDF text ({e}); install poppler-utils"]; continue
        es = []
        flat = re.sub(r"\s+", " ", txt)
        for pat, what in PRIORITIES_OLD:
            if re.search(pat, flat): es.append(f"contains {what}")
        for pat, what in FORBIDDEN:
            for m in re.finditer(pat, txt + "\n" + meta):
                line = (txt + "\n" + meta)[:m.start()].rsplit("\n", 1)[-1] + (txt + "\n" + meta)[m.start():].split("\n", 1)[0]
                es.append(f"{what}: {line.strip()!r}")
        for m in re.finditer(r"(?<![\d-])(?:1-)?\d{3}[-. ]\d{3}[-. ]\d{4}(?!\d)", txt):
            if m.group(0) not in PHONES_OK:
                es.append(f"unexpected phone number {m.group(0)}")
        res[f] = es
    return res


def hidden_urls():
    return {url(l, k) for k in HIDDEN for l in LANGS}


def drop_section(md, title):
    """Remove the '## title' section (heading and everything up to the next '## ')."""
    parts = re.split(r"(?m)^(?=## )", md)
    keep = [p_ for p_ in parts if not p_.startswith(f"## {title}\n")]
    if len(keep) == len(parts): sys.exit(f"home: section '## {title}' not found")
    return "".join(keep)


def drop_hidden_sections(md, lang):
    """Remove '## ...' sections whose only content is links to pages left out of this build (e.g. home 'Questions?' -> FAQ)."""
    if not HIDDEN: return md
    hu = hidden_urls(); parts = re.split(r"(?m)^(?=## )", md); keep = []
    for part in parts:
        body = [l for l in part.split("\n")[1:] if l.strip()] if part.startswith("## ") else None
        links = [re.findall(r"\]\(([^)\s]+)\)|<page url=\"([^\"]+)\"", l) for l in body] if body else []
        if body and all(ls and all((x or y) in hu for x, y in ls) for ls in links):
            continue
        keep.append(part)
    return "".join(keep)


def faq_block(lang):
    U = UI[lang]
    return (f'<section class="block" aria-labelledby="faq-q"><h2 id="faq-q">{esc(U["faq_q"])}</h2>'
            f'<p class="pagelink"><a href="{url(lang, "faq")}">{esc(U["faq_link"])} <span aria-hidden="true">→</span></a></p></section>')


def map_block(lang):
    M = UI[lang]["map"]
    return f'<section class="block" aria-labelledby="riding-map"><h2 id="riding-map">{esc(M["heading"])}</h2>{map_card(lang)}</section>'


MONTHS = {"en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
          "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]}


def updated_for(lang, key):
    U = SITE["updated"]
    p = BYKEY.get(key, {})
    cands = []
    if key in SITE["notion"] and SITE["notion"][key].get(lang):
        cands.append(U.get(f"{lang}-{key}"))
    if p.get("section") or key == "home" or key in ("get-involved", "contact"):
        cands.append(U.get(f"{lang}-home"))
    cands.append(U.get(key))
    if p.get("form"):
        cands.append(U.get("forms"))
    if key == "media" and lang == "fr":
        cands.append(U.get("fr-media") or U.get("en-media"))
    if PARTY["on"] and key in SITE["party"]["pages"]:  # party links change these pages (2 Oct 2026)
        cands.append(SITE["party"]["updated"])
    if lang == "fr" and U.get(f"fr-{key}") and key not in SITE["notion"]:  # French-only date for a hand-written page (fr-privacy, fr-lawn-sign, ...): the English page keeps its own
        cands.append(U.get(f"fr-{key}"))
    if key == "home" and updates.STATE["entries"] and not updates.STATE["sample"]:  # a new update changes the home page
        cands.append(updates.STATE["entries"][0]["date"])
    if lang == "fr" and p.get("form") and U.get("fr-forms"):
        cands.append(U.get("fr-forms"))
    cands.append(draft_updated(lang, key))
    d = max(c for c in cands if c)
    y, m, dd = map(int, d.split("-"))
    txt = f"{'1er' if lang == 'fr' and dd == 1 else dd} {MONTHS[lang][m - 1]} {y}"  # French: « 1er octobre » (French review, 1 Oct 2026)
    return f'<p class="updated">{esc(UI[lang]["updated"])} <time datetime="{d}">{txt}</time></p>'


def hub(lang, home):
    """Get involved: one card per child page. Card text is the first sentence(s) of that page's Notion section
    (lawn sign: the existing lawn-sign page intro)."""
    cards = []
    for c in BYKEY["get-involved"]["children"]:
        p = BYKEY[c]
        if c == "lawn-sign":
            text = esc(UI[lang]["lawnsign"]["intro"])
        elif c == "nominate":
            cl = re.search(r"<callout[^>]*>\n(.*?)\n</callout>", home, re.S).group(1).split("\n")
            text = " ".join(inline(l.strip(), {}) for l in cl if l.strip() and not l.strip().startswith("["))
        else:
            sec = section(home, p["section"][lang])
            first = next(l for l in sec.split("\n") if l.strip() and not l.startswith(("[", "<", "!", "-")))
            text = inline(first, {})
        cards.append(f'<li class="hub-card"><h2 id="h-{c}"><a href="{url(lang, c)}">{esc(p["nav"][lang])}</a></h2><p>{text}</p>'
                     f'<a class="btn {("donate" if SITE.get("promote_donate") else "sec") if c == "donate" else "primary" if c == "nominate" else "sec"}" href="{url(lang, c)}" aria-describedby="h-{c}">{esc(p["nav"][lang])}</a></li>')
    return '<ul class="hub">' + "".join(cards) + "</ul>"


def page_section_title(key, lang):
    return BYKEY[key]["section"][lang]


NOTION_TITLES = {  # page titles as in Notion
    "about": {"en": "About Joachim", "fr": "À propos de Joachim"},
    "priorities": {"en": "My priorities and proposals", "fr": "Mes priorités et propositions"},
    "media": {"en": "Media", "fr": "Médias"},
    "faq": {"en": "Frequently asked questions", "fr": "Foire aux questions"},
}

# ---------------- checks ----------------
FORBIDDEN = [
    (r"Thales", "employer name (Thales)"), (r"\bNATO\b|OTAN", "NATO"), (r"AJISS", "AJISS"), (r"clearance|habilitation de sécurité", "security clearance"),
    (r"(?i:a city that works|\bune ville qui fonctionne|acitythatworks)|\bACTW\b", "A City That Works (hard rule: never on agou.ca)"),
    (r"\bJoa\b(?! Aero Engineering\b)", "the nickname Joa (only the exact business name 'Joa Aero Engineering' is allowed; joa.aero is lowercase and not matched)"), (r"Victoria-Beacon Hill", "hyphen instead of en dash in Victoria–Beacon Hill"),
    (r"is the Conservative Party of BC candidate|Party of BC candidate in|est le candidat du Parti", "'the candidate' / 'le candidat' wording (banned; say 'nominee' / 'investi')"),
    # nomination confirmed (Joachim, 2 Oct 2026 12:47 AM PT): no 'seeking the nomination' wording anywhere, EN or FR
    (r"(?i)seeking (the |this |a )?(BC Conservative |Conservative Party of BC |party |Conservative )?nomination|seeking to represent|I am seeking this|run for the nomination|running for the nomination|nomination (is )?(still )?pending|Not yet\. I['’]m seeking|day my status changes", "old 'seeking the nomination' wording (nomination confirmed 2 Oct 2026)"),
    (r"(?i)sollicit\w* l['’]investiture|je sollicite cette investiture|souhaite représenter Victoria|brigue l['’]investiture|investiture (est )?(toujours )?en attente|Pas encore\. Je sollicite|jour même où ma situation changera", "old 'sollicite l'investiture' wording (investiture confirmée le 2 oct. 2026)"),
    (r"(?i)signatures are complete|nominations (are )?complete|nomination papers? (is |are |have been )?filed|I(['’]ve| have) filed|I(['’]m| am) on the ballot|signatures (de mise en candidature )?(sont )?(complètes|recueillies)|j(['’]ai| ai) déposé mes documents|mon nom (est|figure) (déjà )?sur le bulletin", "a claim that the Elections BC nomination is filed or complete (not filed yet, Joachim 2 Oct 2026 1:04 AM PT; nomination confirmed only by the party)"),
    (r"(?i)platform page says .coming soon|programme du parti indique « coming soon|(party|parti) (has not yet published|n['’]a pas encore publié)|party['’]s plan\]\(https://conservativebc\.ca/our-platform", "party platform 'coming soon' / 'not yet published' wording (removed by Joachim, 2 Oct 2026 8:20 PM PT)"),
    (r"(?i)lawn signs? (are |is )?free|free lawn sign|pancartes? gratuites?|pancartes sont gratuites", "'free' lawn signs (Joachim isn't sure they are free)"),
    (r"date of birth|date de naissance|\bborn on\b", "date of birth"),
    (r"\bACTW\b|candidate site", "drafting-note wording (ACTW / 'candidate site') from the /province/ source; see RESYNC.md"),
    (r"more than 12 years|plus de 12 ans|12 years of experience|12 ans d'expérience", "the old '12 years' experience claim (Joachim, 30 Sep 2026: more than 15 years)"),
    (r"every person who has ever spoken for the party|toutes les personnes qui ont un jour parlé au nom du parti", "the FAQ sentence Joachim removed from 'Why the Conservatives?' (30 Sep 2026)"),
    (r"BC Funeral Videos|Victoria Drone", "a business name Joachim removed from the About Casagou entry (30 Sep 2026; Eventia Media covers it)"),
    (r"(?i)hilda", "Joachim's street name (keep only the neighbourhood; see exclusions.json)"),
    (r"[Rr]obberies in Victoria rose 21%|vols qualifiés ont augmenté de 21\s?%|181 incidents", "the retracted robbery figure (metro area, not the city; fact-check 2026-09-30, see exclusions.json)"),
    (r"paid for by a balanced budget|stopping spending that does not deliver", "the retracted FAQ funding line (fact-check 2026-09-30; see exclusions.json)"),
]

# Old FR wording Joachim corrected on 2026-09-30 (exclusions.json fr-* rules, ui.json, scorecard FR). If a Notion re-sync or an edit
# brings any of it back on a /fr/ page, the build stops. Apostrophes may be ' or ’.
A_ = "['’]"
FR_OLD = [
    (r"[Aa]ppuyer ma candidature|[Aa]ppuyer la candidature|appuyer qu" + A_ + "un seul|Que veut dire appuyer", "'appuyer' for nominating (use 'signer le formulaire de mise en candidature')"),
    (r"payés par le public", "old 'payés par le public' (use 'financés par les fonds publics')"),
    (r"centre-ville ne semble plus sûr", "old 'le centre-ville ne semble plus sûr'"),
    (r"Des soins sécurisés|les soins sécurisés|lits de soins sécurisés", "old 'soins sécurisés' (use 'soins dans un milieu sécurisé')"),
    (r"causes soient jugées plus vite", "old 'pour que les causes soient jugées plus vite'"),
    (r"Aucun impôt provincial sur jusqu", "old 'Aucun impôt provincial sur jusqu'à' (income tax wording)"),
    (r"préavis au personnel", "old 'avec un préavis au personnel'"),
    (r"73\s?% des commerces", "old '73 % des commerces' (use 'entreprises')"),
    (r"Candidat à l" + A_ + "investiture|candidat à l" + A_ + "investiture", "old 'Candidat à l'investiture' status line (nomination confirmed 2 Oct 2026: 'Investi par le Parti conservateur…')"),
    (r"je livre des projets|production média|en 2011 pour des recherches|loyers sont hors de portée", "old FR home wording"),
    (r"si quelque chose fonctionne et d" + A_ + "en rendre compte|apporterai cette habitude|assorti d" + A_ + "un chiffre|rapport à la circonscription|si ça a fonctionné", "old FR home/FAQ wording"),
    (r"Je le mesure, je le règle|Quand une proposition en vient|\bweek-end|d" + A_ + "un deux-chambres|délais de permis|présenté ligne par ligne|voyageurs fréquents|ponctualité des traversiers|dotés de personnel|des tentes à un logement|réduire l" + A_ + "impôt des petites entreprises|locaux commerciaux vacants|Aussi pour la circonscription|Comment vous le saurez", "old FR Priorities wording"),
    (r"J" + A_ + "entends les mêmes problèmes|le prix des loyers et des logements|je porterais les chiffres|ou l" + A_ + "arrêter|[Pp]rélancement|d" + A_ + "opérations de mission|de leurs achats|permis #|membre #", "old FR About wording"),
    (r"Aucune raison nécessaire|carte « Where to Vote »|doit la recevoir avant 20 h|Action de grâce(?!s)", "old FR voter-information wording"),
    (r"venir à ma porte|droits de propriété clairs\b|construire, posséder et décider", "old FR FAQ wording"),
]
ABOUT_OLD = [  # About intro approved 2026-09-30 (EN+FR); the old paragraphs must not come back from Notion
    r"I have lived in Fairfield, in Victoria–Beacon Hill, since January 2023", r"My work has included leading teams",
    r"J['’]habite à Fairfield, dans Victoria–Beacon Hill, depuis janvier 2023", r"J['’]ai dirigé des équipes et géré des projets",
    r"Ran the pre-launch of a new restaurant", r"Development of test and trial procedures", r"Élaboration de procédures d['’]essais pour les systèmes",  # old career-history entries
    r"Start with the numbers\.", r"Fix what does not work, or stop it", r"Partir des chiffres\.",  # old How I work list
]
# Priorities v2 (1 Oct 2026, staging only until Joachim approves; site.json priorities_v2_approved): wording the review retired.
# The build stops if any of it comes back on /priorities/ or /scorecard/ (EN or FR), e.g. through a Notion re-sync.
PRIORITIES_OLD = [
    (r"Those are decisions|Ce sont des décisions|aren['’]t market forces|pas les lois du marché", "the retired 'Those are decisions' ferry line (not every cancellation is a decision)"),
    (r"flat monthly fare|tarif mensuel fixe", "a firm 'flat monthly fare' (the 2024 platform proposed consulting frequent users on a monthly flat-fee program or other measures)"),
    (r"[Vv]ote for bail and repeat-offender law|[Vv]oter pour des lois sur la mise en liberté sous caution", "'vote for bail law' (bail is federal law; an MLA funds and administers the courts and presses Ottawa)"),
    (r"Last year 295|L['’]an dernier, 295|report to the Commissioner, FY2025", "the undated ferry figure (say 'fiscal year ended March 31, 2025')"),
    (r"public drug use as their biggest problem|comme leur principal problème", "'biggest problem' (the DVBA survey asked for top challenges; 73% named public drug use)"),
    (r"(?i)no provincial income tax on up to|aucun impôt provincial sur le revenu sur les sommes versées en loyer ou en intérêts hypothécaires, jusqu['’]à 3 000", "the shortened housing tax line (give the full 2024 detail: $1,500 rising to $3,000, strata fees, tax relief not a payment)"),
    (r"budgets? équilibrés? et honnêtes|honest budgets?[^.]{0,40}équilibr", "'honest budgets' rendered as 'budgets équilibrés'"),
    # Round 2 (Joachim, 1 Oct 2026 5:27 PM PT): also checked on every page and in the media-kit PDFs
    (r"custody where the law allows|detention of repeat violent offenders where the law allows|(?:maintenir|garder) en détention [^.]{0,80}lorsque la loi le permet|détention des récidivistes violents lorsque la loi le permet", "'custody where the law allows' (bail is federal; the MLA levers are provincial funding and administration, plus pressing Ottawa)"),
    (r"Indexation restored from 2027|indexation à partir de 2027", "an indexation year (the year and the funding follow the party's published fiscal plan)"),
    (r"A balanced (?:provincial )?budget, reported line by line|Un budget (?:provincial )?équilibré, présenté poste par poste|push for a balanced provincial budget|défendra un budget provincial équilibré", "a balanced budget listed as a cost-of-living measure (see Responsible spending; it is not a household saving)"),
    (r"quarterly ferry cancellation and on-time results|chiffres trimestriels sur les annulations de traversées", "ferry reporting under cost of living (it is in Transport and BC Ferries, from BC Ferries' reports)"),
    (r"(?i)the candidate announced by|le candidat annoncé par", "'the candidate announced by' (say 'The BC Greens have announced …')"),
    (r"charter and flat fare|charte de BC Ferries et le tarif fixe", "'flat fare' as a firm party item (the 2024 platform proposed consulting frequent users)"),
    # Site consistency audit (Joachim, 1 Oct 2026 6:26 PM PT): retired on every page
    (r"(?i)rent[- ]and[- ]mortgage rebate|remise pour le loyer et les intérêts hypothécaires", "'rent and mortgage rebate' (it is income-tax relief on housing costs, not a payment)"),
    (r"The large items are party commitments|Les mesures importantes sont des engagements du parti", "2024 platform items called 'party commitments' (label them 2024 party platform)"),
    (r"Are you the BC Conservative candidate\?|Êtes-vous le candidat du Parti conservateur", "'the candidate' FAQ question (the strings 'the candidate' / 'le candidat' are banned)"),
    (r"Every hour helps|Chaque heure compte", "'Every hour helps' (cut by Joachim on 1 Oct 2026)"),
    (r"(?i)become a nominator|appui à sa candidature", "a nominator ask (nominations are complete)"),
    # Needs-Joachim answers (1 Oct 2026, 7:49 PM PT): retired on every page
    (r"by Thursday 1 October|by October 1, 2026|d['’]ici le jeudi 1er octobre|d['’]ici le 1er octobre 2026|Closed Wednesday 30 September|Fermé le mercredi 30 septembre", "a past voting date (registration by 1 Oct, office closed 30 Sep)"),
    (r"76 ?% had a family doctor|76 ?% avaient un médecin|1 in 4 people don['’]t have a family doctor|1 personne sur 4 n['’]a pas de médecin", "the old Home family-doctor line (use the Priorities metric: 24.7% had no family doctor or nurse practitioner, June 2025)"),
    (r"What does nominating a candidate mean\?|Que signifie signer le formulaire de mise en candidature", "the retired FAQ entry on nominating"),
    (r"came to Canada at 22 to study|arrivé au Canada à 22 ans pour étudier|Médias \(en anglais\)", "the old About intro (Laval: graduate research, after Florida Tech) or the English-Media fallback link"),
]
EXPERIENCE_OLD = r"(?i)(more than|over)\s+(12|twelve)\s+years|\b(12|twelve) years of experience|plus de (12|douze) ans"
PHONES_OK = {"672-922-7017", "778-996-9910", "1-800-661-8683", "16729227017", "17789969910",
             "1-888-456-5448", "778-405-9892"}  # Elections BC TTY and the Victoria–Beacon Hill district electoral office (How to vote; elections.bc.ca, checked 6 Oct 2026)


def shifts_check(dist, env):
    """Volunteer shifts (migration 48): on only where SHIFTS_ON (staging, or live with volunteer_shifts_live). The public page
    gets shifts only from get_public_shifts (day, time, area), never an address or pin; forms.js calls it only when CFG.shifts."""
    errs = []; on = SHIFTS_ON(env)
    for l_ in LANGS:
        hp = dist / url(l_, "events").lstrip("/") / "index.html"
        if not hp.exists(): continue
        ht = hp.read_text(); has = '"shifts": true' in ht and 'class="evfilter"' in ht
        if on and not has: errs.append(f"{hp.relative_to(dist)}: volunteer shifts are on for this build but the page has no shift config/filter")
        if not on and ('"shifts": true' in ht or 'evfilter' in ht or 'lg-shift' in ht):
            errs.append(f"{hp.relative_to(dist)}: volunteer shifts leaked into a build where they are off (site.json volunteer_shifts_live is false)")
    js = (dist / "assets/js/forms.js").read_text()
    if js.count('rpc("get_public_shifts"') != 1 or 'if (CFG.shifts) shiftsP = rpc("get_public_shifts"' not in js:
        errs.append("assets/js/forms.js: get_public_shifts must be called once, only behind CFG.shifts")
    for l_ in LANGS:
        for k_, v_ in UI[l_]["shifts"].items():
            if re.search(r"\bJoa\b|the candidate|le candidat", v_): errs.append(f"ui.json {l_}.shifts.{k_}: write Joachim, never Joa / the candidate")
    return errs


def check(dist):
    errs = []
    for f in sorted([*dist.rglob("*.webmanifest"), *dist.rglob("*.json"), *dist.rglob("*.ics"), *dist.rglob("*.txt"), *dist.rglob("*.xml")]):  # share/app text outside the HTML
        t = f.read_text(errors="ignore")
        for pat, what in FORBIDDEN:
            if "nomination confirmed" in what or "investiture confirmée" in what or "'free' lawn" in what or "not filed yet" in what:
                if re.search(pat, t): errs.append(f"{f.relative_to(dist)}: contains {what}")
    for f in sorted(dist.rglob("*.html")):
        t = f.read_text()
        vis = re.sub(r"<script.*?</script>", " ", t, flags=re.S)
        if f.relative_to(dist).as_posix() in ("media/index.html", "fr/media/index.html"):  # Joachim, 2 Oct 2026 8:18 PM PT
            a_ = re.search(r'id="(short-bio|biographie-courte)[^"]*"', t); b_ = re.search(r'id="(full-bio|biographie-complète)"', t)
            if not (a_ and b_): errs.append(f"{f.relative_to(dist)}: short or full bio heading not found (needed for the Casagou check)")
            elif "Casagou" in t[a_.start():b_.start()]:
                errs.append(f"{f.relative_to(dist)}: Casagou Inc. is back in the short or medium bio (only the full bio may name it)")
        if 'class="site-footer"' in t:  # social links grouped Campaign / Personal (Joachim, 2 Oct 2026)
            ft = t[t.index('class="site-footer"'):]
            if ft.count('class="soc-row"') != 2 or "facebook.com/joachimagou" not in ft or "instagram.com/joachimagou" not in ft:
                errs.append(f"{f.relative_to(dist)}: footer social links are not grouped Campaign (joachimagou) / Personal (casagou)")
        if re.search(r'href="https://www\.instagram\.com/casagou/"[^>]*>(More photos|Plus de photos)', t):
            errs.append(f"{f.relative_to(dist)}: 'More photos on Instagram' must point at the campaign account")
        for pat, what in FORBIDDEN:
            if re.search(pat, t):
                errs.append(f"{f.relative_to(dist)}: contains {what}")
        for m in re.finditer(r"(?<![\d-])(?:1-)?\d{3}[-. ]\d{3}[-. ]\d{4}(?!\d)", vis):
            if m.group(0) not in PHONES_OK:
                errs.append(f"{f.relative_to(dist)}: unexpected phone number {m.group(0)}")
        plain_t = html.unescape(re.sub(r"<[^>]+>", " ", vis))
        if re.search(EXPERIENCE_OLD, plain_t):
            errs.append(f"{f.relative_to(dist)}: contains a '12 years' experience claim (Joachim: 'more than 15 years' everywhere)")
        rel_ = f.relative_to(dist).as_posix()
        if 'class="lockup' in t and rel_ not in ("index.html", "fr/index.html", "priorities/index.html", "fr/priorities/index.html", "scorecard/index.html", "fr/scorecard/index.html"):
            errs.append(f"{rel_}: the two-line lockup is only for home, Priorities and Scorecard")
        if True:  # every page (round 2: FAQ, home and media must match Priorities v2 too)
            for pat, what in PRIORITIES_OLD:
                if re.search(pat, plain_t): errs.append(f"{rel_}: contains {what}")
            if "<!--MORE-->" in t: errs.append(f"{rel_}: a <more/> marker was not turned into a Read more region")
        for pat in ABOUT_OLD:
            if re.search(pat, plain_t):
                errs.append(f"{f.relative_to(dist)}: contains the old About intro ('{pat}'; rewritten 2026-09-30, see exclusions.json)")
        if f.relative_to(dist).parts[0] == "fr":
            for pat, what in FR_OLD:
                if re.search(pat, plain_t):
                    errs.append(f"{f.relative_to(dist)}: contains {what} (corrected 2026-09-30; see exclusions.json)")
        if "Authorized by Bert Chen, financial agent, bert@bertchen.ca, 778-996-9910." not in t:
            errs.append(f"{f.relative_to(dist)}: missing footer authorization line")
    # FR FAQ must mirror the EN FAQ: same number of sections (topic index) and questions
    en_faq, fr_faq = dist / "faq" / "index.html", dist / "fr" / "faq" / "index.html"
    if en_faq.exists() and fr_faq.exists():
        e_, f_ = en_faq.read_text(), fr_faq.read_text()
        for what, pat in (("questions", r"<summary"), ("topic-index entries", r'<nav class="faq-index".*?</nav>')):
            ne = len(re.findall(pat, e_, re.S)) if what == "questions" else len(re.findall(r"<li>", re.search(pat, e_, re.S).group(0)))
            nf = len(re.findall(pat, f_, re.S)) if what == "questions" else len(re.findall(r"<li>", re.search(pat, f_, re.S).group(0)))
            if ne != nf:
                errs.append(f"fr/faq/index.html: {nf} {what}, EN has {ne} (the FR FAQ must be a full translation; see exclusions.json fr-faq rule)")
    # Upcoming-event banner (4 Oct 2026, Joachim): while any public event has not ended, both home pages must show it,
    # pointing at the soonest one, with the embedded list site.js uses to keep it current. It vanished once before (2-4 Oct)
    # because the old 'New event' line was frozen at build time on an event that then ended.
    for l_ in (() if "events" in HIDDEN else LANGS):  # Events hidden (hide_events_getinvolved_v1): no banner by design
        hp = dist / url(l_, "home").lstrip("/") / "index.html"; ht = hp.read_text(); up = events_cal.upcoming(l_, SITE)
        m_ = re.search(r'<div class="newev nextev" id="nextev"( hidden)?>(.*?)<script type="application/json" id="nextev-data">(.*?)</script>', ht, re.S)
        if not m_: errs.append(f"{hp.relative_to(dist)}: upcoming-event banner missing"); continue
        if up and (m_.group(1) or f'?e={up[0]["i"]}"' not in m_.group(2)):
            errs.append(f"{hp.relative_to(dist)}: {len(up)} upcoming events but the banner is hidden or not on the next one (id {up[0]['i']})")
        try:
            if len(json.loads(m_.group(3).replace("<\\/", "</"))["u"]) != len(up): errs.append(f"{hp.relative_to(dist)}: banner data does not list every upcoming event")
            bd = json.loads(m_.group(3).replace("<\\/", "</"))  # 48 h New badge (4 Oct 2026): exact ISO times, not dates
            if not bd.get("built") or not bd.get("hours") or any(x["n"] and "T" not in x["n"] for x in bd["u"]): errs.append(f"{hp.relative_to(dist)}: banner New times are not ISO timestamps")
        except ValueError as ex: errs.append(f"{hp.relative_to(dist)}: banner data is not valid JSON ({ex})")
    if 'getElementById("nextev")' not in (dist / "assets/js/site.js").read_text(): errs.append("assets/js/site.js no longer updates the upcoming-event banner (#nextev)")
    home = (dist / "index.html").read_text()
    if "Safer streets, honest budgets, a downtown that works." not in home:
        errs.append("index.html: tagline missing")
    return errs


BUILD_ID = "dev"

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--env", choices=["staging", "live"], default="staging"); ap.add_argument("--out", default="dist")
    a = ap.parse_args()
    DRAFT_ENV["env"] = a.env
    import subprocess, datetime
    try:
        BUILD_ID = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        BUILD_ID = datetime.datetime.now().strftime("%Y%m%d%H%M")
    no_party.ON["on"] = no_party.NP_ON(a.env, SITE)
    HIDE_EG["on"] = bool(SITE.get("hide_events_getinvolved_v1")) and (a.env == "staging" or bool(SITE.get("hide_events_getinvolved_v1_live")))
    if HIDE_EG["on"]:  # Joachim 8 Oct 2026 6:00 PM PT: hide Events and Get involved (+ its pages) until he changes them; sources stay
        HIDDEN.update(HIDE_EG["keys"])
    if no_party.ON["on"]:  # no-party version: donate page gone, party text edited out, party events hidden (see no_party.py)
        no_party.setup(HIDDEN, UI, SEO, prio_layout, events_cal, ROOT)
    if a.env == "live" and not SITE.get("publish_faq_live", True):
        HIDDEN.add("faq")
    if a.env == "live" and not SITE.get("publish_scorecard_live", False):
        HIDDEN.add("scorecard")
    if a.env == "live" and not SITE.get("publish_province_live", False):
        HIDDEN.add("province")
    if a.env == "live" and SITE.get("publish_province_live") and not SITE.get("province_fr_reviewed"):
        sys.exit("Live build refused: /fr/province/ is still a draft translation (site.json province_fr_reviewed is false). "
                 "Have Joachim review it, set province_fr_reviewed to true, then build live (see RESYNC.md).")
    if not updates.load(a.env, SITE, VIC.get("photos", {}) if (VIC_ON(a.env) and VIC) else {}):  # zero entries: no section, page, feed or link
        HIDDEN.add("updates")
    else:
        updates.ensure_images(updates.STATE["entries"], VIC.get("photos", {}))
        SITE["updated"]["updates"] = updates.STATE["entries"][0]["date"]
        updates.register(sys.modules[__name__])  # one permalink page per entry (/updates/<date>-<slug>/)
    if HIDDEN:
        PAGES[:] = [p for p in PAGES if p["key"] not in HIDDEN]
        SITE["footer_nav"] = [k for k in SITE["footer_nav"] if k not in HIDDEN]
        for p in PAGES:
            if p.get("children"): p["children"] = [k for k in p["children"] if k not in HIDDEN]
    if NOMINATIONS_CLOSED:  # /nominate/ stays (thank-you note) but leaves every menu, the footer and the sitemap
        SITE["main_nav"] = [k for k in SITE["main_nav"] if k != "nominate"]
        SITE["footer_nav"] = [k for k in SITE["footer_nav"] if k != "nominate"]
        for p in PAGES:
            if p.get("children"): p["children"] = [k for k in p["children"] if k != "nominate"]
        BYKEY["nominate"]["robots"] = "noindex"
    if a.env == "live" and not SITE.get("events_redesign_approved", True):
        sys.exit("Live build refused: staging contains the 30 Sep 2026 events redesign (date tiles, directions, static maps), not yet approved by Joachim. "
                 "Set site.json events_redesign_approved to true after approval, or publish from a branch without it (see RESYNC.md).")
    if a.env == "live" and not SITE.get("fr_faq_approved", True):
        sys.exit("Live build refused: the complete FR FAQ translation (30 Sep 2026) is on staging for Joachim's review. "
                 "Set site.json fr_faq_approved to true after approval, or publish from a branch without it (see RESYNC.md).")
    if a.env == "live" and not SITE.get("fr_edits_approved", True):
        sys.exit("Live build refused: staging contains Joachim's 30 Sep 2026 FR corrections and About career-history changes (navy role, Joa Aero Engineering, 15 years), not yet approved. "
                 "Set site.json fr_edits_approved to true after approval, or publish from a branch without them (see RESYNC.md).")
    if a.env == "live" and not SITE.get("seo_batch_approved", True):
        sys.exit("Live build refused: staging contains the 30 Sep 2026 SEO/social metadata batch (seo.json titles and descriptions, new og:image, JSON-LD, sitemap), not yet approved by Joachim. "
                 "Set site.json seo_batch_approved to true after approval, or publish from a branch without it (see RESYNC.md).")
    if a.env == "live" and HS_BG and not SITE.get("headshot_background_approved"):
        sys.exit("Live build refused: staging shows a headshot background option (site.json headshot_background), not yet picked by Joachim. "
                 "Set headshot_background_approved to true after he picks, or publish from a branch without it (see RESYNC.md).")
    if a.env == "live" and not SITE.get("priorities_v2_approved", True):
        sys.exit("Live build refused: staging contains the Priorities v2 restructure (1 Oct 2026: Priorities EN/FR, scorecard item 7 lever), not yet approved by Joachim. "
                 "Set site.json priorities_v2_approved to true after approval, or publish from a branch without it (see RESYNC.md).")
    if a.env == "live" and not SITE.get("review_batch_approved", True):
        sys.exit("Live build refused: staging contains the 30 Sep 2026 review batch (header, forms, sections, actions, FAQ index), not yet approved by Joachim. "
                 "Set site.json review_batch_approved to true after approval, or publish from a branch without it (see RESYNC.md).")
    dist = ROOT / a.out
    if dist.exists(): shutil.rmtree(dist)
    shutil.copytree(ROOT / "assets", dist / "assets")
    if not PRIO2_ON(a.env):  # Priorities summary-first layout off (live while site.json priorities_layout_v2_live is false): its files don't ship
        for f in ("assets/css/prio2.css", "assets/js/prio2.js"): (dist / f).unlink(missing_ok=True)
    for f in (dist / "assets/img").glob("joachim-agou-headshot-bg-*"):  # only the chosen background option ships (site.json headshot_background)
        if not any(f.name.startswith(f"joachim-agou-headshot-bg-{v}-") for v in HS_USED): f.unlink()
    if not (VIC_ON(a.env) and VIC):  # site.json victoria_photos_live false: no Victoria photo files on live
        shutil.rmtree(dist / "assets/img/vic", ignore_errors=True)
    updates.prune_dist(dist)  # Updates: only the photos shown in this build (none with zero entries; never samples on live)
    for f in (dist / "assets/img").glob("og-joachim-agou-photo-bg-*"):
        if not HS_BG or not f.name.startswith(f"og-joachim-agou-photo-bg-{HS_BG}-"): f.unlink()
    # favicon (JOA, tools/make_favicon.py): /favicon.ico at the root, one web manifest per language
    shutil.copy(ROOT / "assets/img/favicon.ico", dist / "favicon.ico")
    for ml, start, desc in (("en", "/", "Joachim Agou, Conservative Party of BC nominee in Victoria–Beacon Hill"),
                            ("fr", "/fr/", "Joachim Agou, investi par le Parti conservateur de la Colombie-Britannique dans Victoria–Beacon Hill")):
        if no_party.ON["on"]: desc = no_party.MANIFEST_DESC[ml]
        man = {"name": "Joachim Agou – Victoria–Beacon Hill", "short_name": "Joachim Agou", "lang": f"{ml}-CA",
               "description": desc, "start_url": start, "scope": "/", "display": "browser",
               "background_color": "#ffffff", "theme_color": "#123a6d",
               "icons": [{"src": "/assets/img/icon-192.png", "sizes": "192x192", "type": "image/png"},
                         {"src": "/assets/img/icon-512.png", "sizes": "512x512", "type": "image/png"},
                         {"src": "/assets/img/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}]}
        (dist / start.lstrip("/")).mkdir(parents=True, exist_ok=True)
        (dist / start.lstrip("/") / "site.webmanifest").write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n")
    MEDIAKIT["env"] = a.env
    MEDIAKIT["on"] = (a.env == "staging" or bool(SITE.get("publish_media_kit_live"))) and not no_party.ON["on"]  # the media-kit PDFs name the party
    if not MEDIAKIT["on"]:
        shutil.rmtree(dist / "assets" / "media", ignore_errors=True)
    MEDIAKIT["errs"] = {f: e for f, e in pdf_check(dist).items() if e}
    for f, es in MEDIAKIT["errs"].items():
        print(f"{'PDF CHECK' if a.env == 'live' else 'WARNING (staging only, would block live)'}: {f.relative_to(dist)}:\n    " + "\n    ".join(es))
    PARTY["on"] = PARTY_ON(a.env) and not no_party.ON["on"]  # no-party version: our own volunteer / lawn-sign forms again
    if PARTY["on"]:  # bridge pages leave the sitemap and search; party wording for their descriptions and the lawn-sign card
        for k in PARTY_MOVED: BYKEY[k]["robots"] = "noindex"
        for k, v in SEO["party_pages"].items(): SEO["pages"][k] = v
        for l in LANGS: UI[l]["lawnsign"]["intro"] = UI[l]["party"]["lawnsign_intro"]
    for lang in LANGS:
        for p in PAGES:
            out = dist / url(lang, p["key"]).lstrip("/") / "index.html"
            out.parent.mkdir(parents=True, exist_ok=True)
            h_ = build_page(lang, p, a.env)
            out.write_text(party_rewrite(h_, lang) if PARTY["on"] else h_)
    # 404
    PAGE_STATE["vic_used"] = []
    nf = shell("en", {"key": "home", "slug": ""}, "Page not found – Joachim Agou", "Page not found.",
               '<div class="page-head"><div class="wrap"><h1>Page not found</h1></div></div><div class="wrap content"><section class="block lead"><p><a href="/">Home</a> · <a href="/fr/" lang="fr">Accueil en français</a></p></section></div>', a.env, robots_override="noindex")
    (dist / "404.html").write_text(party_rewrite(nf, "en") if PARTY["on"] else nf)
    if a.env == "staging":
        (dist / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
        (dist / "_headers").write_text("/*\n  X-Robots-Tag: noindex, nofollow\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n")
    else:
        (dist / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {LIVE}/sitemap.xml\n")
        (dist / "CNAME").write_text("agou.ca\n"); (dist / ".nojekyll").write_text("")
    updates.write_feeds(sys.modules[__name__], dist, a.env)  # /updates/feed.xml, /fr/updates/feed.xml (only with entries)
    (dist / "sitemap.xml").write_text(sitemap())  # staging too, for review (its robots.txt still disallows everything)
    errs = check(dist) + seo_check(dist, a.env) + shifts_check(dist, a.env) + updates.check(sys.modules[__name__], dist, a.env)
    if no_party.ON["on"]:
        errs += sorted(set(no_party.ERRS))
    STUBS = ["donate"] * no_party.ON["on"] + list(HIDE_EG["keys"]) * HIDE_EG["on"]
    if STUBS:
        if a.env == "staging":
            with open(dist / "_redirects", "a") as fh:
                for k_ in STUBS: fh.write(f"/{k_}/ / 302\n/{k_} / 302\n/fr/{k_}/ /fr/ 302\n/fr/{k_} /fr/ 302\n")
        else:  # GitHub Pages has no _redirects: old /donate/ (and hidden Events / Get involved) links and printed QR codes forward to the home page; noindex, no content
            for k_, (pre_, to_) in ((k_, x) for k_ in STUBS for x in (("", "/"), ("fr/", "/fr/"))):
                (dist / pre_ / k_).mkdir(parents=True, exist_ok=True)
                (dist / pre_ / k_ / "index.html").write_text(f'<!doctype html><html lang="{"fr" if pre_ else "en"}"><head><meta charset="utf-8"><meta name="robots" content="noindex">'
                    f'<link rel="canonical" href="{LIVE}{to_}"><meta http-equiv="refresh" content="0; url={to_}"><title>Joachim Agou</title></head>'
                    f'<body><script>location.replace("{to_}")</script><p><a href="{to_}">agou.ca</a></p></body></html>\n')
    if no_party.ON["on"]:
        npl = [h for h in no_party.scan(dist) if not h[3]]
        errs += [f"no_party: {h[0].relative_to(dist)}: {h[1]!r} in …{h[2]}…" for h in npl]
    if NOMINATIONS_CLOSED:  # nothing may link to the retired Nominate page or ask people to sign (its own EN/FR pages excepted)
        nom = {url(l, "nominate") for l in LANGS}; nom_pages = {dist / u.lstrip("/") / "index.html" for u in nom}
        ask = re.compile(r"Sign up to nominate|Become a nominator|I need 75|Put a test engineer on the ballot|S'inscrire pour signer|Il me faut la signature|Mettre un ingénieur d'essais sur le bulletin")
        for f in sorted(dist.rglob("*.html")):
            if f in nom_pages: continue
            t = f.read_text()
            errs += [f"{f.relative_to(dist)}: links to the retired Nominate page ({u})" for u in nom if f'href="{u}"' in t]
            errs += [f"{f.relative_to(dist)}: still asks people to nominate ({m!r})" for m in sorted(set(ask.findall(t)))]
        if "/nominate/" in (dist / "sitemap.xml").read_text(): errs.append("sitemap.xml lists the retired Nominate page")
    if PARTY["on"]:  # party links: no link to our old form pages (language switcher excepted), no form on them, no 'coming soon' donation text
        old = re.compile(r'<a (?![^>]*class="lang")[^>]*href="(?:/fr)?/(?:volunteer|lawn-sign|donate)/"')
        for f in sorted(dist.rglob("*.html")):
            t = f.read_text(); rel_ = f.relative_to(dist).as_posix()
            if old.search(t): errs.append(f"{rel_}: still links to our own volunteer / lawn-sign / donate page (party links are on)")
            if re.search(r"Online donations are coming soon|Les dons en ligne seront bientôt|arrivent bientôt", t): errs.append(f"{rel_}: 'online donations coming soon' text (donations go through the party)")
            if rel_.split("/")[-2:-1] and rel_.split("/")[-2] in PARTY_MOVED and 'id="form-config"' in t: errs.append(f"{rel_}: still has a form (moved to the party)")
        for k in ("volunteer", "lawn-sign"):
            if "recruiter_id=251" not in _PU(k): errs.append(f"site.json party.urls.{k} lost recruiter_id=251")
        if "/volunteer/" in (dist / "sitemap.xml").read_text() or "/donate/" in (dist / "sitemap.xml").read_text() or "/lawn-sign/" in (dist / "sitemap.xml").read_text():
            errs.append("sitemap.xml lists a bridge page (volunteer / lawn-sign / donate)")
    if a.env == "live" and not SITE.get("volunteer_shifts_note_live"):  # 5 Oct 2026 door-knocking shifts block: staging only until approved
        errs += [f"{f.relative_to(dist)}: shows the volunteer-page shifts block, but volunteer_shifts_note_live is false" for f in sorted(dist.rglob("*.html")) if 'class="block vshifts"' in f.read_text()]
    if HIDDEN:
        hu = hidden_urls()
        errs += [f"{f.relative_to(dist)}: links to a page left out of this build ({u})" for f in sorted(dist.rglob("*.html")) for u in hu if f'href="{u}"' in f.read_text()]
    if not VIC_ON(a.env):
        errs += [f"{f.relative_to(dist)}: shows a Victoria photo, but victoria_photos_live is false" for f in sorted(dist.rglob("*.html")) if "/assets/img/vic/" in f.read_text()]
    if a.env == "live":
        errs += [f"{f.relative_to(dist)}: PDF fails content checks ({len(e)} hits, listed above)" for f, e in MEDIAKIT["errs"].items()]
        if not MEDIAKIT["on"]:
            errs += [f"{f.relative_to(dist)}: links to a media-kit PDF, but publish_media_kit_live is false" for f in sorted(dist.rglob("*.html")) if "/assets/media/" in f.read_text()]
        errs += [f"{f.relative_to(dist)}: open draft note (Notion red text, e.g. [TO COMPLETE]); finish it in Notion first" for f in sorted(dist.rglob("*.html")) if 'class="todo"' in f.read_text()]
    n = len(list(dist.rglob("index.html")))
    if errs:
        print("BUILD CHECK FAILED:\n  " + "\n  ".join(errs)); sys.exit(1)
    print(f"Built {n} pages ({a.env}) into {dist.relative_to(ROOT)}; content checks passed.")
