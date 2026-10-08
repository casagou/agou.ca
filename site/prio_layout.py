"""Priorities: summary-first layout ("v2", 7 Oct 2026; Joachim approved building it on STAGING ONLY, 9:48 PM PT).
Live builds keep the current layout while site.json priorities_layout_v2_live is false.

Presentation only: every sentence and link of the page stays on it (build.py runs a coverage check against the
classic layout and stops if anything is missing). What changes:
  - an 'At a glance' box at the top (each section's 'What changes for you', first clause, verbatim) and a sticky section bar;
  - each section starts with its 'What changes for you' box, right under the heading;
  - each promise becomes a card: H3 title (the bold lead, or the bullet's own opening words), a 'For you' line
    (data/priorities-for-you.json, DRAFT wording), its source labels, then the full text; long texts sit in
    <details> 'Details and sources' (open for deep links, for print and for Ctrl/Cmd+F);
  - source parentheticals are set quieter (smaller, grey); long paragraphs are split at sentence ends;
  - the 'Read more' region becomes a <details>; 'Back to the summary' at the end of each section.
Assets: assets/css/prio2.css, assets/js/prio2.js (removed from live builds while the flag is false)."""
import html as H, json, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
EN_ORDER = ["how-i-work", "1-health-care-you-can-get", "2-homes-people-can-afford", "3-cost-of-living", "4-a-downtown-that-works",
            "transport-and-bc-ferries", "responsible-spending", "also-for-this-riding", "how-ill-report-to-you"]
CARDS = EN_ORDER[1:8]          # sections whose first list becomes promise cards
VISIBLE_MAX = 30               # body of at most this many words (EN) stays visible; longer goes into <details>
SPLIT_MIN = 70                 # card bodies longer than this are split into paragraphs
SPLIT_P_MIN = 110              # 'Read more' paragraphs longer than this too

T = {
    "en": {"glance_h": "At a glance: what changes for you", "for_you": "For you:",
           "glance_note": "Each promise below says what it means for you. “Details and sources” opens the full text, figures and links. Each one is labelled: my position, party commitment or 2024 platform.",
           "also": "Also on this page:", "open_all": "Open all details", "close_all": "Close all details",
           "details": "Details and sources", "details_nolink": "Details", "deep": "Background: why, how and what it costs",
           "deep_nocost": "Background and figures", "totop": "Back to the summary", "nav": "Sections of this page", "top": "Summary",
           "in_practice": "In practice", "chips": {"mine": "My position", "party": "Party commitment", "plat": "2024 platform"},
           "hiw_intro": "I'm an engineer: I start with the problem, measure it, fix it and report the result. Each promise is labelled with where it comes from:",
           "legend": {"mine": "mine; I'll advocate for it within the party.", "party": "announced by the party during this campaign, with a link to the announcement.",
                      "plat": "from the party's October 2024 platform, not yet confirmed for this election."},
           "hiw_more": "More about how I work and the sources",
           "short": ["Health", "Homes", "Cost of living", "Downtown", "Ferries", "Spending", "This riding", "Reporting"]},
    "fr": {"glance_h": "En bref : ce qui change pour vous", "for_you": "Pour vous :",
           "glance_note": "Chaque engagement ci-dessous dit ce qu'il change pour vous. « Détails et sources » affiche le texte complet, les chiffres et les liens. Chacun porte sa provenance : ma position, engagement du parti ou programme 2024.",
           "also": "Aussi sur cette page :", "open_all": "Ouvrir tous les détails", "close_all": "Fermer tous les détails",
           "details": "Détails et sources", "details_nolink": "Détails", "deep": "Contexte : pourquoi, comment et à quel coût",
           "deep_nocost": "Contexte et chiffres", "totop": "Retour au résumé", "nav": "Sections de cette page", "top": "Résumé",
           "in_practice": "Concrètement", "chips": {"mine": "Ma position", "party": "Engagement du parti", "plat": "Programme 2024"},
           "hiw_intro": "Je suis ingénieur : je pars du problème, j'en évalue l'ampleur, j'y apporte une solution et je rends compte du résultat. Chaque engagement porte sa provenance :",
           "legend": {"mine": "la mienne; je la défendrai au sein du parti.", "party": "annoncé par le parti pendant cette campagne, avec un lien vers l'annonce.",
                      "plat": "tiré du programme d'octobre 2024 du parti, pas encore confirmé pour cette élection."},
           "hiw_more": "En savoir plus sur ma façon de travailler et les sources",
           "short": ["Santé", "Logement", "Coût de la vie", "Centre-ville", "Traversiers", "Dépenses", "Circonscription", "Bilans"]},
}
CHIP_RE = {"mine": r"\bmy position\b|\bma position\b",
           "party": r"\bparty commitment\b|\bthe party (?:has committed|made the same pledge)|\bengagement du parti\b|\ble parti (?:s'est engagé|a pris le même engagement)",
           "plat": r"\b2024 party platform\b|\bprogramme 2024 du parti\b"}

DATA_OVERRIDE = None          # no_party.py: the no-party version of data/priorities-for-you.json
LEGEND = ("mine", "party", "plat")  # chips listed in the How I work legend (no_party.py: mine only)

VOID = {"img", "source", "br", "hr", "meta", "link", "input", "wbr"}
TAG = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)\b[^>]*?(/?)>")


def children(s):
    """Top-level nodes of an HTML fragment: element strings and non-empty text runs, in order."""
    out, depth, start, pos = [], 0, 0, 0
    for m in TAG.finditer(s):
        close, name, selfc = m.group(1), m.group(2).lower(), m.group(3)
        if depth == 0 and m.start() > pos and s[pos:m.start()].strip():
            out.append(s[pos:m.start()])
        if depth == 0 and not close: start = m.start()
        if name in VOID or selfc:
            if depth == 0: out.append(s[m.start():m.end()]); pos = m.end()
            continue
        depth += -1 if close else 1
        if depth < 0: raise ValueError(f"prio_layout: unbalanced HTML near {s[max(0, m.start() - 60):m.end()]!r}")
        if depth == 0 and close: out.append(s[start:m.end()]); pos = m.end()
        elif depth == 1 and not close: pos = m.start()
    if depth: raise ValueError("prio_layout: unclosed element")
    if s[pos:].strip(): out.append(s[pos:])
    return [c.strip("\n") for c in out]


def inner(el):
    return el[el.index(">") + 1: el.rindex("<")]


def text(h):
    return re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", h))).strip()


def words(h):
    return len(text(h).split())


def scan(h):
    """Yield (index, char, paren_depth, in_tag, in_a) over an HTML string."""
    depth = 0; in_a = 0; i = 0
    while i < len(h):
        if h[i] == "<":
            j = h.index(">", i)
            t = h[i:j + 1].lower()
            if t.startswith("<a ") or t == "<a>": in_a += 1
            elif t.startswith("</a"): in_a -= 1
            yield i, "<", depth, True, in_a; i = j + 1; continue
        c = h[i]
        if c == "(": depth += 1
        yield i, c, depth, False, in_a
        if c == ")" and depth: depth -= 1
        i += 1


def balanced(h):
    d = 0
    for m in TAG.finditer(h):
        if m.group(2).lower() in VOID or m.group(3): continue
        d += -1 if m.group(1) else 1
        if d < 0: return False
    return d == 0


def quiet(h):
    """Wrap top-level source parentheticals (with a link, or a 'my position' / party / platform / scorecard label) in span.cite."""
    spans, start = [], None
    for i, c, d, tag, _ in scan(h):
        if tag: continue
        if c == "(" and d == 1: start = i
        elif c == ")" and d == 1 and start is not None:
            seg = h[start:i + 1]
            if balanced(seg) and ("<a " in seg or re.search(CHIP_RE["mine"] + "|" + CHIP_RE["party"] + "|" + CHIP_RE["plat"] + r"|scorecard (?:line|promise)|du bulletin|Safe Streets for BC|Island Health, m|en anglais", text(seg), re.I)):
                spans.append((start, i + 1))
            start = None
    for a, b in reversed(spans):
        h = h[:a] + '<span class="cite">' + h[a:b] + "</span>" + h[b:]
    return h


ABBR = re.compile(r"(?:\b(?:[A-Z]\.){2,}|C\.-B\.|\bp\.|\bpp\.|\bvs\.|\bno\.|\bSt\.|\bMr\.|\bDr\.)$")


def sentences(h):
    """Split an inline-HTML run at sentence ends (outside tags, links and parentheses)."""
    cuts = []
    for i, c, d, tag, in_a in scan(h):
        if tag or d or in_a or c not in ".!?;": continue
        rest = h[i + 1:]
        m = re.match(r"(\s+|\s*</(?:strong|em)>\s+)(?=[A-ZÀ-ÖØ-Þ«\"“0-9<])", rest)
        if not m or c == ";": continue
        if ABBR.search(text(h[:i + 1])[-8:]): continue
        if re.match(r"\s+\d", rest) and re.search(r"\bp\.$", h[:i + 1]): continue
        cuts.append(i + 1 + len(m.group(1)))
    parts, prev = [], 0
    for c in cuts:
        parts.append(h[prev:c].rstrip()); prev = c
    parts.append(h[prev:])
    return [p for p in parts if p.strip()]


def paras(h, min_words):
    """Group sentences into paragraphs of about 40-70 words (text unchanged)."""
    if words(h) <= min_words: return [h]
    out, cur = [], []
    for s in sentences(h):
        cur.append(s)
        if words(" ".join(cur)) >= 40: out.append(" ".join(cur)); cur = []
    if cur:
        if out and words(" ".join(cur)) < 18: out[-1] += " " + " ".join(cur)
        else: out.append(" ".join(cur))
    return out


def split_title(li):
    """(title_html, body_html, how) for a promise bullet."""
    m = re.match(r"\s*<strong>(.*?)</strong>\s*", li, re.S)
    if m and balanced(m.group(1)):
        t = re.sub(r"(?:\s|&nbsp;|\u00a0)*[:.]\s*$", "", m.group(1))
        return t, li[m.end():], "lead"
    first = {}
    for i, c, d, tag, in_a in scan(li):
        if tag or in_a: continue
        if c == ":" and d == 0 and ":" not in first and words(li[:i]) <= 12: first[":"] = i
        if c == "(" and d == 1 and "(" not in first: first["("] = i
    if not first: return li, "", "whole"
    k = min(first, key=first.get); i = first[k]
    t = re.sub(r"[\s,\u00a0]+$", "", li[:i]).replace("&nbsp;", "").rstrip()
    body = li[i + 1:].lstrip() if k == ":" else li[i:]
    return t, body, k


def chips(lang, h):
    tx = text(h)
    return [k for k in ("mine", "party", "plat") if re.search(CHIP_RE[k], tx, re.I)]


def transform(body, lang, slugify, flags):
    """body: the classic Priorities body (after collapse(), scorecard and photo strips). Returns the v2 body."""
    U = T[lang]; DATA = DATA_OVERRIDE or json.loads((ROOT / "data/priorities-for-you.json").read_text()); FY = DATA[lang]
    SHORT = DATA.get("short_titles", {}).get(lang, {})
    secs = list(re.finditer(r'<section class="block" aria-labelledby="([^"]+)">(.*?)</section>', body, re.S))
    if len(secs) != len(EN_ORDER): raise SystemExit(f"prio_layout ({lang}): expected {len(EN_ORDER)} sections, found {len(secs)} (Notion headings changed?)")
    ids = [m.group(1) for m in secs]
    if lang == "en" and ids != EN_ORDER: raise SystemExit(f"prio_layout: EN section ids changed: {ids}")
    used = set(re.findall(r'\bid="([^"]+)"', body)); vis_decisions = flags.setdefault("visible", {})
    glance, new_secs = [], []
    for n, (m, en_id) in enumerate(zip(secs, EN_ORDER)):
        sid, kids = m.group(1), children(m.group(2))
        if en_id == "how-i-work":  # the old 'On this page' list moves to the At a glance box and the section bar
            k = next(i for i, c in enumerate(kids) if c.startswith('<nav class="toc"'))
            if text(kids[k - 1]) not in ("On this page", "Sur cette page"): raise SystemExit("prio_layout: 'On this page' label not found")
            toc_links = re.findall(r'<a href="(#[^"]+)">(.*?)</a>', kids[k]); del kids[k - 1:k + 1]
            head = [c for c in kids if c.startswith("<h2") or c.startswith('<span id="')]; more = [c for c in kids if c not in head]
            leg = "".join(f'<li><span class="chip chip-{c}">{U["chips"][c]}</span> {U["legend"][c]}</li>' for c in LEGEND)
            new_secs.append(f'<section class="block hiw" aria-labelledby="{sid}">' + "\n".join(head)
                            + f'<p class="hiw-intro">{U["hiw_intro"]}</p><ul class="hiw-legend">{leg}</ul>'
                            + f'<details class="pc-det hiw-more"><summary>{U["hiw_more"]}</summary><div class="pc-dbody">' + "\n".join(more) + "</div></details></section>"); continue
        h2 = next(c for c in kids if c.startswith("<h2"))
        title_txt = text(h2)
        out = []; pre = []; wcfy = None; practice = None; cards_html = ""; rest = []; deep = None; tail = []
        i = 0
        while i < len(kids):
            c = kids[i]
            if c.startswith("<h2") or c.startswith('<span id="') or c.startswith('<figure'): pre.append(c)
            elif c.startswith("<ul") and en_id in CARDS and not cards_html:
                lis = [inner(x) for x in children(inner(c)) if x.startswith("<li")]
                lines = FY.get(en_id)
                if lines is None or len(lines) != len(lis):
                    raise SystemExit(f"prio_layout ({lang}): {sid}: {len(lis)} promises but {0 if lines is None else len(lines)} 'For you' lines in data/priorities-for-you.json")
                cl = []
                for j, (li, fy) in enumerate(zip(lis, lines)):
                    t, b, how = split_title(li)
                    st = SHORT.get(en_id, {}).get(str(j + 1))
                    pid = slugify(text(t)); pid = (pid if len(pid) <= 48 else pid[:49].rsplit("-", 1)[0]).strip("-") or f"{sid}-{j + 1}"  # whole words, at most 48 characters
                    while pid in used: pid += "-2"
                    used.add(pid)
                    if st: t, b = H.escape(st, quote=False), li  # short heading; the whole original bullet stays as the card text
                    key = f"{en_id}/{j}"
                    if lang == "en": vis_decisions[key] = words(b) <= VISIBLE_MAX
                    vis = vis_decisions.get(key, words(b) <= VISIBLE_MAX)
                    ch = "".join(f'<span class="chip chip-{k}">{U["chips"][k]}</span>' for k in chips(lang, li))
                    card = (f'<article class="pc" id="{pid}"><h3 class="pc-h">{t}</h3>'
                            f'<p class="pc-you"><strong>{U["for_you"]}</strong> {H.escape(fy, quote=False)}'
                            + (f' <span class="pc-tags">{ch}</span>' if ch else "") + "</p>")
                    if b.strip() and vis:
                        card += f'<p class="pc-body">{quiet(b)}</p>'
                    elif b.strip():
                        nl = len(re.findall(r"<a ", b))
                        lab = f'{U["details"]} ({nl})' if nl else U["details_nolink"]
                        ps = "".join(f"<p>{quiet(p)}</p>" for p in paras(b, SPLIT_MIN))
                        card += f'<details class="pc-det"><summary>{lab}</summary><div class="pc-dbody">{ps}</div></details>'
                    cl.append(card + "</article>")
                cards_html = '<div class="pcards">' + "\n".join(cl) + "</div>"
            elif c.startswith("<p>") and re.match(r"<p><strong>(What changes for you|Ce qui change pour vous)", c):
                wcfy = c
                if i + 1 < len(kids) and kids[i + 1].startswith("<ul") and re.search(r"(In practice|Concrètement)\s*:\s*</p>$", c):
                    practice = kids[i + 1]; i += 1
            elif c.startswith('<div class="rm-more"'):
                deep = c
            elif c.startswith('<p class="rm">'): pass
            elif c.startswith('<p class="sc-rel"'): tail.append(c)
            elif c.startswith("<ul") and en_id not in CARDS: rest.append(c)
            else: rest.append(c)
            i += 1
        box = ""
        if wcfy:
            w = wcfy
            if practice:
                m_ = re.search(r"\s*(In practice|Concrètement)\s*:\s*</p>$", w); w = w[:m_.start()] + "</p>"
                box_p = (f'<details class="pc-det pc-practice"><summary>{m_.group(1)} ({len(children(inner(practice)))})</summary>'
                         f'<div class="pc-dbody">{practice}</div></details>')
            else: box_p = ""
            box = f'<div class="wcfy">{quiet(w)}{box_p}</div>'
            first = re.sub(r"^(What changes for you|Ce qui change pour vous)\s*:\s*", "", text(w))
            cut = [p for p in (first.find("; "), first.find(". ")) if p > 0]
            first = first[:min(cut)] + "." if cut else first
            glance.append((sid, title_txt, first))
        else:
            glance.append((sid, title_txt, None))
        h2s = [p for p in pre if p.startswith("<h2") or p.startswith('<span id="')]; figs = [p for p in pre if p.startswith("<figure")]
        dd = ""
        if deep:
            did = re.match(r'<div class="rm-more" id="([^"]+)">', deep).group(1)
            dk = []
            for p in children(inner(deep)):
                if p.startswith("<p>") and words(p) > SPLIT_P_MIN:
                    dk += [f"<p>{quiet(x)}</p>" for x in paras(inner(p), SPLIT_P_MIN)]
                else: dk.append(quiet(p))
            lab = U["deep"] if re.search(r"\b(Cost|cost|Coût|coût)\b", text(deep)) else U["deep_nocost"]
            dd = f'<details class="pc-deep" id="{did}"><summary>{lab}</summary><div class="pc-dbody">' + "\n".join(dk) + "</div></details>"
        totop = f'<p class="totop"><a href="#glance">{U["totop"]} <span aria-hidden="true">↑</span></a></p>'
        parts = h2s + ([box] if box else []) + figs + ([cards_html] if cards_html else []) + [quiet(r) for r in rest] + ([dd] if dd else []) + tail + [totop]
        new_secs.append(f'<section class="block" aria-labelledby="{sid}">' + "\n".join(parts) + "</section>")
    # At a glance + section bar
    gl = "".join(f'<li><a href="#{sid}"><strong>{H.escape(t)}</strong></a> <span class="g-sum">{H.escape(s)}</span></li>' for sid, t, s in glance if s)
    other = " · ".join(f'<a href="#{sid}">{H.escape(t)}</a>' for sid, t, s in glance if not s)
    gbox = (f'<section class="glance" id="glance" aria-labelledby="glance-h"><h2 id="glance-h">{U["glance_h"]}</h2><ul>{gl}</ul>'
            f'<p class="g-also">{U["also"]} {other}</p><p class="g-note">{U["glance_note"]}</p>'
            f'<p class="g-tools"><button type="button" class="p2-all" data-open="{U["open_all"]}" data-close="{U["close_all"]}" hidden>{U["open_all"]}</button></p></section>')
    nav_ids = [sid for sid, _, _ in glance]
    if len(nav_ids) != len(U["short"]): raise SystemExit("prio_layout: section bar labels don't match the sections")
    if sorted(h for h, _ in toc_links) != sorted("#" + s for s in nav_ids): raise SystemExit("prio_layout: the old 'On this page' links don't match the sections")
    bar = (f'<nav class="pnav" aria-label="{U["nav"]}"><ul><li><a href="#glance">{U["top"]} <span aria-hidden="true">↑</span></a></li>'
           + "".join(f'<li><a href="#{s}">{H.escape(l)}</a></li>' for s, l in zip(nav_ids, U["short"])) + "</ul></nav>")
    first_sec = secs[0].start()
    out = body[:first_sec] + gbox + "\n" + bar + "\n"
    prev = first_sec
    for m, ns in zip(secs, new_secs):
        out += body[prev:m.start()] if prev != first_sec else ""
        out += ns; prev = m.end()
    out += body[prev:]
    return f'<div class="prio2">{out}</div>'


def _norm(s):
    s = text(s).lower().replace("’", "'")
    s = re.sub(r"[^\w%$']+", " ", s, flags=re.U)
    return re.sub(r"\s+", " ", s).strip()


def coverage(classic, new, lang):
    """Every text block and every link of the classic page must be on the v2 page. Returns a list of problems."""
    skip = {"on this page", "sur cette page", "show less", "afficher moins", "read more", "lire la suite"}
    stripped = new
    for pat in (r'<p class="pc-you">.*?</p>', r"<summary>.*?</summary>", r'<p class="totop">.*?</p>',
                r'<nav class="pnav".*?</nav>', r'<section class="glance".*?</section>'):
        stripped = re.sub(pat, " ", stripped, flags=re.S)
    hay = " " + _norm(stripped) + " "
    probs = []
    toc = re.search(r'<nav class="toc".*?</nav>', classic, re.S)
    for m in re.finditer(r"<(p|li|h[1-4]|figcaption|td|th|button)\b[^>]*>(.*?)</\1>", classic, re.S):
        if toc and toc.start() <= m.start() < toc.end(): continue
        b = _norm(m.group(2))
        b = re.sub(r" (in practice|concrètement)$", "", b)
        if not b or b in skip: continue
        if f" {b} " not in hay: probs.append(f"text block missing: {text(m.group(2))[:120]!r}")
    links = lambda h: re.findall(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', h, re.S)
    from collections import Counter
    need = Counter((u, _norm(t)) for u, t in links(classic)); have = Counter((u, _norm(t)) for u, t in links(new))
    for k, v in need.items():
        if have[k] < v: probs.append(f"link missing: {k[0]} ({k[1][:60]!r}) {have[k]}/{v}")
    return probs
