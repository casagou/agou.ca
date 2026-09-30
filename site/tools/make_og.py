#!/usr/bin/env python3
"""Social preview images (og:image), 1200x630 PNG, one per language: assets/img/og-joachim-agou-{en,fr}.png.
Design system: navy #123a6d background, white text, yellow #ffd23f underline accent, no gradients.
All text sits inside the central 630x630 square (x 285-915), so WhatsApp/iMessage square crops still read cleanly.
Needs Pillow and the Roboto variable font. Usage: python3 tools/make_og.py"""
import pathlib
from PIL import Image, ImageDraw, ImageFont
ROOT = pathlib.Path(__file__).resolve().parent.parent
FONT = "/usr/share/fonts/truetype/sand-box/google/Roboto/Roboto-VariableFont_wdth,wght.ttf"
NAVY, WHITE, YELLOW, PALE = (18, 58, 109), (255, 255, 255), (255, 210, 63), (214, 226, 240)
W, H = 1200, 630; SQ = (W - H) // 2; PAD = 34; COL = H - 2 * PAD  # text column: 562 px wide inside the square
SLOGAN = {"en": "Safer streets, honest budgets, a downtown that works.",
          "fr": "Des rues plus sûres, des budgets honnêtes et un centre-ville qui fonctionne."}


def font(size, weight):
    f = ImageFont.truetype(FONT, size); f.set_variation_by_axes([weight, 100]); return f


def wrap(d, text, f, width):
    lines, cur = [], ""
    for w in text.split(" "):
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= width: cur = t
        else: lines.append(cur); cur = w
    return lines + [cur]


def make(lang):
    im = Image.new("RGB", (W, H), NAVY); d = ImageDraw.Draw(im)
    cx = W // 2
    name_f = font(80, 800); riding_f = font(38, 600); slog_f = font(35, 500); url_f = font(28, 700)
    slog = wrap(d, SLOGAN[lang], slog_f, COL)
    # vertical layout, centred as a block
    blocks = [("name", 80), ("gap", 22), ("bar", 8), ("gap", 26), ("riding", 44), ("gap", 34)] + [("s", 46)] * len(slog) + [("gap", 34), ("url", 32)]
    y = (H - sum(h for _, h in blocks)) // 2; si = 0
    for kind, h in blocks:
        if kind == "name": d.text((cx, y), "Joachim Agou", font=name_f, fill=WHITE, anchor="mt")
        elif kind == "bar": d.rectangle([cx - 70, y, cx + 70, y + h - 1], fill=YELLOW)
        elif kind == "riding": d.text((cx, y), "Victoria–Beacon Hill", font=riding_f, fill=PALE, anchor="mt")
        elif kind == "s": d.text((cx, y), slog[si], font=slog_f, fill=WHITE, anchor="mt"); si += 1
        elif kind == "url": d.text((cx, y), "agou.ca", font=url_f, fill=YELLOW, anchor="mt")
        y += h
    # every glyph must stay inside the square
    diff = [x for x in range(W) if any(im.getpixel((x, yy)) != NAVY for yy in range(0, H, 3))]
    assert min(diff) >= SQ + PAD - 4 and max(diff) <= SQ + H - PAD + 4, (lang, min(diff), max(diff))
    out = ROOT / f"assets/img/og-joachim-agou-{lang}.png"
    im = im.quantize(colors=256, method=Image.Quantize.MAXCOVERAGE, dither=Image.Dither.NONE)  # exact navy/yellow/white kept; ~20 KB
    im.save(out, optimize=True)
    print(out.relative_to(ROOT), out.stat().st_size // 1024, "KB; text x", min(diff), "-", max(diff), "(square", SQ, "-", SQ + H, ")")


if __name__ == "__main__":
    for l in ("en", "fr"): make(l)
