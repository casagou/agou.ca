#!/usr/bin/env python3
"""Real Victoria photos (site.json victoria_photos): crop, resize and encode for the site.

  /workspace/.mapenv/bin/python tools/make_vic_photos.py [--orig DIR]

For each photo in site.json victoria_photos.photos and each variant in its "focus" (strip 3:1, tile 4:3, thumb 1:1),
writes assets/img/vic/<id>-<variant>-<width>.{avif,webp,jpg} (sRGB, no EXIF/GPS/XMP/ICC). focus = [x, y, zoom]: the crop
centre as a fraction of the original's width/height, and the crop size as a fraction of the largest crop that fits.
Originals come from Wikimedia Commons (source_url; downloaded once into --orig, default /tmp/vic-photos-orig; they are
not kept in the repo). Needs Pillow with AVIF support (Pillow >= 11.3; /workspace/.mapenv has it).
"blur" (optional) = [[x0, y0, x1, y1], ...]: areas of the original (fractions of its width/height) blurred before cropping, so
no passer-by is recognizable at any size (the footer credit then says "cropped, people blurred")."""
import argparse, io, json, pathlib, urllib.parse, urllib.request
from PIL import Image, ImageCms, ImageDraw, ImageFilter, ImageOps, features

ROOT = pathlib.Path(__file__).resolve().parent.parent
VARIANTS = {"strip": (3, 1, (480, 800, 1200)), "tile": (4, 3, (240, 360, 480)), "thumb": (1, 1, (80, 160, 240))}
Q = {"avif": 52, "webp": 74, "jpg": 80}  # small crops (tile, thumb)
Q_STRIP = {"avif": 38, "webp": 64, "jpg": 74}  # full-width strips: lower quality keeps a 3x phone under ~45 KB per strip
UA = {"User-Agent": "agou.ca site build (photo credits on every page that shows them)"}


def original(pid, src, orig):
    f = orig / f"{pid}.jpg"
    if not f.exists():
        name = urllib.parse.unquote(src.split("/wiki/File:", 1)[1])
        u = "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(name)
        f.write_bytes(urllib.request.urlopen(urllib.request.Request(u, headers=UA)).read())
    im = ImageOps.exif_transpose(Image.open(f))
    icc = im.info.get("icc_profile")
    if icc:
        im = ImageCms.profileToProfile(im, ImageCms.ImageCmsProfile(io.BytesIO(icc)), ImageCms.createProfile("sRGB"), outputMode="RGB")
    return im.convert("RGB")


def blur(im, boxes):
    """Blur each box (fractions of the image) strongly, with a feathered edge."""
    if not boxes: return im
    W, H = im.size; r = max(8, round(max(W, H) / 120))
    soft = im.filter(ImageFilter.GaussianBlur(r)); mask = Image.new("L", im.size, 0); d = ImageDraw.Draw(mask)
    for x0, y0, x1, y1 in boxes: d.rectangle((x0 * W, y0 * H, x1 * W, y1 * H), fill=255)
    return Image.composite(soft, im, mask.filter(ImageFilter.GaussianBlur(r / 2)))


def crop(im, aw, ah, fx, fy, z):
    W, H = im.size
    cw = min(W, H * aw / ah) * z; ch = cw * ah / aw
    x = min(max(fx * W - cw / 2, 0), W - cw); y = min(max(fy * H - ch / 2, 0), H - ch)
    return im.crop((round(x), round(y), round(x + cw), round(y + ch)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--orig", default="/tmp/vic-photos-orig"); a = ap.parse_args()
    if not features.check("avif"): raise SystemExit("Pillow without AVIF support: use /workspace/.mapenv/bin/python")
    orig = pathlib.Path(a.orig); orig.mkdir(parents=True, exist_ok=True)
    out = ROOT / "assets/img/vic"; out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*"): old.unlink()
    P = json.loads((ROOT / "site.json").read_text())["victoria_photos"]["photos"]
    for pid, p in P.items():
        im = blur(original(pid, p["source_url"], orig), p.get("blur"))
        for var, (fx, fy, z) in p["focus"].items():
            aw, ah, widths = VARIANTS[var]
            c = crop(im, aw, ah, fx, fy, z)
            for w in widths:
                h = round(w * ah / aw)
                r = c.resize((w, h), Image.LANCZOS)
                base = out / f"{pid}-{var}-{w}"; q = Q_STRIP if var == "strip" else Q
                r.save(f"{base}.avif", quality=q["avif"], speed=4)
                r.save(f"{base}.webp", quality=q["webp"], method=6)
                r.save(f"{base}.jpg", quality=q["jpg"], optimize=True, progressive=True)
                if c.width < w: print(f"warning: {pid} {var} {w}px is upscaled from {c.width}px")
        print(pid, ", ".join(p["focus"]))
    kb = sum(f.stat().st_size for f in out.glob("*")) / 1024
    print(f"{len(list(out.glob('*')))} files, {kb:.0f} KB in {out.relative_to(ROOT)}")
