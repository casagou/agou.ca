# agou.ca: bilingual site (site/)

A static EN/FR site built from the Notion pages. No framework and no trackers. The only third-party calls are the Supabase RPCs made by the forms and the events list.
Content lives in Notion. This folder holds a verbatim snapshot of it (`notion-raw/`), and `build.py` turns that snapshot into plain HTML in `dist/`.

- **Staging:** https://agou-staging.pages.dev (noindex: meta tag, X-Robots-Tag header, and robots.txt Disallow)
- **Live:** https://agou.ca serves this site (published 2026-09-30 from branch `staging`, see RESYNC.md "Publish to live"). Notion is for drafting only; agou.ca is the public site.
- Re-sync from Notion, redeploy staging and publish: **see `../RESYNC.md`.**

## Pages (EN at `/…`, FR at `/fr/…`)
`/` · `/about/` · `/priorities/` · `/get-involved/` (hub: volunteer, lawn-sign, nominate, donate) · `/volunteer/` · `/lawn-sign/` · `/nominate/` · `/donate/` · `/events/` (`?e=<id>`) · `/how-to-vote/` · `/faq/` · `/media/` · `/contact/` · `/privacy/`

- Main nav: About · Priorities · Get involved · Events · How to vote. The EN/FR switch is always in the header. The primary CTA is Volunteer.
- Footer: contact, social links (Instagram, X, Facebook from Notion), Frequently asked questions · Media · Contact · Privacy, and the authorization line.
- FAQ (`/faq/`, from Notion) is also linked from How to vote, Get involved and the home page "Questions?" section.
- Notion red text (e.g. `[TO COMPLETE: …]` in the FAQ) is shown highlighted on staging so reviewers see it. `build.py --env live` refuses to build while any is left: finish or delete it in Notion, then re-sync.

## Files
| Path | What it is |
|---|---|
| `notion-raw/<lang>-<key>.txt` | Notion page text exactly as fetched (source of truth for the snapshot) |
| `tools/notion2md.py` | notion-raw → `content/<lang>/<key>.md` (strips Notion nav/contact blocks, applies `exclusions.json`, maps links) |
| `exclusions.json` | Every intentional edit to Notion text, with the reason |
| `content/<lang>/*.md` | Generated page bodies (privacy.md is hand-written; approved with the go-live on 2026-09-30) |
| `site.json` | Pages, nav, photo slots, social links, `promote_donate`, "Last updated" dates |
| `ui.json` | Interface and form wording EN/FR, How to vote facts with elections.bc.ca source links |
| `build.py` | `python3 build.py --env staging|live` → `dist/` (and runs content checks: forbidden terms, phone whitelist, authorization line) |
| `tools/diffcheck.py` | Word-for-word check of the built pages against notion-raw; only listed exclusions may differ |
| `tools/qa.py BASE OUT` | Screenshots (390×844 phone, 1440×900 desktop, EN and FR) plus console errors, horizontal overflow, tap targets <48px and broken internal links |
| `assets/media/` | Media-kit PDFs (EN/FR), checked with pdftotext by build.py |
| `assets/` | CSS, JS (`forms.js` has the same RPCs/payloads as the existing live forms; `site.js` is the menu), images |

## Forms (Supabase project qhyttuzmysookdgxymrl, the campaign app at beacon-hill-map.pages.dev)
| Form | Pages | RPC → table | Shows in app |
|---|---|---|---|
| Volunteer | /volunteer/, /fr/volunteer/ | submit_volunteer_signup → volunteer_signups | ☰ Volunteers |
| Lawn sign | /lawn-sign/, /fr/lawn-sign/ | submit_lawn_sign_request → lawn_sign_requests | ☰ Lawn signs |
| Nominate | /nominate/, /fr/nominate/ | submit_nominator_signup → nominator_signups | Nominators |
| Event RSVP | /events/?e=<id>, /fr/events/?e=<id> | submit_event_rsvp → event_rsvps | ☰ Events |

On FR forms, choice values (nominate sessions, lawn-sign placement) are stored in English, so the app shows them the same way whichever language was used. The consent text saved with each record is the text the person saw (EN or FR).
There is no contact or newsletter form in Notion, so no new table was needed.

## Photo slots (no stock images)
The design is complete without photos. The slots are set in `site.json` → `photos`:

| Slot | Where | When empty (null) |
|---|---|---|
| `hero` | Home, beside the intro text on desktop and under it on phones. Never behind text. | The riding map card (below) |
| `about-portrait` | Top of About | Nothing is shown |

To fill a slot, save a JPG (at least 1600px wide, real campaign photo) as `assets/img/photos/<slot>.jpg` and set `"hero": "hero.jpg"`. Then rebuild. Text always stays on a solid background, never over a photo.

## FAQ switch
`site.json` → `"publish_faq_live"` (currently `true`: the FAQ is live since 2026-09-30). With `false`, the live build leaves out `/faq/` and `/fr/faq/` and every link to them (footer nav, How to vote, Get involved, the home "Questions?" section and the Contact page link). The build fails if any link to them is left. Staging always shows the FAQ.
To publish it again after holding it back: finish every `[TO COMPLETE]` note in Notion, re-sync `en-faq`/`fr-faq`, set `"publish_faq_live": true`, then build live and publish. The live build refuses to run while any TO COMPLETE note remains.

## Riding map
`tools/make_map.py` renders the riding map as static PNGs from OpenStreetMap data (`data/osm-victoria.json.gz`, fetched with `data/osm-victoria.overpass`) and the Elections BC boundary (`data/boundary.js`). There are no map tiles and no scripts at runtime.
- Files: `assets/img/riding-map-{en,fr}-{desk,phone}-{2x,3x}.png`. Phones get a tighter crop with bigger labels (`<picture>` media query).
- It is shown in a light card with the caption "Am I in Victoria–Beacon Hill?", a link to the Elections BC address lookup, and the attribution. It appears in the home hero (while the `hero` photo slot is empty) and on How to vote, in EN and FR. The home page's Notion map image is not repeated lower down.
- To change labels or colours, edit `LABELS` / `PHONE_POS` in the script, then run it with matplotlib and shapely (`python3 -m venv /tmp/mapenv && /tmp/mapenv/bin/pip install matplotlib shapely && /tmp/mapenv/bin/python tools/make_map.py`) and rebuild.

## Donate switch
`site.json` → `"promote_donate": false` (the default). Donate is a quiet item in Get involved and points people to the financial agent (Bert).
Set it to `true` and rebuild: a Donate button appears in the header, and the Donate item on Get involved becomes a full button. Nothing else needs to change.

## Design rules this build follows
Mobile-first. Body text 18px with line-height 1.55 and lines of about 62 characters at most. Every button and link target is at least 48px. The header is not sticky, and there are no popups, modals, cookie banners (no trackers), autoplay or bottom bars. `prefers-reduced-motion` turns off transitions and smooth scrolling. Colours meet WCAG AA. Every page shows a "Last updated" date (`site.json` → `updated`).

## Content exclusions (from `exclusions.json`)
- "Most people call me Joa." (EN/FR): the site says Joachim, never Joa.
- The Thales Canada job line (EN/FR): current employer is not shown.
- "Joa Aero Engineering (…)," (EN/FR): the business name contains "Joa". Joachim can approve or rename it.
- Media: "Joachim Agou is the Conservative Party of BC candidate…" was removed, because he is *seeking* the nomination.
- Media-kit PDFs: they are in `assets/media/` (not Notion), and `<placeholder>MEDIAKIT</placeholder>` renders as the download links (see RESYNC.md "Media kit PDFs"). Staging shows them. Live has shown them since 2026-09-30 (`publish_media_kit_live: true`). Both PDFs still call him the candidate (EN medium bio: "is the Conservative Party of BC candidate"; FR: "est le candidat du Parti conservateur"). Joachim approved them as-is on 30 Sep 2026, so their exact hashes are allow-listed in `site.json` → `media_kit_approved`.
- FR "(page en anglais)" notes were removed (home and FAQ), because those pages now exist in French.
