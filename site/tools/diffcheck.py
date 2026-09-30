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
        # excluded on purpose? (whole line, or the line with the excluded part removed)
        hit = [r for r in EXCL if r["page"] in (name, "*") and any(plain(fl) and (plain(fl) in p or p == plain(fl)) for fl in r["find"].split("\n"))]
        if hit:
            excluded.append(f"{name}: {p[:110]!r}  -> {hit[0]['why']}")
        else:
            problems.append(f"{name} ({page.relative_to(dist)}): NOT FOUND: {p[:140]!r}")
    for u in re.findall(r"\]\((https?://[^)\s]+)\)", main_part):
        if "notion.com" in u or "agou.ca" in u or "prod-files-secure" in u: continue
        if u not in hrefs: problems.append(f"{name}: link missing on page: {u}")
    # contact block (every page footer)
    for l in contact.split("\n"):
        p = plain(l)
        if p == "Instagram · X · Facebook":  # shown as three labelled buttons; check the links instead
            for u in re.findall(r"\((https://[^)]+)\)", l):
                if u not in hrefs: problems.append(f"{name}: social link missing: {u}")
            continue
        if p and p not in ptxt: problems.append(f"{name}: contact line not in footer: {p[:100]!r}")
print(f"Checked {total} Notion lines.")
print("Intentional differences (exclusions.json):"); print("\n".join("  " + e for e in excluded) or "  none")
print("Unexpected differences:"); print("\n".join("  " + p for p in problems) or "  none")
sys.exit(1 if problems else 0)
