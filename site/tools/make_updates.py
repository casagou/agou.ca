#!/usr/bin/env python3
"""Updates photos (updates.py): strip metadata from the originals in data/updates/ and write the web sizes.

  /workspace/.mapenv/bin/python tools/make_updates.py            # new or changed photos only
  /workspace/.mapenv/bin/python tools/make_updates.py --force    # redo every photo
  /workspace/.mapenv/bin/python tools/make_updates.py --samples  # also the staging SAMPLE photos (data/updates-samples.json)

Checks data/updates.json first (required fields, limits, link domains, photo files). Writes assets/img/updates/<stem>-<width>.
{webp,jpg} (4:3 crop around 'focus', widths 320/640/960/1280 up to the photo's own width, sRGB, no EXIF/GPS/XMP) and
assets/img/updates/index.json. Re-saves an original that still carries EXIF/GPS (orientation applied, long edge max 2400 px)
so no location data reaches the public repo. Needs Pillow. Commit data/updates.json, data/updates/ and assets/img/updates/
afterwards (the CI build has no Pillow and only checks the files)."""
import argparse, json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import updates

ap = argparse.ArgumentParser(); ap.add_argument("--force", action="store_true"); ap.add_argument("--samples", action="store_true")
a = ap.parse_args()
vic = json.loads((ROOT / "site.json").read_text()).get("victoria_photos", {}).get("photos", {})
real = updates._read("updates.json"); errs = updates.validate(real, "data/updates.json")
samples = updates._read("updates-samples.json") if a.samples else []
errs += updates.validate(samples, "data/updates-samples.json")
if errs: sys.exit("\n".join(errs))
done = updates.make_images(updates.all_images(real + samples), vic, force=a.force)
print(f"updates: {len(real)} entries, {len(samples)} samples; regenerated: {', '.join(done) or 'none'}")
