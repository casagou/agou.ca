# agou.ca: temporary redirect

This branch (`redirect-cbc`) is what GitHub Pages serves while agou.ca forwards to https://conservativebc.ca/candidate/joachim-agou/
(Joachim, 8 Oct 2026). Every page is a noindex redirect stub; the real site is untouched on `main`.

Rollback: `gh api -X PUT repos/casagou/agou.ca/pages -f cname=agou.ca -F https_enforced=true -f 'source[branch]=main' -f 'source[path]=/'`
