#!/usr/bin/env python3
"""Word-for-word check for /scorecard/: every sentence of content/en/scorecard.md (Joachim's text) must appear in the
built page dist/scorecard/index.html. Row labels ("**Target:**" ...) are shown as the row headings, so they are
stripped before comparing. Optional: --source FILE also checks that content/en/scorecard.md is taken verbatim, line
for line, from Joachim's full text (which is kept outside the repo because it contains private notes).
Usage: python3 tools/scorecard_check.py [--source /workspace/agou-site/scorecard-source.md]"""
import re, sys, html, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
md = (ROOT / "content/en/scorecard.md").read_text()
page = (ROOT / "dist/scorecard/index.html").read_text()
txt = re.sub(r"<(script|style).*?</\1>", " ", page, flags=re.S)
txt = re.sub(r"</?(em|strong|a|span|mark)\b[^>]*>", "", txt)
txt = html.unescape(re.sub(r"<[^>]+>", " ", txt)); txt = re.sub(r"\s+", " ", txt)
bad = []; n = 0
for l in md.split("\n"):
    s = l.strip()
    if not s or s == "---": continue
    s = re.sub(r"^\*\*(Target|Today|Source / cadence|Quarterly stand-in|My lever):\*\*\s*", "", s)
    s = re.sub(r"^\d\. ", "", s)
    s = re.sub(r"^\*\*(\d+)\. ", "", s)  # item number is shown in its own badge
    s = s.replace("**Promise — I control this.**", "I control this.")
    s = re.sub(r"\*\*|(?<!\w)\*|\*(?!\w)", "", s).replace("`", "")
    s = re.sub(r"\s+", " ", s).strip()
    for part in re.split(r"(?<=[.!?])\s+", s):
        n += 1
        if part not in txt: bad.append(part)
print(f"scorecard: {n} sentences checked, {len(bad)} not found on the page")
for b in bad: print("  NOT FOUND:", b[:140])
if "--source" in sys.argv:
    src = pathlib.Path(sys.argv[sys.argv.index("--source") + 1]).read_text()
    missing = [l for l in md.split("\n") if l.strip() and l not in src.split("\n")]
    print(f"content/en/scorecard.md vs source: {len(missing)} line(s) not verbatim")
    for l in missing: print("  CHANGED:", l[:140])
    bad += missing
    for banned in ("How this gets paid for", "keep these three sentences", "What changed from the last draft", "Here is the honest version", "Use this as"):
        if banned in page: print("  PRIVATE TEXT ON PAGE:", banned); bad.append(banned)
sys.exit(1 if bad else 0)
