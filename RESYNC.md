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
