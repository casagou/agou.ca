#!/usr/bin/env python3
"""Make assets/img/riding-outline.svg from data/boundary.js (window.RIDING_BOUNDARY, Elections BC 2023 boundary).
Outline only: no addresses, no voter or campaign data."""
import json, math, re, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
s = (ROOT / "data/boundary.js").read_text()
f = json.loads(re.search(r"RIDING_BOUNDARY=(\{.*\})", s, re.S).group(1))
g = f["geometry"]
polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
rings = [p[0] for p in polys]
# The legal boundary runs far out into the Strait; for a readable graphic, clip the water south of CLIP_LAT.
CLIP_LAT = 48.402
def clip(ring):
    out = []
    n = len(ring)
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        ain, bin_ = a[1] >= CLIP_LAT, b[1] >= CLIP_LAT
        if ain: out.append(a)
        if ain != bin_:
            t = (CLIP_LAT - a[1]) / (b[1] - a[1]); out.append([a[0] + t * (b[0] - a[0]), CLIP_LAT])
    return out
rings = [c for c in (clip(r) for r in rings) if len(c) > 2]
lat0 = sum(c[1] for r in rings for c in r) / sum(len(r) for r in rings)
k = math.cos(math.radians(lat0))
pts = [(c[0] * k, -c[1]) for r in rings for c in r]
minx, maxx = min(p[0] for p in pts), max(p[0] for p in pts)
miny, maxy = min(p[1] for p in pts), max(p[1] for p in pts)
W = 400; sc = W / (maxx - minx); H = (maxy - miny) * sc
d = ""
for r in rings:
    d += "M" + " L".join(f"{(c[0]*k-minx)*sc:.1f},{(-c[1]-miny)*sc:.1f}" for c in r) + " Z "
svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-6 -6 {W+12:.0f} {H+12:.0f}" role="img" aria-labelledby="t"><title id="t">Victoria–Beacon Hill riding outline (boundary: Elections BC, 2023; water area trimmed)</title><path d="{d.strip()}" fill="currentColor" fill-opacity=".14" stroke="currentColor" stroke-width="3" stroke-linejoin="round"/></svg>\n'
(ROOT / "assets/img/riding-outline.svg").write_text(svg)
print("wrote riding-outline.svg", round(W), round(H), len(svg), "bytes")
