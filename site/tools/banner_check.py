"""Home-page upcoming-event banner test (4 Oct 2026). python3 tools/banner_check.py BASE_URL [SHOT_DIR]
Loads BASE/ and BASE/fr/ at 1440 and 390 px and fails (exit 1) if get_public_events has an event that has not ended
but the banner (#nextev) is missing, hidden, or not on the soonest one. Also checks the French title (title_fr) and the
event link, and that the banner sits between the header and the hero. Screenshots: SHOT_DIR/{en,fr}-{1440,390}.png.
Since migration 49 (4 Oct 2026) get_public_events also returns past events: only those not ended count as upcoming,
and the banner must never link a past one."""
import asyncio, datetime, json, sys, urllib.request
from playwright.async_api import async_playwright
BASE = sys.argv[1].rstrip("/"); SHOTS = sys.argv[2].rstrip("/") if len(sys.argv) > 2 else None
API = "https://qhyttuzmysookdgxymrl.supabase.co/rest/v1/rpc/get_public_events"; KEY = "sb_publishable_yJEI3Tmfk2bnZanIF-W1gQ_tgBwW-N7"
ev = json.loads(urllib.request.urlopen(urllib.request.Request(API, data=b"{}", method="POST", headers={"apikey": KEY, "Content-Type": "application/json"}), timeout=15).read())
now = datetime.datetime.now(datetime.timezone.utc)
up = sorted([e for e in ev if datetime.datetime.fromisoformat(e["ends_at"]) > now], key=lambda e: (e["starts_at"], e["id"]))
past_ids = {e["id"] for e in ev if datetime.datetime.fromisoformat(e["ends_at"]) <= now}
async def main():
    errs = []; out = {}
    async with async_playwright() as p:
        br = await p.chromium.launch()
        for lang in ("en", "fr"):
            for w, h, mob in ((1440, 900, False), (390, 844, True)):
                ctx = await br.new_context(viewport={"width": w, "height": h}, is_mobile=mob, has_touch=mob, device_scale_factor=2 if mob else 1, timezone_id="America/Vancouver")
                pg = await ctx.new_page(); cerr = []; pg.on("pageerror", lambda e: cerr.append(str(e)))
                await pg.goto(BASE + ("/fr/" if lang == "fr" else "/") + "?bannercheck=" + str(int(now.timestamp())), wait_until="networkidle"); await pg.wait_for_timeout(600)
                info = await pg.evaluate("""()=>{const b=document.getElementById('nextev'); if(!b) return null; const r=b.getBoundingClientRect(), hero=document.querySelector('.hero');
                  return {visible: !b.hidden && r.height>0, text: b.innerText.trim(), href: (b.querySelector('p a')||{}).getAttribute ? b.querySelector('p a').getAttribute('href') : null,
                          top: Math.round(r.top), beforeHero: hero ? !!(b.compareDocumentPosition(hero) & 4) : null, hscroll: document.documentElement.scrollWidth > innerWidth}}""")
                k = f"{lang}-{w}"; out[k] = info; out[k + "-errors"] = cerr
                if up:
                    e = up[0]; t = ((lang == "fr" and e.get("title_fr")) or e["title"]).split("|")[-1].strip()
                    if not info or not info["visible"]: errs.append(f"{k}: {len(up)} upcoming events but no visible banner")
                    else:
                        if not (info["href"] or "").endswith(f"?e={e['id']}"): errs.append(f"{k}: banner links {info['href']}, soonest event is {e['id']}")
                        if any((info["href"] or "").endswith(f"?e={i}") for i in past_ids): errs.append(f"{k}: banner links a past event ({info['href']})")
                        if t not in info["text"]: errs.append(f"{k}: banner text lacks {t!r}")
                        if not info["beforeHero"]: errs.append(f"{k}: banner is not above the hero")
                        if info["hscroll"]: errs.append(f"{k}: page scrolls sideways")
                elif info and info["visible"]: errs.append(f"{k}: no upcoming events but the banner shows")
                if cerr: errs.append(f"{k}: page errors {cerr}")
                if SHOTS: await pg.screenshot(path=f"{SHOTS}/{lang}-{w}.png")
                await ctx.close()
        await br.close()
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("BANNER CHECK FAILED:\n  " + "\n  ".join(errs) if errs else f"banner check passed ({len(ev)} public: {len(up)} upcoming, {len(past_ids)} past; next id {up[0]['id'] if up else None})")
    sys.exit(1 if errs else 0)
asyncio.run(main())
