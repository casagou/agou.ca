# agou.ca

This branch (`main`) is what GitHub Pages serves at https://agou.ca. **It is generated. Do not edit these files by hand.**

- Source: branch `staging`, folder `site/`. Content is drafted in Notion, re-synced into `site/notion-raw/`, and built with `python3 build.py --env live`.
- How to update, publish and roll back: `RESYNC.md` and `site/README.md` on branch `staging`.
- Preview: https://agou-staging.pages.dev (noindex).
- Forms (same Supabase project and RPCs as before): `/volunteer/`, `/nominate/`, `/lawn-sign/`, `/events/` (`?e=<id>`); French versions under `/fr/`. Submissions appear in the campaign app (beacon-hill-map.pages.dev).
