#!/usr/bin/env python3
"""Render the static riding map (no tiles, no runtime scripts): OpenStreetMap data + the Elections BC boundary.

Needs matplotlib + shapely (e.g. python3 -m venv /tmp/mapenv && /tmp/mapenv/bin/pip install matplotlib shapely).
Usage:  /tmp/mapenv/bin/python tools/make_map.py
Input:  data/osm-victoria.json.gz  (Overpass result of data/osm-victoria.overpass; refresh by re-running that query)
        data/boundary.js           (Elections BC 2023 boundary, Victoria–Beacon Hill)
Output: assets/img/riding-map-{en,fr}-{desk,phone}-{2x,3x}.png
        desk  = designed for ~520 CSS px wide (hero card, How to vote), labels 13 px
        phone = designed for ~340 CSS px wide, labels 12 px
Attribution shown under the map on the site: © OpenStreetMap contributors (ODbL); boundary: Elections BC.
"""
import gzip, json, math, re, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MPath
from shapely.geometry import LineString, Polygon, box, Point, MultiPolygon
from shapely.ops import linemerge, unary_union, polygonize
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
K = math.cos(math.radians(48.42))           # simple local projection: x = lon*K, y = lat
def xy(lon, lat): return (lon * K, lat)

# ---- extent (4:3)
LAT0, LAT1 = 48.3985, 48.4435
LON_C = -123.3620
W_LON = (LAT1 - LAT0) * 4 / 3 / K
LON0, LON1 = LON_C - W_LON / 2, LON_C + W_LON / 2
EXT = box(*xy(LON0, LAT0), *xy(LON1, LAT1))
BIG = EXT.buffer(0.01)
# phone: tighter crop around the riding so labels have room at 340 CSS px
P_LAT0, P_LAT1, P_LON_C = 48.4015, 48.4395, -123.3615
P_W = (P_LAT1 - P_LAT0) * 4 / 3 / K
PHONE_EXT = box(*xy(P_LON_C - P_W / 2, P_LAT0), *xy(P_LON_C + P_W / 2, P_LAT1))
PHONE_POS = {  # label positions that differ on the phone map
    "North Park": (48.4325, -123.3612), "Fernwood": (48.4298, -123.3428), "Beacon Hill Park": (48.4108, -123.3660),
    "Fairfield": (48.4135, -123.3478), "Gonzales": (48.4168, -123.3392),
    "Esquimalt": (48.4290, -123.3930), "Downtown": (48.4282, -123.3700), "Juan de Fuca Strait": (48.4045, -123.3640),
}

osm = json.loads(gzip.open(ROOT / "data/osm-victoria.json.gz").read())["elements"]
def way_line(e): return LineString([xy(p["lon"], p["lat"]) for p in e["geometry"]])

# ---- land / water from coastline (OSM: land on the left of the way direction)
coast = [e for e in osm if e["type"] == "way" and e.get("tags", {}).get("natural") == "coastline"]
segs = []
for e in coast:
    pts = [xy(p["lon"], p["lat"]) for p in e["geometry"]]
    segs += list(zip(pts, pts[1:]))
cl = unary_union([way_line(e) for e in coast]).intersection(BIG.buffer(0.002))  # overshoot so lines cross BIG's edge and get noded
faces = [f for f in polygonize(unary_union([BIG.boundary, cl])) if BIG.buffer(1e-9).contains(f)]
def is_land(poly):
    p = poly.representative_point(); px, py = p.x, p.y; best = None
    for (ax, ay), (bx, by) in segs:
        dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy or 1e-18
        t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
        d = (px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2
        if best is None or d < best[0]: best = (d, dx * (py - ay) - dy * (px - ax))
    return best[1] > 0
land = unary_union([f for f in faces if is_land(f)])

def area_polys(pred):
    out = []
    for e in osm:
        t = e.get("tags", {})
        if not pred(t): continue
        if e["type"] == "way" and len(e.get("geometry", [])) > 3:
            g = e["geometry"]
            if (g[0]["lat"], g[0]["lon"]) == (g[-1]["lat"], g[-1]["lon"]):
                out.append(Polygon([xy(p["lon"], p["lat"]) for p in g]).buffer(0))
        elif e["type"] == "relation":
            outer = [LineString([xy(p["lon"], p["lat"]) for p in m["geometry"]]) for m in e.get("members", []) if m.get("role") == "outer" and m.get("geometry")]
            inner = [LineString([xy(p["lon"], p["lat"]) for p in m["geometry"]]) for m in e.get("members", []) if m.get("role") == "inner" and m.get("geometry")]
            o = unary_union(list(polygonize(unary_union(outer)))) if outer else None
            if o is None or o.is_empty: continue
            if inner:
                i = unary_union(list(polygonize(unary_union(inner))))
                o = o.difference(i)
            out.append(o.buffer(0))
    return unary_union(out).intersection(BIG) if out else Polygon()
water = area_polys(lambda t: t.get("natural") == "water")
parks = area_polys(lambda t: t.get("leisure") in ("park",))
greens = area_polys(lambda t: t.get("leisure") == "golf_course" or t.get("landuse") == "cemetery")

# ---- riding
b = json.loads(re.search(r"=\s*(\{.*\})", (ROOT / "data/boundary.js").read_text(), re.S).group(1))
bg = b.get("geometry", b)
riding = Polygon([xy(*c) for c in bg["coordinates"][0]]).buffer(0)

ROADS = {  # class: (css width, fill, casing)
    "motorway": (3.0, "#fdf3d0", "#d8c9a0"), "trunk": (3.0, "#fdf3d0", "#d8c9a0"), "primary": (2.8, "#fdf3d0", "#d8c9a0"),
    "secondary": (2.2, "#ffffff", "#cfc9bd"), "tertiary": (1.7, "#ffffff", "#d3cec3"),
    "residential": (1.0, "#ffffff", "#dcd7cc"), "unclassified": (1.0, "#ffffff", "#dcd7cc"), "living_street": (1.0, "#ffffff", "#dcd7cc"),
}
ROADS.update({k + "_link": v for k, v in list(ROADS.items()) if k in ("motorway", "trunk", "primary", "secondary", "tertiary")})
roads = [(e["tags"]["highway"], way_line(e)) for e in osm if e["type"] == "way" and e.get("tags", {}).get("highway") in ROADS]

LABELS = [  # (kind, en, fr, lat, lon, phone?)
    ("in", "Downtown", "Centre-ville", 48.4287, -123.3688, True),
    ("in", "Harris Green", "Harris Green", 48.4247, -123.3567, True),
    ("in", "James Bay", "James Bay", 48.4148, -123.3792, True),
    ("in", "Fairfield", "Fairfield", 48.4118, -123.3505, True),
    ("in", "Rockland", "Rockland", 48.4213, -123.3418, True),
    ("in", "North Park", "North Park", 48.4318, -123.3585, True),
    ("in", "Fernwood", "Fernwood", 48.4306, -123.3448, True),
    ("in", "Gonzales", "Gonzales", 48.4152, -123.3378, True),
    ("in", "Jubilee", "Jubilee", 48.4331, -123.3378, False),
    ("in", "Burnside", "Burnside", 48.4331, -123.3668, False),
    ("park", "Beacon Hill Park", "Parc Beacon Hill", 48.4130, -123.3650, True),
    ("out", "Oak Bay", "Oak Bay", 48.4262, -123.3225, False),
    ("out", "Esquimalt", "Esquimalt", 48.4288, -123.4000, True),
    ("out", "Victoria West", "Victoria West", 48.4360, -123.3880, False),
    ("water", "Juan de Fuca Strait", "Détroit de Juan de Fuca", 48.4028, -123.3640, True),
    ("water", "Victoria Harbour", "Port de Victoria", 48.4268, -123.3858, False),
]
TITLE = {"en": "Victoria–Beacon Hill", "fr": "Victoria–Beacon Hill"}

def fill(ax, geom, **kw):
    geoms = getattr(geom, "geoms", [geom])
    for g in geoms:
        if g.is_empty or g.geom_type != "Polygon": continue
        verts = list(g.exterior.coords); codes = [MPath.MOVETO] + [MPath.LINETO] * (len(verts) - 2) + [MPath.CLOSEPOLY]
        for r in g.interiors:
            rv = list(r.coords); verts += rv; codes += [MPath.MOVETO] + [MPath.LINETO] * (len(rv) - 2) + [MPath.CLOSEPOLY]
        ax.add_patch(PathPatch(MPath(verts, codes), linewidth=0, **kw))

def render(lang, variant, scale):
    css_w = 520 if variant == "desk" else 340
    fs = 13 if variant == "desk" else 12
    css_h = css_w * 3 / 4
    dpi = 100; px = css_w * scale / dpi  # 1 css px = scale device px
    lw = lambda css: css * scale * 72 / dpi   # linewidth in points
    fig = plt.figure(figsize=(css_w * scale / dpi, css_h * scale / dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
    ext = EXT if variant == "desk" else PHONE_EXT
    x0, y0, x1, y1 = ext.bounds; ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal")
    fig.patch.set_facecolor("#cfe2f1")
    fill(ax, land, facecolor="#f6f4ef", zorder=1)
    fill(ax, greens, facecolor="#e4eedc", zorder=2)
    fill(ax, parks, facecolor="#d6e9cc", zorder=2)
    fill(ax, water, facecolor="#cfe2f1", zorder=3)
    order = ["residential", "unclassified", "living_street", "tertiary_link", "tertiary", "secondary_link", "secondary", "primary_link", "primary", "trunk_link", "trunk", "motorway_link", "motorway"]
    thin = 0.55 if variant == "phone" else 1.0
    for z, cls in enumerate(order):
        w, f, c = ROADS[cls]
        if variant == "phone" and cls in ("residential", "unclassified", "living_street"): w = 0.7
        for k, ln in roads:
            if k != cls: continue
            xs, ys = ln.xy
            ax.plot(xs, ys, color=c, linewidth=lw(w + 0.9), solid_capstyle="round", zorder=4 + z * 0.01)
    for z, cls in enumerate(order):
        w, f, c = ROADS[cls]
        if variant == "phone" and cls in ("residential", "unclassified", "living_street"): w = 0.7
        for k, ln in roads:
            if k != cls: continue
            xs, ys = ln.xy
            ax.plot(xs, ys, color=f, linewidth=lw(w), solid_capstyle="round", zorder=5 + z * 0.01)
    # dim everything outside the riding, tint inside
    fill(ax, EXT.buffer(0.02).difference(riding), facecolor="#ffffff", alpha=0.5, zorder=6)
    fill(ax, riding, facecolor="#1a4c8b", alpha=0.13, zorder=6)   # riding shaded in the brand blue
    rx, ry = riding.exterior.xy
    ax.plot(rx, ry, color="#ffffff", linewidth=lw(6), zorder=7, solid_joinstyle="round")
    ax.plot(rx, ry, color="#1a4c8b", linewidth=lw(2.6), zorder=8, solid_joinstyle="round")
    halo = lambda w: [pe.withStroke(linewidth=lw(w), foreground="#ffffff")]
    for kind, en, fr, la, lo, onphone in LABELS:
        if variant == "phone" and not onphone: continue
        t = en if lang == "en" else fr
        if variant == "phone" and en in PHONE_POS: la, lo = PHONE_POS[en]
        x, y = xy(lo, la)
        if kind == "in":
            ax.text(x, y, t, fontsize=lw(fs), fontweight="bold", color="#12294d", ha="center", va="center", zorder=10, path_effects=halo(3.2), family="DejaVu Sans")
        elif kind == "park":
            ax.text(x, y, t, fontsize=lw(fs - 2), style="italic", color="#2f6b2a", ha="center", va="center", zorder=10, path_effects=halo(2.6), family="DejaVu Sans")
        elif kind == "out":
            ax.text(x, y, t, fontsize=lw(fs - 1), color="#5d6773", ha="center", va="center", zorder=10, path_effects=halo(2.6), family="DejaVu Sans")
        else:
            ax.text(x, y, t, fontsize=lw(fs - 1), style="italic", color="#2d5f8a", ha="center", va="center", zorder=10, family="DejaVu Sans")
    out = ROOT / "assets/img" / f"riding-map-{lang}-{variant}-{scale}x.png"
    fig.savefig(out, dpi=dpi, facecolor=fig.get_facecolor()); plt.close(fig)
    im = Image.open(out).convert("RGB").quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    im.save(out, optimize=True)
    return out, im.size

if __name__ == "__main__":
    for lang in ("en", "fr"):
        for variant in ("desk", "phone"):
            for scale in (2, 3):
                o, s = render(lang, variant, scale)
                print(o.relative_to(ROOT), s, o.stat().st_size // 1024, "KB")
