# agou.ca

- `/` → redirects to https://casagou.notion.site/joachim (same as the old GoDaddy forward)
- `/nominate` → nominator sign-up form (submissions go to Supabase project beacon-hill-campaign, table `nominator_signups`, admin-only read)

Edit the wording in `nominate/index.html` (the TEXT block at the top of the script).
- `/volunteer` → volunteer sign-up form (submissions go to the same Supabase project via rpc `submit_volunteer_signup`, table `volunteer_signups`; public cannot read, organizers/admin read and manage). Migration: casagou/Beacon-Hill `supabase/migrations/37_volunteer_signups.sql`.

Edit the wording in `volunteer/index.html` the same way (TEXT block).
- `/events` → public events list and detail pages (`/events/?e=<id>`) with RSVP form and Add to calendar (.ics + Google Calendar). Reads rpc `get_public_events` (only public, Scheduled, upcoming events; public fields only) and posts RSVPs to rpc `submit_event_rsvp` (table `event_rsvps`; public cannot read). Events are managed in the campaign app (☰ → Events). Indexable on purpose (unlike /nominate and /volunteer). Migration: casagou/Beacon-Hill `supabase/migrations/38_campaign_events.sql`.

Edit the wording in `events/index.html` the same way (TEXT block).
- `/lawn-sign` → lawn sign request form (rpc `submit_lawn_sign_request`, table `lawn_sign_requests`; public cannot read, organizers/admin manage status, delivery volunteer, dates and notes in the campaign app, ☰ → Lawn signs). noindex like /volunteer. Migration: casagou/Beacon-Hill `supabase/migrations/40_lawn_sign_requests.sql`.

Edit the wording in `lawn-sign/index.html` the same way (TEXT block).

## Bilingual site source (branch `staging`; published to agou.ca)
`site/` holds the new EN/FR site built from Notion (static, no trackers). Preview: https://agou-staging.pages.dev (noindex).
See `site/README.md` (structure, forms, photo slots, `promote_donate`, exclusions) and `RESYNC.md` (re-sync from Notion, redeploy staging, publish to live).
