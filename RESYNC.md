# agou.ca: re-sync from Notion, redeploy staging, publish

The new bilingual site lives in `site/` on branch **`staging`**. Branch `main` (root `index.html`, `/volunteer/`, …) is what GitHub Pages serves at https://agou.ca today. Do not change it until the new site is approved.

## 1. Re-sync after editing Notion
Notion pages (ids are also in `site/site.json` → `notion`):

| Key | EN | FR |
|---|---|---|
| home | 3e7e245a-e5f3-8189-b010-c0b008f99f7e | 3e8e245a-e5f3-81b8-82ed-f46ff291e069 |
| about | 3e8e245a-e5f3-81ab-a121-efa7bf13cc57 | 8e3e245a-e5f3-83f3-afca-01c296ec9ce6 |
| priorities | 3e8e245a-e5f3-8181-b6b1-dbc98a2cde9a | b03e245a-e5f3-8201-ae89-010013ebc80e |
| media | 3ebe245a-e5f3-8157-9873-c06a8d0db06d | (none, FR media page is a placeholder) |
| faq | 3ebe245a-e5f3-8138-8df6-f42979a5ca5f | 3ebe245a-e5f3-81d3-8683-d40f8909891f |

1. Fetch the page (Notion MCP `notion-fetch <id>`, or copy its text) and save the full text as `site/notion-raw/<lang>-<key>.txt`, e.g. `en-about.txt`. Keep it verbatim. You may strip query strings from signed image URLs.
2. `cd site && python3 tools/notion2md.py en-about` (no argument = all pages). This regenerates `content/<lang>/<key>.md` and applies `exclusions.json`. If a rule no longer matches, you get a warning. Update the rule; do not hand-edit content/.
3. If the page's "Last updated" date should change, update `site.json` → `updated` (notion2md does this automatically when the fetched text includes `page_last_edited_at`).
4. `python3 build.py --env staging`. The content checks must pass (no Thales/Joa/"the candidate" wording, only whitelisted phone numbers, authorization line on every page).
5. `python3 tools/diffcheck.py` must end with `Unexpected differences: none`.
6. Optional: `python3 -m http.server 8931 --directory dist` and `python3 tools/qa.py http://localhost:8931 /tmp/qa`.
7. `git commit -am "site: re-sync <page> from Notion" && git push origin staging`.

### Media kit PDFs (do not lose these on a re-sync)
The media-kit links on `/media/` and `/fr/media/` do **not** come from Notion, so a re-sync cannot remove them, as long as these rules hold:
- The PDFs are `site/assets/media/joachim-agou-media-kit-en.pdf` and `-fr.pdf` (names in `site.json` → `media_kit`). To update one, replace the file under the same name. The KB size in the link text is worked out at build time.
- `exclusions.json` rule "en-media … `<pdf src=…>`" turns Notion's two PDF attachments into `<placeholder>MEDIAKIT</placeholder>`, and `build.py` renders that token as the download links. If Notion's attachment block changes, notion2md warns that the rule no longer matches. **Update the rule's `find` text so it still outputs `<placeholder>MEDIAKIT</placeholder>`.** Don't delete the rule, and don't hand-edit content/.
- `/fr/media/` has no Notion page. build.py writes it (FR PDF, EN PDF, link to the English page). If a FR Notion media page is ever added, put `<placeholder>MEDIAKIT</placeholder>` in it through an exclusions rule in the same way.
- **Media kit PDFs approved as-is by Joachim on 30 Sep 2026** (both still contain the 'candidate' wording in the medium bio; his decision). Their sha256 hashes are in `site.json` → `media_kit_approved`, and the build scan skips only those exact files. Any replaced or new PDF is scanned again. To approve a new version, add its hash there, and only after Joachim has approved it.
- `site.json` → `publish_media_kit_live` (currently `true`, since 30 Sep 2026). Staging always shows the links. The live build leaves out the PDFs and links until this is `true`. Even then it runs pdftotext + pdfinfo on each PDF with the same forbidden-term and phone checks as the pages, and it refuses to build if any fail. Staging prints the hits as warnings and shows a yellow note on the media pages.

### FAQ sources and the funding line (do not lose these on a re-sync)
Joachim approved these on 2026-09-30 after a fact-check. They are `en-faq` rules in `site/exclusions.json`, so every re-sync reapplies them. Notion still has the old text.
- **Funding line:** "The party said those tax cuts would be paid for by a balanced budget and by stopping spending that does not deliver." becomes "The party said faster economic growth would pay for those tax cuts, and committed to balancing the budget in a second term." plus a link to the 2024 costing appendix. The old line was wrong: the appendix credits economic growth and promises a balanced budget in a second term. `build.py` refuses the old wording ("paid for by a balanced budget", "stopping spending that does not deliver"), so it cannot go live even if someone adds it to Notion under different surrounding text.
- **Source links:** 310 cruise calls → GVHA (Oct 2025). The $900M rebate, $60M drivers' package and $150M small-business figures, and the "2024 platform appendix" line, link to the costing appendix and/or the 2024 platform PDF.
- **Every public number keeps a source.** If a rule warns that it no longer matches, update its `find` text so the link survives. Don't delete the rule. Better still, put the links in Notion itself; then the rule stops matching and can be removed.
- The French FAQ now has these answers, with the same funding line and source links (see "Complete French FAQ" below).

### Complete French FAQ (30 Sep 2026; staging only until approved)
Notion's FR FAQ still has the old 17-question text. One `fr-faq` rule in `site/exclusions.json` (the last `fr-faq` rule) replaces the whole FR FAQ body with a full translation of the current EN FAQ: 36 questions and 7 sections, in the EN order, including the EN fact-check rules above and Joachim's FR wording.
- If the Notion FR FAQ is edited, the rule stops matching. notion2md warns, and `build.py` fails because the FR FAQ must have the same number of questions and topic-index entries as EN. Then update the rule's `find`, or better, paste the translation into Notion and delete the rule.
- If the EN FAQ gains or loses a question, update the FR `replace` text to match. The count check stops the build until you do.
- `site.json` → `fr_faq_approved: false`: `build.py --env live` refuses to run until Joachim approves.

### FR wording corrections and About career changes (30 Sep 2026; staging only until approved)
Joachim's FR corrections to Home, Priorities, About and the voter information are `fr-home`, `fr-priorities` and `fr-about` rules in `site/exclusions.json`. The rest are direct edits in `ui.json` (nominate sub/intro, vote facts), `site.json` (nominate button label), `content/fr/scorecard.md` ("soins dans un milieu sécurisé") and `build.py` (the FR manifest description). Examples: "Je sollicite l'investiture…" instead of "Candidat à l'investiture…", and "signer mon formulaire de mise en candidature" instead of "appuyer ma candidature" for the nomination.
- About (EN+FR): the current role is shown without the company name ("Test & Evaluation Engineer — Defence contractor supporting the Royal Canadian Navy, Mill Bay, BC · April 2026 – present"). The Casagou entry lists JOA Aero Engineering first, then Eventia Media, Victoria Drone and BC Funeral Videos. It's "more than 15 years" everywhere (EN FAQ too).
- About intro (EN+FR, 'Who I am' and 'Work' paragraphs): rewritten with Joachim's approved text, as whole-paragraph `en-about`/`fr-about` rules. `build.py` `ABOUT_OLD` fails the build if the old paragraphs come back.
- About career history (EN+FR): rebuilt from Joachim's Notion CV (page 2dde245ae5f380fd8002f8f32bec3cac) as one whole-list `en-about`/`fr-about` rule each: roles in CV order, one or two short sentences. A City That Works must never appear on agou.ca (build.py refuses it); the Victoria Conservative Association volunteer role is held until Joachim decides. Also left out: the CV's career break, SpaceX private investment, Sar-El volunteer programme and Casagou Ops/Learning/Ventures. JOA Aero Engineering and Eventia Media are folded into the Casagou entry. If the Notion About list changes, the rule stops matching; update its `find`.
- About 'How I work' (EN+FR): Joachim's approved four-step list (bold lead + one sentence each) replaces Notion's short list via `en-about`/`fr-about` rules. It appears only on About. `ABOUT_OLD` refuses the old list.
- Home hero (EN+FR, 30 Sep 2026): intro paragraph, 'Put a test engineer on the ballot.' callout and a 'Sources:' line (build.py renders the lines between the tagline and the callout as `.hero-intro`, and the lines after the callout as `.hero-src`). The method line opens the home About block, and the old method sentences are removed. These are `en-home`/`fr-home` rules.
- Priorities: four-beat first paragraph in each numbered section, as `en-priorities`/`fr-priorities` rules. §3 is Joachim's text; §1, §2 and §4 are proposals.
- Two-line lockup (ui.json `lockup`): build.py places it only under the home tagline, under the Priorities and Scorecard H1s, and once in the Priorities 'How I'll report to you' block. The build fails if it appears on any other page.
- FR nominating wording: « Signer mon formulaire de mise en candidature » (home heading = site.json nominate section.fr, nominate title, privacy). `FR_OLD` refuses « appuyer ma/la candidature ».
- `build.py` `FR_OLD` fails the build (both envs) if any old FR phrase comes back on a `/fr/` page. `EXPERIENCE_OLD` fails any page that says "more than 12 years" / "plus de 12 ans".
- `site.json` → `fr_edits_approved: false`: `build.py --env live` refuses to run until Joachim approves.

### Priorities robbery figure (do not lose this on a re-sync)
Joachim approved this on 2026-09-30 after a fact-check. Notion still has the old line, so `en-priorities` and `fr-priorities` rules in `site/exclusions.json` rewrite it on every re-sync.
- EN: "Robberies in Victoria rose 21% in 2025 (Victoria News)" becomes "Robberies in Victoria rose 19% in 2025", with a link to [Statistics Canada Table 35-10-0184](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3510018401). FR: « Les vols qualifiés ont augmenté de 19 % à Victoria en 2025 », linking to the same table in French.
- Why: the 21% (181 robberies) is the Victoria **metro area** (Table 35-10-0177). The City of Victoria figure (VicPD, municipal) is 106 robberies in 2024 and 126 in 2025, +19% in incidents (+17.9% per capita). That is in Table 35-10-0184, by police service.
- `build.py` refuses the old wording ("Robberies in Victoria rose 21%", "vols qualifiés ont augmenté de 21 %", "181 incidents"). `tools/diffcheck.py` treats the replaced Victoria News link as an intentional difference.
- If notion2md warns that a rule no longer matches (the Notion sentence changed), update its `find` text. Don't delete the rule. Better still, fix the sentence in Notion; then the rule stops matching and can be removed.
- The same correction is on `/scorecard/` item 7 (see `site/scorecard.json` → `approved_edits`).

### Priorities v2 (1 Oct 2026; staging only until approved)
Joachim adopted his reviewer's notes ("update the priorities accordingly. Be meticulous"). The restructured text is on staging for his review. Sources, before/after and open questions: `/workspace/agou.ca-priorities-v2-review.md` on the box.
- Priorities EN/FR: one whole-page `en-priorities` / `fr-priorities` rule at the end of `site/exclusions.json` (find = the page after the earlier rules, replace = the v2 text). Notion still has the old text. After approval, paste the approved text into Notion and delete the two rules. If Notion changes first, the rule stops matching and notion2md warns: re-base the `find` on the new text, don't delete the rule.
- `<more/>` on its own line marks where a section's "Read more" starts: actions, "What changes for you" and "How you'll know" stay visible above it; evidence and implementation notes go below.
- Scorecard item 7 lever (EN/FR): bail is federal law, so the lever is provincial funding of sheriffs and court time plus pressing Ottawa. The EN line is in `scorecard.json` → `approved_edits` under a key marked PROPOSED.
- `build.py` `PRIORITIES_OLD` refuses the old wording (cancellations "are decisions", "flat monthly fare", "vote for bail law", "Last year 295", "biggest problem", the short housing-tax line).
- `site.json` → `priorities_v2_approved: false`: `build.py --env live` refuses to run until Joachim approves.

#### Priorities v2, round 2 (Joachim, 1 Oct 2026 5:27 PM PT; staging only)
- **Scorecard items 1, 6, 7 (EN/FR):** item 1 target no longer prints an indexation year ("The year and the funding follow the party’s published fiscal plan"); items 6 and 7 levers are provincial funding (prosecutors, sheriffs, court time) plus pressing Ottawa on federal bail law. The EN lines are in `scorecard.json` → `approved_edits` under the "2026-10-01 (Joachim, 5:27 PM PT …)" key, so `tools/scorecard_check.py --source ../scorecard-source.md` still passes without editing Joachim's source file. Still 12 lines; no ferry line.
- **Priorities:** the whole-page `en-priorities`/`fr-priorities` rules now carry the round-2 text (ferry "How you'll know" points to BC Ferries' own reports; April–December 2025 and FY2026 ferry figures with sailings vs round trips; labelled housing tax-relief example; 2024-platform overlap noted on secure care and tents).
- **FAQ (EN/FR) and Media (EN):** targeted `en-faq`, `fr-faq` and `en-media` rules at the end of `exclusions.json` (each `why` starts "Priorities v2 round 2"). The `fr-faq` ones run after the whole-body FR FAQ rule. If Notion changes a sentence, notion2md warns that the rule no longer matches: re-base its `find`, don't delete it.
- **Media-kit PDFs** were edited in place (PyMuPDF, page 2 only: Cost-of-living bullet and the downtown bail sentence, same Lato font and layout; the script is on the box at `/workspace/prio-v2-src/mk/edit_mk.py`). Their hashes changed, so they are no longer in `media_kit_approved`: the staging build warns about the medium-bio 'candidate' wording Joachim approved on 30 Sep, and the live build would refuse. After Joachim approves the new files, add these hashes to `site.json` → `media_kit_approved`: EN `e8e47f6e7b4ca6679269a01dc11fd817bd432085669227c481e19a212ec86d46`, FR `df98916a9273359b0440e6f7e0c99eca437f03fac42da245797cef807a51432c`.
- `build.py` `PRIORITIES_OLD` now runs on every page and on the PDFs, and also refuses "custody where the law allows" (EN/FR), "Indexation restored from 2027", a balanced budget listed as a cost-of-living measure, ferry reporting under cost of living, "the candidate announced by", and "charter and flat fare".

### Priorities summary-first layout (7 Oct 2026; staging only until approved)
Joachim approved building it on staging only (9:48 PM PT), EN and FR, behind `site.json` → `priorities_layout_v2_live` (false). Based on the readability review (`/workspace/prio-review/REPORT.md` on the box).
- Code: `site/prio_layout.py` (runs after collapse(), scorecard lines and photo strips), `assets/css/prio2.css`, `assets/js/prio2.js`, `data/priorities-for-you.json` (the 44 "For you" / « Pour vous » lines, DRAFT wording, in page order per section). Live builds leave out both asset files while the flag is false, so a live publish from staging stays byte-identical.
- Presentation only: no Notion text changes. `build.py` stops if any text block or link of the classic page is missing from the new one (`prio_layout.coverage`). A re-sync that adds or removes a promise bullet stops the build until `priorities-for-you.json` gets a matching line.
- Layout: At a glance box (each section's "What changes for you", first clause, verbatim; replaces the "On this page" list), sticky section bar, "What changes for you" right under each heading ("In practice" list in a details inside that box, open question for Joachim), promise cards (H3 = the bold lead or the bullet's opening words, For you line, source labels, short texts visible, longer ones in "Details and sources"), source parentheticals quieter, long texts split at sentence ends, "Read more" now a details element (same id), "Back to the summary" per section. Details open for deep links, Ctrl/Cmd+F and print.
- To publish: Joachim approves, set the flag true, rebuild live, publish as usual. To drop: delete the four files and the build.py hooks (search PRIO2).

### Priorities summary-first layout, live in PR #74 (merge e3ed25c, live 11:04 PM PT, 7 Oct 2026)
Approved by Joachim in chat 7 Oct 2026 10:57 PM PT, with fixes made on staging first (d3718c2), then `priorities_layout_v2_live` set true (staging 49dd01a).
- Fixes: Responsible spending #4 For you line no longer claims every promise has a cost ("Where a cost has been published, it's shown next to the promise…"); Also for this riding #2 For you line drops the public-service share figure (Campaign Ops excluded it; the bullet's own Notion text still carries it). Short card titles (`priorities-for-you.json` → `short_titles`, EN/FR): the heading is the short title, the card text is the whole original bullet, the anchor is still made from the original opening words. How I work is a compact source legend; its full text sits under "More about how I work and the sources".
- Live diff vs PR #73: /priorities/ and /fr/priorities/, new assets/css/prio2.css and assets/js/prio2.js (loaded only on those pages); everything else the ?v= cache token (site.css/site.js unchanged). No other flag changed (`volunteer_shifts_note_live` false); no Updates pages.
- Checks: coverage vs live 0 missing (138 text blocks, 97 links, EN and FR); all 19 old ids kept; 24 inbound scorecard anchor links resolve; scorecard/province/diffcheck guards and banner_check pass; home, FAQ, events, how-to-vote identical at 1440/390 (height, text, fold pixels); live files byte-identical to the build (43 text files); no console errors or sideways scroll at 1440/1024/768/390/360; deep links open their card; Ctrl/Cmd+F opens all 32 details; print includes all collapsed text. Screenshots: /workspace/prio-layout/live/.
- Rollback: `git revert -m 1 e3ed25c` on main and push (restores the classic layout and removes prio2.css/js); then set `priorities_layout_v2_live` false on staging.

### Review-batch guard
`site.json` → `review_batch_approved` is `false` while the 30 Sep 2026 design batch (header, forms, sections, actions, FAQ index, Instagram link) is on staging for Joachim's review. `build.py --env live` refuses to run until it is `true`. To publish something else before then, build it from a branch without the batch (for example main's source commit plus cherry-picks).

### "What the Province actually controls" (/province/, /fr/province/): not from Notion
A Notion re-sync never touches this page. Its text comes from Joachim's message of 30 Sep 2026.
- EN text: `site/content/en/province.md`. This is Joachim's text word for word, with three approved changes: the byline line ("Sep 30, 2026 · @Joachim Agou") and the drafting note ("Separation of powers. Page copy for the … candidate site …") are left out, and "Victoria-Beacon Hill" becomes "Victoria–Beacon Hill". The site never says "the candidate" or "ACTW", and `build.py` refuses both "ACTW" and "candidate site". Section headings are `## `, tables are `[TABLE: A | B | C]` followed by `a | b | c` rows, and sources are `- text (https://…)`. `province.py` bolds the lead words before the first ". " of each bullet. Don't add the bold in the text file.
- The full source text is kept outside the repo at `/workspace/agou-site/province-controls-source.md`. After any edit, run `python3 build.py --env staging && python3 tools/province_check.py --source /workspace/agou-site/province-controls-source.md`. It must report 0 sentences not found and 0 lines that differ.
- To change the text: change it only when Joachim sends new wording. Update the source file and `content/en/province.md` together, then update `site.json` → `updated.province`.
- FR: `site/content/fr/province.md` is a draft translation. It shows a "Traduction provisoire" banner while `site.json` → `province_fr_reviewed` is `false`. Keep it in step with the EN file when the EN text changes.
- Live switch: `site.json` → `publish_province_live` is `false` until Joachim approves. The live build then leaves out both pages and every link to them: the menu item under Priorities, the "Who controls what?" line on Priorities and in the scorecard's "How this page works", the footer, and the sitemap. With `publish_province_live` set to `true`, the live build still refuses to run while `province_fr_reviewed` is `false`.
- Fact-check (30 Sep 2026): the claims the check flagged are listed in the page's commit message and the report to Joachim. Nothing was changed in his text. Apply fixes only when he approves them.

### Search and social metadata (seo.json): not from Notion
- Every page's `<title>` and meta/og/twitter description come from `site/seo.json` (EN and FR). A Notion re-sync never changes them, so update `seo.json` when a page's subject changes. Titles follow "Page – Joachim Agou, Victoria–Beacon Hill". Descriptions run 110 to 165 characters, say "Joachim", and never say "the candidate", the employer or a street.
- `build.py` fails if any page lacks a title, description, canonical, hreflang trio, og or twitter tag, or if two pages share a title, description or canonical (`seo_check`).
- Social image (since 30 Sep 2026): `site/assets/img/og-joachim-agou-photo-{en,fr}.jpg` (1200×630: name, riding, slogan and agou.ca on navy at left, the headshot at right). Regenerate with `python3 tools/make_og.py` after `tools/make_headshot.py`. The older text-only cards `og-joachim-agou-{en,fr}.png` stay in the repo but are no longer referenced (`seo.json` → `og_image`). Staging builds point og:image at agou-staging.pages.dev and live builds at agou.ca.
- JSON-LD: Person + WebSite on the home pages, BreadcrumbList on the others, and Event on /events/ (added in forms.js from get_public_events, with lat/lng).
- `sitemap.xml` (both envs) lists the indexable pages with hreflang alternates and lastmod (the page's "Last updated" date). Every page is indexable on live, including Volunteer, Lawn sign and Nominate (noindex removed with Joachim's approval, 30 Sep 2026); a page with `"robots": "noindex"` in site.json would be left out. Staging stays `noindex` (meta robots, X-Robots-Tag, robots.txt Disallow).
- `site.json` → `seo_batch_approved` is `false` until Joachim approves this batch, and the live build refuses to run until then.

### Site-made additions a re-sync keeps (not from Notion)
- "More photos on Instagram ↗" after the Media photo (`site.json` → `more_photos_after`).
- Buttons and reading links: the leading "→" on Notion call-to-action lines is dropped when rendering, not in content/.
- Read more toggles, Home shortcuts and the FAQ topic index are generated at build time from the headings and sections, so they follow whatever Notion contains.

### Home upcoming-event banner (Joachim, 4 Oct 2026; live since PR #41/#42, merges e8911fe and 48f5fae)
- Above the home hero, EN and FR: always the next public event that has not ended (`events_cal.home_banner`, `site.js`), New badge while new, "+N more events". Not from Notion; a re-sync keeps it.
- New badges (banner, list, calendar, Events menu) last 48 hours from when an event was added or meaningfully changed (`site.json events_new_hours`, `data/events-added.json` added_at / changed_at; Joachim, 4 Oct 2026). Not from Notion; a re-sync keeps it.
- `build.py` fails if events are upcoming and a home page lacks the banner. After every deploy run `python3 site/tools/banner_check.py https://agou.ca` (or the staging URL); it exits 1 if the banner is missing while events are upcoming.

## 2. Redeploy staging (https://agou-staging.pages.dev)
Deployment runs from casagou/Beacon-Hill, branch **`agou-site-staging`**, workflow `.github/workflows/agou-staging.yml`. It checks out agou.ca@staging, builds with `--env staging`, runs diffcheck, and deploys to the Cloudflare Pages project `agou-staging` with the repo's existing Cloudflare secret.
Trigger it by pushing to that branch:
```
git -C <Beacon-Hill clone> checkout agou-site-staging
git commit --allow-empty -m "redeploy agou staging" && git push
```
(Manual "Run workflow" is not available because the workflow is not on the default branch.)

## 3. Photos, Donate switch and exclusions
See `site/README.md`: "Photo slots", "Donate switch" (`site.json` → `promote_donate`) and "Content exclusions".

### TEMPORARY REDIRECT ACTIVE (Joachim, 8 Oct 2026 12:43 PM PT): agou.ca forwards to the party candidate page
- Joachim in chat: "can you point agou.ca to the campaign website", "I don't want people to see agou.ca for now." Every path on agou.ca and www.agou.ca (EN and FR) now forwards to https://conservativebc.ca/candidate/joachim-agou/.
- Method: GitHub Pages source switched from `main` to the orphan branch `redirect-cbc` (commit 74cd102), live 12:50 PM PT. Every page path that existed on main, plus 404.html (any other path, assets, PDFs, sitemap), is a noindex stub with a canonical link to the party page, a meta refresh and a JS `location.replace`, and no site content. Not a true HTTP 302 (200, or 404 for other paths, then an immediate browser redirect): Cloudflare does not front agou.ca (DNS at GoDaddy) and the only true 302 is GoDaddy forwarding, which needs Joachim's GoDaddy login. Generator: /workspace/agou-redirect/make_tree.py on the box.
- `main` (e3ed25c, PR #74) is untouched. DNS, email (Google Workspace MX/SPF/DKIM/DMARC), the campaign app, Supabase and staging were not changed.
- **While this is active, merging a publish PR into `main` does NOT go live.** Pages serves `redirect-cbc` until the source is switched back.
- Rollback (about 1 minute): `gh api -X PUT repos/casagou/agou.ca/pages -f cname=agou.ca -F https_enforced=true -f 'source[branch]=main' -f 'source[path]=/'` then `gh api -X POST repos/casagou/agou.ca/pages/builds` (the source switch alone did not trigger a build), wait for `gh api repos/casagou/agou.ca/pages/builds/latest` to show `built` on main's head; pages may stay cached up to 10 min (max-age=600). Then run `python3 site/tools/banner_check.py https://agou.ca`.

### No-party version (Joachim via Campaign Ops, 8 Oct 2026 2:50/2:52 PM PT), staging; live prepared, NOT published
- Joachim is no longer supported by the party but is still running in Victoria–Beacon Hill. `site.json` `no_party_v1` (true) turns on `site/no_party.py` on staging; `no_party_v1_live` (false on staging) does the same for live builds.
- What it does: EN/FR text edits (Priorities "my position", party-only items dropped, FAQ, home, About, media, privacy, scorecard lines 1–2), no party links (own volunteer / lawn-sign forms), no Donate page or appeals (`/donate/` 302 on staging, noindex stub forwarding home on live), no media-kit PDFs, event 114 and any public event naming the party hidden on the build side (JS filters the live RPC data; Supabase untouched). The build fails on any party term outside `no_party.ALLOW`.
- Guards: diffcheck excuses exactly the no-party differences; `scorecard_check.py --no-party --dist DIR`; `province_check.py --dist DIR`; banner_check ignores the page's hidden ids.
- Live: draft PR #75 (branch publish-20261008-no-party) built from branch `no-party-live-flag`. Going live also needs the Pages source switched from `redirect-cbc` back to `main`; runbook in /workspace/no-party/GO-LIVE.md on the box. Authorization line unchanged (Bert Chen, financial agent).

## 4. Publish to live (first done 2026-09-30, PR on casagou/agou.ca; repeat for every update)
Option A (keeps the current GitHub Pages "deploy from branch" setup):
1. Make sure no Notion red `[TO COMPLETE]` notes remain (the live build stops if any do). `cd site && python3 build.py --env live`. This writes `dist/` with canonical https://agou.ca URLs, sitemap.xml, robots.txt allowing indexing, `CNAME` (agou.ca) and `.nojekyll`, and no staging banner or noindex.
2. On a new branch from `main`, replace the root site files with the contents of `site/dist/`. Keep `CNAME` = `agou.ca`. The new build replaces `/volunteer/`, `/nominate/`, `/events/`, `/lawn-sign/` at the same URLs and with the same RPCs.
3. Open a PR, check the preview, and merge after approval. GitHub Pages redeploys main within a few minutes.
4. Check https://agou.ca/, /fr/, and each form (a ZZTEST submission, then delete it in the app or with SQL).

Option B: switch GitHub Pages to "GitHub Actions" and add a workflow that runs `build.py --env live` and uploads `site/dist`. This keeps the source and the build separate. It needs a Pages settings change on the repo.

Exactly as done for the first publish:
```
cd site && python3 build.py --env live           # must print "content checks passed"
git -C <agou.ca clone> checkout -b publish-YYYYMMDD origin/main
# replace the root with the build (keeps nothing else; README.md is re-added below)
cd <agou.ca clone> && git rm -rq . && cp -a <staging clone>/site/dist/. . && git checkout origin/main -- README.md
git add -A && git commit -m "agou.ca: publish site from staging <sha>" && git push -u origin HEAD
gh pr create --base main --fill && gh pr merge --merge
```
Then wait for the Pages build (`gh api repos/casagou/agou.ca/pages/builds/latest`) and check https://agou.ca.
Only built files go on `main` (never `site/`), because GitHub Pages serves everything in the root, including the Notion snapshot.

Rollback: `git revert -m 1 <merge commit>` on `main` and push (or open a revert PR from the PR page). Pages rebuilds the previous site in about a minute.

### Published live (1 Oct 2026, Joachim approved 5:51 PM PT)
- `site.json`: `priorities_v2_approved` set to true. The new media-kit hashes (EN e8e47f6e…, FR df98916a…) were added to `media_kit_approved`.
- The live build (32 pages, content checks passed) went out from staging f35abdf plus these flags in casagou/agou.ca PR #37, merge commit fec1dba.

### French review (Joachim, 1 Oct 2026 6:32 PM PT), staging only
- Source: Joachim's French review (`french-review-2026-10-02.md`). English is the master: every French sentence was checked against the current English, and English wins where they differ. Changelog with what was applied or skipped: `/workspace/fr-review/applied.md` on the build box.
- Notion pages (home, about, faq, priorities): the edits are rules in `exclusions.json` whose "why" starts with "French review 2026-10-02". New: rules with `"page": "fr-home:contact"` apply to the footer contact block (tools/notion2md.py; diffcheck accepts them).
- Hand-written French files edited directly: `content/fr/province.md`, `content/fr/scorecard.md`, `content/fr/privacy.md`, plus the new `content/fr/media.md` (no French Notion page exists; keep it in step with `content/en/media.md` by hand). Also `scorecard.json`, `seo.json`, `ui.json` and `site.json` (French fields only).
- The home "Read more" split in French keeps the same paragraphs visible as English (`build.py` COLLAPSE_EN).
- Events: Supabase migration `46_campaign_events_fr` adds `title_fr`, `description_fr` and `location_name_fr` to `public.campaign_events`. `get_public_events()` returns them as 3 extra columns at the end. **When Events adds a row, it must fill these three French fields.** The French site falls back to English if one is empty. Downtown shows as Centre-ville in French.

### Needs-Joachim answers (1 Oct 2026, 7:49 PM PT), staging only
Rules in `exclusions.json` whose "why" starts with "Joachim (1 Oct 2026, 7:49 PM PT)":
- The past voting dates are gone: registration by 1 Oct (Home, FAQ and How to vote key dates in `ui.json`) and "closed 30 Sep".
- The Home family-doctor line now uses the Priorities metric and source (24.7% with no family doctor or nurse practitioner in June 2025; Ministry of Health records via The Canada Report).
- The FAQ entry "What does nominating a candidate mean?" is removed.
- The DRIPA answer cites BC Laws (SBC 2019, c. 44).
- The About intro follows the media bios (Florida Tech, then graduate research at Laval), and the Community list adds Chabad.
- The extra French footer Media line is removed. The footer navigation already links Media / Médias on every page.
- `build.py` PRIORITIES_OLD now blocks the old wording. The media-kit PDFs are unchanged.

### Party links (Joachim, 2 Oct 2026 12:28 AM PT), staging only
See `site/README.md` "Party links". If Notion's Home or FAQ volunteer, lawn-sign or donate text changes, update `build.py` PARTY_MD; the build stops if a replacement no longer matches. To publish, set `site.json` `party_links_live` to true after Joachim approves.

### Published live (2 Oct 2026, Joachim approved 1:20 AM PT: "Now you can publish as is.")
- `site.json`: `party_links_live` set to true. Everything on staging up to 89259f7 (consistency audit, French review, Needs-Joachim answers, party links, nominee wording, filing FAQ) went out from staging b8f4190 in casagou/agou.ca PR #38, merge commit 8278fde. Media-kit PDFs unchanged (still the e8e47f6e…/df98916a… files; their bios still say "seeking to represent" / « souhaite représenter »).
- Migration 46 recorded in casagou/Beacon-Hill `supabase/migrations/46_campaign_events_fr.sql` (commit 9eba025; already applied, do not re-apply).
- Rollback: `git revert -m 1 8278fde` on main and push.

### Social links (2 Oct 2026, Joachim via Provincial Campaign Ops), live in PR #39 (merge 1c9d657)
- `site.json` → `social.campaign` (facebook.com/joachimagou, instagram.com/joachimagou) and `social.personal` (@casagou Instagram, Facebook, X). Footer and Home "Follow along" render "Campaign: …" / "Personal: …" (FR « Campagne » / « Personnel »); Contact uses `exclusions.json` rules on `<lang>-home:contact`. JSON-LD sameAs lists all five; "More photos on Instagram" uses `social.campaign.Instagram`. The build fails if a footer lacks the two groups.
- Rollback: `git revert -m 1 1c9d657` on main and push.

### Media bios and Priorities intro (2 Oct 2026, Joachim 8:18 and 8:20 PM PT)
- Media short and medium bios no longer name Casagou Inc. (EN rules on `en-media`, FR edited in `content/fr/media.md`); the full bio still does. `build.py` fails if Casagou appears between the Short bio and Full bio headings.
- Priorities intro is now "I'm the Conservative Party of BC's nominee in Victoria–Beacon Hill. Each proposal on this page says where it comes from:" (FR « Je suis investi … en indique la provenance : »); the "party's plan" link and the platform "coming soon" sentence are gone. Also removed: "The party has not yet published a 2026 version / fiscal plan" (Priorities, FAQ) and the FAQ's "coming soon" aside (now "October 2024; not yet confirmed for this election"). Rules in `exclusions.json` with why "Joachim (2 Oct 2026, 8:20 PM PT)". No existing guard or diffcheck needed the old sentence; a new FORBIDDEN entry blocks the platform 'coming soon' / 'not yet published' wording.

### Published live: How to vote v2 + home Voter information (Joachim approved 6 Oct 2026 9:49 AM PT), PR #63 (merge e2bf891)
- `site.json`: `how_to_vote_v2_live` set to true (draft `how_to_vote_v2` in `staging-drafts.json`, page-scoped `en/how-to-vote` / `fr/how-to-vote` edits; its find is the home Voter information section *after* the `exclusions.json` rules, so re-base it if those rules or the Notion section change).
- Home Voter information: `exclusions.json` rules with why "Joachim (6 Oct 2026, 9:49 AM PT)": "Unit 101, 722 Johnson Street" / « Local 101, 722 Johnson Street », FR « bureau électoral de circonscription » (Elections BC 2026 term). FR events key date (12 Oct) « bureaux électoraux de circonscription fermés ». CSS: `.content a[href^="tel:"]` nowrap.
- Went out from staging 4553aa6 (merged 6 Oct 2026 9:51 AM PT). `volunteer_shifts_note_live` still false; no trail samples. Not changed: FR FAQ still says « directeur du scrutin »; home "Last updated" still 2 Oct.
- Rollback: `git revert -m 1 e2bf891` on main and push.

### Updates / Nouvelles (6 Oct 2026, Joachim via Provincial Campaign Ops; replaces "On the campaign trail")
- Renamed throughout: `trail.py` → `site/updates.py`, `tools/make_trail.py` → `tools/make_updates.py`, `data/trail*.json` → `data/updates*.json`, `assets/img/trail/` → `assets/img/updates/`, `site.json` page `trail` → `updates` (`/updates/`, nav "Updates" / « Nouvelles ») and config `trail` → `updates` (home_max 4), `ui.json` / `seo.json` `trail` → `updates`, CSS `.trail*` → `.upd-*`. No `/trail/` redirect (never public).
- New: per-entry permalink pages (`/updates/<date>-<slug>/`, page keys `u:<date>-<slug>` registered by `updates.register`), RSS feeds (`/updates/feed.xml`, `/fr/updates/feed.xml`), entry format (title/body/links/up to 4 images/alt/slug; README "Updates"), photo layouts 0-4, home cards with "Read more". `shell()` now takes a per-page Open Graph override (`page["og"]`), used only by permalink pages.
- Hidden while `data/updates.json` has no entries (HIDDEN + `updates.check`). 4 SAMPLE entries on staging only (`data/updates-samples.json`).
- Published live (code only, zero entries) from staging 57288b8 in casagou/agou.ca PR #64, merge 64e190e (6 Oct 2026 10:42 AM PT). Live diff: site.css only (+ cache tokens, banner build timestamp). Live home pixel-identical before/after (EN/FR, 1440/390); /updates/, /fr/updates/, feeds and sample files 404; `volunteer_shifts_note_live` still false, `how_to_vote_v2_live` true. Rollback: `git revert -m 1 64e190e` on main and push.

### Published live: FAQ bundle (Joachim approved via Campaign Ops, 6 Oct 2026 10:46 AM PT), PR #65 (merge 8428d5d)
- `site.json`: `faq_why_running_live` set to true (draft `faq_why_running` in `staging-drafts.json`, `en/faq` + `fr/faq` edits).
- FAQ EN+FR: new "Why are you running for office?" / « Pourquoi vous présentez-vous? » 2nd under About the campaign (24.7% family-doctor figure with its Canada Report source, the neighbours' four concerns, test engineer + quarterly report); the old "Why are you running to represent Victoria–Beacon Hill?" entry removed (with its unsourced $2,120 line). FAQ entries have no ids, so no question anchor needed keeping.
- "When and where can I vote?": links to /#voter-information (FR /fr/#renseignements-pour-voter) and Elections BC's Ways to Vote page (FR « (en anglais) »: no French version). « directeur du scrutin » unchanged.
- Freshness after nominations closed (Elections BC final candidate list, retrieved 6 Oct 2026 10:38 AM PT; copies in /workspace/faq-why/sources/ on the box): own Elections BC nomination accepted; Lore/Sahota answer = final list (Grace Lore BC NDP, Raj Sahota BC Green Party, on the ballot as Rajinder S. Sahota, Joachim Conservative Party of BC), Green 24 Sep announcement source dropped; FR « Lore a été la députée », « déposés au plus tard »; section "Get involved" / « S'impliquer » (was "Nominating and helping" / « Mise en candidature et aide à la campagne »). Old heading ids kept as alias spans (`site.json anchor_aliases`, build.py).
- `tools/diffcheck.py` treats Notion lines named in an active staging draft's finds (and links it drops) as intentional differences.
- Went out from staging 2b93b1c (merged 6 Oct 2026 10:48 AM PT). Everything else in the live build only differs by the ?v= cache-bust; `volunteer_shifts_note_live` still false, `how_to_vote_v2_live` true, no trail/Updates samples.
- Rollback: `git revert -m 1 8428d5d` on main and push.

### Event 113 + shift 105 time (6 Oct 2026, Events agent, Joachim approved), live in PR #66 (merge 7bd436a, 1:51 PM PT)
- campaign_events id 113 (public): All-Candidates Meeting | Downtown Victoria Business Association, Tue Oct 20 6:30-8:00 PM PT, Greenhouse at the Victoria Conservatory of Music, 900 Johnson St (BC Geocoder 48.4267205, -123.3586625; inside the riding). Host contact and RSVP details are in `notes` only (never public; get_public_events does not return notes).
- Shift id 105 (James Bay, Oct 20) moved 5:00-7:30 PM -> 4:30-6:00 PM in campaign_events (1 sign-up at the old time; its bell notification text updated; Google Calendar instance had already been moved). Backup: /workspace/events/campaign_events_backup_20261006_id_105.json.
- Site files: venue photo `conservatory-of-music` (Michal Klajban, CC BY-SA 4.0, passers-by blurred; thumb only) + `"900 Johnson St"` mapping (above the Downtown default), static map event-113, data/events-added.json record. Rendered from the 1280px Commons thumbnail, because Commons returned 429 for the full original; re-running tools/make_vic_photos.py downloads the full original into /tmp/vic-photos-orig when it is missing.
- Rollback: `git revert -m 1 7bd436a` on main and push; set event 113 `is_public=false` or `status='Cancelled'`.
- Oct 6, 2026 ~1:57 PM PT (Events-approved): shift 105 `description` / `description_fr` replaced in campaign_events (FR « jumellerons »; U+00A0 before « : » and in « 20 h »). Data only, no site files, no PR: the public site never shows shift descriptions (`get_public_shifts` omits them; forms.js builds the shift page and ICS text from ui.json `shifts`). Backup: /workspace/events/campaign_events_backup_20261006b_id_105.json.

- 2026-10-06 2:01 PM PT, shift time-of-day label (Events): forms.js partOfDay now morning <12:00, afternoon 12:00-16:59, evening 17:00+ (was evening from 16:00). Shifts 93, 102, 105 now say afternoon / après-midi. Staging 3334fdf; live agou.ca PR #67, merge commit eb28d28. Rollback: `git revert -m 1 eb28d28` in casagou/agou.ca (and revert 3334fdf on staging).

### Published live: health wait figures (Joachim approved via Campaign Ops, 6 Oct 2026 8:10 PM PT), PR #68 (merge 794a48f)
- `site.json`: `health_wait_figures_v1_live` set to true (draft `health_wait_figures_v1` in `staging-drafts.json`; `en/home`, `fr/home`, `en/priorities`, `fr/priorities` edits), exactly as approved on staging 61b9d5d.
- Home EN+FR hero: the 32.2-week beat ("the median wait from a family doctor's referral to treatment was 32.2 weeks") beside the 24.7% line, plus the Fraser Institute Waiting Your Turn 2025 source link.
- Priorities §1 EN+FR: Why (32.2 weeks vs Canadian median 28.6; B.C.'s longest since the Fraser Institute began measuring in 1993, cited to the Fraser commentary of 17 Aug 2026; second-shortest after Ontario at 19.2 weeks); surgery bullet 35% past benchmark (98,545 of 282,887; MoH FOI HTH-2026-60818 via SecondStreet, Apr 2026); new "Emergency rooms that stay open" bullet (~2,400 temporary ER closures 2023-2025, more than 900 of 1,095 days; The Province, Jul 2026); What changes ("Fewer ER closures, because more shifts are staffed."); What shortens waits (quarterly report line). Sources and retrieval notes: /workspace/agou-health-figs/sources/ on the box.
- "Last updated" 6 Oct 2026 on home and Priorities (EN+FR, from the draft's `updated`); sitemap lastmod 2026-10-06 for those four URLs.
- Went out from staging 9e4089f (merged 6 Oct 2026 8:11 PM PT; Pages built 8:12 PM PT). Live diff vs PR #67: content only in index.html, fr/index.html, priorities/index.html, fr/priorities/index.html and sitemap.xml; everything else is the ?v= cache token and banner build timestamp. The home banner's build-time "New" badge on event 99 also dropped because its 48-hour window ended at 8:00 PM PT (time-based, not content).
- Flags unchanged: `volunteer_shifts_note_live` false; `how_to_vote_v2_live`, `faq_why_running_live` true; no Updates entries or samples (/updates/, /fr/updates/ and the feed return 404).
- Verified on agou.ca at 1440 and 390 px (EN/FR home and Priorities): live HTML byte-identical to the published build, every approved line present, four source links 200, no console errors, no sideways scroll; banner_check passed. Phone screenshots: /workspace/agou-health-figs/live/ on the box.
- Rollback: `git revert -m 1 794a48f` on main and push (and set `health_wait_figures_v1_live` false on staging).

### Published live: Priorities section 4 v2, A downtown that works (Joachim approved via Campaign Ops, 7 Oct 2026 8:46 AM PT), PR #69 (merge 05ae7a8)
- `site.json`: `priorities_downtown_v2_live` set to true (draft `priorities_downtown_v2` in `staging-drafts.json`; `en/priorities` and `fr/priorities` edits), exactly as approved on staging 5937f1b.
- Section 4 EN+FR follows the party's Safe Streets for BC announcement (6 Oct 2026, https://conservativebc.ca/safe-streets-for-bc/; copy in /workspace/agou-downtown/sources/ on the box), each item labelled party commitment or my position. New: Police (250 officers via the JIBC Police Academy; Victoria's share reported as VicPD officers), Compassionate intervention (Mental Health Act), Care that keeps people alive (end "safe supply", expand naloxone), Safe places to heal, Courts (50 Crown prosecutors, 20 more trial judges with Ottawa, sheriff and court capacity). Treatment adds psychiatric services, crisis response and residential treatment. Kept: detox beds with monthly waits, secure care with safeguards, tents to housing with 12-month reporting, bail. The 2024 platform p. 79 and sheriffs/judges citations are replaced; housing p. 5, small business p. 11 and the 2024 costing paragraph remain. 500 RCMP / rural item omitted (Victoria has VicPD). How you'll know adds repeat offending, bail compliance, treatment access and long-term recovery to the quarterly report; scorecard unchanged (12 lines). FR « entreprises » replaces « commerces » in section 4.
- "Last updated" 7 Oct 2026 on Priorities EN+FR; sitemap lastmod 2026-10-07 for /priorities/ and /fr/priorities/.
- Went out from staging a2e863d (merged 7 Oct 2026 8:48 AM PT; live 8:48 AM PT). Live diff vs PR #68: content only in priorities/index.html, fr/priorities/index.html and sitemap.xml; all else ?v= cache token and banner build timestamp; no files added or removed.
- Flags unchanged otherwise: `volunteer_shifts_note_live` false; no Updates entries or samples (/updates/, /fr/updates/ 404).
- Verified on agou.ca at 1440 and 390 px: live HTML byte-identical to the published build, all new lines present, Safe Streets link 200, no console errors, no sideways scroll; banner_check passed. Screenshots: /workspace/agou-downtown/live/ on the box.
- Rollback: `git revert -m 1 05ae7a8` on main and push (and set `priorities_downtown_v2_live` false on staging).

### Published live: FAQ sync with live Priorities (Joachim approved in chat, 7 Oct 2026 9:09 AM PT), PR #70 (merge 80e5fd2)
- `site.json`: `faq_priorities_sync_v1_live` set to true (draft `faq_priorities_sync_v1` in `staging-drafts.json`; `en/faq` and `fr/faq` edits), exactly as approved on staging eec70f7.
- FAQ EN+FR synced to the live Priorities (PR #68 health quarterly items; PR #69 section 4 v2, Safe Streets for BC, 6 Oct 2026), party commitment vs my position labelled, no new figures: family doctors (quarterly median wait / past benchmark / ER closures sentence); public safety (new Police bullet, Treatment adds party psychiatric/crisis/residential and compassionate intervention, Safety -> Courts with 50 prosecutors / 20 judges / sheriff and court capacity, quarterly items); safer supply (party: end "safe supply" + naloxone, compassionate intervention, drug-free facilities; decriminalization line kept); cost (Safe Streets has no published cost); party vs own (new Safe Streets commitments list; own positions drop the items now party commitments, add bail). 2024 involuntary-treatment and sheriffs/judges citations replaced. « directeur du scrutin » unchanged (out of scope).
- "Last updated" 7 Oct 2026 on FAQ EN+FR; sitemap lastmod 2026-10-07 for /faq/ and /fr/faq/.
- Went out from staging ee68895 (merged 7 Oct 2026 9:10 AM PT; live 9:10 AM PT). Live diff vs PR #69: content only in faq/index.html, fr/faq/index.html and sitemap.xml; all else ?v= cache token and banner build timestamp; no files added or removed.
- Flags otherwise unchanged: `volunteer_shifts_note_live` false; no Updates entries or samples (/updates/, /fr/updates/ 404).
- Verified on agou.ca at 1440 and 390 px: live HTML byte-identical to the published build, all changed lines present, Safe Streets link 200, internal links 200, no console errors, no sideways scroll; banner_check passed. Screenshots: /workspace/faq-sync/live/ on the box.
- Rollback: `git revert -m 1 80e5fd2` on main and push (and set `faq_priorities_sync_v1_live` false on staging).

### Published live: CPBC alignment, Priorities + FAQ (Joachim approved in chat, 7 Oct 2026 1:28 PM PT), PR #71 (merge c0cd2ae)
- `site.json`: `cpbc_alignment_v1_live` set to true (draft `cpbc_alignment_v1` in `staging-drafts.json`; `en/priorities`, `fr/priorities`, `en/faq`, `fr/faq` edits), exactly as approved on staging 0d23025.
- Sources (quotes verified against the live pages; copies in /workspace/cpbc-align/sources/ on the box): Keep Emergency Rooms Open (5 Oct 2026), Supercharge British Columbia's Economy (7 Oct 2026), Conservatives to Remove PST from Canadian Alcohol (29 Sep 2026), leader's housing statement (25 Sep 2026), no new taxes (27 Sep 2026).
- Priorities EN+FR: source key adds "2026 party commitment"; §1 licensing line completed (train more doctors in B.C., bring home Canadians who studied medicine abroad, faster credential recognition, tied to the 388-day Island Health median), clinic backstop "You show your health card and pay nothing" + party "universal and publicly funded" / "never need anything more than their health card", new "An expert commission within 100 days" bullet (my position: bring Saskatchewan results, the backstop and Island Health data), ER line adds keep ERs open / hire and retain doctors and nurses / $50 million emergency fund (announcement doesn't say which hospitals); 32.2 weeks now cited to Waiting Your Turn 2025 (Dec. 2025) as on home, 17 Aug commentary kept for "since 1993"; §2 fees line + 25 Sep statement and no-new-taxes, new red-tape bullet (Minister, 2017 levels, one-in two-out; fewer rules, not fewer public servants); §3 no PST for 3 years on machinery/equipment/business software (café example), no PST at the till on Canadian beer/wine/spirits during the trade war (no rate printed), 180-day tax-simplification plan; Responsible spending front-line line now cites 5 Oct. 120 Day Permitting Act not added (major projects only). 5.06% and 2024-only items keep their labels; ER ~2,400 and 24.7% unchanged.
- FAQ EN+FR (Joachim's standing FAQ-sync rule): family doctors, housing, cost of living, balanced budget/public service, cost ($50 million fund the only 2026 figure; other 2026 items no published cost), party vs own (two new 2026 commitment lines).
- Neighbourhood lists checked against the official boundary (BCEBC Final Report 3 Apr 2023 p. 52; Elections BC VTB boundary gazetted 7 Dec 2023 intersected with City of Victoria neighbourhoods): North Park wholly in, Fernwood ~84.5% in (north strip near Bay St in Victoria-Swan Lake); all site lists correct, none changed. Notes: /workspace/cpbc-align/sources/BOUNDARY_NOTES.md.
- Went out from staging b5bdc2c (merged 7 Oct 2026 1:28 PM PT; live 1:29 PM PT). Live diff vs PR #70: content only in priorities/, fr/priorities/, faq/, fr/faq/ (main content byte-identical to the approved staging build); all else ?v= cache token and banner build timestamp; no files added or removed; sitemap unchanged (lastmod already 7 Oct).
- Flags otherwise unchanged: `volunteer_shifts_note_live` false; no Updates entries or samples (/updates/, /fr/updates/ 404).
- Verified on agou.ca at 1440 and 390 px: live HTML byte-identical to the published build, all changed lines present, all 8 cited links 200 (5 party pages, Hansard, two Fraser), no console errors, no sideways scroll; banner_check passed. Screenshots: /workspace/cpbc-align/live/ on the box.
- Rollback: `git revert -m 1 c0cd2ae` on main and push (and set `cpbc_alignment_v1_live` false on staging).

### Event 114 + shift 111 time (Joachim via Campaign Ops, 7 Oct 2026), live in PR #72 (merge fe07ca7, 9:55 PM PT)
- campaign_events id 114 (public): Thanksgiving Rally in Langford / « Rassemblement de l'Action de grâce à Langford », Mon Oct 12 1:00-2:30 PM PT, Royal Canadian Legion, Langford Branch, 761 Station Ave, Langford (BC Address Geocoder 48.4459535, -123.4997338, civic-number match; outside the riding). A Conservative Party of BC rally with special guest MP Aaron Gunn; Joachim will say a few words. `signup_url` https://conservativebc.ca/events (first public event with one: rendered as "Sign up ↗" / « S'inscrire ↗ »; the site's own optional RSVP still shows, so the description says "The party also takes RSVPs on its events page"). Inserted with is_public=false, made public once the map and photo were ready.
- Shift id 111 (Rockland & North Fairfield, Oct 12) moved 1:30-4:00 PM -> 3:00-4:00 PM PT (starts_at only; still "afternoon" / « après-midi »). 0 sign-ups. Not changed: its description still says "Evening door knocking… whole evening" (not shown on the site), its notes, and the Google Calendar instance (Events handles). Backup: /workspace/events/campaign_events_backup_20261007_id_111.json.
- Site files: photo `langford-goldstream` (Wikimedia Commons "Langford BC" by P199, CC BY-SA 4.0; the Goldstream Village archway in central Langford, about 280 m from the venue, since Commons has no licensed photo of the Legion; thumb crop kept above the 2024 roadside election signs) mapped for `"761 Station Ave"`; OSM data for a small Langford box added to data/osm-events (Overpass via the maps.mail.ru mirror, overpass-api.de failed TLS) and static map event-114 rendered alone; data/events-added.json record. Thumbs and map rendered for this event only (no other image re-encoded).
- Live diff vs PR #71: events/ and fr/events/ (photo credit, photo config, map index, New time), home EN/FR banner data ("+22 more events"), assets/img/events/index.json, 12 new image files; everything else the ?v= cache token. Flags unchanged (`volunteer_shifts_note_live` false); no Updates entries or samples (/updates/, /fr/updates/, feed 404).
- Verified on agou.ca at 1440 and 390 px, EN/FR: live files byte-identical to the build (39/39), list cards, calendar (1:00 PM rally, 3:00 PM shift), event 114 page (map, photo credit, party link), shift 111 page and calendar file (3:00-4:00 PM, afternoon), no notes text in HTML, rpc responses or ICS, no console errors, no sideways scroll; banner_check passed. Screenshots: /workspace/events/ev114_live/ (staging: ev114_stg/).
- Rollback: `git revert -m 1 fe07ca7` on main and push; set event 114 `is_public=false` or `status='Cancelled'`; restore shift 111 `starts_at` to 2026-10-12T20:30:00Z from the backup.

### Event 114 FR title « Action de grâces » (Campaign Ops, 7 Oct 2026), live in PR #73 (merge 9e2de04, live 9:59 PM PT)
- campaign_events id 114 `title_fr`: « Rassemblement de l'Action de grâce à Langford » -> « Rassemblement de l'Action de grâces à Langford » (with s, like the rest of the site). Nothing else in the row changed. Backup: /workspace/events/campaign_events_backup_20261007b_id_114.json.
- data/events-added.json: the record's `title_fr` corrected by hand so the build does not set `changed_at` (a typo fix, not a new event; the New badge window stays as it was). Staging commit 9b1af79.
- Live diff vs PR #72: fr/index.html banner data only (the "t" title); everything else the ?v= cache token. No flags changed; no Priorities layout work (nothing written yet at publish time); notes-leak grep clean; scorecard, province and diffcheck guards passed.
- Verified on agou.ca at 390 px: /fr/events/?e=114 shows the new title (old one absent), FR calendar Mon Oct 12 entry shows it with the NOUVEAU badge, no console errors, no sideways scroll. Screenshots: /workspace/events/verify73/.
- Rollback: `git revert -m 1 9e2de04` on main and push; restore `title_fr` from the backup.
