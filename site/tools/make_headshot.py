#!/usr/bin/env python3
"""Headshot web files from Joachim's original photo (square, sRGB): assets/img/joachim-agou-headshot-{400,800,1200}.{jpg,webp}.
Pixels only: no EXIF/GPS, XMP, IPTC or ICC data is written (the original is sRGB, so dropping its profile changes nothing).
The original (camera file, 2779x2779) is not kept in the repo. Usage: python3 tools/make_headshot.py <original.jpg>"""
import pathlib, sys
from PIL import Image, ImageOps
ROOT = pathlib.Path(__file__).resolve().parent.parent
src = Image.open(sys.argv[1]); src = ImageOps.exif_transpose(src).convert("RGB")
side = min(src.size); l = (src.width - side) // 2; t = (src.height - side) // 2
src = src.crop((l, t, l + side, t + side))  # already square; keep the full frame (face is centred)
clean = Image.new("RGB", src.size); clean.putdata(list(src.getdata()))  # fresh image: carries no metadata at all
for w in (400, 800, 1200):
    im = clean.resize((w, w), Image.LANCZOS)
    base = ROOT / f"assets/img/joachim-agou-headshot-{w}"
    im.save(f"{base}.jpg", "JPEG", quality=82, optimize=True, progressive=True, subsampling="4:2:0")
    im.save(f"{base}.webp", "WEBP", quality=80, method=6)
    print(base.name, (base.with_suffix(".jpg")).stat().st_size // 1024, "KB jpg,", (base.with_suffix(".webp")).stat().st_size // 1024, "KB webp")
