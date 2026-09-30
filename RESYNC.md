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
