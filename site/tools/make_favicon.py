"""Favicon "JOA" (Joachim's explicit choice, 2026-09-30): navy rounded square, white bold condensed
letters, yellow underline. Writes every icon asset into assets/img/ and the web manifests.
Letters are drawn as outlines (no font needed in the browser). Font: Barlow Condensed Bold, ExtraBold for 16-48 px (OFL).
Run: /workspace/.mapenv/bin/python tools/make_favicon.py   (needs matplotlib + Pillow)
"""
import pathlib
import numpy as np
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from PIL import Image, ImageDraw
from matplotlib.path import Path

HERE = pathlib.Path(__file__).resolve().parent.parent
OUT = HERE / "assets/img"
FONTDIR = "/usr/share/fonts/truetype/sand-box/google/Barlow Condensed/"
FONTS = {"large": FONTDIR + "BarlowCondensed-Bold.ttf", "small": FONTDIR + "BarlowCondensed-ExtraBold.ttf"}
NAVY, YELLOW, WHITE = "#123a6d", "#ffd23f", "#ffffff"
TEXT = "JOA"
# layouts in a 64-unit box: (cap top, cap bottom, max text width, letter gap, underline y, h, x0, x1, radius)
LAYOUTS = {
    "large": dict(font="large", top=13, bottom=43, maxw=46, gap=1.5, uy=49, uh=4, ux0=12, ux1=52, rx=12),
    # 16/32 px: bigger letters and a pixel-aligned underline (4 units = 1 px at 16 px)
    "small": dict(font="small", top=8, bottom=44, maxw=58, gap=1.0, uy=52, uh=4, ux0=6, ux1=58, rx=10),
}

def glyphs(L):
    fp = FontProperties(fname=FONTS[L["font"]])
    parts, x = [], 0.0
    for ch in TEXT:
        tp = TextPath((0, 0), ch, size=100, prop=fp)
        ext = tp.get_extents()
        parts.append((tp, x - ext.x0)); x += ext.width + L["gap"] * 100 / 30
    total = x - L["gap"] * 100 / 30
    capH = max(TextPath((0, 0), c, size=100, prop=fp).get_extents().y1 for c in TEXT)
    s = min((L["bottom"] - L["top"]) / capH, L["maxw"] / total)
    x0 = 32 - total * s / 2
    polys = []
    for tp, dx in parts:
        for poly in tp.to_polygons(closed_only=True):
            polys.append([(x0 + (px + dx) * s, L["bottom"] - py * s) for px, py in poly])
    return polys

def svg(L):
    d = "".join("M" + "L".join(f"{x:.2f} {y:.2f}" for x, y in p) + "Z" for p in glyphs(L))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            f'<title>JOA</title><rect width="64" height="64" rx="{L["rx"]}" fill="{NAVY}"/>'
            f'<path fill="{WHITE}" fill-rule="evenodd" d="{d}"/>'
            f'<rect x="{L["ux0"]}" y="{L["uy"]}" width="{L["ux1"]-L["ux0"]}" height="{L["uh"]}" rx="{L["uh"]/2}" fill="{YELLOW}"/></svg>')

def png(L, px, square=False):
    ss = 16; S = px * ss; k = S / 64
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    if square: dr.rectangle([0, 0, S, S], fill=NAVY)       # apple-touch / maskable: iOS rounds it
    else: dr.rounded_rectangle([0, 0, S - 1, S - 1], radius=L["rx"] * k, fill=NAVY)
    mask = Image.new("L", (S, S), 0); md = ImageDraw.Draw(mask)
    for p in glyphs(L):   # even-odd fill (counters of O and A)
        m2 = Image.new("L", (S, S), 0); ImageDraw.Draw(m2).polygon([(x * k, y * k) for x, y in p], fill=255)
        mask = Image.fromarray(np.bitwise_xor(np.array(mask), np.array(m2)))
    im.paste(WHITE, (0, 0), mask)
    box = [L["ux0"] * k, L["uy"] * k, L["ux1"] * k - 1, (L["uy"] + L["uh"]) * k - 1]
    if px <= 48: dr.rectangle(box, fill=YELLOW)            # square ends stay crisp on the pixel grid
    else: dr.rounded_rectangle(box, radius=L["uh"] / 2 * k, fill=YELLOW)
    return im.resize((px, px), Image.BOX if px <= 48 else Image.LANCZOS)

def main():
    big, small = LAYOUTS["large"], LAYOUTS["small"]
    (OUT / "favicon.svg").write_text(svg(small) + "\n")   # tabs show the SVG at 16-32 px
    files = {"favicon-16.png": png(small, 16), "favicon-32.png": png(small, 32), "favicon-48.png": png(small, 48),
             "apple-touch-icon.png": png(big, 180, square=True), "icon-192.png": png(big, 192),
             "icon-512.png": png(big, 512), "icon-maskable-512.png": png(big, 512, square=True)}
    for n, im in files.items():
        im.save(OUT / n, optimize=True)
    files["favicon-48.png"].save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)],
                                 append_images=[files["favicon-16.png"], files["favicon-32.png"]])
    print("wrote", ", ".join(["favicon.svg", "favicon.ico", *files]))

if __name__ == "__main__":
    main()
