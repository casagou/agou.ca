#!/usr/bin/env python3
"""Social preview images (og:image), 1200x630, one per language. Current: assets/img/og-joachim-agou-photo-{en,fr}.jpg (make_photo: headshot + text).
Older text-only card: og-joachim-agou-{en,fr}.png (make).
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


def make_photo(lang):
    """og-joachim-agou-photo-{lang}.jpg: headshot on the right (face whole, natural framing), the same text on navy on the left.
    Uses assets/img/joachim-agou-headshot-1200.jpg (tools/make_headshot.py, no metadata)."""
    im = Image.new("RGB", (W, H), NAVY); d = ImageDraw.Draw(im)
    PW = 560  # photo panel width (right side, full height)
    ph = Image.open(ROOT / "assets/img/joachim-agou-headshot-1200.jpg").convert("RGB").resize((H, H), Image.LANCZOS)
    cx_face = H // 2  # face is centred in the square original
    left = max(0, min(H - PW, cx_face - PW // 2))
    im.paste(ph.crop((left, 0, left + PW, H)), (W - PW, 0))
    TX = 64; COLW = W - PW - 2 * TX + 8
    name_f = font(76, 800); riding_f = font(36, 600); slog_f = font(33, 500); url_f = font(28, 700)
    slog = wrap(d, SLOGAN[lang], slog_f, COLW)
    blocks = [("name", 76), ("gap", 22), ("bar", 8), ("gap", 26), ("riding", 42), ("gap", 30)] + [("s", 44)] * len(slog) + [("gap", 32), ("url", 32)]
    y = (H - sum(h for _, h in blocks)) // 2; si = 0
    for kind, h in blocks:
        if kind == "name": d.text((TX, y), "Joachim Agou", font=name_f, fill=WHITE)
        elif kind == "bar": d.rectangle([TX, y, TX + 140, y + h - 1], fill=YELLOW)
        elif kind == "riding": d.text((TX, y), "Victoria–Beacon Hill", font=riding_f, fill=PALE)
        elif kind == "s": d.text((TX, y), slog[si], font=slog_f, fill=WHITE); si += 1
        elif kind == "url": d.text((TX, y), "agou.ca", font=url_f, fill=YELLOW)
        y += h
    assert d.textlength("Joachim Agou", font=name_f) <= W - PW - TX - 20
    out = ROOT / f"assets/img/og-joachim-agou-photo-{lang}.jpg"
    im.save(out, "JPEG", quality=86, optimize=True, progressive=True)
    print(out.relative_to(ROOT), out.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    for l in ("en", "fr"): make_photo(l)  # current og:image (seo.json); make(l) draws the older text-only card
