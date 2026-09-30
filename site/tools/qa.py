#!/usr/bin/env python3
"""QA: screenshots (phone 390x844 + desktop 1440x900, EN+FR), console errors, horizontal scroll, small tap targets, internal links.
Usage: python3 tools/qa.py BASE_URL OUT_DIR   (e.g. http://localhost:8765 /workspace/bhm-shots/site)"""
import sys, json, re, pathlib, urllib.parse
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = json.loads((ROOT / "site.json").read_text())
base = sys.argv[1].rstrip("/"); out = pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
paths = [("/fr/" if l == "fr" else "/") + p["slug"] for p in SITE["pages"] for l in ("en", "fr")] + ["/404.html"]
report = {"pages": {}, "links": {}}
seen_links = set()
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for vp, (w, h) in {"phone": (390, 844), "desktop": (1440, 900)}.items():
        ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=2 if vp == "phone" else 1, is_mobile=vp == "phone", has_touch=vp == "phone")
        for path in paths:
            pg = ctx.new_page(); errs = []
            pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(base + path, wait_until="networkidle")
            pg.wait_for_timeout(300)
            info = pg.evaluate("""() => {
              const sw = document.documentElement.scrollWidth, cw = document.documentElement.clientWidth;
              const small = [];
              document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea, summary').forEach(e => {
                if (e.closest('.hp') || e.closest('[hidden]')) return;
                const r = e.getBoundingClientRect(); if (!r.width || !r.height) return;
                const st = getComputedStyle(e); if (st.visibility === 'hidden' || st.display === 'none') return;
                let h = r.height, w = r.width;
                if ((e.type === 'checkbox' || e.type === 'radio') && e.parentElement.classList.contains('cb')) { const pr = e.parentElement.getBoundingClientRect(); h = pr.height; w = pr.width; }
                const inline = st.display === 'inline' && e.closest('p,li,figcaption');
                if (!inline && (h < 44 || w < 44)) small.push((e.tagName + ' ' + (e.textContent || e.name || e.id || '').trim()).slice(0, 60) + ' ' + Math.round(w) + 'x' + Math.round(h));
              });
              return { overflow: sw > cw, sw, cw, small, links: [...document.querySelectorAll('a[href]')].map(a => a.getAttribute('href')) };
            }""")
            name = ("fr-" if path.startswith("/fr/") else "en-") + (path.strip("/").replace("fr/", "").replace("/", "-").replace(".html", "") or "home")
            if path == "/fr/": name = "fr-home"
            pg.screenshot(path=str(out / f"{name}-{vp}.png"), full_page=True)
            report["pages"].setdefault(path, {})[vp] = {"console_errors": errs, "horizontal_scroll": info["overflow"], "small_targets": info["small"]}
            for l in info["links"]: seen_links.add((path, l))
            pg.close()
        ctx.close()
    # internal links
    rq = pw.request.new_context()
    for src, l in sorted(seen_links):
        if l.startswith(("mailto:", "tel:", "#")) or l.startswith("http") and not l.startswith(base): continue
        u = urllib.parse.urljoin(base + src, l).split("#")[0]
        if u in report["links"]: continue
        r = rq.get(u); report["links"][u] = r.status
    b.close()
bad_links = {u: s for u, s in report["links"].items() if s != 200}
probs = {p: {vp: d for vp, d in v.items() if d["console_errors"] or d["horizontal_scroll"] or d["small_targets"]} for p, v in report["pages"].items()}
probs = {p: v for p, v in probs.items() if v}
(out / "qa-report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
print("internal links checked:", len(report["links"]), "broken:", bad_links)
print("pages with issues:", json.dumps(probs, indent=1, ensure_ascii=False)[:6000])
