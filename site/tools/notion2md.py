#!/usr/bin/env python3
"""Convert a saved notion-fetch result into a clean content file.

Usage:  python3 tools/notion2md.py            # convert every notion-raw/*.txt
        python3 tools/notion2md.py en-about   # convert one page

Input:  notion-raw/<lang>-<key>.txt  = the page text returned by the notion-fetch tool
        (the whole "text" value, or just what is between <content> and </content>).
Output: content/<lang>/<key>.md       (+ content/<lang>/_contact.md from the home page)

What it does, in order (nothing else is changed; the words stay Notion's):
 1. keeps only the <content> part;
 2. drops the Notion nav bar at the top (everything up to the first '---' line);
 3. cuts the Contact / Coordonnées block at the bottom (the site shows it on every page from the home page);
 4. removes Notion colour tags like {color="blue"} and signed-URL query strings on images;
 5. applies the exact-string rules in exclusions.json (privacy / wording rules) and reports each one;
 6. rewrites links: Notion page links and agou.ca links become site links in the right language.
"""
import json, re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = json.loads((ROOT / "site.json").read_text())
EXCL = json.loads((ROOT / "exclusions.json").read_text())["rules"]

# Notion page id (no dashes) -> (lang, key)
NOTION = {}
for key, ids in SITE["notion"].items():
    for lang, pid in ids.items():
        if pid:
            NOTION[pid.replace("-", "")] = (lang, key)
AGOU = {"": "home", "volunteer": "volunteer", "nominate": "nominate", "events": "events", "lawn-sign": "lawn-sign"}
SLUG = {p["key"]: p["slug"] for p in SITE["pages"]}


def url_for(lang, key):
    return ("/fr/" if lang == "fr" else "/") + SLUG[key]


def map_link(url, lang):
    m = re.match(r"https?://(?:app\.notion\.com|www\.notion\.so|notion\.so)/(?:[^/]+/)*p?/?(?:[^/?#]*-)?([0-9a-f]{32})", url)
    if m and m.group(1) in NOTION:
        l, key = NOTION[m.group(1)]
        return url_for(l, key)
    m = re.match(r"https?://(?:www\.)?agou\.ca/?([a-z-]*)/?(#.*)?$", url)
    if m and m.group(1) in AGOU:
        return url_for(lang, AGOU[m.group(1)]) + (m.group(2) or "")
    if "notion.com" in url or "notion.so" in url:
        raise SystemExit(f"Unknown Notion link {url}: add the page to site.json 'notion'.")
    return url


def convert(name, report):
    lang, key = name.split("-", 1)
    raw = (ROOT / "notion-raw" / f"{name}.txt").read_text()
    # 'Last updated' date: Notion's page_last_edited_at (UTC) converted to Pacific time, if present in the saved text
    m = re.search(r'"?page_last_edited_at"?\s*[:=]\s*"?(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)', raw)
    if m:
        import datetime, zoneinfo
        d = datetime.datetime.fromisoformat(m.group(1)).replace(tzinfo=datetime.timezone.utc).astimezone(zoneinfo.ZoneInfo("America/Vancouver")).date().isoformat()
        site = json.loads((ROOT / "site.json").read_text()); site["updated"][name] = d
        (ROOT / "site.json").write_text(json.dumps(site, ensure_ascii=False, indent=2) + "\n")
        report.append(f"{name}: last updated {d} (from Notion)")
    else:
        report.append(f"{name}: no page_last_edited_at in the saved text; set site.json updated['{name}'] by hand")
    if "<content>" in raw:
        raw = raw.split("<content>", 1)[1].split("</content>", 1)[0]
    raw = raw.replace("\\n", "\n") if "\\n" in raw and "\n" not in raw.strip() else raw
    lines = raw.strip("\n").split("\n")
    # 2. nav bar
    if "---" in lines[:6]:
        lines = lines[lines.index("---") + 1:]
    text = "\n".join(lines) + "\n"
    # 3. contact block
    contact = None
    m = re.search(r"\n---\n## (Contact|Coordonnées)[^\n]*\n", text)
    if m:
        contact = text[m.end():]
        text = text[:m.start() + 1]
    # 4. colour tags, signed URLs
    text = re.sub(r"\s*\{color=\"[a-z_]+\"\}", "", text)
    text = re.sub(r"(\(https://prod-files-secure\.s3[^)?]+)\?[^)]*\)", r"\1)", text)
    # 5. exclusions
    for r in EXCL:
        if r["page"] != name:
            continue
        if r["find"] in text:
            text = text.replace(r["find"], r["replace"])
            report.append(f"{name}: applied rule: {r['why']}  [removed: {r['find'].strip()[:90]!r}]")
        else:
            report.append(f"{name}: WARNING rule not matched (Notion text changed? check by hand): {r['find'].strip()[:90]!r}")
    # 6. links
    text = re.sub(r"\]\((https?://[^)\s]+)\)", lambda mm: "](" + map_link(mm.group(1), lang) + ")", text)
    text = re.sub(r'<(page|mention-page) url="([^"]+)"', lambda mm: f'<{mm.group(1)} url="{map_link(mm.group(2), lang)}"', text)
    out = ROOT / "content" / lang / f"{key}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text.strip("\n") + "\n")
    report.append(f"{name}: wrote {out.relative_to(ROOT)}")
    if key == "home" and contact is not None:
        contact = re.sub(r"\s*\{color=\"[a-z_]+\"\}", "", contact)
        contact = re.sub(r"\]\((https?://[^)\s]+)\)", lambda mm: "](" + map_link(mm.group(1), lang) + ")", contact)
        contact = re.sub(r'<(page|mention-page) url="([^"]+)"', lambda mm: f'<{mm.group(1)} url="{map_link(mm.group(2), lang)}"', contact)
        (ROOT / "content" / lang / "_contact.md").write_text(contact.strip("\n") + "\n")
        report.append(f"{name}: wrote content/{lang}/_contact.md")


if __name__ == "__main__":
    names = sys.argv[1:] or sorted(p.stem for p in (ROOT / "notion-raw").glob("*.txt"))
    rep = []
    for n in names:
        convert(n, rep)
    print("\n".join(rep))
