"""'What the Province actually controls' page (/province/, /fr/province/), called from build.py.

Text: content/en/province.md is Joachim's text word for word (source kept outside the repo; see RESYNC.md), minus the
byline and the drafting note. content/fr/province.md is a draft translation (banner until site.json
province_fr_reviewed is true). Not from Notion. Left out of live builds unless site.json publish_province_live is true.
Markup: '# ' title, '## ' sections, '- ' bullets (lead words before the first '. ' are bolded),
'[TABLE: A | B | C]' followed by 'a | b | c' rows, and '- text (https://...)' in Sources."""
import re

T = {
    "en": {
        "nav": "What the Province controls",
        "jump": "On this page",
        "desc": "What the Province of British Columbia actually controls, what belongs to Ottawa, and what belongs to cities and the Capital Regional District, in plain words.",
        "prio_line": "Who controls what?", "prio_link": "See what the Province actually controls",
        "sc_line": "Who controls what?", "sc_link": "See what the Province actually controls",
        "tables": {"whose": "Whose job is it? The problem, whose job it is, and why", "promises": "What this means for our promises"},
    },
    "fr": {
        "nav": "Ce que contrôle la Province",
        "jump": "Sur cette page",
        "desc": "Ce que la Province de la Colombie-Britannique contrôle vraiment, ce qui relève d’Ottawa, et ce qui relève des villes et du district régional de la capitale, en termes simples.",
        "fr_draft": "Traduction provisoire de l’anglais, à faire réviser par Joachim avant la mise en ligne. Le texte de référence est la version anglaise.",
        "prio_line": "Qui contrôle quoi?", "prio_link": "Voir ce que la Province contrôle vraiment",
        "sc_line": "Qui contrôle quoi?", "sc_link": "Voir ce que la Province contrôle vraiment",
        "tables": {"whose": "À qui revient la tâche? Le problème, à qui revient la tâche, et pourquoi", "promises": "Ce que cela veut dire pour nos promesses"},
    },
}
NB = "\u00a0"


def fr_space(s):
    return s.replace(" :", NB + ":").replace(" %", NB + "%").replace(" $", NB + "$").replace("« ", "«" + NB).replace(" »", NB + "»").replace(" ?", NB + "?")


def parse(md):
    title = None; intro = []; secs = []; cur = None
    lines = md.split("\n"); i = 0
    while i < len(lines):
        s = lines[i].strip(); i += 1
        if not s: continue
        if s.startswith("# "): title = s[2:]; continue
        if s.startswith("## "):
            cur = {"h": s[3:], "blocks": []}; secs.append(cur); continue
        tgt = cur["blocks"] if cur else intro
        m = re.match(r"^\[TABLE: (.+)\]$", s)
        if m:
            head = [c.strip() for c in m.group(1).split("|")]; rows = []
            while i < len(lines) and lines[i].strip():
                row = [c.strip() for c in lines[i].split(" | ")]
                if len(row) != len(head): raise SystemExit(f"province.md: table row has {len(row)} cells, expected {len(head)}: {lines[i][:80]!r}")
                rows.append(row); i += 1
            tgt.append(("table", head, rows)); continue
        if s.startswith("- "):
            if tgt and tgt[-1][0] == "ul": tgt[-1][1].append(s[2:])
            else: tgt.append(("ul", [s[2:]]))
            continue
        tgt.append(("p", s))
    if not title or not secs: raise SystemExit("province.md: title or sections missing")
    return title, intro, secs


def page(B, lang, pg, env):
    L = T[lang]; esc = B.esc
    fx = (lambda s: fr_space(s)) if lang == "fr" else (lambda s: s)
    inl = lambda s: B.inline(fx(s), {})
    title, intro, secs = parse(B.read(lang, "province"))
    def sid(h): return "pv-" + B.slugify(h)
    def block(b, sec_i, tab_n):
        if b[0] == "p": return f"<p>{inl(b[1])}</p>"
        if b[0] == "ul":
            lis = []
            for x in b[1]:
                m = re.match(r"^(.+?\.)\s(.*)$", x)
                lis.append(f"<li><strong>{inl(m.group(1))}</strong> {inl(m.group(2))}</li>" if m else f"<li>{inl(x)}</li>")
            return f'<ul class="pv-list">{"".join(lis)}</ul>'
        _, head, rows = b
        cap = L["tables"]["whose" if len(head) == 3 else "promises"]
        th = "".join(f'<th scope="col" role="columnheader">{esc(fx(h))}</th>' for h in head)
        body = []
        for r in rows:
            cells = [f'<th scope="row" role="rowheader"><span class="pv-lbl" aria-hidden="true">{esc(fx(head[0]))}</span><span class="pv-v">{inl(r[0])}</span></th>']
            cells += [f'<td role="cell"><span class="pv-lbl" aria-hidden="true">{esc(fx(head[k]))}</span><span class="pv-v">{inl(v)}</span></td>' for k, v in enumerate(r) if k]
            body.append(f'<tr role="row">{"".join(cells)}</tr>')
        return (f'<div class="pv-tablewrap"><table class="pv-table cols-{len(head)}" role="table"><caption class="vh">{esc(fx(cap))}</caption>'
                f'<thead role="rowgroup"><tr role="row">{th}</tr></thead><tbody role="rowgroup">{"".join(body)}</tbody></table></div>')
    out = []
    for n, s in enumerate(secs):
        last = n == len(secs) - 1  # the last section is Sources: its list becomes numbered links
        inner = "".join(sources(B, b[1], fx) if (last and b[0] == "ul") else block(b, n, 0) for b in s["blocks"])
        out.append(f'<section class="block pv-sec" aria-labelledby="{sid(s["h"])}"><h2 id="{sid(s["h"])}">{esc(fx(s["h"]))}</h2>{inner}</section>')
    jump = (f'<nav class="pv-jump" aria-label="{esc(L["jump"])}"><p class="pv-jump-t" aria-hidden="true">{esc(L["jump"])}</p><ul>'
            + "".join(f'<li><a href="#{sid(s["h"])}">{esc(fx(s["h"]))}</a></li>' for s in secs) + "</ul></nav>")
    fr_note = ""
    if lang == "fr" and not B.SITE.get("province_fr_reviewed"):
        fr_note = f'<p class="pv-frdraft"><mark class="todo">{esc(L["fr_draft"])}</mark></p>'
    lead = "".join(f'<p>{inl(b[1])}</p>' if b[0] == "p" else block(b, 0, 0) for b in intro)
    head = f'<div class="page-head"><div class="wrap"><h1>{esc(fx(title))}</h1></div></div>'
    body = (f'<div class="wrap content pv-wrap">{fr_note}<section class="block lead pv-intro">{lead}</section>{jump}'
            f'{"".join(out)}{B.updated_for(lang, "province")}</div>')
    extra_head = f'<link rel="stylesheet" href="/assets/css/province.css?v={B.BUILD_ID}">\n'
    return B.shell(lang, pg, f'{L["nav"]} – Joachim Agou – Victoria–Beacon Hill', L["desc"], head + body, env, extra_head=extra_head)


def sources(B, items, fx):
    lis = []
    for x in items:
        m = re.match(r"^(.*) \((https?://[^)\s]+)\)$", x)
        lis.append(f'<li><a href="{B.esc(m.group(2))}" rel="noopener">{B.esc(fx(m.group(1)))}{NB}<span aria-hidden="true">↗</span></a></li>')
    return f'<ol class="pv-sources">{"".join(lis)}</ol>'


def line(B, lang, which):
    """Reading line linking to the page: which = 'prio' (Priorities) or 'sc' (scorecard 'How this page works')."""
    L = T[lang]
    return (f'<p class="pv-link pv-link-{which}">{B.esc(L[which + "_line"])} <a href="{B.url(lang, "province")}">{B.esc(L[which + "_link"])}'
            f'{NB}<span aria-hidden="true">→</span></a></p>')
