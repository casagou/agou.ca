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

**Headshot (filled 30 Sep 2026).** `hero`, `about-portrait` and `media` are set to `"joachim-agou-headshot"`: Joachim's square headshot (white shirt, foliage), made by `tools/make_headshot.py <original.jpg>` as `assets/img/joachim-agou-headshot-{400,800,1200}.{webp,jpg}` with no EXIF/GPS/XMP/ICC data (the camera original is not in the repo). `build.py` `headshot()` renders a `<picture>` (WebP first, JPEG fallback) with width/height 1200 and alt "Joachim Agou" (EN and FR). Hero: beside the intro on desktop (400px), under the nominator callout on phones (260px); the riding map then moves down to the home Notion map spot. About: top of the page (200px on phones, floated right at 280px from 800px). Media (EN): first image under Photos, with the caption "Joachim Agou", linked to the 1200px JPEG for download (`media` slot; null removes it). The JSON-LD Person image is `joachim-agou-headshot-1200.jpg`.

## Nominations closed (30 Sep 2026)
`site.json` → `"nominations_closed": true` (Joachim: 96 signatures in the riding, 75 needed). The build leaves out the home nominator callout (the hero button is now Volunteer), the home "Become a nominator" section and the "75 nominators" hero source. The riding map, which sat in that section, comes back as the "Am I in Victoria–Beacon Hill?" map section after Priorities. `/nominate/` and `/fr/nominate/` still work but only show a thank-you note (`ui.json` → `nominations_closed`). They are noindex, left out of the menus, footer and sitemap, and have no form. The Supabase rpc `submit_nominator_signup` is untouched. The FAQ and About asks are removed by `exclusions.json` rules, so a Notion re-sync can't bring them back. The build fails if any other page links to `/nominate/` or still asks people to sign. `tools/diffcheck.py` lists the removed home lines as intentional.

## FAQ switch
`site.json` → `"publish_faq_live"` (currently `true`: the FAQ is live since 2026-09-30). With `false`, the live build leaves out `/faq/` and `/fr/faq/` and every link to them (footer nav, How to vote, Get involved, the home "Questions?" section and the Contact page link). The build fails if any link to them is left. Staging always shows the FAQ.
To publish it again after holding it back: finish every `[TO COMPLETE]` note in Notion, re-sync `en-faq`/`fr-faq`, set `"publish_faq_live": true`, then build live and publish. The live build refuses to run while any TO COMPLETE note remains.

## Favicon (JOA)
Joachim chose "JOA" on 2026-09-30 (the "never Joa" text rule does not apply to the favicon). `tools/make_favicon.py` draws it (navy rounded square, white Barlow Condensed letters as outlines, yellow underline) and writes `assets/img/favicon.svg`, `favicon.ico` (16/32/48), `favicon-16/32/48.png`, `apple-touch-icon.png` (180), `icon-192/512.png` and `icon-maskable-512.png`. The 16–48 px sizes and the SVG use bigger ExtraBold letters and a pixel-aligned underline so the three letters stay legible in a tab. `build.py` copies `/favicon.ico` to the root and writes `/site.webmanifest` and `/fr/site.webmanifest`. Run `/workspace/.mapenv/bin/python tools/make_favicon.py` (matplotlib, Pillow, numpy), then rebuild. If you change the icon, bump `?v=joa` in the `<head>` so browsers pick it up.

## Riding map
`tools/make_map.py` renders the riding map as static PNGs from OpenStreetMap data (`data/osm-victoria.json.gz`, fetched with `data/osm-victoria.overpass`) and the Elections BC boundary (`data/boundary.js`). There are no map tiles and no scripts at runtime.
- Files: `assets/img/riding-map-{en,fr}-{desk,phone}-{2x,3x}.png`. Phones get a tighter crop with bigger labels (`<picture>` media query).
- It is shown in a light card with the caption "Am I in Victoria–Beacon Hill?", a link to the Elections BC address lookup, and the attribution. It appears in the home hero (while the `hero` photo slot is empty) and on How to vote, in EN and FR. The home page's Notion map image is not repeated lower down.
- To change labels or colours, edit `LABELS` / `PHONE_POS` in the script, then run it with matplotlib and shapely (`python3 -m venv /tmp/mapenv && /tmp/mapenv/bin/pip install matplotlib shapely && /tmp/mapenv/bin/python tools/make_map.py`) and rebuild.

## Donate switch
`site.json` → `"promote_donate": false` (the default). Donate is a quiet item in Get involved and points people to the financial agent (Bert).
Set it to `true` and rebuild: a Donate button appears in the header, and the Donate item on Get involved becomes a full button. Nothing else needs to change.

## Design rules this build follows
Mobile-first. Body text 18px with line-height 1.55 and lines of about 62 characters at most. Every button and link target is at least 48px. Below 1024px the header is a shallow 56px bar that stays at the top (solid white, no blur, safe-area insets respected, `scroll-padding-top` so anchors and focused fields are not covered); on desktop it is not sticky. There are no popups, modals, cookie banners (no trackers), autoplay or bottom bars. `prefers-reduced-motion` turns off transitions and smooth scrolling. Colours meet WCAG AA. Every page shows a "Last updated" date (`site.json` → `updated`).

### Header
- Phones and tablets (below 1024px): a 56px bar. On the left, "Joachim Agou" with "Victoria–Beacon Hill" under it (never wrapped, never shrunk). On the right, the FR/EN switch and a "Menu" button whose label is always visible. From 480px wide, Volunteer is also in the bar. Below 480px it is the first item of the menu, as a primary button.
- Main menu: About, Priorities (sub-item Scorecard / Bulletin), Get involved (with sub-items), Events, How to vote, FAQ. Sub-items are indented in the phone menu and appear in a small dropdown on desktop (on hover or keyboard focus) (`site.json` → `main_nav`; the short label "FAQ" comes from `nav_short`). The footer still links to the FAQ. At 1024px the desktop nav fits on one row in EN and FR.

### Section treatments
- **Open** (`.block`): the default for reading. No box. It sits on the page background, and spacing (44px, or 56px on desktop) separates sections.
- **Card** (`.card-sec`, `.hub-card`, `.ev`, `.formblock`, `.map-card`): white with a pale border and 12px radius. Used only for grouped actions: the ways to help on Home, Get involved cards, event cards, forms and the map.
- **Band** (`.band-sky`): a full-width pale-blue strip (`--sky` #edf3fa) for a major transition. It is used once, on Home, for the ways to help (Become a nominator, Volunteer, Donate as cards). Text on the band is #1b1f24 (14.8:1) or #4a5561 (6.8:1), and links are #1a4c8b (7.7:1). All pass AA.
- No new colours, shadows, gradients or animation. Page titles on text pages use the same 800px container as the reading column, so the title and body text share one left edge. The FAQ at 1100px and wider uses 1052px (reading column plus a 220px topic list).

### Actions
- **Primary** (`.btn.primary`, blue #1a4c8b, white text 8.6:1): the one main action of a section, such as the hero "Sign up to nominate (takes 1 minute)", the first Notion call-to-action line in a section, the form submit, the media-kit download, and the Nominate card on Get involved. On phones it is full width.
- **Secondary** (`.btn.sec`, outlined): the other actions, such as the second call-to-action line in a section (e.g. "Request a lawn sign") and the other Get involved cards.
- **Reading and navigation links** (`.pagelink`, `.readlink`): bold text links with one trailing → to pages on this site, or ↗ to other sites. Notion call-to-action lines that point to the FAQ, About, Priorities or Media become reading links.
- Buttons never have arrows. The leading "→" in Notion's `[**→ …**]` lines is dropped when rendering (`tools/diffcheck.py` treats it as presentational).
- Focus: a 3px navy outline (yellow on navy backgrounds).

### Events (redesign, 30 Sep 2026, staging until Joachim approves)
- Data: `get_public_events` also returns `lat`, `lng` and `neighbourhood`, added by migration 41 (casagou/Beacon-Hill `supabase/migrations/41_campaign_events_coordinates.sql`). If an organizer edits the address in the campaign app without new coordinates, the database clears `lat`/`lng`.
- Maps and links (`assets/js/forms.js`): with `lat`/`lng`, "Get directions" goes to `google.com/maps/dir/?api=1&destination=LAT,LNG`, the map image to `google.com/maps/search/?api=1&query=LAT,LNG`, and "Apple Maps" to `maps.apple.com/?ll=LAT,LNG&q=<venue>`. Without them, only the street address is searched. The free-text spot description ("on the public sidewalk outside…") is never sent to Google, because that is what produced lists of wrong places.
- Static map per event: `tools/make_event_maps.py` draws OSM data (`data/osm-events.json.gz`, from `data/osm-events.overpass`) around the pin, as PNGs in `assets/img/events/`, plus `index.json`. There are no tiles and no iframe, and nothing loads from a third party. The credit "© OpenStreetMap contributors" is shown under the map. The page shows a map only when `index.json` has the event with the same `lat`/`lng`. **After adding an event or moving a pin, re-run the script (and widen the Overpass bbox if the event is outside it).**
- Detail page: date tile, title (a `|` in the title is shown as " — "), time range, and the neighbourhood if the title doesn't already name it. Then "Where to find me" (from the description's "Where to find me:" line, or the location and address), Get directions (primary), Add to calendar (secondary), Apple Maps (text link), the map, one When/Where block, then the description. The description's own "When:", "Where to find me:" and "RSVP is optional" paragraphs are left out, and long paragraphs are split. RSVP is a quiet text button at the end.
- List: cards with date tile, title, time, neighbourhood and Directions. Upcoming events come first; events that ended in the last day come last, marked "Ended".
- `site.json` → `events_redesign_approved: false`: `build.py --env live` refuses to run until Joachim approves.

### Read more (Home and Priorities)
`collapse()` in build.py keeps the start of a long section visible (about 320 characters, at least one block) and puts the rest behind a "Read more" / "Lire la suite" button (`aria-expanded`, `aria-controls`; the label changes to "Show less" / "Afficher moins", and focus stays on the button). Without JS everything stays visible and the button stays hidden. The trailing call-to-action and page links always stay visible, so the link to the full About page remains. The text is unchanged, so diffcheck still finds every line. Home also has a row of shortcuts under the hero (Priorities, Get involved, Events, How to vote).

### Forms (front end)
- One form surface. The section is the card, and the form inside has no second box. On phones up to 640px the card runs edge to edge, so fields sit 16px from the screen edge (358px wide at 390px). Fields stay in a single column up to 640px. Fields are 52px tall with 18px text.
- Errors: a summary at the submit button ("Please fix the following:"). Each item is a link that focuses its field. Each field also gets a message under it (an "!" icon plus words), `aria-invalid="true"`, and `aria-describedby` pointing to the message. The message clears when the field is edited. The loading ("Sending…") and success states are unchanged.
- Fields, payloads and RPCs are unchanged (front end only).

### FAQ page
A "Topics" / "Thèmes" index links to each group heading. On phones it shows as chips at the top. From 1100px it becomes a sticky list to the right of the reading column. Each question row is a full-width `<summary>` at least 56px tall, with a circled +/− indicator and a visible focus outline.

### Priorities ↔ Scorecard (scorecard.py `PRIORITY`)
- The top of /priorities/ has one reading line: "I’ll report on these every quarter. See the scorecard →" (FR « Je fais le point chaque trimestre. Voir le bulletin → »). It replaces the old button.
- Each Priorities section ends with "Tracked on the scorecard:" and links to its lines. Each scorecard detail card links back to its priority ("Priority N: … →"), then "Back to the report card ↑".
- Mapping: 1 Health care → 8, 9, 10. 2 Homes → 3, 4. 3 Cost of living → 1, 2. 4 Downtown → 5, 6, 7, 12. "How I'll report to you" → 11.
- The scorecard has a jump list: The two promises, How this page works, then lines 1–12. On phones it is a row of chips that scrolls sideways. From 1100px it is a sticky side list. Report-card cards link to their detail cards.

### "More photos on Instagram"
After the photo "Joachim Agou presenting a test program" (Media, Photos), build.py adds the reading link "More photos on Instagram ↗" / "Plus de photos sur Instagram ↗". It links to `site.json` → `social.Instagram` (same tab, `rel="noopener"`, no embed and no tracking). It is not in Notion. `site.json` → `more_photos_after` lists the images it follows, so a Notion re-sync keeps it.

## Content exclusions (from `exclusions.json`)
- "Most people call me Joa." (EN/FR): the site says Joachim, never Joa.
- The Thales Canada job line (EN/FR): current employer is not shown.
- "Joa Aero Engineering" is spelled that way on Joachim's instruction (30 Sep 2026). The nickname check blocks "Joa" everywhere except that exact business name (joa.aero, lowercase, is not matched).
- Media: "Joachim Agou is the Conservative Party of BC candidate…" was removed, because he is *seeking* the nomination.
- Media-kit PDFs: they are in `assets/media/` (not Notion), and `<placeholder>MEDIAKIT</placeholder>` renders as the download links (see RESYNC.md "Media kit PDFs"). Staging shows them. Live has shown them since 2026-09-30 (`publish_media_kit_live: true`). Both PDFs still call him the candidate (EN medium bio: "is the Conservative Party of BC candidate"; FR: "est le candidat du Parti conservateur"). Joachim approved them as-is on 30 Sep 2026, so their exact hashes are allow-listed in `site.json` → `media_kit_approved`.
- FR "(page en anglais)" notes were removed (home and FAQ), because those pages now exist in French.

## Scorecard (`/scorecard/`, `/fr/scorecard/`; staging only until approved)
Not from Notion. Joachim's public scorecard text, word for word, is in `content/en/scorecard.md` (his private notes, the pay-for talking points and the draft change log are not in the repo). `content/fr/scorecard.md` is the FR translation (FR title: "Bulletin"), approved by Joachim on 2026-09-30 (`fr_reviewed: true`).
- `scorecard.json`: report-card summary per item (short title, headline figure, cadence, as-of), the source links under each "Today" row, `last_published` (null shows "—"), `fr_reviewed`, and open `factcheck` flags.
- `scorecard.py` renders the page (own stylesheet `assets/css/scorecard.css`); build.py adds the "See the scorecard" links on Priorities and in the home priorities section, and `site.json` puts it in the footer.
- `site.json` → `"publish_scorecard_live"` (`true` since 2026-09-30; both EN and FR are live). When false, the live build leaves out both pages and every link to them. Staging always shows them. Even when true, the live build refuses to run while any `factcheck` flag is left in `scorecard.json` or `fr_reviewed` is false (both render as highlighted draft notes).
- After editing: `python3 build.py --env staging && python3 tools/scorecard_check.py` (every sentence of `content/en/scorecard.md` must be on the page; add `--source <file>` to compare against Joachim's full text).

## Headshot background options (30 Sep 2026, staging only)
Joachim asked for a real Victoria background instead of the foliage behind his headshot. Three options are in `assets/img/joachim-agou-headshot-bg-{a,b,c}-*` (cutout with rembg isnet-general-use + matting; the face is untouched):
- **a**: business-card style, light-blue line drawing of the Parliament Buildings / Inner Harbour on navy, adapted from "Capitol of British Columbia" by Rennett Stowe (CC BY 2.0).
- **b**: Dallas Road / Beacon Hill Park waterfront, blurred: Adam Jones (CC BY-SA 2.0; share-alike, so the composite is CC BY-SA 2.0 too).
- **c**: Parliament Buildings / Inner Harbour, blurred: Rennett Stowe (CC BY 2.0).
`site.json headshot_background` picks one (null = original photo). The footer then shows the credit the licence requires (`headshot_backgrounds`, build.py `bg_credit`). Live builds are refused while `headshot_background_approved` is false. Joachim picked **c** on 30 Sep 2026 (approved for live); only the chosen option's files ship (build.py prunes the others from dist), and the OG card is og-joachim-agou-photo-bg-c-{en,fr}.jpg (tools/make_og.py follows headshot_background). On phones the hero headshot is centred under the Volunteer button.
Second headshot: `site.json headshot_background_second` = b (Dallas Road) is the About photo (EN+FR, slot value `joachim-agou-headshot-second`) and a second download next to the main one on Media; its CC BY-SA 2.0 credit and share-alike note are in the footer too.

## Victoria photos (1 Oct 2026; approved by Joachim 12:26 PT and live)
Real photos of the riding, all from Wikimedia Commons under CC BY or CC BY-SA (licence and author checked on each file page on 1 Oct 2026). Config: `site.json` → `victoria_photos` (`photos`: title, file page, author, licence, EN/FR alt text and place name, crop focus per variant). No identifiable people in close-up, no political signs, nothing about defence sites.
- **Where:** Priorities: a slim 3:1 strip under each numbered heading and under "Also for this riding" (`priorities`: 1 Royal Jubilee Hospital, 2 Fairfield apartments, 3 Cook Street Village, 4 Johnson Street, also: Inner Harbour). Volunteer: one Fairfield street scene under the welcome note (`volunteer`). Home: three small neighbourhood photos under the hero shortcuts (James Bay, Fairfield, Downtown), each linking to the riding map section (`home`). Events: an 80px venue photo on each list card (`events`), chosen in `forms.js` from the event's own public fields only (address first, then neighbourhood), so nothing comes from hidden events; an event with no match (e.g. North Park) has no photo.
- **Files:** `tools/make_vic_photos.py` (run with `/workspace/.mapenv/bin/python`, Pillow with AVIF) downloads each original from Commons (not kept in the repo), crops it and writes `assets/img/vic/<id>-<strip|tile|thumb>-<width>.{avif,webp,jpg}` in sRGB with no metadata. `build.py` `vic_picture()` renders `<picture>` (AVIF, WebP, JPEG fallback) with width/height and `loading="lazy"`; CSS reserves the aspect ratio, so there is no layout shift.
- **Credits:** each page's footer lists the photos it shows in the same style as the headshot background credits ("Photo (Cook Street Village): <title>, NevinThompson, CC BY-SA 4.0 (cropped).").
- **Live switch:** `site.json` → `victoria_photos_live` (`true` since 1 Oct 2026, 12:26 PT approval). With `false`, live builds leave out every photo, the footer credits, the events photo config and the `assets/img/vic/` files, and the build fails if any page still points at them.
- To change a photo: edit its entry (only CC BY / CC BY-SA / CC0 / public domain, check the file page), run the tool, rebuild, and check the footer credit.

## Events calendar (staging only until Joachim approves)
`/events/` and `/fr/events/` get a **List | Calendar** toggle (two buttons with `aria-pressed`; `?view=calendar` opens the calendar, so it can be linked). The list is unchanged and stays the default.
- Month view of October 2026 (`site.json calendar_month`), Monday first (Joachim, 1 Oct 2026; Sat/Sun cells and headers get class `we` from the date), built as a real `<table>` (caption, `scope="col"` day headers with full day names in `<abbr title>`, each day labelled in full for screen readers) by `events_cal.py`.
- **Key dates**: `site.json key_dates`, only from Elections BC (`build.py` stops if a key date has no `elections.bc.ca` source). Each date was checked on 1 Oct 2026 (`key_dates_checked`) against https://elections.bc.ca/2026-provincial-election/ (Key dates table) and https://elections.bc.ca/2026-provincial-election/ways-to-vote/. They are drawn in the grid (◆, pale yellow day) and listed under it with their source links.
- **Events**: the same `get_public_events` data the list uses. `forms.js` adds a chip (● time + short title, linking to the event's page) to each day, so the calendar follows the database automatically. Events after the month get a note pointing to the list.
- Phones (<700px): the grid shrinks to day numbers and markers (◆ key date, ● event). A marked day is a link to that day in "October at a glance" below, which lists everything with times and links. Desktop: full grid with chips; no agenda.
- Without JS: the list cannot load (as before), and the calendar shows with the key dates and the agenda.
- Colour is never the only cue: markers have distinct shapes, and the legend and text say what each one is. Today has a navy outline and `aria-current="date"`.
- `site.json events_calendar_live: false`: live builds leave out the toggle, the calendar and all the "New" parts below. Set it to `true` after approval.

## New events
- `data/events-added.json` records when each public event was first added (Pacific date). It was seeded on 1 Oct 2026 from `campaign_events.created_at`. After that, every build fetches `get_public_events` and records an id it has not seen with the build day (it prints a line: commit the file). If the rpc is unreachable, the file's own copy of title/start/end is used.
- An event is **new for `site.json events_new_days` days (7)** from its added date: from the added day up to the day before added + 7 (Pacific time).
- While new: a red **New / Nouveau** badge (text, not just colour) on its list card, its calendar chip and its agenda line (`forms.js`, which checks the date on the visitor's clock, so the badge ends on time without a rebuild).
- While any upcoming event is new: a **New** badge on "Events" in the main menu (desktop bar and phone menu, EN and FR; screen readers hear "Events, new event"), and a "New event: <title>, <date>" line above the home hero linking to the most recently added upcoming event (and "N more new events" linking to the list). These are made at build time; `site.js` removes them once the newest one has expired or the event has ended (no cookies, no storage, no trackers). A rebuild after the 7 days removes them from the HTML too.
- To mark an event as new again or by hand, edit its `added` date in `data/events-added.json` and rebuild.
