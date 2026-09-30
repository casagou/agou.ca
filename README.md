# agou.ca

- `/` → redirects to https://casagou.notion.site/joachim (same as the old GoDaddy forward)
- `/nominate` → nominator sign-up form (submissions go to Supabase project beacon-hill-campaign, table `nominator_signups`, admin-only read)

Edit the wording in `nominate/index.html` (the TEXT block at the top of the script).
- `/volunteer` → volunteer sign-up form (submissions go to the same Supabase project via rpc `submit_volunteer_signup`, table `volunteer_signups`; public cannot read, organizers/admin read and manage). Migration: casagou/Beacon-Hill `supabase/migrations/37_volunteer_signups.sql`.

Edit the wording in `volunteer/index.html` the same way (TEXT block).
