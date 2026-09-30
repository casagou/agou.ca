#!/usr/bin/env python3
"""Static build for agou.ca.  python3 build.py --env staging|live  ->  dist/

Content comes from content/<lang>/*.md (made from Notion by tools/notion2md.py).
Interface/form wording comes from ui.json. Page list, photo slots and social links from site.json.
No framework, no dependencies (Python 3 standard library only)."""
import argparse, html, json, re, shutil, pathlib, sys
import scorecard  # /scorecard/ page (scorecard.py, scorecard.json, content/<lang>/scorecard.md)
import province  # /province/ page (province.py, content/<lang>/province.md; not from Notion)

ROOT = pathlib.Path(__file__).resolve().parent
SITE = json.loads((ROOT / "site.json").read_text())
UI = json.loads((ROOT / "ui.json").read_text())
SEO = json.loads((ROOT / "seo.json").read_text())  # titles, descriptions, og:image per page and language (see seo.json _doc)
STAGING_ORIGIN = "https://agou-staging.pages.dev"  # og:image host on staging builds, so shared staging links preview the new image
PAGES = SITE["pages"]
BYKEY = {p["key"]: p for p in PAGES}
LIVE = SITE["live_origin"]
LANGS = ["en", "fr"]
HIDDEN = set()  # page keys left out of this build (see site.json publish_faq_live); filled in __main__
MEDIAKIT = {"on": True, "env": "staging", "errs": {}}  # media-kit PDFs (site.json media_kit / publish_media_kit_live); set in __main__
IMG = {  # local image name -> (files by width, width, height)
    "joachim-agou-speaking": ({800: "joachim-agou-speaking-800.jpg", 1600: "joachim-agou-speaking-1600.jpg"}, 1600, 1000),
}
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


PAGE_STATE = {"hero_map": False}  # set while building the home page when the hero already shows the riding map


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
                out.append(f'<p class="readlink"><a href="{esc(SITE["social"]["Instagram"])}" rel="noopener">{esc(UI[lang]["more_photos"])} <span aria-hidden="true">↗</span></a></p>')
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


def collapse(html, lang, keep_chars=320, min_hidden=300):
    """Presentation only: in each <section class="block">, keep the first children visible (about keep_chars of text),
    put the rest in a region toggled by a 'Read more' button. Without JS the region stays visible (the button is hidden).
    Trailing call-to-action / page links stay visible. Text is unchanged (diffcheck still sees every line)."""
    U = UI[lang]; lines = html.split("\n"); out = []; i = 0; n = 0
    while i < len(lines):
        ln = lines[i]
        if not ln.startswith('<section class="block"'):
            out.append(ln); i += 1; continue
        j = i + 1; kids = []
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
        vis = []
        while kids and (not vis or sum(map(txt, vis)) < keep_chars):
            vis.append(kids.pop(0))
        if kids and sum(map(txt, kids)) >= min_hidden and not any("<details" in k or "<nav" in k for k in kids):
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
    p = ROOT / "content" / lang / f"{key}.md"
    return p.read_text() if p.exists() else None


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


def form_html(kind, lang):
    T = UI[lang][kind] if kind != "events" else UI[lang]["events"]
    if kind == "volunteer":
        body = (f'<div class="row"><div>{f_input("first_name", T["first_name"], attrs="autocomplete=\"given-name\" autocapitalize=\"words\" required maxlength=\"80\"")}</div>'
                f'<div>{f_input("last_name", T["last_name"], attrs="autocomplete=\"family-name\" autocapitalize=\"words\" required maxlength=\"80\"")}</div></div>'
                + f_input("email", T["email"], "email", 'autocomplete="email" autocapitalize="off" spellcheck="false" required maxlength="200" inputmode="email"')
                + f_input("phone", T["phone"], "tel", 'autocomplete="tel" required maxlength="30" inputmode="tel"')
                + f_input("address", T["address"], "text", f'autocomplete="street-address" maxlength="200" placeholder="{esc(T["address_ph"])}"', opt=T["optional"])
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
    btn = f'<button id="btn" class="btn primary block" type="submit">{esc(T["button"])}</button><div id="msg" class="msg" role="status" aria-live="polite" tabindex="-1"></div>'
    return f'<form id="f" class="card form" novalidate>{body}{honeypot(T)}{btn}</form>'


def form_block(kind, lang):
    T = UI[lang][kind]
    intro = f'<p>{esc(T["intro"])}</p>' + (f'<p>{esc(T["delivery"])}</p>' if kind == "lawnsign" else "")
    return (f'<section class="block formblock" id="form" aria-labelledby="form-title"><h2 id="form-title">{esc(T["title"])}</h2>'
            f'<p class="sub">{esc(T["sub"])}</p><div class="intro">{intro}</div>{form_html(kind, lang)}'
            f'<p class="privacy-note"><a href="{url(lang, "privacy")}">{esc(BYKEY["privacy"]["nav"][lang])}</a></p></section>')


# ---------------- page shell ----------------
ICONS = {
    "Instagram": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M12 2.2c3.2 0 3.6 0 4.8.1 1.2.1 1.8.2 2.2.4.6.2 1 .5 1.4.9.4.4.7.8.9 1.4.2.4.4 1.1.4 2.2.1 1.3.1 1.6.1 4.8s0 3.6-.1 4.8c-.1 1.2-.2 1.8-.4 2.2-.2.6-.5 1-.9 1.4-.4.4-.8.7-1.4.9-.4.2-1.1.4-2.2.4-1.3.1-1.6.1-4.8.1s-3.6 0-4.8-.1c-1.2-.1-1.8-.2-2.2-.4-.6-.2-1-.5-1.4-.9-.4-.4-.7-.8-.9-1.4-.2-.4-.4-1.1-.4-2.2C2.2 15.6 2.2 15.2 2.2 12s0-3.6.1-4.8c.1-1.2.2-1.8.4-2.2.2-.6.5-1 .9-1.4.4-.4.8-.7 1.4-.9.4-.2 1.1-.4 2.2-.4C8.4 2.2 8.8 2.2 12 2.2zm0 1.8c-3.1 0-3.5 0-4.7.1-1.1.1-1.7.2-2.1.4-.5.2-.9.4-1.3.8-.4.4-.6.8-.8 1.3-.2.4-.3 1-.4 2.1C2.6 8.9 2.6 9.3 2.6 12s0 3.1.1 4.3c.1 1.1.2 1.7.4 2.1.2.5.4.9.8 1.3.4.4.8.6 1.3.8.4.2 1 .3 2.1.4 1.2.1 1.6.1 4.7.1s3.5 0 4.7-.1c1.1-.1 1.7-.2 2.1-.4.5-.2.9-.4 1.3-.8.4-.4.6-.8.8-1.3.2-.4.3-1 .4-2.1.1-1.2.1-1.6.1-4.3s0-3.1-.1-4.3c-.1-1.1-.2-1.7-.4-2.1-.2-.5-.4-.9-.8-1.3-.4-.4-.8-.6-1.3-.8-.4-.2-1-.3-2.1-.4C15.5 4 15.1 4 12 4zm0 3.1a4.9 4.9 0 110 9.8 4.9 4.9 0 010-9.8zm0 8a3.1 3.1 0 100-6.2 3.1 3.1 0 000 6.2zm5.1-8.3a1.1 1.1 0 110-2.3 1.1 1.1 0 010 2.3z"/></svg>',
    "X": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M18.2 2.3h3.4l-7.4 8.4 8.7 11.5h-6.8l-5.3-7-6.1 7H1.3l7.9-9L.9 2.3h7l4.8 6.4 5.5-6.4zm-1.2 17.9h1.9L7.1 4.2H5.1l11.9 16z"/></svg>',
    "Facebook": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M22 12a10 10 0 10-11.6 9.9v-7H7.9V12h2.5V9.8c0-2.5 1.5-3.9 3.8-3.9 1.1 0 2.2.2 2.2.2v2.5h-1.3c-1.2 0-1.6.8-1.6 1.6V12h2.8l-.4 2.9h-2.3v7A10 10 0 0022 12z"/></svg>',
}


def social_links(cls):
    return f'<ul class="{cls}">' + "".join(f'<li><a href="{esc(u)}" rel="me noopener">{ICONS[n]}<span>{n}</span></a></li>' for n, u in SITE["social"].items() if not n.startswith("_")) + "</ul>"


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
            f'<section aria-labelledby="fc"><h2 id="fc">{contact_h}</h2>{contact_html}<p class="soc-label">{esc(U["social_label"])}</p>{social_links("social")}{rest_html}</section>'
            f'<section aria-label="{esc(fa[0].strip("*"))}">{fa_html}</section>'
            f'<nav aria-label="{esc(U["footer_nav"])}"><ul class="fnav">{nav}</ul></nav>'
            f'</div><div class="wrap">{auth}</div></footer>')


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
    OG = SEO["og_image"]
    og_img = f'{LIVE if env == "live" else STAGING_ORIGIN}/assets/img/{OG[lang]}'
    og_type = "profile" if key == "about" else "website"
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
        items.append(f'<li{" class=\"has-sub\"" if kids else ""}><a href="{url(lang, k)}"{cur(k)}{active}>{esc(p.get("nav_short", p["nav"])[lang])}</a>{sub}</li>')
    navs = f'<li class="nav-cta"><a class="btn primary" href="{url(lang, "volunteer")}">{esc(U["cta_volunteer"])}</a></li>' + "".join(items)
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
<meta property="og:image:type" content="image/png">
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
   <a class="btn primary hdr-cta" href="{cta_v}">{esc(U['cta_volunteer'])}</a>
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
              "image": LIVE + "/assets/img/joachim-agou-speaking-1600.jpg", "knowsLanguage": ["en", "fr"],
              "sameAs": [u for n, u in SITE["social"].items() if not n.startswith("_")],
              "description": SEO["pages"]["home"][lang]["desc"]}
    if key == "home":
        graph = [person, {"@type": "WebSite", "@id": LIVE + "/#website", "name": UI[lang]["site_name"], "url": home,
                          "inLanguage": f"{lang}-CA", "publisher": {"@id": LIVE + "/#joachim"}}]
    else:
        crumbs = [(BYKEY["home"]["nav"][lang], home)]
        parent = next((p["key"] for p in PAGES if key in (p.get("children") or [])), None)
        if parent: crumbs.append((BYKEY[parent]["nav"][lang], LIVE + url(lang, parent)))
        crumbs.append((BYKEY[key]["nav"][lang], canonical))
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
    if key == "scorecard":  # /scorecard/: own layout, see scorecard.py
        return scorecard.scorecard_page(sys.modules[__name__], lang, page, env)
    if key == "province":  # /province/: own layout, see province.py
        return province.page(sys.modules[__name__], lang, page, env)
    self_path = url(lang, key)
    ctx = {"self": self_path, "self_anchor": "#form" if page.get("form") in ("volunteer", "nominate", "lawnsign") else "#events-list"}
    home = read(lang, "home")
    if key == "home":
        md = drop_hidden_sections(home, lang)
        top, rest = md.split("\n## ", 1)
        rest = "## " + rest
        tl = [l for l in top.split("\n") if l.strip()]
        sub, tagline = tl[0], tl[1]
        # hero: status line, tagline, short intro paragraph(s), the nominator callout, then an optional "Sources:" line
        c0 = next(k for k, l in enumerate(tl) if l.strip().startswith("<callout"))
        c1 = next(k for k, l in enumerate(tl) if l.strip().startswith("</callout>"))
        intro = "".join(f'<p class="hero-intro">{inline(l.strip(), ctx)}</p>' for l in tl[2:c0])
        callout = "\n".join(tl[c0:c1 + 1])
        hero_src = "".join(f'<p class="hero-src">{inline(l.strip(), ctx)}</p>' for l in tl[c1 + 1:])
        # Follow along section goes before Donate
        donate_h = page_section_title("donate", lang)
        follow = f'<section class="block follow" aria-labelledby="follow"><h2 id="follow">{esc(U["follow_title"])}</h2><p>{esc(U["follow_text"])}</p>{social_links("social big")}</section>'
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
        hero = (f'<div class="hero"><div class="wrap hero-grid"><div class="hero-text">'
                f'<h1>{esc(U["home_title"])}</h1><p class="hero-sub">{inline(sub, ctx)}</p><p class="tagline">{inline(tagline, ctx)}</p><p class="lockup">{esc(U["lockup"])}</p>'
                f'{intro}{hero_callout}</div>{hero_media}</div>'
                + (f'<div class="wrap">{hero_src}</div>' if hero_src else "") + '</div>')
        main = hero + shortcuts(lang) + home_layout(collapse(body, lang), lang) + f'<div class="wrap home-foot">{updated_for(lang, "home")}</div>'
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
        h1 = page["section"][lang]; md = section(home, h1)
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
    if key == "priorities":
        body = collapse(body, lang)
    if key == "priorities" and "province" not in HIDDEN:  # "Who controls what? See what the Province actually controls →"
        body = province.line(sys.modules[__name__], lang, "prio") + body
    if key == "priorities" and "scorecard" not in HIDDEN:
        body = scorecard.priorities_link(sys.modules[__name__], lang) + scorecard.priorities_related(sys.modules[__name__], lang, body)
    if key == "faq" and heads:
        idx = "".join(f'<li><a href="#{h}">{inline(t_, ctx)}</a></li>' for h, t_ in heads)
        body = (f'<div class="faq-layout"><nav class="faq-index" aria-label="{esc(U["faq_index"])}"><p class="faq-index-t" aria-hidden="true">{esc(U["faq_index"])}</p><ul>{idx}</ul></nav>'
                f'<div class="faq-main">{body}</div></div>')
    if key == "get-involved":
        body = hub(lang, home)
    if key in ("how-to-vote", "donate", "volunteer", "events", "nominate") and body and not body.lstrip().startswith("<section"):
        body = f'<section class="block lead">{body}</section>'
    if key == "how-to-vote":
        V = U["vote"]
        facts = "".join(f'<li>{esc(t)} <a class="srclink" href="{esc(u_)}" rel="noopener">{esc(V["src_link"])}</a></li>' for t, u_ in V["facts"])
        links = "".join(f'<li><a href="{esc(u_)}" rel="noopener">{esc(t)}</a></li>' for t, u_ in V["links"])
        body = (f'<section class="block keydates" aria-labelledby="kd"><h2 id="kd">{esc(V["title"])}</h2><p class="src">{esc(V["source"])}</p><ul class="facts">{facts}</ul>'
                f'<h3>{esc(V["links_title"])}</h3><ul class="links">{links}</ul></section>' + body + map_block(lang))
    if key in ("how-to-vote", "get-involved") and "faq" not in HIDDEN:
        body += faq_block(lang)
    if key == "about":
        body = photo_slot("about-portrait", lang, "about-photo") + body
    if page.get("form") in ("volunteer", "nominate", "lawnsign"):
        body += form_block(page["form"], lang)
        extra = f'<script id="form-config" type="application/json">{json.dumps({"form": page["form"], "text": UI[lang][page["form"]], "common": UI[lang]["form_common"]}, ensure_ascii=False).replace("</", "<\\/")}</script>\n<script src="/assets/js/forms.js?v={BUILD_ID}" defer></script>\n'
    if page.get("form") == "events":
        T = U["events"]
        body = f'<div data-hide-on-detail>{body}</div><section class="block" id="events-list" aria-live="polite"><div id="listView"><div id="list"><p class="note">{esc(T["loading"])}</p></div></div><article id="detailView" class="detail" hidden></article></section>'
        extra = f'<script id="form-config" type="application/json">{json.dumps({"form": "events", "live_url": LIVE + self_path, "text": T, "common": U["form_common"], "maps": event_maps()}, ensure_ascii=False).replace("</", "<\\/")}</script>\n<script src="/assets/js/forms.js?v={BUILD_ID}" defer></script>\n'
    lock = f'<p class="lockup">{esc(U["lockup"])}</p>' if key == "priorities" else ""  # two-line lockup: home, Priorities, Scorecard only
    if key == "priorities":
        rid = slugify(U["lockup_block"])
        m_ = re.search(rf'<h2 id="{re.escape(rid)}">.*?</h2>', body)
        if not m_: sys.exit(f"priorities: '{U['lockup_block']}' section not found (needed for the lockup)")
        body = body[:m_.end()] + f'<p class="lockup lockup-block">{esc(U["lockup"])}</p>' + body[m_.end():]
    main = f'<div class="page-head"><div class="wrap"><h1>{esc(h1)}</h1>{lock}</div></div><div class="wrap content">{body}{updated_for(lang, key)}</div>'
    desc = first_text(md) if md else U["lawnsign"]["intro"] if key == "lawn-sign" else ""
    if key == "lawn-sign": desc = U["lawnsign"]["intro"]
    title = f"{h1} – Joachim Agou – Victoria–Beacon Hill"
    out = shell(lang, page, title, desc, main, env)
    return out.replace("</body>", extra + "</body>", 1) if extra else out


def shortcuts(lang):
    """Compact row of section shortcuts under the home hero (existing pages)."""
    items = "".join(f'<li><a href="{url(lang, k)}">{esc(BYKEY[k]["nav"][lang])}</a></li>' for k in ("priorities", "get-involved", "events", "how-to-vote"))
    return f'<nav class="shortcuts" aria-label="{esc(UI[lang]["shortcuts_label"])}"><div class="wrap"><ul>{items}</ul></div></nav>'


def home_layout(body, lang):
    """Home: open reading sections, one pale-blue band with the ways to help as cards, then Events and Follow along side by side."""
    parts = re.split(r"\n?(?=<section class=\"block)", body)
    secs = [s for s in parts if s.strip()]
    sid = lambda s: re.search(r'aria-labelledby="([^"]+)"', s).group(1)
    by = {sid(s): s for s in secs}
    pick = lambda k: slugify(page_section_title(k, lang))
    help_ids = [i for i in (pick("nominate"), pick("volunteer"), pick("donate")) if i in by]
    side_ids = [i for i in (pick("events"), "follow") if i in by]
    order = [sid(s) for s in secs]
    first = [i for i in order[:2]]
    rest = [i for i in order if i not in first + help_ids + side_ids]
    card = lambda s: s.replace('<section class="block"', '<section class="block card-sec"', 1)
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
        cands.append(U.get("en-media"))
    d = max(c for c in cands if c)
    y, m, dd = map(int, d.split("-"))
    txt = f"{dd} {MONTHS[lang][m - 1]} {y}"
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
    (r"\bJoa\b", "the nickname Joa"), (r"Victoria-Beacon Hill", "hyphen instead of en dash in Victoria–Beacon Hill"),
    (r"is the Conservative Party of BC candidate|Party of BC candidate in|est le candidat du Parti", "wording that implies he is the confirmed candidate"),
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
    (r"Candidat à l" + A_ + "investiture|candidat à l" + A_ + "investiture", "old 'Candidat à l'investiture' status line (use 'Je sollicite l'investiture…')"),
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
EXPERIENCE_OLD = r"(?i)(more than|over)\s+(12|twelve)\s+years|\b(12|twelve) years of experience|plus de (12|douze) ans"
PHONES_OK = {"672-922-7017", "778-996-9910", "1-800-661-8683", "16729227017", "17789969910"}


def check(dist):
    errs = []
    for f in sorted(dist.rglob("*.html")):
        t = f.read_text()
        vis = re.sub(r"<script.*?</script>", " ", t, flags=re.S)
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
    home = (dist / "index.html").read_text()
    if "Safer streets, honest budgets, a downtown that works." not in home:
        errs.append("index.html: tagline missing")
    return errs


BUILD_ID = "dev"

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--env", choices=["staging", "live"], default="staging"); ap.add_argument("--out", default="dist")
    a = ap.parse_args()
    import subprocess, datetime
    try:
        BUILD_ID = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        BUILD_ID = datetime.datetime.now().strftime("%Y%m%d%H%M")
    if a.env == "live" and not SITE.get("publish_faq_live", True):
        HIDDEN.add("faq")
    if a.env == "live" and not SITE.get("publish_scorecard_live", False):
        HIDDEN.add("scorecard")
    if a.env == "live" and not SITE.get("publish_province_live", False):
        HIDDEN.add("province")
    if a.env == "live" and SITE.get("publish_province_live") and not SITE.get("province_fr_reviewed"):
        sys.exit("Live build refused: /fr/province/ is still a draft translation (site.json province_fr_reviewed is false). "
                 "Have Joachim review it, set province_fr_reviewed to true, then build live (see RESYNC.md).")
    if HIDDEN:
        PAGES[:] = [p for p in PAGES if p["key"] not in HIDDEN]
        SITE["footer_nav"] = [k for k in SITE["footer_nav"] if k not in HIDDEN]
        for p in PAGES:
            if p.get("children"): p["children"] = [k for k in p["children"] if k not in HIDDEN]
    if a.env == "live" and not SITE.get("events_redesign_approved", True):
        sys.exit("Live build refused: staging contains the 30 Sep 2026 events redesign (date tiles, directions, static maps), not yet approved by Joachim. "
                 "Set site.json events_redesign_approved to true after approval, or publish from a branch without it (see RESYNC.md).")
    if a.env == "live" and not SITE.get("fr_faq_approved", True):
        sys.exit("Live build refused: the complete FR FAQ translation (30 Sep 2026) is on staging for Joachim's review. "
                 "Set site.json fr_faq_approved to true after approval, or publish from a branch without it (see RESYNC.md).")
    if a.env == "live" and not SITE.get("fr_edits_approved", True):
        sys.exit("Live build refused: staging contains Joachim's 30 Sep 2026 FR corrections and About career-history changes (navy role, JOA Aero Engineering, 15 years), not yet approved. "
                 "Set site.json fr_edits_approved to true after approval, or publish from a branch without them (see RESYNC.md).")
    if a.env == "live" and not SITE.get("seo_batch_approved", True):
        sys.exit("Live build refused: staging contains the 30 Sep 2026 SEO/social metadata batch (seo.json titles and descriptions, new og:image, JSON-LD, sitemap), not yet approved by Joachim. "
                 "Set site.json seo_batch_approved to true after approval, or publish from a branch without it (see RESYNC.md).")
    if a.env == "live" and not SITE.get("review_batch_approved", True):
        sys.exit("Live build refused: staging contains the 30 Sep 2026 review batch (header, forms, sections, actions, FAQ index), not yet approved by Joachim. "
                 "Set site.json review_batch_approved to true after approval, or publish from a branch without it (see RESYNC.md).")
    dist = ROOT / a.out
    if dist.exists(): shutil.rmtree(dist)
    shutil.copytree(ROOT / "assets", dist / "assets")
    # favicon (JOA, tools/make_favicon.py): /favicon.ico at the root, one web manifest per language
    shutil.copy(ROOT / "assets/img/favicon.ico", dist / "favicon.ico")
    for ml, start, desc in (("en", "/", "Joachim Agou, seeking the BC Conservative nomination in Victoria–Beacon Hill"),
                            ("fr", "/fr/", "Joachim Agou sollicite l'investiture du Parti conservateur de la Colombie-Britannique afin de représenter Victoria–Beacon Hill à l'Assemblée législative")):
        man = {"name": "Joachim Agou – Victoria–Beacon Hill", "short_name": "Joachim Agou", "lang": f"{ml}-CA",
               "description": desc, "start_url": start, "scope": "/", "display": "browser",
               "background_color": "#ffffff", "theme_color": "#123a6d",
               "icons": [{"src": "/assets/img/icon-192.png", "sizes": "192x192", "type": "image/png"},
                         {"src": "/assets/img/icon-512.png", "sizes": "512x512", "type": "image/png"},
                         {"src": "/assets/img/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}]}
        (dist / start.lstrip("/")).mkdir(parents=True, exist_ok=True)
        (dist / start.lstrip("/") / "site.webmanifest").write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n")
    MEDIAKIT["env"] = a.env
    MEDIAKIT["on"] = a.env == "staging" or bool(SITE.get("publish_media_kit_live"))
    if not MEDIAKIT["on"]:
        shutil.rmtree(dist / "assets" / "media", ignore_errors=True)
    MEDIAKIT["errs"] = {f: e for f, e in pdf_check(dist).items() if e}
    for f, es in MEDIAKIT["errs"].items():
        print(f"{'PDF CHECK' if a.env == 'live' else 'WARNING (staging only, would block live)'}: {f.relative_to(dist)}:\n    " + "\n    ".join(es))
    for lang in LANGS:
        for p in PAGES:
            out = dist / url(lang, p["key"]).lstrip("/") / "index.html"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(build_page(lang, p, a.env))
    # 404
    nf = shell("en", {"key": "home", "slug": ""}, "Page not found – Joachim Agou", "Page not found.",
               '<div class="page-head"><div class="wrap"><h1>Page not found</h1></div></div><div class="wrap content"><section class="block lead"><p><a href="/">Home</a> · <a href="/fr/" lang="fr">Accueil en français</a></p></section></div>', a.env, robots_override="noindex")
    (dist / "404.html").write_text(nf)
    if a.env == "staging":
        (dist / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
        (dist / "_headers").write_text("/*\n  X-Robots-Tag: noindex, nofollow\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n")
    else:
        (dist / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {LIVE}/sitemap.xml\n")
        (dist / "CNAME").write_text("agou.ca\n"); (dist / ".nojekyll").write_text("")
    (dist / "sitemap.xml").write_text(sitemap())  # staging too, for review (its robots.txt still disallows everything)
    errs = check(dist) + seo_check(dist, a.env)
    if HIDDEN:
        hu = hidden_urls()
        errs += [f"{f.relative_to(dist)}: links to a page left out of this build ({u})" for f in sorted(dist.rglob("*.html")) for u in hu if f'href="{u}"' in f.read_text()]
    if a.env == "live":
        errs += [f"{f.relative_to(dist)}: PDF fails content checks ({len(e)} hits, listed above)" for f, e in MEDIAKIT["errs"].items()]
        if not MEDIAKIT["on"]:
            errs += [f"{f.relative_to(dist)}: links to a media-kit PDF, but publish_media_kit_live is false" for f in sorted(dist.rglob("*.html")) if "/assets/media/" in f.read_text()]
        errs += [f"{f.relative_to(dist)}: open draft note (Notion red text, e.g. [TO COMPLETE]); finish it in Notion first" for f in sorted(dist.rglob("*.html")) if 'class="todo"' in f.read_text()]
    n = len(list(dist.rglob("index.html")))
    if errs:
        print("BUILD CHECK FAILED:\n  " + "\n  ".join(errs)); sys.exit(1)
    print(f"Built {n} pages ({a.env}) into {dist.relative_to(ROOT)}; content checks passed.")
