#!/usr/bin/env python3
"""Static street maps for agou.ca event pages (no tiles, no trackers, no runtime map scripts).

Draws OpenStreetMap data (streets with names, buildings, parks) around each event's exact spot,
with a pin, in the same palette as the riding map (tools/make_map.py).
Needs matplotlib + shapely + pillow (python3 -m venv /tmp/mapenv && /tmp/mapenv/bin/pip install matplotlib shapely pillow).

Usage:  /tmp/mapenv/bin/python tools/make_event_maps.py          # read events + lat/lng from rpc get_public_events
        /tmp/mapenv/bin/python tools/make_event_maps.py --ids 5,9  # only these
Input:  rpc get_public_events (public key, same as the site); data/osm-events.json.gz
        (Overpass result of data/osm-events.overpass; widen the bbox there for events outside it and re-run the query).
Output: assets/img/events/event-<id>-{phone,desk}-{2x,3x}.png and assets/img/events/index.json ({id: {"lat","lng","v"}}).
        The page shows a map only for events listed in index.json whose lat/lng still match the database,
        so a moved event never shows an old map. Re-run this script after adding an event or moving its pin.
Credit shown under every map: © OpenStreetMap contributors (ODbL).
"""
import gzip, json, math, re, sys, pathlib, hashlib, urllib.request
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MPath
from shapely.geometry import LineString, Polygon, box, Point
from shapely.ops import linemerge, unary_union
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets/img/events"
K = math.cos(math.radians(48.42))
M = 111320.0                                   # metres per degree of latitude
def xy(lon, lat): return (lon * K * M, lat * M)  # local metres

VARIANTS = {  # css size, metres across, label px, scales
    "phone": dict(w=358, h=224, metres=380, fs=12, scales=(2, 3)),
    "desk": dict(w=640, h=320, metres=640, fs=13, scales=(2,)),
}
ROADS = {  # class: (css width, fill, casing)
    "primary": (7.0, "#fdf3d0", "#d8c9a0"), "secondary": (6.5, "#ffffff", "#cfc9bd"), "tertiary": (6.0, "#ffffff", "#cfc9bd"),
    "residential": (5.0, "#ffffff", "#d3cec3"), "unclassified": (5.0, "#ffffff", "#d3cec3"), "living_street": (5.0, "#ffffff", "#d3cec3"),
    "service": (2.6, "#ffffff", "#dcd7cc"), "pedestrian": (4.0, "#f1efe9", "#d3cec3"),
}
for k in ("primary", "secondary", "tertiary"): ROADS[k + "_link"] = ROADS[k]
PATHS = ("footway", "path", "steps", "cycleway")
NAVY, BLUE, MUTED = "#123a6d", "#1a4c8b", "#4a5561"
NO_LABEL = re.compile(r"(?i)hilda")   # Joachim's own street: drawn, never labelled (same rule as build.py's text scan)

def load_osm():
    return json.loads(gzip.open(ROOT / "data/osm-events.json.gz").read())["elements"]

def poly_of(e):
    g = e.get("geometry") or []
    if len(g) < 4 or (g[0]["lat"], g[0]["lon"]) != (g[-1]["lat"], g[-1]["lon"]): return None
    return Polygon([xy(p["lon"], p["lat"]) for p in g]).buffer(0)

def fetch_events():
    js = (ROOT / "assets/js/forms.js").read_text()
    key = re.search(r'SUPABASE_KEY\s*=\s*"([^"]+)"', js).group(1)
    url = re.search(r'SUPABASE_URL\s*=\s*"([^"]+)"', js).group(1)
    req = urllib.request.Request(url.rstrip("/") + "/rest/v1/rpc/get_public_events", data=b"{}", method="POST",
                                 headers={"apikey": key, "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())

def venue(e):
    """Short pin label from location_name: 'Fernwood Square, on the public sidewalk outside Little June' -> 'Little June'."""
    s = e.get("location_name") or ""
    m = re.search(r"\b(?:outside|beside|at)\s+(?:the\s+(?=[A-Z][a-z]+\s+[A-Z]))?(.+)$", s)
    v = (m.group(1) if m else s.split(",")[0]).strip()
    v = re.sub(r"\s*\(.*?\)\s*$", "", v)
    v = re.sub(r"^the\s+(?=[a-z])", "", v)                # 'at the foot of Cook St' -> 'Foot of Cook St'
    return v[:1].upper() + v[1:]

def fill(ax, geom, **kw):
    for g in getattr(geom, "geoms", [geom]):
        if g.is_empty or g.geom_type != "Polygon": continue
        verts = list(g.exterior.coords); codes = [MPath.MOVETO] + [MPath.LINETO] * (len(verts) - 2) + [MPath.CLOSEPOLY]
        for r in g.interiors:
            rv = list(r.coords); verts += rv; codes += [MPath.MOVETO] + [MPath.LINETO] * (len(rv) - 2) + [MPath.CLOSEPOLY]
        ax.add_patch(PathPatch(MPath(verts, codes), **kw))

def lines_of(g):
    return [l for l in getattr(g, "geoms", [g]) if l.geom_type == "LineString" and not l.is_empty]

def render(osm, ev, variant, scale):
    V = VARIANTS[variant]; w, h, fs = V["w"], V["h"], V["fs"]
    cx, cy = xy(ev["lng"], ev["lat"])
    mpp = V["metres"] / w                                  # metres per css px
    half_w, half_h = w * mpp / 2, h * mpp / 2
    cy_view = cy + 0.10 * h * mpp                          # pin tip a little below the middle, so the pin head is centred
    ext = box(cx - half_w, cy_view - half_h, cx + half_w, cy_view + half_h)
    big = ext.buffer(60)
    dpi = 100
    lw = lambda css: css * scale * 72 / dpi                # css px -> points
    fig = plt.figure(figsize=(w * scale / dpi, h * scale / dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
    x0, y0, x1, y1 = ext.bounds; ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal")
    fig.patch.set_facecolor("#f6f4ef")
    near = [e for e in osm if e.get("geometry") and big.intersects(box(*xy(e["bounds"]["minlon"], e["bounds"]["minlat"]), *xy(e["bounds"]["maxlon"], e["bounds"]["maxlat"])))] if osm and "bounds" in osm[0] else osm
    for e in near:
        t = e.get("tags", {})
        if e["type"] != "way": continue
        if t.get("leisure") in ("park", "garden", "playground", "pitch") or t.get("landuse") in ("grass", "recreation_ground", "cemetery"):
            p = poly_of(e)
            if p is not None and p.intersects(big): fill(ax, p.intersection(big), facecolor="#d6e9cc", linewidth=0, zorder=1)
        elif t.get("amenity") in ("parking", "marketplace"):
            p = poly_of(e)
            if p is not None and p.intersects(big): fill(ax, p.intersection(big), facecolor="#eceae4", linewidth=0, zorder=1)
    for e in near:
        if e["type"] == "way" and "building" in e.get("tags", {}):
            p = poly_of(e)
            if p is not None and p.intersects(big):
                fill(ax, p.intersection(big), facecolor="#e7e2d8", edgecolor="#d6cfc1", linewidth=lw(0.6), zorder=2)
    roads, named = [], {}
    for e in near:
        t = e.get("tags", {}); hw = t.get("highway")
        if e["type"] != "way" or not hw: continue
        ln = LineString([xy(p["lon"], p["lat"]) for p in e["geometry"]])
        if not ln.intersects(big): continue
        if hw in PATHS:
            if t.get("footway") in ("sidewalk", "crossing"): continue   # sidewalks drawn as part of the street
            xs, ys = ln.xy; ax.plot(xs, ys, color="#b9b2a4", linewidth=lw(1.1), linestyle=(0, (2, 1.6)), zorder=3)
            continue
        if hw not in ROADS: continue
        roads.append((hw, ln))
        if t.get("name") and hw != "service" and not NO_LABEL.search(t["name"]): named.setdefault(t["name"], []).append(ln)
    order = ["service", "pedestrian", "living_street", "unclassified", "residential", "tertiary_link", "tertiary", "secondary_link", "secondary", "primary_link", "primary"]
    for z, cls in enumerate(order):
        wd, f, c = ROADS[cls]
        for k, ln in roads:
            if k == cls: xs, ys = ln.xy; ax.plot(xs, ys, color=c, linewidth=lw(wd + 1.6), solid_capstyle="round", zorder=4 + z * 0.01)
    for z, cls in enumerate(order):
        wd, f, c = ROADS[cls]
        for k, ln in roads:
            if k == cls: xs, ys = ln.xy; ax.plot(xs, ys, color=f, linewidth=lw(wd), solid_capstyle="round", zorder=5 + z * 0.01)
    # ---- pin (drawn in css px around the spot) and its label
    px = lambda css: css * mpp                               # css px -> metres
    R = 11
    head = Point(cx, cy + px(R + 9)).buffer(px(R), resolution=24)
    tip = Polygon([(cx, cy), (cx - px(R * 0.78), cy + px(R + 9) - px(R * 0.45)), (cx + px(R * 0.78), cy + px(R + 9) - px(R * 0.45))])
    pin = unary_union([head, tip])
    fill(ax, pin, facecolor=BLUE, edgecolor="#ffffff", linewidth=lw(2.2), zorder=20)
    fill(ax, Point(cx, cy + px(R + 9)).buffer(px(4.2)), facecolor="#ffffff", linewidth=0, zorder=21)
    halo = lambda wd: [pe.withStroke(linewidth=lw(wd), foreground="#ffffff")]
    label = venue(ev)
    right = True
    lx = cx + px(R + 7) if right else cx - px(R + 7)
    ax.text(lx, cy + px(R + 9), label, fontsize=lw(fs + 1), fontweight="bold", color=NAVY, ha="left" if right else "right", va="center",
            zorder=22, path_effects=halo(3.4), family="DejaVu Sans")
    taken = [box(cx - px(R + 4), cy - px(3), lx + px(len(label) * (fs + 1) * 0.62), cy + px(2 * R + 14))]
    # ---- street names: one label per street, on its longest visible piece, skipping overlaps
    fig.canvas.draw()
    labels = []
    for name, ls in named.items():
        g = unary_union(ls).intersection(ext.buffer(-px(6)))
        ls_ = [l for part in getattr(g, "geoms", [g]) for l in lines_of(part)]
        parts = lines_of(linemerge(ls_)) if len(ls_) > 1 else ls_
        if not parts: continue
        best = max(parts, key=lambda l: l.length)
        labels.append((best.length, name, best))
    labels.sort(key=lambda t: -t[0])
    for L, name, ln in labels:
        text = re.sub(r"\bStreet$", "St", re.sub(r"\bAvenue$", "Ave", re.sub(r"\bRoad$", "Rd", name)))
        for sz in (fs, fs - 1):
          tw = len(text) * sz * 0.58 + 6
          placed = False
          if L < px(tw): continue
          for frac in (0.5, 0.3, 0.7, 0.2, 0.8, 0.4, 0.6):
              p = ln.interpolate(frac, normalized=True)
              a = ln.interpolate(max(0, frac * L - px(12))); b = ln.interpolate(min(L, frac * L + px(12)))
              ang = math.degrees(math.atan2(b.y - a.y, b.x - a.x))
              if ang > 90: ang -= 180
              if ang < -90: ang += 180
              r = math.radians(ang); dx, dy = math.cos(r) * px(tw) / 2, math.sin(r) * px(tw) / 2
              hw_ = px(sz * 0.75)
              bb = LineString([(p.x - dx, p.y - dy), (p.x + dx, p.y + dy)]).buffer(hw_, cap_style=2)
              if not ext.contains(bb) or any(bb.intersects(t) for t in taken): continue
              taken.append(bb)
              ax.text(p.x, p.y, text, fontsize=lw(sz), color=MUTED, ha="center", va="center", rotation=ang, rotation_mode="anchor",
                      zorder=15, path_effects=halo(3), family="DejaVu Sans")
              placed = True; break
          if placed: break
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"event-{ev['id']}-{variant}-{scale}x.png"
    fig.savefig(out, dpi=dpi, facecolor=fig.get_facecolor()); plt.close(fig)
    im = Image.open(out).convert("RGB").quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    im.save(out, optimize=True)
    return out

if __name__ == "__main__":
    ids = None
    if "--ids" in sys.argv: ids = {int(x) for x in sys.argv[sys.argv.index("--ids") + 1].split(",")}
    events = [e for e in fetch_events() if e.get("lat") is not None and (ids is None or e["id"] in ids)]
    osm = load_osm()
    idx_path = OUT / "index.json"
    idx = json.loads(idx_path.read_text()) if idx_path.exists() else {}
    for ev in events:
        h = hashlib.sha1()
        for v in VARIANTS:
            for s in VARIANTS[v]["scales"]:
                o = render(osm, ev, v, s); h.update(o.read_bytes())
                print(o.relative_to(ROOT), Image.open(o).size, o.stat().st_size // 1024, "KB")
        idx[str(ev["id"])] = {"lat": ev["lat"], "lng": ev["lng"], "v": h.hexdigest()[:8]}
    idx_path.write_text(json.dumps(dict(sorted(idx.items(), key=lambda t: int(t[0]))), indent=1) + "\n")
    print("wrote", idx_path.relative_to(ROOT))
