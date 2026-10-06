#!/usr/bin/env python3
"""Campaign trail photos (trail.py): strip metadata from the originals in data/trail/ and write the web sizes.

  /workspace/.mapenv/bin/python tools/make_trail.py            # new or changed entries only
  /workspace/.mapenv/bin/python tools/make_trail.py --force    # redo every entry
  /workspace/.mapenv/bin/python tools/make_trail.py --samples  # also the staging SAMPLE entries (data/trail-samples.json)

Writes assets/img/trail/<image stem>-<width>.{webp,jpg} (4:3 crop around 'focus', widths 320/640/960/1280 up to the
photo's own width, sRGB, no EXIF/GPS/XMP) and assets/img/trail/index.json. Re-saves an original that still carries EXIF/GPS
(orientation applied, long edge max 2400 px) so no location data reaches the public repo. Needs Pillow. Commit
data/trail.json, data/trail/ and assets/img/trail/ afterwards (the CI build has no Pillow and only checks the files)."""
import argparse, json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import trail

ap = argparse.ArgumentParser(); ap.add_argument("--force", action="store_true"); ap.add_argument("--samples", action="store_true")
a = ap.parse_args()
vic = json.loads((ROOT / "site.json").read_text()).get("victoria_photos", {}).get("photos", {})
real = trail._read("trail.json"); errs = trail.validate(real, "data/trail.json")
samples = trail._read("trail-samples.json") if a.samples else []
errs += trail.validate(samples, "data/trail-samples.json")
if errs: sys.exit("\n".join(errs))
done = trail.make_images(real + samples, vic, force=a.force)
print(f"campaign trail: {len(real)} entries, {len(samples)} samples; regenerated: {', '.join(done) or 'none'}")
