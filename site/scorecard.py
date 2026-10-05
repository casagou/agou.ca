"""Scorecard page (/scorecard/, /fr/scorecard/), called from build.py.

Text: content/<lang>/scorecard.md holds Joachim's public scorecard text word for word (EN), or the draft FR translation.
Summary cards, source links and fact-check flags: scorecard.json. Interface wording: T below.
The page is left out of live builds unless site.json "publish_scorecard_live" is true (see README "Scorecard")."""
import json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent
SC = json.loads((ROOT / "scorecard.json").read_text())
NB = "\u00a0"

T = {
    "en": {
        "title": "Scorecard",
        "kicker": "Victoria–Beacon Hill · 12 numbers, every quarter",
        "last_pub": "Last published:", "last_pub_none": "—",
        "baseline": "Baseline:", "baseline_next": "First quarterly report after the election.",
        "next_due": "Next update due within 30 days of quarter-end.",
        "votes_note": "How I voted: printed beside every line once there are votes to report.",
        "promises_h": "Two promises, checked every three months",
        "promise": "Promise", "target": "Target", "coming": "Coming",
        "card_h": "The report card",
        "card_intro": "Tap a line for the full target, today’s number, the source and my lever.",
        "legend_promise": "I control it, so I promise it.", "legend_target": "A target, and the lever I have to move it.",
        "how_h": "How this page works",
        "details_h": "The 12 lines in full",
        "rows": {"target": "Target", "promise": "Promise", "today": "Today", "source": "Source & cadence", "standin": "Quarterly stand-in", "lever": "My lever", "vote": "How I voted"},
        "vote_row": "Printed here, beside this line, once there are votes to report.",
        "asof": "As of", "sources": "Sources for today’s number", "source": "Source",
        "no_source": "No public source yet: that is the point of this line.",
        "back": "Back to the report card",
        "cad": {"annual": "Annual", "quarterly": "Quarterly", "annual_standin": "Annual + quarterly stand-in", "pit_standin": "Every 1–3 years + quarterly stand-in",
                "monthly": "Quarterly (monthly data)", "quarterly_foi": "Quarterly (FOI if needed)", "none_yet": "Quarterly, once a source exists"},
        "factcheck": "Fact-check (review before this page goes live):",
        "desc": "Joachim Agou’s scorecard for Victoria–Beacon Hill: 12 numbers published every quarter, with sources, as-of dates and how he voted.",
        "priorities_link": "See the scorecard", "priorities_sub": "12 numbers, published every quarter, with sources.",
        "home_link": "See the scorecard",
        "jump": "Jump to", "jump_promises": "The two promises",
        "prio_lead": "I’ll report on these every quarter.", "prio_link": "See the scorecard",
        "rel": "Tracked on the scorecard:", "prio": "Priority", "from": "From my priorities:",
    },
    "fr": {
        "title": "Bulletin",
        "kicker": "Victoria–Beacon Hill · 12 chiffres, chaque trimestre",
        "last_pub": "Dernière publication :", "last_pub_none": "—",
        "baseline": "Point de départ :", "baseline_next": "Premier bilan trimestriel après l’élection.",
        "next_due": "Prochaine mise à jour dans les 30 jours suivant la fin du trimestre.",
        "votes_note": "Comment j’ai voté : indiqué à côté de chaque ligne dès qu’il y aura des votes à rapporter.",
        "promises_h": "Deux promesses, vérifiées tous les trois mois",
        "promise": "Promesse", "target": "Cible", "coming": "À venir",
        "card_h": "Le bulletin",
        "card_intro": "Touchez une ligne pour voir la cible complète, le chiffre d’aujourd’hui, la source et mon levier.",
        "legend_promise": "Je le contrôle, donc je le promets.", "legend_target": "Une cible, et le levier dont je dispose pour la faire bouger.",
        "how_h": "Comment fonctionne cette page",
        "details_h": "Les 12 lignes en détail",
        "rows": {"target": "Cible", "promise": "Promesse", "today": "Aujourd’hui", "source": "Source et fréquence", "standin": "Indicateur trimestriel", "lever": "Mon levier", "vote": "Comment j’ai voté"},
        "vote_row": "Indiqué ici, à côté de cette ligne, dès qu’il y aura des votes à rapporter.",
        "asof": "En date de", "sources": "Sources du chiffre d’aujourd’hui", "source": "Source",
        "no_source": "Aucune source publique pour l’instant : c’est justement l’objet de cette ligne.",
        "back": "Retour au bulletin",
        "cad": {"annual": "Annuel", "quarterly": "Trimestriel", "annual_standin": "Annuel + indicateur trimestriel", "pit_standin": "Tous les 1 à 3 ans + indicateur trimestriel",
                "monthly": "Trimestriel (données mensuelles)", "quarterly_foi": "Trimestriel (accès à l’information au besoin)", "none_yet": "Trimestriel, dès qu’une source existe"},
        "factcheck": "Vérification des faits (à revoir avant la mise en ligne) :",
        "fr_draft": "Traduction provisoire de l’anglais, à faire réviser par Joachim avant la mise en ligne. Le texte de référence est la version anglaise.",
        "desc": "Le bulletin de Joachim Agou pour Victoria–Beacon Hill : 12 chiffres publiés chaque trimestre, avec leurs sources, leurs dates et ses votes.",
        "priorities_link": "Voir le bulletin", "priorities_sub": "12 chiffres, publiés chaque trimestre, avec leurs sources.",
        "home_link": "Voir le bulletin",
        "jump": "Aller à", "jump_promises": "Les deux promesses",
        "prio_lead": "Je rendrai compte de ces priorités chaque trimestre.", "prio_link": "Voir le bulletin",
        "rel": "Suivi dans le bulletin :", "prio": "Priorité", "from": "Tiré de mes priorités :",
    },
}

# scorecard line -> the Priorities section it reports on ("1"-"4" = the numbered priorities; "report" = "How I'll report to you")
PRIORITY = {"8": "1", "9": "1", "10": "1", "3": "2", "4": "2", "1": "3", "2": "3", "5": "4", "6": "4", "7": "4", "12": "4", "11": "report"}


def priority_heads(B, lang):
    """Priorities page headings -> {"1": (id, title), ..., "report": (id, title)} (ids as build.py makes them)."""
    heads = [l[3:].strip() for l in B.read(lang, "priorities").split("\n") if l.startswith("## ")]
    out = {}
    for h in heads:
        m = re.match(r"^(\d)\.\s", h)
        if m: out[m.group(1)] = (B.slugify(h.replace("*", "")), h)
    out["report"] = (B.slugify(heads[-1].replace("*", "")), heads[-1])
    return out


LABELS = {  # row label in content/<lang>/scorecard.md -> row key
    "Target": "target", "Today": "today", "Source / cadence": "source", "Quarterly stand-in": "standin", "My lever": "lever",
    "Cible": "target", "Aujourd’hui": "today", "Source / fréquence": "source", "Indicateur trimestriel": "standin", "Mon levier": "lever",
}


def fr_space(s):
    s = s.replace(" :", NB + ":").replace(" %", NB + "%").replace(" $", NB + "$").replace("« ", "«" + NB).replace(" »", NB + "»")
    return re.sub(r"(\d) (\d{3})(?!\d)", lambda m: m.group(1) + NB + m.group(2), s)


def asof_label(L, v, lang):
    """'As of <date>'. French needs the right preposition (French review, 1 Oct 2026): « Pour l’année d’imposition 2026 »,
    « En date des 25 et 26 mars 2025 », « En date d’octobre 2025 », « En date de mars 2026 ». English: unchanged."""
    if lang != "fr": return f'{L["asof"]} {v}'
    if v.startswith("année"): return "Pour l’" + v
    if re.match(r"\d+ et \d+ ", v): return "En date des " + v
    if re.match(r"[aeiouyéèêàâîôûhAEIOUYÉ]", v): return "En date d’" + v
    return f'{L["asof"]} {v}'


def tx(d, lang):
    s = d[lang]
    return fr_space(s) if lang == "fr" else s


def parse(md):
    """content/<lang>/scorecard.md -> intro paragraphs, promises heading, promises, items."""
    lines = [l.rstrip() for l in md.split("\n")]
    blocks = []  # (kind, text)
    for l in lines:
        s = l.strip()
        if not s or s == "---": continue
        blocks.append(s)
    how_h = blocks[0].strip("*")
    i = 1; how = []
    while not re.match(r"^\*\*[^*]+\*\*$", blocks[i]): how.append(blocks[i]); i += 1
    prom_h = blocks[i].strip("*"); i += 1
    promises = []
    while re.match(r"^\d\. ", blocks[i]):
        m = re.match(r"^\d\. \*\*(.+?)\*\*\s*(.*)$", blocks[i]); promises.append((m.group(1), m.group(2))); i += 1
    items = []
    for s in blocks[i:]:
        m = re.match(r"^\*\*(\d+)\. (.+)\*\*$", s)
        if m:
            items.append({"n": m.group(1), "title": m.group(2), "rows": []}); continue
        m = re.match(r"^\*\*([^*]+?)\s?:\*\*\s*(.*)$", s)
        if m and m.group(1) in LABELS:
            items[-1]["rows"].append((LABELS[m.group(1)], m.group(2))); continue
        m = re.match(r"^\*\*(Promise|Promesse) — (.+?)\*\*\s*(.*)$", s)
        if m:
            items[-1]["rows"].append(("promise", m.group(2)[0].upper() + m.group(2)[1:] + " " + m.group(3))); continue
        raise SystemExit(f"scorecard.md: cannot place this line: {s[:80]!r}")
    if len(items) != 12: raise SystemExit(f"scorecard.md: expected 12 items, found {len(items)}")
    return how_h, how, prom_h, promises, items


def chip(kind, lang, extra=""):
    return f'<span class="chip chip-{kind}{extra}">{T[lang][kind]}</span>'


def src_links(B, meta, lang, cls="sc-srcs"):
    if not meta["sources"]:
        return f'<p class="{cls} none">{B.esc(T[lang]["no_source"])}</p>'
    lis = "".join(f'<li><a href="{B.esc(s["url"])}" rel="noopener">{B.esc(tx(s, lang))} <span aria-hidden="true">↗</span></a></li>' for s in meta["sources"])
    return f'<div class="{cls}"><p class="sc-srcs-h">{B.esc(T[lang]["sources"])}</p><ul>{lis}</ul></div>'


def scorecard_page(B, lang, page, env):
    L = T[lang]; esc = B.esc; inl = lambda t: B.inline(t, {})
    md = B.read(lang, "scorecard")
    how_h, how, prom_h, promises, items = parse(md)
    meta = SC["items"]
    # status strip
    lp = SC.get("last_published")
    if lp:
        first = f'<strong>{esc(L["last_pub"])}</strong> {esc(lp)}'
    else:  # nothing published yet: show the baseline date (scorecard.json "baseline") instead of "Last published: —"
        y, m, d = map(int, SC["baseline"].split("-"))
        first = f'<strong>{esc(tx({lang: L["baseline"]}, lang))}</strong> <time datetime="{SC["baseline"]}">{"1er" if lang == "fr" and d == 1 else d} {B.MONTHS[lang][m - 1]} {y}</time>. {esc(L["baseline_next"])}'
    status = (f'<div class="sc-status" role="note"><p>{first} · {esc(L["next_due"])}</p>'
              f'<p class="sc-votes">{chip("coming", lang)} {esc(L["votes_note"])}</p></div>')
    fr_note = ""
    if lang == "fr" and not SC.get("fr_reviewed"):
        fr_note = f'<p class="sc-frdraft"><mark class="todo">{esc(L["fr_draft"])}</mark></p>'
    head = (f'<div class="page-head sc-head"><div class="wrap"><p class="sc-kicker">{esc(L["kicker"])}</p><h1>{esc(L["title"])}</h1><p class="lockup">{esc(B.UI[lang]["lockup"])}</p>{status}</div></div>')
    # promises
    pr = "".join(f'<li class="sc-promise"><p class="sc-pnum">{chip("promise", lang)} <span class="sc-pn">{n}</span></p>'
                 f'<p class="sc-plead">{inl(lead)}</p><p>{inl(rest)}</p></li>' for n, (lead, rest) in enumerate(promises, 1))
    promises_html = f'<section class="sc-promises" aria-labelledby="promises"><h2 id="promises">{esc(prom_h)}</h2><ol class="sc-plist">{pr}</ol></section>'
    # report card
    cards = []
    for it in items:
        m = meta[it["n"]]; st = m["status"]
        src = m["sources"][0] if m["sources"] else None
        srca = (f'<a class="sc-csrc" href="{esc(src["url"])}" rel="noopener" aria-label="{esc(L["source"])}: {esc(tx(src, lang))}">{esc(L["source"])} <span aria-hidden="true">↗</span></a>'
                if src else "")
        flag = ' <span class="sc-flag" title="fact-check">!</span>' if m.get("factcheck") else ""
        cards.append(f'<li class="sc-card is-{st}"><div class="sc-ctop"><span class="sc-num" aria-hidden="true">{it["n"]}</span>{chip(st, lang)}{flag}</div>'
                     f'<h3 class="sc-ctitle"><a class="sc-link" href="#item-{it["n"]}"><span class="vh">{it["n"]}. </span>{esc(tx(m["short"], lang))}</a></h3>'
                     f'<p class="sc-fig">{esc(tx(m["fig"], lang))}</p><p class="sc-figlabel">{esc(tx(m["figlabel"], lang))}</p>'
                     f'<div class="sc-cfoot"><span class="sc-cad">{esc(L["cad"][m["cadence"]])}</span>{srca}</div></li>')
    legend = (f'<p class="sc-legend"><span>{chip("promise", lang)} {esc(L["legend_promise"])}</span> <span>{chip("target", lang)} {esc(L["legend_target"])}</span></p>')
    grid = (f'<section class="sc-report" id="report-card" aria-labelledby="rc-h"><h2 id="rc-h">{esc(L["card_h"])}</h2>'
            f'<p class="sc-intro">{esc(L["card_intro"])}</p>{legend}<ol class="sc-grid">{"".join(cards)}</ol></section>')
    how_html = (f'<section class="block sc-how" aria-labelledby="how"><h2 id="how">{esc(how_h)}</h2>' + "".join(f"<p>{inl(p)}</p>" for p in how)
                + (B.province.line(B, lang, "sc") if "province" not in B.HIDDEN else "") + "</section>")
    # details: each line links back to the priority it reports on
    PH = priority_heads(B, lang)
    def prio_link(n):
        k = PRIORITY.get(n)
        if not k or k not in PH: return ""
        hid, ht = PH[k]
        label = f'{L["prio"]} {ht}' if k != "report" else ht
        label = re.sub(r"^(\S+) (\d)\. ", r"\1 \2 : " if lang == "fr" else r"\1 \2: ", label)
        return f'<p class="sc-prio"><a href="{B.url(lang, "priorities")}#{hid}">{esc(label)} <span aria-hidden="true">→</span></a></p>'
    det = []
    for it in items:
        m = meta[it["n"]]; st = m["status"]
        asof = f'<span class="sc-asof">{esc(asof_label(L, tx(m["asof"], lang), lang))}</span>' if m.get("asof") else ""
        rows = []
        for k, v in it["rows"]:
            extra = src_links(B, m, lang) if k == "today" else ""
            rows.append(f'<div class="sc-row r-{k}"><dt>{esc(L["rows"][k])}</dt><dd><p>{inl(v)}</p>{extra}</dd></div>')
        rows.append(f'<div class="sc-row r-vote"><dt>{esc(L["rows"]["vote"])}</dt><dd><p>{chip("coming", lang)} {esc(L["vote_row"])}</p></dd></div>')
        fc = f'<p class="sc-fc"><mark class="todo" lang="en"><strong>{esc(T["en"]["factcheck"])}</strong> {esc(m["factcheck"])}</mark></p>' if m.get("factcheck") else ""
        det.append(f'<article class="sc-item is-{st}" id="item-{it["n"]}" aria-labelledby="item-{it["n"]}-h" tabindex="-1">'
                   f'<header class="sc-ihead"><span class="sc-num big" aria-hidden="true">{it["n"]}</span><div><h3 id="item-{it["n"]}-h"><span class="vh">{it["n"]}. </span>{inl(it["title"])}</h3>'
                   f'<p class="sc-meta">{chip(st, lang)} <span class="sc-cad">{esc(L["cad"][m["cadence"]])}</span>{"<span class=\"sc-asofw\">·" + NB + asof + "</span>" if asof else ""}</p></div></header>'
                   f'<dl class="sc-rows">{"".join(rows)}</dl>{fc}'
                   f'{prio_link(it["n"])}'
                   f'<p class="sc-back"><a href="#report-card">{esc(L["back"])} <span aria-hidden="true">↑</span></a></p></article>')
    details = f'<section class="sc-details" aria-labelledby="det-h"><h2 id="det-h">{esc(L["details_h"])}</h2>{"".join(det)}</section>'
    jl = ([("promises", L["jump_promises"], "")] + [("how", how_h, "")]
          + [(f"item-{it['n']}", tx(meta[it["n"]]["short"], lang), it["n"]) for it in items])
    jump = (f'<nav class="sc-jump" aria-label="{esc(L["jump"])}"><p class="sc-jump-t" aria-hidden="true">{esc(L["jump"])}</p><ul>'
            + "".join(f'<li><a href="#{h}">{f"<span class=\"sc-jn\">{n}</span> " if n else ""}{esc(t_)}</a></li>' for h, t_, n in jl) + "</ul></nav>")
    body = (f'<div class="wrap sc-wrap sc-layout">{jump}<div class="sc-main">{fr_note}{promises_html}{grid}{how_html}{details}'
            f'{B.updated_for(lang, "scorecard")}</div></div>')
    extra_head = f'<link rel="stylesheet" href="/assets/css/scorecard.css?v={B.BUILD_ID}">\n'
    title = f'{L["title"]} – Joachim Agou – Victoria–Beacon Hill'
    return B.shell(lang, page, title, L["desc"], head + body, env, extra_head=extra_head)


def priorities_link(B, lang):
    """Top of /priorities/: one reading line (no extra button)."""
    L = T[lang]
    return (f'<p class="sc-prio-lead">{B.esc(L["prio_lead"])} <a href="{B.url(lang, "scorecard")}">{B.esc(L["prio_link"])}'
            f'{chr(160)}<span aria-hidden="true">→</span></a></p>')


def priorities_related(B, lang, body):
    """In each Priorities section, a text link to its scorecard lines (inverse of PRIORITY)."""
    L = T[lang]; PH = priority_heads(B, lang); meta = SC["items"]
    for k, (hid, _) in PH.items():
        ns = sorted((n for n, p in PRIORITY.items() if p == k), key=int)
        if not ns: continue
        start = body.find(f'<section class="block" aria-labelledby="{hid}">')
        if start < 0: raise SystemExit(f"priorities: section {hid!r} not found (needed for scorecard links)")
        end = body.index("</section>", start)
        links = " · ".join(f'<a href="{B.url(lang, "scorecard")}#item-{n}">{n}. {B.esc(tx(meta[n]["short"], lang))}</a>' for n in ns)
        body = body[:end] + f'<p class="sc-rel"><span class="sc-rel-t">{B.esc(L["rel"])}</span> {links}</p>' + body[end:]
    return body


def home_link(B, lang):
    return f'<p class="pagelink sc-home"><a href="{B.url(lang, "scorecard")}">{B.esc(T[lang]["home_link"])} <span aria-hidden="true">→</span></a></p>'
