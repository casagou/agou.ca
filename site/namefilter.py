"""Names that must never appear on agou.ca (Joachim, 11 Oct 2026 3:07 PM PT: "don't mention [the company] or [the former employer] on my website. No naming.").
The words are built from fragments on purpose, so this file (and every file that imports it) does not spell them out.

  scrub(text)  rewrites Notion / content text that still carries the names into the neutral wording the site uses
               (applied by tools/notion2md.py, build.py read() and tools/diffcheck.py, so a re-sync from Notion stays clean);
  hits(text)   finds the names (any case, accents, HTML entities, tags in between) for the build and golive_check failures."""
import html, re, unicodedata

_C = "ca" + "sa" + "gou"        # the company, its Ops line, and the personal social handle
_T = "tha" + "les"              # the former employer
ONE = re.compile(f"{_C}|{_T}", re.I)


def fold(s):
    s = html.unescape(re.sub(r"<[^>]*>", "", s))  # tags inside a name must not hide it
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch) and ch not in "\u00ad\u200b\u200c\u200d\u2060\ufeff")


def hits(text):
    """[(matched text, context)] for each name found in text (also in the folded text, e.g. an accented or soft-hyphenated spelling)."""
    out = []
    for src in (text, fold(text)):
        for m in ONE.finditer(src):
            out.append((m.group(0), re.sub(r"\s+", " ", src[max(0, m.start() - 40):m.end() + 40])))
        if out: break
    return out


C, T = _C.capitalize(), _T.capitalize()
_LINK = rf"\[(?:Instagram|Facebook|X)\]\(https://(?:www\.)?(?:instagram\.com|facebook\.com|x\.com)/{_C}/?\)"
SCRUB = [  # (pattern, replacement), applied in this order; each is idempotent
    (re.compile(rf"\n(?:Personal|Personnel) ?: (?:{_LINK}(?: · )?)+"), ""),          # 'Personal: …' line built from the personal social accounts (the build adds it back from site.json when shown)
    (re.compile(rf"(?:{_LINK}(?: · )?)+"), "<personal-social/>"),                      # the personal accounts in Notion's contact block
    (re.compile(rf"{T} Canada, "), ""),                                                # role line: employer not named
    (re.compile(rf"{C} Inc\., (?=Victoria)"), ""),                                     # About role line: company not named
    (re.compile(rf"{C} Inc\., (?=(?:a|an|une) )"), ""),                                # bios: '… I run {C} Inc., a Victoria …' -> '… I run a Victoria …'
    (re.compile(rf"through {C} Inc\."), "through my company"),                        # FAQ (EN)
    (re.compile(rf"par l'intermédiaire de {C} Inc\."), "par l'intermédiaire de mon entreprise"),
    (re.compile(rf"par {C} Inc\."), "par mon entreprise"),                             # FAQ (FR)
    (re.compile(rf"{C} Ops \(business systems and automation\)"), "a business systems and automation practice"),
    (re.compile(rf"{C} Ops \(systèmes d.affaires et automatisation\)"), "une activité de systèmes d’affaires et d’automatisation"),
]


def scrub(text):
    for pat, rep in SCRUB:
        text = pat.sub(rep, text)
    return text


# explanatory 'why' / comment text in exclusions.json: same idea, wording only
WHY = [(re.compile(rf"{C} Inc\."), "the company"), (re.compile(rf"{C} Ops"), "the Ops line"), (re.compile(rf"@{_C}"), "the personal handle"),
       (re.compile(rf"{C} businesses"), "company businesses"), (re.compile(rf"{C} lists"), "the company lists"), (re.compile(rf"{C}"), "the company"),
       (re.compile(rf"{T} Canada"), "the former employer"), (re.compile(rf"{T}"), "the former employer")]


def why(text):
    for pat, rep in WHY:
        text = pat.sub(rep, text)
    return text
