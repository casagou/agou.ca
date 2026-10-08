#!/usr/bin/env python3
"""Word-for-word check for /province/ ('What the Province actually controls').
1. Every sentence of content/en/province.md must appear in the built dist/province/index.html (markup stripped;
   table rows are compared cell by cell, source lines without their '(https://...)' part).
2. With --source FILE (Joachim's full text, kept outside the repo, e.g. /workspace/agou-site/province-controls-source.md):
   content/en/province.md must be that text line for line, except the approved changes below.
   The source file already holds Joachim's approved fact-check fixes of 30 Sep 2026 (policing line, decriminalization end
   date, parole, and three added sources); APPROVED lists them so the check fails if an old wording comes back.
Usage: python3 tools/province_check.py [--source /workspace/agou-site/province-controls-source.md]"""
import re, sys, html, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
OMIT = ("Sep 30, 2026 · @Joachim Agou", "Separation of powers. Page copy for the Victoria-Beacon Hill candidate site")  # byline + drafting note (approved omissions)
APPROVED = {  # old wording (retracted) -> approved wording, Joachim 30 Sep 2026
    "It also pays for most policing": "It also pays for policing in rural areas and small towns, and cities pay for their own officers.",
    "and parole for sentences of 2 years or more": "and parole (in BC, the Parole Board of Canada decides it for all sentences).",
    "was a federal exemption the Province asked for.\n": "was a federal exemption the Province asked for. It ended on January 31, 2026.",
}
md = (ROOT / "content/en/province.md").read_text()
page = ((pathlib.Path(sys.argv[sys.argv.index("--dist") + 1]) if "--dist" in sys.argv else ROOT / "dist") / "province/index.html").read_text()
txt = re.sub(r"<(script|style).*?</\1>", " ", page, flags=re.S)
txt = re.sub(r'<span class="pv-lbl"[^>]*>.*?</span>', " ", txt)
txt = re.sub(r"</?(em|strong|a|span|mark)\b[^>]*>", "", txt)
txt = html.unescape(re.sub(r"<[^>]+>", " ", txt)).replace("\u00a0", " "); txt = re.sub(r"\s+", " ", txt)
bad = []; n = 0
for old, new in APPROVED.items():
    if old in md or new not in md: bad.append(f"approved fix missing: {new[:80]}")
for l in md.split("\n"):
    s = l.strip()
    if not s: continue
    s = re.sub(r"^#+ |^- ", "", s); s = re.sub(r" \(https?://[^)\s]+\)$", "", s)
    m = re.match(r"^\[TABLE: (.+)\]$", s)
    parts = [c.strip() for c in (m.group(1) if m else s).split(" | ")] if (m or " | " in s) else re.split(r"(?<=[.!?])\s+", s)
    for part in parts:
        n += 1
        if part not in txt: bad.append(part)
print(f"province: {n} sentences/cells checked, {len(bad)} not found on the page")
for b in bad: print("  NOT FOUND:", b[:140])
for banned in ("ACTW", "candidate site", "@Joachim Agou", "Victoria-Beacon Hill", "Separation of powers"):
    if banned in page: print("  DRAFTING TEXT ON PAGE:", banned); bad.append(banned)
if "--source" in sys.argv:
    src = pathlib.Path(sys.argv[sys.argv.index("--source") + 1]).read_text().split("\n")
    want = [l.replace("Victoria-Beacon Hill", "Victoria–Beacon Hill") for l in src if l.strip() and not l.startswith(OMIT)]
    have = [re.sub(r"^#+ ", "", l) for l in md.split("\n") if l.strip()]
    diff = [("missing", w) for w in want if w not in have] + [("added/changed", h) for h in have if h not in want]
    print(f"content/en/province.md vs source: {len(diff)} line(s) differ (after the approved omissions)")
    for k, l in diff: print(f"  {k.upper()}:", l[:140])
    bad += diff
sys.exit(1 if bad else 0)
