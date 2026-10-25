"""Landing-only mode (site.json thankyou_oct24_v1, 24 Oct 2026). The normal build and all its content checks run first on the full site;
make() then replaces dist/ with ONE English page (Joachim Agou + the thank-you message, no nav, no links, minimal footer) and a noindex
stub for every URL the site had, forwarding to /. check() re-scans what is left. English only: /fr/ forwards to /."""
import html, re, shutil
H1 = "Joachim Agou"
PARAS = [  # Joachim's text, verbatim (Victoria–Beacon Hill with an en dash, the site rule)
    "Thank you, Victoria–Beacon Hill.",
    "It's not the result we hoped for, and I respect the choice voters made. Congratulations to Grace Lore on her re-election, and thank you to Raj Sahota for a respectful campaign.",
    "To every volunteer, supporter and neighbour who gave their time, shared their ideas or opened their door to me: thank you. I learned a lot from you, and I'm grateful.",
    "Health care, housing, costs and safety are still the issues that matter, and I'll keep working on them for a Victoria that works for everyone.",
    "Thank you.",
]
FOOT = "© 2026 Joachim Agou"
MARK = "thankyou_oct24_v1"
CSS = ("*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}body{margin:0;min-height:100vh;display:flex;flex-direction:column;background:#f6f8fc;color:#1b2430;"
       "font:18px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}"
       "main{flex:1;width:100%;max-width:40rem;margin:0 auto;padding:12vh 1.5rem 3rem}"
       "h1{margin:0 0 2.2rem;padding-bottom:1rem;border-bottom:3px solid #123a6d;color:#123a6d;font-size:2.1rem;line-height:1.2;letter-spacing:.01em}"
       "h2{margin:0 0 1.2rem;font-size:1.6rem;line-height:1.25;color:#123a6d}p{margin:0 0 1.2rem}"
       "footer{padding:1.2rem 1.5rem;text-align:center;font-size:.85rem;color:#566175}"
       "@media(max-width:600px){body{font-size:17px}main{padding-top:8vh}h1{font-size:1.8rem}}")


def page(live_origin, env="live"):
    desc = "Thank you, Victoria–Beacon Hill."
    body = f"<h2>{html.escape(PARAS[0])}</h2>" + "".join(f"<p>{html.escape(p)}</p>" for p in PARAS[1:])
    return (f'<!doctype html>\n<html lang="en-CA"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n'
            f'<title>Joachim Agou – Thank you, Victoria–Beacon Hill</title><meta name="description" content="{html.escape(desc)}">\n'
            f'<meta name="landing-only" content="{MARK}">{'<meta name="robots" content="noindex, nofollow">' if env == "staging" else ""}<link rel="canonical" href="{live_origin}/"><link rel="icon" href="/favicon.ico">\n'
            f'<meta property="og:title" content="Joachim Agou – Thank you, Victoria–Beacon Hill"><meta property="og:description" content="{html.escape(desc)}">'
            f'<meta property="og:type" content="website"><meta property="og:url" content="{live_origin}/">\n<style>{CSS}</style></head>\n'
            f'<body><main><h1>{html.escape(H1)}</h1>{body}</main><footer>{html.escape(FOOT)}</footer></body></html>\n')


def stub(live_origin):
    return ('<!doctype html><html lang="en-CA"><head><meta charset="utf-8"><meta name="robots" content="noindex">'
            f'<link rel="canonical" href="{live_origin}/"><meta http-equiv="refresh" content="0; url=/"><title>Joachim Agou</title></head>'
            '<body><script>location.replace("/")</script><p><a href="/">Joachim Agou</a></p></body></html>\n')


def make(dist, env, live_origin):
    old = {"/" + f.parent.relative_to(dist).as_posix() + "/" for f in dist.rglob("index.html") if f.parent != dist}
    for k in ("donate", "events", "nominate", "volunteer", "lawn-sign", "get-involved", "media", "updates"):  # pages the live site has had at any time, even if hidden in this build
        old |= {f"/{k}/", f"/fr/{k}/"}
    old = sorted(old | {"/fr/"})
    keep = (dist / "favicon.ico").read_bytes()
    for f in list(dist.iterdir()):
        shutil.rmtree(f) if f.is_dir() else f.unlink()
    (dist / "favicon.ico").write_bytes(keep)
    (dist / "index.html").write_text(page(live_origin, env))
    for u in old:
        (dist / u.strip("/")).mkdir(parents=True, exist_ok=True); (dist / u.strip("/") / "index.html").write_text(stub(live_origin))
    (dist / "404.html").write_text(stub(live_origin))  # any other old URL (assets, PDFs, feeds, sitemap pages) gets the 404 page, which forwards to /
    if env == "staging":
        (dist / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
        (dist / "_headers").write_text("/*\n  X-Robots-Tag: noindex, nofollow\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n")
        (dist / "_redirects").write_text("".join(f"{u} / 302\n{u.rstrip('/')} / 302\n" for u in old))
    else:
        (dist / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {live_origin}/sitemap.xml\n")
        (dist / "CNAME").write_text("agou.ca\n"); (dist / ".nojekyll").write_text("")
    (dist / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{live_origin}/</loc></url></urlset>\n')


BAD = [(r"(?i)conservative|\bNDP\b|\bgreen party\b|\bBC United\b|\bparty\b|\bparti\b", "a party name or word"), (r"(?i)independent|indépendant", "a label ('Independent')"),
       (r"(?i)donat|\bdons?\b|contribut", "donation wording"), (r"(?i)casagou|thales|\bbert\b|\bchen\b|authori[sz]ed by", "a blocked name / authorization line"),
       (r"(?i)coming soon|bientôt", "'coming soon'"), (r"(?i)\bagou\.ca\b", "an agou.ca link or text"), (r"(?i)\bcandidate\b|\bcandidat\b", "'candidate'"),
       (r"(?i)volunteer sign|sign up|rsvp|nominat|lawn sign", "a call to action")]


def check(dist, env, live_origin, no_party, namefilter):
    errs = []; idx = (dist / "index.html").read_text()
    main = re.search(r"<main>(.*)</main>", idx, re.S).group(1); foot = re.search(r"<footer>(.*)</footer>", idx, re.S).group(1)
    vis = html.unescape(re.sub(r"<[^>]+>", "\n", main)); got = [l.strip() for l in vis.split("\n") if l.strip()]
    if got != [H1] + PARAS: errs.append(f"landing text differs from Joachim's message: {got}")
    if re.search(r"<(a|form|nav|button|input|iframe|img|video|script)\b", idx): errs.append("landing page has a link, form, nav, image or script")
    if "href=" in re.sub(r'<link rel="(canonical|icon)"[^>]*>', "", idx): errs.append("landing page has an href beyond canonical/icon")
    if foot != html.escape(FOOT): errs.append("footer is not the minimal line")
    for pat, why in BAD:
        for m in re.finditer(pat, vis + " " + foot + " " + re.search(r"<title>.*?</title>", idx).group(0) + re.search(r'name="description" content="[^"]*"', idx).group(0)): errs.append(f"landing page contains {why}: {m.group(0)!r}")
    for m in no_party.TERMS.finditer(idx):
        if not no_party.allowed(idx, m): errs.append(f"landing page party term {m.group(0)!r}")
    h = namefilter.hits(idx)
    if h: errs.append(f"landing page: blocked name {h[0][0]!r}")
    files = sorted(p.relative_to(dist).as_posix() for p in dist.rglob("*") if p.is_file())
    for f in files:
        if f.endswith("index.html") and f != "index.html" and "noindex" not in (dist / f).read_text(): errs.append(f"{f}: stub is not noindex")
        if f.endswith("index.html") and f != "index.html" and 'content="0; url=/"' not in (dist / f).read_text(): errs.append(f"{f}: stub does not forward to /")
        if f.rsplit(".", 1)[-1] in ("pdf", "jpg", "jpeg", "png", "webp", "avif", "js", "css", "ics", "json"): errs.append(f"{f}: leftover asset in landing-only mode")
    sm = (dist / "sitemap.xml").read_text()
    if re.findall(r"<loc>", sm) != ["<loc>"]: errs.append("sitemap should list only /")
    if env == "staging" and "Disallow: /" not in (dist / "robots.txt").read_text(): errs.append("staging robots.txt must disallow")
    return errs
