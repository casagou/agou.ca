"""No-party version of the site (Joachim via Campaign Ops, 8 Oct 2026 2:50 PM PT; decisions 2:52 PM PT).
The BC Conservatives no longer support Joachim; he is still running in Victoria–Beacon Hill. With site.json no_party_v1
(staging; live only with no_party_v1_live too) the build:
  - applies the exact text edits below to the page text (after the Notion text, party links and staging drafts), so no
    party is named and every proposal is Joachim's own position (party-only items dropped; see KEPT/DROPPED in RESYNC.md);
  - turns the party links off (our own volunteer and lawn-sign forms again) and leaves out Donate everywhere (no page,
    button, link or appeal), the media-kit PDFs (they name the party) and events whose public text names the party;
  - overrides the interface and search text below, the Priorities labels/legend and the 'For you' lines;
  - fails the build if any party term is left in the output (check()).
Every edit must match exactly once, or the build stops (the underlying text changed: redo the edit).
Ops: ("sub", find, repl) · ("cut", start, end, repl): from start through the first end after it · ("dropline", anchor) ·
("line", anchor, new): whole line, leading whitespace kept · ("dropq", summary anchor): a whole FAQ <details> question ·
("q", summary anchor, new summary, [body lines]) · ("dropsec", heading line): a '## ' section up to the next '## '."""
import json, re

ON = {"on": False}
NP_ON = lambda env, site: bool(site.get("no_party_v1")) and (env == "staging" or bool(site.get("no_party_v1_live")))

# Party terms that must not appear in the built site. Reviewed exceptions are in ALLOW.
TERMS = re.compile(r"conservat|conservateur|\bCPBC\b|BC Cons|conservativebc|recruiter_id|Rustad|Aaron Gunn|\bparty\b|\bparti\b|\bparties\b|\bpartis\b|Doerkson|Findlay|Safe Streets for BC|Keep Emergency Rooms Open|Supercharge British Columbia|nationbuilder|filesusr|Taxpayer Respect|JIBC", re.I)
ALLOW = [  # (regex that must cover the hit itself, why it is fine)
    (r"Victoria[ _]Conservatory[ _]of[ _]Music|conservatory-of-music", "a Victoria venue (event 113 location, its photo credit and map key), not the party"),
    (r"(?:party|parti)[^.]{0,40}(?:its riding associations|ses associations)|registered political part(?:y|ies)", "Elections BC wording"),
    (r"the governing party|(?:par )?le parti au pouvoir", "home intro: the riding was held by the governing party (generic, names no party)"),
    (r"third[- ]part(?:y|ies)", "'third-party' (scripts, sponsors), not a political party"),
    (r"elections\.bc\.ca/candidates-parties/", "Elections BC page address (URL path), not shown as text"),
    (r"\.chip-party\b", "CSS class name in prio2.css (unused by the no-party page), not shown"),
]


def allowed(t, m):
    """The ALLOW reason covering the hit m in text t, else None."""
    a, b = max(0, m.start() - 120), m.end() + 120
    for p, why in ALLOW:
        for x in re.finditer(p, t[a:b], re.I):
            if x.start() + a <= m.start() and x.end() + a >= m.end(): return why
    return None


ERRS = []  # edit ops that did not match (build.py reports them all with the other check errors)
_SP = "[ \u00a0\u202f]"


def _pat(s):
    """Regex for s where any space may be a normal, non-breaking or narrow non-breaking space (French typography)."""
    return re.compile(_SP.join(re.escape(x) for x in s.split(" ")))


def _real(t, find, where):
    """The exact text in t that matches find (spaces may be NBSP); must occur once."""
    if t.count(find) == 1: return find
    ms = list(_pat(find).finditer(t))
    if len(ms) != 1: raise SystemExit(f"no_party: {where}: text to change found {len(ms)} times (want 1): {find[:90]!r}")
    return ms[0].group(0)


def _nb(real, repl):
    """French: if the original used NBSPs before : ; ? ! % » (or after «), use them in the new text too."""
    if "\u00a0" not in real and "\u202f" not in real: return repl
    return re.sub(r"« ", "«\u00a0", re.sub(r" (?=[:;?!%»])", "\u00a0", repl))


def _one(t, find, where):
    real = _real(t, find, where)
    return t.index(real), real


def _line(t, anchor, where):
    ls = t.split("\n"); P = _pat(anchor); idx = [i for i, l in enumerate(ls) if P.search(l)]
    if len(idx) != 1: raise SystemExit(f"no_party: {where}: line anchor found on {len(idx)} lines (want 1): {anchor[:90]!r}")
    return ls, idx[0]


def apply_ops(t, ops, where):
    for op in ops:
        try: t = _op(t, op, where)
        except SystemExit as ex: ERRS.append(str(ex))
    return t


def _op(t, op, where):
    k = op[0]
    if k == "sub":
        i, real = _one(t, op[1], where); t = t[:i] + _nb(real, op[2]) + t[i + len(real):]
    elif k == "cut":
        i, real = _one(t, op[1], where); m = _pat(op[2]).search(t, i)
        if not m: raise SystemExit(f"no_party: {where}: cut end not found after {op[1][:60]!r}: {op[2][:60]!r}")
        t = t[:i] + _nb(t[i:m.end()], op[3]) + t[m.end():]
    elif k in ("dropline", "line"):
        ls, i = _line(t, op[1], where)
        if k == "dropline": del ls[i]
        else: ls[i] = re.match(r"\s*", ls[i]).group(0) + _nb(ls[i], op[2])
        t = "\n".join(ls)
    elif k in ("dropq", "q"):
        ls, i = _line(t, "<summary>" + op[1], where)
        s = i - 1
        if ls[s].strip() != "<details>": raise SystemExit(f"no_party: {where}: no <details> right before {op[1]!r}")
        e = next(j for j in range(i, len(ls)) if ls[j].strip() == "</details>")
        if k == "dropq": del ls[s:e + 1]
        else:
            body = [_nb("\n".join(ls[i + 1:e]), x) for x in op[3]]
            ls[i + 1:e] = body; ls[i] = re.sub(r"<summary>.*</summary>", lambda m_: f"<summary>{_nb(ls[i], op[2])}</summary>", ls[i])
        t = "\n".join(ls)
    elif k == "dropsec":
        ls, i = _line(t, op[1], where)
        if ls[i].strip() != op[1]: raise SystemExit(f"no_party: {where}: {op[1]!r} is not a whole heading line")
        e = next((j for j in range(i + 1, len(ls)) if ls[j].startswith("## ")), len(ls))
        del ls[i:e]; t = "\n".join(ls)
    else: raise SystemExit(f"no_party: unknown op {k}")
    return t


def apply(t, lang, key):
    ops = EDITS.get(f"{lang}/{key}")
    return apply_ops(t, ops, f"{lang}/{key}") if (ON["on"] and ops and t is not None) else t


PLAT = "https://assets.nationbuilder.com/themes/62bc6e06c294807a1b297b61/attachments/original/1729201650/Conservative_Party_of_British_Columbia_Policy_Platform_%282%29.pdf?1729201650"
COST = "https://da1a036c-b798-4e6b-a8c4-5a6d84a800d4.filesusr.com/ugd/b66bba_fbc8340168dc439eacbcb1017d85193e.pdf"
KERO = "(https://conservativebc.ca/keep-emergency-rooms-open/)"

EDITS = {
"en/priorities": [
    ("cut", "I'm the Conservative Party of BC's nominee in Victoria–Beacon Hill.", "- **My position:** mine. I'll advocate for it within the party.",
     "I'm running to be the MLA for Victoria–Beacon Hill. Every proposal on this page is my own position, with the source of each figure."),
    ("cut", " The party has also committed to train more doctors", KERO + ").", ""),
    ("cut", "; the 2024 party platform cites a CFIB estimate", "#page=61)", ""),
    ("cut", "(my position, building on the 2024 party platform", "the starting list are mine)", "(my position)"),
    ("cut", " The party has committed to protect current health care funding and keep B.C.'s system", KERO + ").", ""),
    ("cut", "; 2024 party platform, [p. 54]", "#page=54)", ""),
    ("dropline", "**An expert commission within 100 days.**"),
    ("cut", " The party has committed to keep emergency rooms open", "The announcement doesn't say which hospitals the fund supports.", ""),
    ("sub", "I'll report every quarter whether closures fall.", "I'll report every quarter whether closures fall (my position)."),
    ("line", "- **Staff:** extra hours need staff first.", "- **Staff:** extra hours need staff first. Work with physicians, nurse practitioners, nurses and physician assistants to see more patients per practice, and expand the programs that fill positions in high-need communities (my position)."),
    ("cut", "so they can buy equipment and recruit staff (2024 party platform", "#page=54)).", "so they can buy equipment and recruit staff (my position)."),
    ("cut", "move the money to front-line staffing (2024 party platform", "#page=61)).", "move the money to front-line staffing (my position)."),
    ("sub", "I'll publish a local cost note once the party releases updated 2026 figures. Until then I won't invent a number.",
     "Where a change needs new staff or clinic time, I'll publish the cost when Ministry of Health or Island Health figures exist. I won't invent a number."),
    ("line", "- Approve homes in months, not years:", "- Approve homes in months, not years, with fixed deadlines for rezoning, development and building permits. If city hall doesn't give a clear yes or no in time, the Province issues the permits (my position)."),
    ("cut", ' The party has committed to "bring down the cost', "(https://conservativebc.ca/conservative-party-of-bc-pledges-no-new-taxes-on-british-columbians/)).", ""),
    ("dropline", "- Cut red tape: a new Minister of Red Tape Reduction"),
    ("dropline", "- Income-tax relief on housing costs (2024 party platform"),
    ("sub", "which eases rents over time; and, under the 2024 proposal, less provincial income tax if you pay rent, mortgage interest or strata fees.", "which eases rents over time."),
    ("dropline", "**The 2024 tax relief in detail:**"),
    ("dropline", "**Example (illustration only, from the 2024 platform's figures):**"),
    ("sub", "faster approvals mean less municipal control, and the tax relief lowers provincial revenue.", "faster approvals mean less municipal control."),
    ("sub", "(my position, scorecard promise 2; the party made the same pledge on 27 Sep 2026).", "(my position, scorecard promise 2)."),
    ("dropline", "- No PST for 3 years on machinery"),
    ("dropline", "- No PST at the till on Canadian beer"),
    ("dropline", "- No PST on affordable used cars (2024 party platform"),
    ("sub", "or other measures (2024 party platform; see Transport and BC Ferries below).", "or other measures (my position; see Transport and BC Ferries below)."),
    ("line", "**Timing and funding:** the year each tax change", "**Timing and funding:** no year or cost has been published for these changes, and I won't print one. I'll vote for them in a budget that says when they take effect and how they are paid for."),
    ("sub", " Under the 2026 party commitments: no PST at the till on Canadian beer, wine and spirits during the trade war, and none on a small business's new equipment and software for 3 years.", ""),
    ("line", "**Cost:** the party has not published a cost for restoring", "**Cost:** no cost has been published for restoring the rate and indexing, and I won't print a figure of my own."),
    ("dropline", "- **Police:** 250 more police officers"),
    ("sub", " More psychiatric services, crisis response and residential treatment (party commitment, Safe Streets for BC).", ""),
    ("line", "- **Compassionate intervention:**", "- **Secure care:** for people with severe addiction who are a danger to themselves or others, with medical and legal safeguards (my position)."),
    ("line", "- **Care that keeps people alive:**", '- **Care that keeps people alive:** end "safe supply" and expand access to naloxone, so the focus moves to treatment and recovery while an overdose can still be reversed (my position).'),
    ("dropline", "- **Safe places to heal:**"),
    ("cut", "(my position; the 2024 party platform also proposed moving campers", "#page=5)).", "(my position)."),
    ("line", "- **Courts:** 50 new Crown prosecutors", "- **Courts:** add sheriffs and judges so cases reach trial faster. The courts, prosecution and sheriffs are provincial, and I'll vote to fund them. Bail is federal law, so for repeat violent offenders I'll press Ottawa for amendments (my position)."),
    ("line", "- **Small business:** cut the small-business tax", "- **Small business:** work with cities to publish business permit wait times (my position)."),
    ("sub", " The party has committed to report these public safety results openly (Safe Streets for BC).", ""),
    ("cut", "**Staffing and funding:** the party's 2024 costing", COST + ")). ", "**Staffing and funding:** "),
    ("cut", "with new leadership sought if they aren't met (2024 party platform", "#page=112)).", "with new leadership sought if they aren't met (my position)."),
    ("cut", "so fewer sailings are lost to breakdowns (2024 party platform", "#page=113)).", "so fewer sailings are lost to breakdowns (my position)."),
    ("sub", "tie part of executive pay to performance results (2024 party platform, p. 112).", "tie part of executive pay to performance results (my position)."),
    ("sub", "more certainty and less hassle (2024 party platform, p. 112).", "more certainty and less hassle (my position)."),
    ("sub", " The 2024 party platform described a fleet aging to the point where maintenance challenges routinely affect service (p. 113).", ""),
    ("sub", " The 2024 platform also proposed pressing Ottawa for B.C.'s fair share of federal support for fleet renewal (p. 112).", ""),
    ("line", "- Protect front-line services:", "- Protect front-line services: I won't cut health care or education to write a slogan (my position)."),
    ("line", "- Review government spending to find", "- Review government spending to find what isn't delivering results and move the money to priorities (my position)."),
    ("line", "- Show what each commitment on this page costs", "- Show what each commitment on this page costs where a published figure exists, and say so where none does (my position)."),
    ("sub", "it shows whether the tax relief on this page is paid for.", "it shows whether the tax changes on this page are paid for."),
    ("dropline", "**The route to balance:**"),
    ("line", "**What the commitments cost (party estimates, Oct 2024):**", "**What the commitments cost:** restoring the 5.06% rate and indexing has no published cost yet, and I won't print one of my own (scorecard line 1)."),
],
"fr/priorities": [
    ("cut", "Je suis investi par le Parti conservateur de la Colombie-Britannique dans Victoria–Beacon Hill.", "- **Ma position :** la mienne. Je la défendrai au sein du parti.",
     "Je me présente pour devenir le député de Victoria–Beacon Hill. Chaque proposition de cette page est ma propre position, avec la source de chaque chiffre."),
    ("cut", " Le parti s'est aussi engagé à former plus de médecins", KERO + ", en anglais).", ""),
    ("cut", "; le programme 2024 du parti cite une estimation de la FCEI", "#page=61), en anglais", ""),
    ("cut", "(ma position, dans le prolongement du programme 2024 du parti", "sont mes propositions)", "(ma position)"),
    ("cut", " Le parti s'est engagé à protéger le financement actuel des soins de santé et à garder le système de la C.-B.", KERO + ", en anglais).", ""),
    ("cut", "; programme 2024 du parti, [p. 54]", "#page=54), en anglais", ""),
    ("dropline", "**Une commission d'experts dans les 100 premiers jours.**"),
    ("cut", " Le parti s'est engagé à garder les urgences ouvertes", "L'annonce ne précise pas quels hôpitaux ce fonds soutiendra.", ""),
    ("sub", "Chaque trimestre, je dirai si les fermetures diminuent.", "Chaque trimestre, je dirai si les fermetures diminuent (ma position)."),
    ("line", "- **Personnel :** pour prolonger les heures d'ouverture des cliniques", "- **Personnel :** pour prolonger les heures d'ouverture des cliniques, il faut d'abord du personnel. Travailler avec les médecins, les infirmières praticiennes, le personnel infirmier et les adjoints au médecin pour que chaque cabinet voie plus de patients, et élargir les programmes qui pourvoient les postes dans les collectivités où les besoins sont grands (ma position)."),
    ("cut", "pour qu'elles puissent acheter de l'équipement et recruter du personnel (programme 2024 du parti", "#page=54), en anglais).", "pour qu'elles puissent acheter de l'équipement et recruter du personnel (ma position)."),
    ("cut", "réaffecter l'argent au personnel de première ligne (programme 2024 du parti", "#page=61), en anglais).", "réaffecter l'argent au personnel de première ligne (ma position)."),
    ("sub", "Je publierai une note précisant les coûts pour notre région lorsque le parti rendra publics des chiffres à jour pour 2026. D'ici là, je n'inventerai pas de chiffre.",
     "Lorsqu'un changement exige du personnel ou du temps de clinique supplémentaire, je publierai le coût dès que des chiffres du ministère de la Santé ou d'Island Health existeront. Je n'inventerai pas de chiffre."),
    ("line", "- Approuver les logements en quelques mois, pas en plusieurs années :", "- Approuver les logements en quelques mois, pas en plusieurs années, avec des délais fixes pour les rezonages, les permis d'aménagement et les permis de construire. Si l'hôtel de ville ne donne pas un oui ou un non clair dans ce délai, la Province délivre les permis (ma position)."),
    ("cut", " Le parti s'est engagé à réduire le coût de construction et d'achat d'un logement pour que", "(https://conservativebc.ca/conservative-party-of-bc-pledges-no-new-taxes-on-british-columbians/), en anglais).", ""),
    ("dropline", "- Réduire les formalités administratives : un nouveau ministre"),
    ("dropline", "- Un allègement de l'impôt sur le revenu lié aux frais de logement (programme 2024 du parti"),
    ("sub", "ce qui contribue à faire baisser les loyers au fil du temps; et, selon la proposition de 2024, moins d'impôt provincial sur le revenu si vous payez un loyer, des intérêts hypothécaires ou des frais de copropriété.", "ce qui contribue à faire baisser les loyers au fil du temps."),
    ("dropline", "**L'allègement fiscal de 2024 en détail :**"),
    ("dropline", "**Exemple (à titre d'illustration seulement, d'après les chiffres du programme 2024) :**"),
    ("sub", "des approbations plus rapides réduisent le contrôle municipal, et l'allègement fiscal réduit les revenus de la Province.", "des approbations plus rapides réduisent le contrôle municipal."),
    ("sub", "(ma position, promesse 2 du bulletin; le parti a pris le même engagement le 27 sept. 2026).", "(ma position, promesse 2 du bulletin)."),
    ("dropline", "- Aucune TVP pendant 3 ans sur la machinerie"),
    ("dropline", "- Aucune TVP à la caisse sur la bière"),
    ("dropline", "- Aucune TVP sur les voitures d'occasion abordables (programme 2024 du parti"),
    ("sub", "ou d'autres mesures (programme 2024 du parti; voir Transport et BC Ferries plus bas).", "ou d'autres mesures (ma position; voir Transport et BC Ferries plus bas)."),
    ("line", "**Échéancier et financement :**", "**Échéancier et financement :** aucune année ni aucun coût n'ont été publiés pour ces changements, et je n'en afficherai pas. Je voterai pour ces changements dans un budget qui précise quand ils entrent en vigueur et comment ils sont financés."),
    ("sub", " Selon les engagements du parti de 2026 : aucune TVP à la caisse sur la bière, le vin et les spiritueux canadiens pendant la guerre commerciale, ni sur le nouvel équipement et les logiciels d'une petite entreprise pendant 3 ans.", ""),
    ("line", "**Coût :** le parti n'a pas publié d'estimation du coût du rétablissement", "**Coût :** aucune estimation du coût du retour au taux de 5,06 % et du rétablissement de l'indexation n'a été publiée, et je n'afficherai pas de chiffre de mon cru."),
    ("dropline", "- **Police :** 250 policiers de plus"),
    ("sub", " Plus de services psychiatriques, d'intervention en situation de crise et de traitement en établissement (engagement du parti, Safe Streets for BC).", ""),
    ("line", "- **Intervention bienveillante :**", "- **Soins en milieu sécurisé :** pour les personnes ayant une dépendance grave qui représentent un danger pour elles-mêmes ou pour autrui, avec des garanties médicales et juridiques (ma position)."),
    ("line", "- **Des soins qui gardent les gens en vie :**", "- **Des soins qui gardent les gens en vie :** mettre fin à l'« approvisionnement plus sécuritaire » et élargir l'accès à la naloxone, pour que l'accent passe au traitement et au rétablissement, tout en permettant de renverser une surdose (ma position)."),
    ("dropline", "- **Des lieux sûrs pour se rétablir :**"),
    ("cut", "(ma position; le programme 2024 du parti proposait aussi d'orienter les campeurs", "#page=5), en anglais).", "(ma position)."),
    ("line", "- **Tribunaux :** 50 nouveaux procureurs", "- **Tribunaux :** ajouter des shérifs et des juges pour que les procès se tiennent plus vite. Les tribunaux, les poursuites et les shérifs relèvent de la Province, et je voterai pour les financer. La mise en liberté sous caution relève du droit fédéral; pour les récidivistes violents, je presserai donc Ottawa d'y apporter des modifications (ma position)."),
    ("line", "- **Petites entreprises :** ramener le taux", "- **Petites entreprises :** travailler avec les villes pour publier les délais de délivrance des permis commerciaux (ma position)."),
    ("sub", " Le parti s'est engagé à publier ouvertement ces résultats en matière de sécurité publique (Safe Streets for BC).", ""),
    ("cut", "**Personnel et financement :** l'évaluation des coûts du parti de 2024", COST + "), en anglais). ", "**Personnel et financement :** "),
    ("cut", "si ces attentes ne sont pas respectées (programme 2024 du parti", "#page=112), en anglais).", "si ces attentes ne sont pas respectées (ma position)."),
    ("cut", "pour que moins de traversées soient annulées en raison de pannes (programme 2024 du parti", "#page=113), en anglais).", "pour que moins de traversées soient annulées en raison de pannes (ma position)."),
    ("sub", "lier une partie de la rémunération des dirigeants aux résultats (programme 2024 du parti, p. 112).", "lier une partie de la rémunération des dirigeants aux résultats (ma position)."),
    ("sub", "plus de prévisibilité et moins de tracas (programme 2024 du parti, p. 112).", "plus de prévisibilité et moins de tracas (ma position)."),
    ("sub", " Le programme 2024 du parti décrivait une flotte vieillissante au point où les problèmes d'entretien nuisent régulièrement à la qualité du service (p. 113).", ""),
    ("sub", " Le programme 2024 proposait aussi de presser Ottawa d'accorder à la C.-B. sa juste part du soutien fédéral au renouvellement de la flotte (p. 112).", ""),
    ("line", "- Protéger les services de première ligne :", "- Protéger les services de première ligne : je ne couperai pas dans les soins de santé ou l'éducation pour en faire un slogan (ma position)."),
    ("line", "- Examiner les dépenses du gouvernement pour repérer", "- Examiner les dépenses du gouvernement pour repérer ce qui ne donne pas de résultats et réaffecter l'argent aux priorités (ma position)."),
    ("line", "- Indiquer le coût de chaque engagement de cette page", "- Indiquer le coût de chaque engagement de cette page lorsqu'un chiffre publié existe, et le préciser lorsqu'il n'en existe pas (ma position)."),
    ("sub", "il montre si l'allègement fiscal présenté sur cette page est financé.", "il montre si les changements fiscaux présentés sur cette page sont financés."),
    ("dropline", "**Le chemin vers l'équilibre :**"),
    ("line", "**Ce que coûtent les engagements (estimations du parti, oct. 2024) :**", "**Ce que coûtent les engagements :** le retour au taux de 5,06 % et le rétablissement de l'indexation n'ont pas encore de coût publié, et je n'afficherai pas de chiffre de mon cru (ligne 1 du bulletin)."),
],
"en/home": [
    ("line", "Conservative Party of BC nominee for Member of the Legislative Assembly", "Running to be the Member of the Legislative Assembly (MLA) for Victoria–Beacon Hill"),
    ("sub", "I serve as interim vice-president of the Victoria Conservative Association and volunteer with Chabad of Vancouver Island.", "I volunteer with Chabad of Vancouver Island."),
    ("dropsec", "## Donate"),
],
"fr/home": [
    ("line", "Investi par le Parti conservateur de la Colombie-Britannique pour représenter", "Je me présente pour représenter Victoria–Beacon Hill à l'Assemblée législative"),
    ("sub", "Je suis vice-président par intérim de la Victoria Conservative Association et bénévole auprès de Chabad of Vancouver Island.", "Je suis bénévole auprès de Chabad of Vancouver Island."),
    ("dropsec", "## Faire un don"),
],
"en/about": [
    ("dropline", "Interim Vice-President, Victoria Conservative Association"),
    ("sub", " I support the BC Conservative program, and I would bring this riding's numbers to the Legislature.", " I would bring this riding's numbers to the Legislature."),
],
"fr/about": [
    ("dropline", "Vice-président par intérim, Victoria Conservative Association"),
    ("sub", " J'appuie le programme du Parti conservateur de la Colombie-Britannique, et je présenterais à l'Assemblée législative les données concernant notre circonscription.", " Je présenterais à l'Assemblée législative les données concernant notre circonscription."),
],
"en/media": [
    ("sub", "small-business owner and father, and the Conservative Party of BC's nominee in Victoria–Beacon Hill. He lives in Fairfield with his daughter.", "small-business owner and father, running to be the MLA for Victoria–Beacon Hill. He lives in Fairfield with his daughter."),
    ("sub", "small-business owner and father, and the Conservative Party of BC's nominee in Victoria–Beacon Hill. He lives in Fairfield with his 10-year-old daughter.", "small-business owner and father, running to be the MLA for Victoria–Beacon Hill. He lives in Fairfield with his 10-year-old daughter."),
    ("sub", "He volunteers with Chabad of Vancouver Island and serves as interim vice-president of the Victoria Conservative Association.", "He volunteers with Chabad of Vancouver Island."),
    ("sub", "Joachim volunteers with Chabad of Vancouver Island and is interim vice-president of the Victoria Conservative Association.", "Joachim volunteers with Chabad of Vancouver Island."),
],
"fr/media": [
    ("sub", "père de famille. Investi par le Parti conservateur de la Colombie-Britannique, il se présente dans Victoria–Beacon Hill. Il vit à Fairfield avec sa fille.", "père de famille. Il se présente pour devenir le député de Victoria–Beacon Hill. Il vit à Fairfield avec sa fille."),
    ("sub", "père de famille. Investi par le Parti conservateur de la Colombie-Britannique, il se présente dans Victoria–Beacon Hill. Il vit à Fairfield avec sa fille de 10 ans.", "père de famille. Il se présente pour devenir le député de Victoria–Beacon Hill. Il vit à Fairfield avec sa fille de 10 ans."),
    ("sub", "Il fait du bénévolat auprès de Chabad of Vancouver Island et occupe la vice-présidence par intérim de la Victoria Conservative Association.", "Il fait du bénévolat auprès de Chabad of Vancouver Island."),
    ("sub", "Joachim fait du bénévolat auprès de Chabad of Vancouver Island et occupe la vice-présidence par intérim de la Victoria Conservative Association.", "Joachim fait du bénévolat auprès de Chabad of Vancouver Island."),
],
"en/privacy": [("sub", "The Joachim Agou campaign (Conservative Party of BC, Victoria–Beacon Hill)", "The Joachim Agou campaign (Victoria–Beacon Hill)")],
"fr/privacy": [("sub", "La campagne de Joachim Agou (Parti conservateur de la C.-B., Victoria–Beacon Hill)", "La campagne de Joachim Agou (Victoria–Beacon Hill)")],
"en/scorecard": [
    ("sub", "I vote no — including in my own caucus. The year we restore the 5.06% bottom rate is the year it is in the party fiscal plan. I will not print a year the party has not locked.",
     "I vote no. I will not print a year for restoring the 5.06% bottom rate until a budget sets one."),
    ("sub", "Indexation restored. The year and the funding follow the party’s published fiscal plan. Keep", "Indexation restored. Keep"),
    ("sub", "I will vote to restore 5.06% and indexation when the party prints the year and the offset.", "I will vote to restore 5.06% and indexation in a budget that sets the year and the offset."),
    ("sub", "The dollar total follows the party fiscal plan once it is out — I am not", "The dollar total follows a costed budget — I am not"),
],
"fr/scorecard": [
    ("sub", "je vote contre — y compris au sein de mon propre caucus. L’année où nous rétablirons le taux de 5,06 % de la première tranche sera l’année inscrite dans le plan financier du parti. Je n’annoncerai pas une année que le parti n’a pas arrêtée.",
     "je vote contre. Je n’annoncerai pas d’année pour le retour au taux de 5,06 % de la première tranche tant qu’un budget n’en aura pas fixé une."),
    ("sub", "Rétablir l’indexation. L’année et le financement suivent le plan financier publié par le parti. Maintenir", "Rétablir l’indexation. Maintenir"),
    ("sub", "quand le parti aura fixé l’année et la mesure compensatoire.", "dans un budget qui fixe l’année et la mesure compensatoire."),
    ("sub", "Le montant total suivra le plan financier du parti une fois celui-ci publié — je n’avance pas", "Le montant total suivra un budget chiffré — je n’avance pas"),
],
}

_SRC_EB = "Sources: [Elections BC, candidate nomination FAQ](https://elections.bc.ca/candidates-parties/candidate-nomination-faq/), [Elections BC, candidate list](https://elections.bc.ca/2026-provincial-election/candidate-list/)."
_SRC_EB_FR = "Sources : [FAQ d'Elections BC sur la mise en candidature](https://elections.bc.ca/candidates-parties/candidate-nomination-faq/), [liste des candidats d'Elections BC](https://elections.bc.ca/2026-provincial-election/candidate-list/)."
EDITS["en/faq"] = [
    ("dropq", "Have you won the BC Conservative nomination?"),
    ("q", "Is the party nomination the same thing as getting on the ballot?", "Are you on the ballot?",
     ["Yes. My nomination papers were accepted: 75 nominators who live in Victoria–Beacon Hill and a $250 deposit, filed by 1 p.m. on Saturday 3 October. I'm on Elections BC's final candidate list for Victoria–Beacon Hill. Look for Joachim Agou on your ballot.", _SRC_EB]),
    ("dropq", "Why the Conservatives?"),
    ("dropq", "Where do you stand on the interim leader and the split in the party?"),
    ("sub", "a small Victoria engineering consulting and media company, volunteer with Chabad of Vancouver Island, and serve as interim vice-president of the Victoria Conservative Association.",
     "a small Victoria engineering consulting and media company, and volunteer with Chabad of Vancouver Island."),
    ("sub", "I support the party's plan to replace the current law with clear rules", "I support replacing the current law with clear rules"),
    ("line", "Cut doctors' paperwork so clinics can take more patients (my position; the 2024 party platform",
     "Cut doctors' paperwork so clinics can take more patients (my position). Add evening and weekend clinic hours on the South Island (my position). Use publicly paid surgeries and scans at non-government clinics to shorten waits (my position). You show your health card and pay nothing."),
    ("line", "Cost: cutting paperwork is a rule change, not a new program. Publicly paid surgeries",
     "Cost: cutting paperwork is a rule change, not a new program. Where a change needs new staff or clinic time, I'll publish the cost when Ministry of Health or Island Health figures exist. Until then I will not invent a number."),
    ("line", "Approvals in months, not years: 6 months for a rezoning",
     "Approvals in months, not years, with fixed deadlines for rezoning, development and building permits; if city hall doesn't give a clear yes or no in time, the Province issues the permits (my position). Lower fees and paperwork on new homes (my position)."),
    ("line", "Faster, cheaper approvals count when they turn into finished homes", "Faster, cheaper approvals count when they turn into finished homes, including family-sized ones, which eases rents over time."),
    ("line", "Trade-offs: faster approvals mean less municipal control, and the tax relief", "Trade-offs: faster approvals mean less municipal control."),
    ("line", "I am not proposing a new vacancy-control law.", "I am not proposing a new vacancy-control law. The housing relief on this site is more homes from faster, cheaper permits."),
    ("dropline", "- **Police:** more police in the hardest-hit neighbourhoods, and 250"),
    ("line", "- **Treatment:** more staffed detox and treatment beds on the South Island, with waits published monthly (my position). More psychiatric",
     "- **Treatment:** more staffed detox and treatment beds on the South Island, with waits published monthly (my position). Secure care for people with severe addiction who are a danger to themselves or others, with medical and legal safeguards (my position)."),
    ("sub", "(my position; the 2024 party platform also proposed moving campers into support services).", "(my position)."),
    ("line", "- **Courts:** 50 new Crown prosecutors", "- **Courts:** add sheriffs and judges so cases reach trial faster, and I'll vote to fund the courts, prosecution and sheriffs. Bail is federal law, so for repeat violent offenders I'll press Ottawa for amendments (my position)."),
    ("sub", 'The party has committed to end "safe supply" and expand access to naloxone ([Safe Streets for BC, 6 Oct 2026](https://conservativebc.ca/safe-streets-for-bc/)). The two go together:',
     'I\'d end "safe supply" and expand access to naloxone. The two go together:'),
    ("sub", " The party has committed to compassionate intervention, so people with severe addiction, mental illness or brain injury are taken off the street and into care, and to no illegal drug use in hospitals, shelters and publicly funded supportive housing (Safe Streets for BC).", ""),
    ("sub", "provincial income tax, the PST, ferry fares, and housing costs through the tax system.", "provincial income tax and ferry fares."),
    ("sub", " The year and the funding follow the party's published fiscal plan.", " No year or cost has been published, and I won't print one."),
    ("dropline", "- No PST for 3 years on machinery"),
    ("dropline", "- No PST at the till on Canadian beer"),
    ("dropline", "- A plan within 180 days to simplify"),
    ("line", "- Ferry fares: consult commuters", "- Ferry fares: consult commuters and other frequent users on a monthly flat-fee program or other measures (my position)."),
    ("dropline", "- No PST on affordable used cars"),
    ("dropline", "- The income-tax relief on housing costs above"),
    ("dropline", "- Cut the small-business tax from 2% to 1%"),
    ("line", "I will not cut health care or education to write a slogan. The party has committed",
     "I will not cut health care or education to write a slogan. I also will not invent a savings number. A balanced budget is not a saving for your household; it is how you can check that commitments are paid for."),
    ("sub", " I read the party's red-tape plan ([Supercharge British Columbia's Economy, 7 Oct 2026](https://conservativebc.ca/supercharge-british-columbias-economy/)) as fewer rules and forms, not fewer public servants, and that is how I'll vote on it (my position).",
     " Cutting red tape should mean fewer rules and forms, not fewer public servants, and that is how I'll vote (my position)."),
    ("sub", "a BC Ferries Charter that sets out service and performance expectations (2024 party platform).", "a BC Ferries Charter that sets out service and performance expectations (my position)."),
    ("line", "The large items are from the party's 2024 platform.", "Restoring the 5.06% rate and indexing has no published cost yet, and I won't print a figure of my own. A balanced budget is how you can check that tax changes are paid for, so I'll vote against a bill that doesn't say what it cuts."),
    ("dropline", "- Income-tax relief on housing costs (rent, mortgage interest and strata fees): about $900 million"),
    ("dropline", "- Small-business tax cut to 1%: about $150 million"),
    ("dropline", "- Get BC Building (infrastructure"),
    ("dropline", "- No PST on affordable used vehicles: part of"),
    ("dropline", "In 2024 the party said faster economic growth would pay"),
    ("dropline", "announcement (6 Oct 2026) adds 250 police officers"),
    ("sub", "Items that are mine — cutting doctors' paperwork (also in the 2024 platform), South Island clinic hours,", "Most of my proposals — cutting doctors' paperwork, fixed permit deadlines, South Island clinic hours,"),
    ("sub", "public-service standards — are mostly rule and reporting changes.", "public-service standards — are rule and reporting changes."),
    ("q", "Which proposals are party commitments, and which are your own?", "Whose proposals are these?",
     ["They are my own positions. Each figure links to its source, and the [scorecard](https://agou.ca/scorecard/) shows how you can check the results every quarter."]),
    ("q", "What could you accomplish if your party does not form government?", "What could you accomplish if you are not in government?",
     ["Opposition MLAs still vote on every law, propose amendments and private members' bills, question ministers, sit on committees that review spending, and help constituents deal with government ([Legislative Assembly](https://www.leg.bc.ca/learn/discover-your-legislature/about-the-legislative-assembly)). I'd use all of that, and I'd publish the same quarterly report either way.",
      "I can force numbers onto the record, amend bad bills, and get a neighbour through a broken file at a provincial agency."]),
    ("sub", "Grace Lore (BC NDP), Raj Sahota (BC Green Party; on the ballot as Rajinder S. Sahota) and me (Conservative Party of BC).", "Grace Lore, Raj Sahota (on the ballot as Rajinder S. Sahota) and me."),
    ("sub", "<summary>How would you represent residents who disagree with you or your party?</summary>", "<summary>How would you represent residents who disagree with you?</summary>"),
    ("dropline", "If party policy conflicted with what this riding needs"),
    ("dropq", "How can I donate?"),
]
EDITS["fr/faq"] = [
    ("dropq", "Avez-vous obtenu l'investiture du Parti conservateur de la Colombie-Britannique?"),
    ("q", "L'investiture du parti est-elle la même chose que figurer sur le bulletin de vote?", "Figurez-vous sur le bulletin de vote?",
     ["Oui. Mes documents de mise en candidature ont été acceptés : un formulaire signé par 75 personnes résidant dans Victoria–Beacon Hill et un dépôt de 250 $, déposés au plus tard à 13 h le samedi 3 octobre. Mon nom figure sur la liste finale des candidats d'Elections BC pour Victoria–Beacon Hill. Cherchez Joachim Agou sur votre bulletin de vote.", _SRC_EB_FR]),
    ("dropq", "Pourquoi les conservateurs?"),
    ("dropq", "Quelle est votre position sur le chef intérimaire et la division du parti?"),
    ("sub", "Je suis bénévole auprès de Chabad of Vancouver Island et vice-président par intérim de la Victoria Conservative Association.", "Je suis bénévole auprès de Chabad of Vancouver Island."),
    ("sub", "J'appuie le plan du parti visant à remplacer la loi actuelle par des règles claires", "J'appuie le remplacement de la loi actuelle par des règles claires"),
    ("line", "Réduire la paperasse des médecins pour que les cliniques puissent accueillir plus de patients (ma position; le programme 2024 du parti",
     "Réduire la paperasse des médecins pour que les cliniques puissent accueillir plus de patients (ma position). Élargir les heures d'ouverture des cliniques en soirée et les fins de semaine dans le sud de l'île de Vancouver (ma position). Recourir à des cliniques non gouvernementales pour des interventions chirurgicales et des examens d'imagerie médicale financés par les fonds publics, afin de réduire les délais d'attente (ma position). Vous présentez votre carte santé et vous ne payez rien."),
    ("line", "Coût : réduire la paperasse est un changement de règles, pas un nouveau programme. Le recours",
     "Coût : réduire la paperasse est un changement de règles, pas un nouveau programme. Lorsqu'un changement exige du personnel ou du temps de clinique supplémentaire, je publierai le coût dès que des chiffres du ministère de la Santé ou d'Island Health existeront. D'ici là, je n'inventerai pas de chiffre."),
    ("line", "Approuver les logements en quelques mois, pas en plusieurs années : 6 mois",
     "Approuver les logements en quelques mois, pas en plusieurs années, avec des délais fixes pour les rezonages, les permis d'aménagement et les permis de construire; si l'hôtel de ville ne donne pas un oui ou un non clair dans ce délai, la Province délivre les permis (ma position). Moins de frais et de paperasse pour les logements neufs (ma position)."),
    ("line", "Des approbations plus rapides et moins coûteuses comptent", "Des approbations plus rapides et moins coûteuses comptent lorsqu'elles se traduisent par des logements achevés, y compris des logements familiaux, ce qui modère les loyers avec le temps."),
    ("line", "Compromis : des approbations plus rapides signifient moins de contrôle municipal, et l'allègement", "Compromis : des approbations plus rapides signifient moins de contrôle municipal."),
    ("line", "Je ne propose pas de nouvelle loi qui maintiendrait", "Je ne propose pas de nouvelle loi qui maintiendrait l'encadrement des loyers d'un locataire à l'autre. Les mesures proposées sur ce site pour rendre le logement plus abordable reposent sur la construction de davantage de logements grâce à des permis délivrés plus rapidement et à moindre coût."),
    ("dropline", "- **Police :** davantage de policiers dans les quartiers les plus touchés, et 250"),
    ("line", "- **Traitement :** plus de lits de désintoxication et de traitement, avec le personnel nécessaire pour accueillir",
     "- **Traitement :** plus de lits de désintoxication et de traitement, avec le personnel nécessaire pour accueillir les patients, dans le sud de l'île, avec les délais d'attente publiés chaque mois (ma position). Des soins dans un milieu sécurisé, assortis de garanties médicales et juridiques, pour les personnes ayant une dépendance grave qui représentent un danger pour elles-mêmes ou pour autrui (ma position)."),
    ("sub", "(ma position; le programme 2024 du parti proposait aussi d'orienter les campeurs vers les services de soutien).", "(ma position)."),
    ("line", "- **Tribunaux :** 50 nouveaux procureurs", "- **Tribunaux :** ajouter des shérifs et des juges pour que les procès se tiennent plus vite, et je voterai pour financer les tribunaux, les poursuites et les shérifs. La mise en liberté sous caution relève du droit fédéral; pour les récidivistes violents, je presserai donc Ottawa d'y apporter des modifications (ma position)."),
    ("sub", "Le parti s'est engagé à mettre fin à l'« approvisionnement plus sécuritaire » et à élargir l'accès à la naloxone ([Safe Streets for BC, 6 oct. 2026](https://conservativebc.ca/safe-streets-for-bc/), en anglais). Les deux vont ensemble :",
     "Je mettrais fin à l'« approvisionnement plus sécuritaire » et j'élargirais l'accès à la naloxone. Les deux vont ensemble :"),
    ("sub", " Le parti s'est engagé à une intervention bienveillante, pour que les personnes atteintes d'une dépendance grave, d'une maladie mentale ou d'une lésion cérébrale soient retirées de la rue et prises en charge, et à interdire la consommation de drogues illégales dans les hôpitaux, les refuges et les logements avec services de soutien financés par l'État (Safe Streets for BC).", ""),
    ("sub", "l'impôt provincial sur le revenu, la TVP, les tarifs des traversiers, et les frais de logement, par le régime fiscal.", "l'impôt provincial sur le revenu et les tarifs des traversiers."),
    ("sub", " L'année et le financement suivent le plan financier publié par le parti.", " Aucune année ni aucun coût n'ont été publiés, et je n'en afficherai pas."),
    ("dropline", "- Aucune TVP pendant 3 ans sur la machinerie"),
    ("dropline", "- Aucune TVP à la caisse sur la bière"),
    ("dropline", "- Un plan dans les 180 jours pour simplifier"),
    ("line", "- Tarifs des traversiers : consulter les navetteurs", "- Tarifs des traversiers : consulter les navetteurs et les autres usagers réguliers sur un programme de forfait mensuel ou d'autres mesures (ma position)."),
    ("dropline", "- Aucune TVP sur les voitures d'occasion abordables"),
    ("dropline", "- L'allègement de l'impôt sur le revenu lié aux frais de logement décrit plus haut"),
    ("dropline", "- Ramener le taux d'imposition des petites entreprises de 2 % à 1 %"),
    ("line", "Je ne couperai pas les soins de santé ou l'éducation pour écrire un slogan. Le parti",
     "Je ne couperai pas les soins de santé ou l'éducation pour écrire un slogan. Je n'inventerai pas non plus un chiffre d'économies. Un budget équilibré n'est pas une économie pour votre ménage; c'est ce qui permet de vérifier que les engagements sont financés."),
    ("sub", " Je comprends le plan du parti sur les formalités administratives ([Supercharge British Columbia's Economy, 7 oct. 2026](https://conservativebc.ca/supercharge-british-columbias-economy/), en anglais) comme moins de règles et de formulaires, pas moins de fonctionnaires, et c'est ainsi que je voterai (ma position).",
     " Réduire les formalités administratives doit vouloir dire moins de règles et de formulaires, pas moins de fonctionnaires, et c'est ainsi que je voterai (ma position)."),
    ("sub", "qui énonce les attentes en matière de service et de rendement (programme 2024 du parti).", "qui énonce les attentes en matière de service et de rendement (ma position)."),
    ("line", "Les mesures importantes viennent du programme 2024 du parti.", "Le retour au taux de 5,06 % et le rétablissement de l'indexation n'ont pas encore de coût publié, et je n'afficherai pas de chiffre de mon cru. Un budget équilibré permet de vérifier que les changements fiscaux sont financés; je voterai donc contre un projet de loi qui ne dit pas ce qu'il coupe."),
    ("dropline", "- Allègement de l'impôt sur le revenu lié aux frais de logement (loyer, intérêts hypothécaires et frais de copropriété) : environ 900"),
    ("dropline", "- Taux d'imposition des petites entreprises ramené à 1 %"),
    ("dropline", "- Get BC Building (infrastructures"),
    ("dropline", "- Aucune TVP sur les véhicules d'occasion abordables : fait partie"),
    ("dropline", "En 2024, le parti a dit qu'une croissance économique plus rapide"),
    ("dropline", "du parti (6 oct. 2026, en anglais) ajoute 250 policiers"),
    ("sub", "Les mesures qui sont les miennes — réduire la paperasse des médecins (aussi dans le programme 2024), l'élargissement", "La plupart de mes propositions — réduire la paperasse des médecins, des délais fixes pour les permis, l'élargissement"),
    ("sub", "des normes de service pour la fonction publique — sont surtout des changements", "des normes de service pour la fonction publique — sont des changements"),
    ("q", "Quelles propositions sont des engagements du parti, et lesquelles sont les vôtres?", "D'où viennent ces propositions?",
     ["Ce sont mes propres positions. Chaque chiffre renvoie à sa source, et le [bulletin](https://agou.ca/fr/scorecard/) montre comment vous pourrez vérifier les résultats chaque trimestre."]),
    ("q", "Que pourriez-vous accomplir si votre parti ne forme pas le gouvernement?", "Que pourriez-vous accomplir si vous n'êtes pas au gouvernement?",
     ["Les députés de l'opposition votent quand même sur chaque loi, proposent des amendements et des projets de loi émanant des députés, interrogent les ministres, siègent à des comités qui examinent les dépenses et aident les résidents dans leurs démarches auprès du gouvernement ([Assemblée législative, en anglais](https://www.leg.bc.ca/learn/discover-your-legislature/about-the-legislative-assembly)). J'utiliserais tous ces moyens, et je publierais le même bilan trimestriel dans les deux cas.",
      "Je peux faire consigner des chiffres au compte rendu officiel, amender de mauvais projets de loi et aider un voisin à débloquer un dossier dans un organisme provincial."]),
    ("sub", "Grace Lore (NPD de la C.-B.), Raj Sahota (Parti vert de la C.-B., inscrit sur le bulletin de vote sous le nom de Rajinder S. Sahota) et moi (Parti conservateur de la C.-B.).", "Grace Lore, Raj Sahota (inscrit sur le bulletin de vote sous le nom de Rajinder S. Sahota) et moi."),
    ("sub", "<summary>Comment représenteriez-vous les résidents qui ne partagent pas vos idées ou celles de votre parti?</summary>", "<summary>Comment représenteriez-vous les résidents qui ne partagent pas vos idées?</summary>"),
    ("dropline", "Si la politique du parti allait à l'encontre des besoins"),
    ("dropq", "Comment faire un don?"),
]

UI = {
    "en": {"volunteer": {"sub": "Victoria–Beacon Hill · Provincial election 24 October 2026",
                         "consent": "I agree that the Joachim Agou campaign (Victoria–Beacon Hill) may contact me by email, phone or text about volunteering. I can ask to stop at any time."},
           "nominate": {"sub": "Running to be the Member of the Legislative Assembly (MLA) for Victoria–Beacon Hill · Provincial election 24 October 2026"},
           "lawnsign": {"sub": "Joachim Agou · Victoria–Beacon Hill · Provincial election 24 October 2026",
                        "consent": "I agree that the Joachim Agou campaign (Victoria–Beacon Hill) may contact me by email, phone or text about my lawn sign and the campaign. I can ask to stop at any time."},
           "events": {"consent": "I agree that the Joachim Agou campaign (Victoria–Beacon Hill) may contact me by email, phone or text about this event and the campaign. I can ask to stop at any time."},
           "shifts": {"consent": "I agree that the Joachim Agou campaign (Victoria–Beacon Hill) may contact me by email, phone or text about this shift and about volunteering with the campaign. I can ask to stop at any time."}},
    "fr": {"volunteer": {"sub": "Victoria–Beacon Hill · Élection provinciale du 24 octobre 2026",
                         "consent": "J'accepte que la campagne de Joachim Agou (Victoria–Beacon Hill) communique avec moi par courriel, téléphone ou texto au sujet du bénévolat. Je peux demander que cela cesse à tout moment."},
           "nominate": {"sub": "Je me présente pour représenter Victoria–Beacon Hill à l'Assemblée législative · Élection provinciale du 24 octobre 2026"},
           "lawnsign": {"sub": "Joachim Agou · Victoria–Beacon Hill · Élection provinciale du 24 octobre 2026",
                        "consent": "J'accepte que la campagne de Joachim Agou (Victoria–Beacon Hill) communique avec moi par courriel, téléphone ou texto au sujet de ma pancarte et de la campagne. Je peux demander que cela cesse à tout moment."},
           "events": {"consent": "J'accepte que la campagne de Joachim Agou (Victoria–Beacon Hill) communique avec moi par courriel, téléphone ou texto au sujet de cet événement et de la campagne. Je peux demander que cela cesse à tout moment."},
           "shifts": {"consent": "J'accepte que la campagne de Joachim Agou (Victoria–Beacon Hill) communique avec moi par courriel, téléphone ou texto au sujet de ce quart et du bénévolat pour la campagne. Je peux demander que cela cesse à tout moment."}},
}
SEO = {"pages": {
    "home": {"en": {"desc": "Joachim Agou, a test engineer, is running to be the MLA for Victoria–Beacon Hill. Safer streets, honest budgets, a downtown that works."},
             "fr": {"desc": "Joachim Agou, ingénieur d'essais, se présente pour devenir le député de Victoria–Beacon Hill : rues plus sûres, budgets honnêtes, centre-ville qui fonctionne."}},
    "get-involved": {"en": {"desc": "Help Joachim Agou in Victoria–Beacon Hill: volunteer, request a lawn sign or come to an event. Pick what fits your time."},
                     "fr": {"desc": "Aidez Joachim Agou dans Victoria–Beacon Hill : bénévolat, pancarte ou événements. Choisissez ce qui convient à votre emploi du temps."}}}}
MANIFEST_DESC = {"en": "Joachim Agou, running to be the MLA for Victoria–Beacon Hill", "fr": "Joachim Agou, candidat dans Victoria–Beacon Hill"}

PRIO_T = {
    "en": {"glance_note": "Each promise below says what it means for you. “Details and sources” opens the full text, figures and links. Every one is my own position.",
           "hiw_intro": "I'm an engineer: I start with the problem, measure it, fix it and report the result. Every promise on this page is my own position:",
           "legend": {"mine": "mine, with the source of each figure linked in its details."}},
    "fr": {"glance_note": "Chaque engagement ci-dessous dit ce qu'il change pour vous. « Détails et sources » affiche le texte complet, les chiffres et les liens. Chacun est ma propre position.",
           "hiw_intro": "Je suis ingénieur : je pars du problème, j'en évalue l'ampleur, j'y apporte une solution et je rends compte du résultat. Chaque engagement de cette page est ma propre position :",
           "legend": {"mine": "la mienne, avec la source de chaque chiffre en lien dans ses détails."}},
}
# 'For you' lines: drop the lines of dropped promises (0-based, per section), replace the ones whose promise changed.
FY_DROP = {"1-health-care-you-can-get": [5], "2-homes-people-can-afford": [2, 3], "3-cost-of-living": [5, 6, 7], "4-a-downtown-that-works": [0, 4]}
FY_SET = {
    "en": {("2-homes-people-can-afford", 0): "Fixed deadlines for permits: homes get built sooner, which eases rents over time.",
           ("4-a-downtown-that-works", 6): "More sheriffs and judges: cases reach trial faster, for victims and for the accused.",
           ("4-a-downtown-that-works", 8): "Business permit wait times published, so a local business can plan when it opens or expands."},
    "fr": {("2-homes-people-can-afford", 0): "Des délais fixes pour les permis : les logements sont construits plus tôt, ce qui contribue à faire baisser les loyers au fil du temps.",
           ("4-a-downtown-that-works", 6): "Plus de shérifs et de juges : des procès tenus plus vite, pour les victimes comme pour les accusés.",
           ("4-a-downtown-that-works", 8): "Des délais de délivrance des permis commerciaux publiés : une entreprise d'ici peut planifier son ouverture ou son agrandissement."},
}


def for_you(data):
    """data/priorities-for-you.json -> the no-party version (lines and short titles renumbered after dropped promises)."""
    out = {k: v for k, v in data.items() if k not in ("en", "fr", "short_titles")}
    for lang in ("en", "fr"):
        out[lang] = {}
        for sid, lines in data[lang].items():
            lines = list(lines)
            for (s, i), txt in FY_SET[lang].items():
                if s == sid: lines[i] = txt
            out[lang][sid] = [l for i, l in enumerate(lines) if i not in FY_DROP.get(sid, [])]
    st = {}
    for lang, secs in data.get("short_titles", {}).items():
        st[lang] = {}
        for sid, m in secs.items():
            drop = FY_DROP.get(sid, []); nm = {}
            for n, t in m.items():
                i = int(n) - 1
                if i in drop: continue
                nm[str(i - sum(1 for d in drop if d < i) + 1)] = t
            st[lang][sid] = nm
    if "4" in st.get("fr", {}).get("2-homes-people-can-afford", {}): raise SystemExit("no_party: FR short title for the dropped housing tax relief survived")
    out["short_titles"] = st
    return out


def event_text_has_party(e):
    """True when an event's public text names the party (venue names like the Victoria Conservatory of Music are fine: ALLOW)."""
    t = " ".join(str(e.get(k) or "") for k in ("title", "title_fr", "description", "description_fr", "location_name", "location_name_fr", "signup_url"))
    for m in TERMS.finditer(t):
        if not allowed(t, m): return True
    return False


def scan(dist):
    """Every party-term hit in the built site (HTML/JS/JSON/XML/txt/webmanifest, and PDF text), minus the reviewed ALLOW contexts."""
    import subprocess
    hits = []
    for f in sorted(dist.rglob("*")):
        if not f.is_file(): continue
        if f.suffix in (".html", ".js", ".json", ".xml", ".txt", ".webmanifest", ".css", ".svg", ".ics", ".md") or f.name == "_redirects":
            t = f.read_text(errors="replace")
        elif f.suffix == ".pdf":
            try: t = subprocess.check_output(["pdftotext", "-enc", "UTF-8", str(f), "-"], text=True)
            except Exception as e: hits.append((f, "cannot read PDF", str(e), None)); continue
        else: continue
        for m in TERMS.finditer(t):
            ctx = t[max(0, m.start() - 80):m.end() + 80]
            why = allowed(t, m)
            hits.append((f, m.group(0), re.sub(r"\s+", " ", ctx), why))
    return hits


def _merge(dst, src):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict): _merge(dst[k], v)
        else: dst[k] = v


def hide_ids():
    """Event ids to leave out of this build: 114 (Thanksgiving Rally, a party event) and any public event or shift whose
    text names the party. Read-only call to the public get_public_events / get_public_shifts rpcs; nothing is written."""
    import urllib.request, events_cal
    ids = {114}
    for fn in ("get_public_events", "get_public_shifts"):
        try:
            req = urllib.request.Request(events_cal.SUPABASE_URL + "/rest/v1/rpc/" + fn, data=b"{}", method="POST",
                                         headers={"apikey": events_cal.SUPABASE_KEY, "Content-Type": "application/json"})
            for e in json.loads(urllib.request.urlopen(req, timeout=10).read()):
                if event_text_has_party(e):
                    ids.add(e["id"]); print(f"no_party: hiding {fn} id {e['id']} ({e.get('title')})")
        except Exception as ex:
            print(f"WARNING: no_party could not read {fn} ({ex.__class__.__name__}); hiding 114 only")
    return ids


def setup(hidden, ui, seo, prio_layout, events_cal, root):
    """Called by build.py __main__ when no_party_v1 is on for this env."""
    hidden.add("donate")
    _merge(ui, UI); _merge(seo, SEO)
    for lang in ("en", "fr"): _merge(prio_layout.T[lang], PRIO_T[lang])
    prio_layout.LEGEND = ("mine",)
    prio_layout.DATA_OVERRIDE = for_you(json.loads((root / "data/priorities-for-you.json").read_text()))
    events_cal.HIDE = hide_ids()
