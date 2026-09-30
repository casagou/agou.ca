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
- Main menu: About, Priorities, Get involved (with sub-items), Events, How to vote, FAQ (`site.json` → `main_nav`; the short label "FAQ" comes from `nav_short`). The footer still links to the FAQ. At 1024px the desktop nav fits on one row in EN and FR.

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

### Read more (Home and Priorities)
`collapse()` in build.py keeps the start of a long section visible (about 320 characters, at least one block) and puts the rest behind a "Read more" / "Lire la suite" button (`aria-expanded`, `aria-controls`; the label changes to "Show less" / "Afficher moins", and focus stays on the button). Without JS everything stays visible and the button stays hidden. The trailing call-to-action and page links always stay visible, so the link to the full About page remains. The text is unchanged, so diffcheck still finds every line. Home also has a row of shortcuts under the hero (Priorities, Get involved, Events, How to vote).

### Forms (front end)
- One form surface. The section is the card, and the form inside has no second box. On phones up to 640px the card runs edge to edge, so fields sit 16px from the screen edge (358px wide at 390px). Fields stay in a single column up to 640px. Fields are 52px tall with 18px text.
- Errors: a summary at the submit button ("Please fix the following:"). Each item is a link that focuses its field. Each field also gets a message under it (an "!" icon plus words), `aria-invalid="true"`, and `aria-describedby` pointing to the message. The message clears when the field is edited. The loading ("Sending…") and success states are unchanged.
- Fields, payloads and RPCs are unchanged (front end only).

### FAQ page
A "Topics" / "Thèmes" index links to each group heading. On phones it shows as chips at the top. From 1100px it becomes a sticky list to the right of the reading column. Each question row is a full-width `<summary>` at least 56px tall, with a circled +/− indicator and a visible focus outline.

### "More photos on Instagram"
After the photo "Joachim Agou presenting a test program" (Media, Photos), build.py adds the reading link "More photos on Instagram ↗" / "Plus de photos sur Instagram ↗". It links to `site.json` → `social.Instagram` (same tab, `rel="noopener"`, no embed and no tracking). It is not in Notion. `site.json` → `more_photos_after` lists the images it follows, so a Notion re-sync keeps it.

## Content exclusions (from `exclusions.json`)
- "Most people call me Joa." (EN/FR): the site says Joachim, never Joa.
- The Thales Canada job line (EN/FR): current employer is not shown.
- "Joa Aero Engineering (…)," (EN/FR): the business name contains "Joa". Joachim can approve or rename it.
- Media: "Joachim Agou is the Conservative Party of BC candidate…" was removed, because he is *seeking* the nomination.
- Media-kit PDFs: they are in `assets/media/` (not Notion), and `<placeholder>MEDIAKIT</placeholder>` renders as the download links (see RESYNC.md "Media kit PDFs"). Staging shows them. Live has shown them since 2026-09-30 (`publish_media_kit_live: true`). Both PDFs still call him the candidate (EN medium bio: "is the Conservative Party of BC candidate"; FR: "est le candidat du Parti conservateur"). Joachim approved them as-is on 30 Sep 2026, so their exact hashes are allow-listed in `site.json` → `media_kit_approved`.
- FR "(page en anglais)" notes were removed (home and FAQ), because those pages now exist in French.

## Scorecard (`/scorecard/`, `/fr/scorecard/`; staging only until approved)
Not from Notion. Joachim's public scorecard text, word for word, is in `content/en/scorecard.md` (his private notes, the pay-for talking points and the draft change log are not in the repo). `content/fr/scorecard.md` is the FR translation (FR title: "Bulletin"), approved by Joachim on 2026-09-30 (`fr_reviewed: true`).
- `scorecard.json`: report-card summary per item (short title, headline figure, cadence, as-of), the source links under each "Today" row, `last_published` (null shows "—"), `fr_reviewed`, and open `factcheck` flags.
- `scorecard.py` renders the page (own stylesheet `assets/css/scorecard.css`); build.py adds the "See the scorecard" links on Priorities and in the home priorities section, and `site.json` puts it in the footer.
- `site.json` → `"publish_scorecard_live"` (`true` since 2026-09-30; both EN and FR are live). When false, the live build leaves out both pages and every link to them. Staging always shows them. Even when true, the live build refuses to run while any `factcheck` flag is left in `scorecard.json` or `fr_reviewed` is false (both render as highlighted draft notes).
- After editing: `python3 build.py --env staging && python3 tools/scorecard_check.py` (every sentence of `content/en/scorecard.md` must be on the page; add `--source <file>` to compare against Joachim's full text).
