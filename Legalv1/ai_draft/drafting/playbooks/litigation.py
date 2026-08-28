"""
Litigation playbooks — plaint, written statement, bail, anticipatory bail,
writ petition, consumer complaint, affidavit, vakalatnama.

Two of these (`bail`, `anticipatory_bail`) are the only playbooks in the package
with `branch = CRIMINAL`. They are therefore the only ones whose prompt receives
`build_bns_prompt_fragment()` and whose `deny_patterns` is empty — the penal
codes belong in a bail application and nowhere else in this file.

The corpus backs plaint (4 `Pleadings/` RTFs), affidavit (9) and vakalatnama (3)
well; written statement, anticipatory bail and consumer complaint have no
precedent at all and rely on the skeleton alone until §10.6 sourcing lands.
"""

from __future__ import annotations

from .base import CIVIL, CONSTITUTIONAL, CRIMINAL, Playbook, Section

PLEADING_CONVENTIONS = (
    'Open with the cause title — the court, the case number placeholder, and the '
    'array of parties with their full description and address, each numbered.',
    'Body paragraphs are numbered and each begins with the word "That".',
    'Refer to parties by their procedural description ("the Plaintiff", "the '
    'Defendant No. 1", "the Petitioner"), not by bare personal names.',
    'State amounts as "Rs. 5,00,000/- (Rupees Five Lakh only)".',
    'Close with the prayer, then place, date, and signature blocks for the party '
    'and the advocate.',
)

_VERIFICATION = Section(
    name='VERIFICATION',
    guidance=(
        'Verified at [PLACE] on [DATE]. State which paragraphs are true to the '
        'deponent\'s personal knowledge and which are believed to be true on legal '
        'advice or information derived from records — the two categories must be '
        'separated by paragraph number.'
    ),
    must_contain=(('Verified', 'verification'),),
)


# ---------------------------------------------------------------------------
PLAINT = Playbook(
    doc_type='plaint',
    label='Plaint (Civil Suit)',
    branch=CIVIL,
    category='Pleadings',
    aliases=('plaint', 'civil suit', 'suit'),
    keywords=(
        (r'\bplaint\b', 8),
        (r'\bfile\s+a?\s*suit\b|\bcivil\s+suit\b', 6),
        (r'\bplaintiff\b', 4),
        (r'\bdecree\b|\bpermanent\s+injunction\b', 3),
    ),
    skeleton=(
        Section(
            name='CAUSE TITLE',
            guidance=(
                'IN THE COURT OF [COURT], AT [PLACE]. Suit No. ____ of [YEAR]. Then the '
                'parties: full name, age, parentage, occupation and address, described as '
                'Plaintiff and Defendant(s).'
            ),
            must_contain=(('IN THE COURT OF', 'BEFORE THE'),),
        ),
        Section(
            name='SUIT DESCRIPTION',
            guidance='One line naming the nature of the suit and the relief sought.',
        ),
        Section(
            name='FACTS / STATEMENT OF CLAIM',
            guidance=(
                'Numbered "That" paragraphs in chronological order setting out the '
                'material facts constituting the claim. Plead facts, not evidence and not '
                'law.'
            ),
            must_contain=('That ',),
        ),
        Section(
            name='CAUSE OF ACTION',
            guidance=(
                'State when and where the cause of action arose, with the specific date '
                'of each accrual. Required by Order VII Rule 1(e) of the Code of Civil '
                'Procedure, 1908.'
            ),
            must_contain=(('cause of action',),),
        ),
        Section(
            name='JURISDICTION',
            guidance=(
                'Plead both territorial and pecuniary jurisdiction, and the facts that '
                'establish each.'
            ),
            must_contain=(('jurisdiction',),),
        ),
        Section(
            name='LIMITATION',
            guidance=(
                'State that the suit is within limitation and identify the Article of the '
                'Limitation Act, 1963 relied upon, or the ground of exclusion.'
            ),
            must_contain=(('limitation',),),
        ),
        Section(
            name='VALUATION AND COURT FEE',
            guidance=(
                'State the value of the subject matter for the purposes of court fee and '
                'jurisdiction, and the court fee paid.'
            ),
            must_contain=(('court fee', 'court-fee'),),
        ),
        Section(
            name='PRAYER',
            guidance=(
                'Lettered sub-clauses beginning "It is therefore most respectfully prayed '
                'that this Hon\'ble Court may be pleased to:". Each relief must be '
                'specific and capable of being decreed. Close with a prayer for costs and '
                'for such further relief as the Court deems fit.'
            ),
            must_contain=(('most respectfully prayed', 'prayed that this'),),
        ),
        _VERIFICATION,
        Section(
            name='LIST OF DOCUMENTS',
            guidance='Numbered list of documents filed with the plaint, per Order VII Rule 14.',
            required=False,
        ),
    ),
    conventions=PLEADING_CONVENTIONS,
    statutes_allow=(
        'Code of Civil Procedure, 1908 (Order VI, Order VII, s. 26)',
        'Limitation Act, 1963',
        'Court Fees Act, 1870, and the applicable State amendment',
        'Specific Relief Act, 1963',
        'Indian Contract Act, 1872',
        'Transfer of Property Act, 1882',
    ),
    pitfalls=(
        'A civil plaint must not cite the BNS, BNSS, BSA, IPC, CrPC or the Indian '
        'Evidence Act. Where the same facts also disclose an offence, say so in words '
        'without citing a penal section.',
        'Cause of action, jurisdiction, limitation and valuation are mandatory averments. '
        'A plaint missing any of them is liable to rejection under Order VII Rule 11.',
        'Plead material facts only — not the evidence by which they will be proved, and '
        'not legal argument.',
        'The prayer must be specific. A vague prayer for "appropriate relief" cannot be '
        'decreed.',
        'Do not assert a court-fee amount unless it is given; state the valuation and '
        'mark the fee "(to be computed as per the applicable State schedule)".',
    ),
    required_facts=(
        'the court and its territorial jurisdiction',
        'full particulars of every party',
        'the date on which the cause of action arose',
        'the value of the subject matter',
    ),
    kb_doc_types=('Pleadings',),
    min_sections=9,
    target_tokens=8000,
)


# ---------------------------------------------------------------------------
WRITTEN_STATEMENT = Playbook(
    doc_type='written_statement',
    label='Written Statement',
    branch=CIVIL,
    category='Pleadings',
    aliases=('written statement', 'written_statement', 'reply to plaint', 'ws'),
    keywords=(
        (r'written\s+statement', 9),
        (r'\breply\s+to\s+(the\s+)?plaint\b', 6),
        (r'\bdefendant\b.*\breply\b|\breply\b.*\bdefendant\b', 3),
        (r'\bcounter\s*claim\b|\bset[- ]off\b', 4),
    ),
    skeleton=(
        Section(
            name='CAUSE TITLE',
            guidance='The same cause title as the plaint, with the suit number filled in.',
            must_contain=(('IN THE COURT OF', 'BEFORE THE'),),
        ),
        Section(
            name='PRELIMINARY OBJECTIONS',
            guidance=(
                'Numbered "That" paragraphs raising threshold objections: maintainability, '
                'limitation, cause of action, jurisdiction, non-joinder or misjoinder of '
                'parties, and bar by any statute.'
            ),
            must_contain=('That ',),
        ),
        Section(
            name='PARAWISE REPLY',
            guidance=(
                'Reply to each paragraph of the plaint by its number. Admit, deny, or state '
                'that the Defendant has no knowledge and puts the Plaintiff to strict proof. '
                'Every allegation not specifically denied is deemed admitted.'
            ),
            must_contain=(('parawise', 'para-wise', 'paragraph'),),
        ),
        Section(
            name='ADDITIONAL PLEAS',
            guidance='The Defendant\'s own version of the facts, in numbered "That" paragraphs.',
        ),
        Section(
            name='SET-OFF OR COUNTERCLAIM',
            guidance=(
                'Where the Defendant claims a sum from the Plaintiff, plead it as a set-off '
                'or counterclaim under Order VIII Rules 6 and 6A, with its own valuation '
                'and court fee.'
            ),
            required=False,
        ),
        Section(
            name='PRAYER',
            guidance='Prayer for dismissal of the suit with costs.',
            must_contain=(('prayed', 'prayer'),),
        ),
        _VERIFICATION,
    ),
    conventions=PLEADING_CONVENTIONS,
    statutes_allow=(
        'Code of Civil Procedure, 1908 (Order VIII — especially Rules 1, 3, 4, 5, 6 and 6A)',
        'Limitation Act, 1963',
        'Indian Contract Act, 1872',
    ),
    pitfalls=(
        'A civil written statement must not cite the BNS, BNSS, BSA, IPC, CrPC or the '
        'Indian Evidence Act.',
        'Denials must be specific. An evasive denial, or a failure to deal with an '
        'allegation, is deemed an admission under Order VIII Rules 3 to 5 — this is the '
        'single most common drafting failure in a written statement.',
        'A written statement is due within 30 days of service, extendable for recorded '
        'reasons to 90 days; in a commercial suit the 120-day outer limit is mandatory '
        'and the right to file stands forfeited thereafter.',
        'A counterclaim requires its own valuation and court fee — it is a cross-suit, '
        'not an argument.',
    ),
    required_facts=(
        'the suit number and the court',
        'the paragraph structure of the plaint being replied to',
        'the date of service of summons',
    ),
    min_sections=6,
    target_tokens=8000,
)


# ---------------------------------------------------------------------------
# The two criminal playbooks. branch=CRIMINAL => deny_patterns is empty and the
# prompt receives the verified IPC->BNS / CrPC->BNSS correspondence table.
# ---------------------------------------------------------------------------
_CRIMINAL_PITFALL_CODES = (
    'Lead with the 2023 codes: BNS replaced the IPC, BNSS replaced the CrPC, BSA '
    'replaced the Indian Evidence Act. Give the old-code equivalent in parentheses on '
    'first mention, and use ONLY the verified correspondences supplied to you. For any '
    'provision not in that list, name the offence in words and mark the section '
    '"(exact section to be confirmed)" — never guess a section number.'
)

BAIL = Playbook(
    doc_type='bail',
    label='Bail Application',
    branch=CRIMINAL,
    category='Criminal',
    aliases=('bail', 'bail application', 'regular bail'),
    keywords=(
        (r'\bbail\b', 7),
        (r'\banticipatory\b', -6),          # steer to the anticipatory playbook
        (r'\bjudicial\s+custody\b|\bremand\b', 3),
        (r'\bFIR\b|\barrest', 3),
    ),
    skeleton=(
        Section(
            name='CAUSE TITLE',
            guidance=(
                'IN THE COURT OF [COURT]. Bail Application No. ____ of [YEAR]. In the '
                'matter of FIR No. [NO.] dated [DATE], Police Station [PS], under Sections '
                '[SECTIONS] of the Bharatiya Nyaya Sanhita, 2023. Applicant versus the '
                'State.'
            ),
            must_contain=(('IN THE COURT OF', 'BEFORE THE'),),
        ),
        Section(
            name='APPLICATION UNDER',
            guidance=(
                'Name the enabling provision — s. 480 BNSS (formerly s. 437 CrPC) before a '
                'Magistrate, or s. 483 BNSS (formerly s. 439 CrPC) before the Sessions '
                'Court or High Court.'
            ),
        ),
        Section(
            name='FACTS',
            guidance=(
                'Numbered "That" paragraphs: the registration of the FIR, the sections '
                'invoked, the date of arrest, the applicant\'s custody status, and the '
                'stage of investigation.'
            ),
            must_contain=('That ',),
        ),
        Section(
            name='GROUNDS',
            guidance=(
                'Lettered or numbered grounds: the applicant is innocent and falsely '
                'implicated; the offence is triable by a Magistrate / not punishable with '
                'death or life imprisonment; the applicant has roots in society and is not '
                'a flight risk; no likelihood of tampering with evidence or influencing '
                'witnesses; custodial interrogation is not required; parity with a '
                'co-accused already enlarged on bail; period already undergone in custody.'
            ),
        ),
        Section(
            name='PRAYER',
            guidance=(
                'Prayer for release on bail on such terms and conditions as the Court may '
                'impose, with an undertaking to abide by them and to attend on every date.'
            ),
            must_contain=(('most respectfully prayed', 'prayed that this'),),
        ),
        Section(
            name='AFFIDAVIT IN SUPPORT',
            guidance='Short affidavit of the applicant or a relative verifying the contents.',
            required=False,
        ),
    ),
    conventions=PLEADING_CONVENTIONS,
    statutes_allow=(
        'Bharatiya Nagarik Suraksha Sanhita, 2023 — s. 480 (formerly CrPC s. 437), '
        's. 483 (formerly CrPC s. 439), s. 478 (formerly s. 436)',
        'Bharatiya Nyaya Sanhita, 2023 — for the substantive offences alleged',
        'Bharatiya Sakshya Adhiniyam, 2023',
        'Constitution of India, Articles 21 and 22',
    ),
    pitfalls=(
        _CRIMINAL_PITFALL_CODES,
        'Do not assert the sections of the FIR unless they are given in the facts. If they '
        'are not supplied, use [SECTIONS] as a placeholder and record the gap in the '
        'assumptions — never invent the offences charged.',
        'Distinguish the forum: s. 480 BNSS lies before the Magistrate, s. 483 BNSS before '
        'the Sessions Court or High Court. Applying to the wrong forum is fatal.',
        'Where the offence falls under a special statute (NDPS, PMLA, UAPA), the general '
        'bail provisions are subject to that statute\'s own restrictions — say so rather '
        'than pleading as if only the BNSS applied.',
        'Do not plead the merits as though at trial. A bail application addresses custody, '
        'not guilt.',
    ),
    required_facts=(
        'the FIR number, date and police station',
        'the sections under which the FIR is registered',
        'the date of arrest and the current custody status',
        'the court before which the application lies',
    ),
    kb_doc_types=('BAIL',),
    min_sections=5,
    target_tokens=6000,
)


ANTICIPATORY_BAIL = Playbook(
    doc_type='anticipatory_bail',
    label='Anticipatory Bail Application',
    branch=CRIMINAL,
    category='Criminal',
    aliases=('anticipatory bail', 'anticipatory_bail', 'pre-arrest bail'),
    keywords=(
        (r'\banticipatory\b', 10),
        (r'\bpre[- ]arrest\b', 7),
        (r'\bapprehend\w*\s+arrest\b', 6),
        (r'\b482\b|\b438\b', 4),
    ),
    skeleton=(
        Section(
            name='CAUSE TITLE',
            guidance=(
                'IN THE COURT OF [SESSIONS COURT / HIGH COURT]. Anticipatory Bail '
                'Application No. ____ of [YEAR], in the matter of FIR No. [NO.].'
            ),
            must_contain=(('IN THE COURT OF', 'BEFORE THE'),),
        ),
        Section(
            name='APPLICATION UNDER',
            guidance=(
                'Application under s. 482 of the Bharatiya Nagarik Suraksha Sanhita, 2023 '
                '(formerly s. 438 of the CrPC) for direction to release the applicant on '
                'bail in the event of arrest.'
            ),
            must_contain=(('482', 'anticipatory'),),
        ),
        Section(
            name='FACTS',
            guidance=(
                'Numbered "That" paragraphs setting out the FIR or the apprehension of '
                'arrest, the applicant\'s version, and the reasonable grounds for believing '
                'that the applicant may be arrested for a non-bailable offence.'
            ),
            must_contain=('That ',),
        ),
        Section(
            name='GROUNDS',
            guidance=(
                'False implication and its motive; the applicant\'s cooperation with '
                'investigation; absence of any need for custodial interrogation; no '
                'antecedents; readiness to abide by conditions under s. 482(2) BNSS.'
            ),
        ),
        Section(
            name='PRAYER',
            guidance=(
                'Prayer for a direction that in the event of arrest the applicant be '
                'released on bail, and for interim protection pending disposal.'
            ),
            must_contain=(('most respectfully prayed', 'prayed that this'),),
        ),
    ),
    conventions=PLEADING_CONVENTIONS,
    statutes_allow=(
        'Bharatiya Nagarik Suraksha Sanhita, 2023 — s. 482 (formerly CrPC s. 438)',
        'Bharatiya Nyaya Sanhita, 2023 — for the substantive offences alleged',
        'Constitution of India, Article 21',
    ),
    pitfalls=(
        _CRIMINAL_PITFALL_CODES,
        'Anticipatory bail presupposes a reasonable apprehension of arrest for a '
        'NON-BAILABLE offence. Plead the grounds of that apprehension specifically.',
        'The application lies only before the Court of Session or the High Court — never '
        'before a Magistrate.',
        'Anticipatory bail is not available where the applicant is already in custody; in '
        'that case the remedy is regular bail under s. 483 BNSS.',
    ),
    required_facts=(
        'whether an FIR has been registered, and its particulars if so',
        'the offences apprehended',
        'the court before which the application lies',
    ),
    min_sections=5,
    target_tokens=6000,
)


# ---------------------------------------------------------------------------
WRIT_PETITION = Playbook(
    doc_type='writ_petition',
    label='Writ Petition (Art. 226 / 32)',
    branch=CONSTITUTIONAL,
    category='Constitutional',
    aliases=('writ', 'writ petition', 'writ_petition', 'article 226', 'article 32'),
    keywords=(
        (r'\bwrit\b', 9),
        (r'article\s*226|article\s*32', 8),
        (r'\bmandamus\b|\bcertiorari\b|\bhabeas\s+corpus\b|\bquo\s+warranto\b|\bprohibition\b', 7),
        (r'\bfundamental\s+right', 5),
    ),
    skeleton=(
        Section(
            name='CAUSE TITLE',
            guidance=(
                'IN THE HIGH COURT OF [STATE] AT [PLACE] — or IN THE SUPREME COURT OF INDIA '
                'for Article 32. Writ Petition (Civil/Criminal) No. ____ of [YEAR], with '
                'the array of Petitioners and Respondents.'
            ),
            must_contain=(('IN THE HIGH COURT', 'IN THE SUPREME COURT'),),
        ),
        Section(
            name='PETITION UNDER',
            guidance=(
                'Name the article invoked and the writ sought, e.g. "Petition under Article '
                '226 of the Constitution of India for a writ of mandamus".'
            ),
            must_contain=(('Article 226', 'Article 32'),),
        ),
        Section(
            name='SYNOPSIS AND LIST OF DATES',
            guidance='A short synopsis followed by a chronological table of material dates.',
            required=False,
        ),
        Section(
            name='FACTS',
            guidance=(
                'Numbered "That" paragraphs: the petitioner\'s standing, the impugned action '
                'or inaction, the authority responsible, and the representations made.'
            ),
            must_contain=('That ',),
        ),
        Section(
            name='GROUNDS',
            guidance=(
                'Lettered grounds, each identifying the constitutional or statutory '
                'violation — breach of a fundamental right under Part III, violation of '
                'natural justice, arbitrariness under Article 14, or action without '
                'jurisdiction.'
            ),
        ),
        Section(
            name='ALTERNATIVE REMEDY',
            guidance=(
                'Aver that no equally efficacious alternative remedy is available, or '
                'explain why the existing remedy is inadequate.'
            ),
            required=False,
        ),
        Section(
            name='PRAYER',
            guidance=(
                'Lettered prayers naming the writ sought, the impugned order to be quashed, '
                'and the direction sought against the Respondents.'
            ),
            must_contain=(('most respectfully prayed', 'prayed that this'),),
        ),
        Section(
            name='INTERIM RELIEF',
            guidance='Prayer for stay of the impugned action pending disposal.',
            required=False,
        ),
        _VERIFICATION,
    ),
    conventions=PLEADING_CONVENTIONS,
    statutes_allow=(
        'Constitution of India — Articles 12, 14, 19, 21, 226, 227, 32, 300A',
        'The statute under which the impugned action was taken',
        'The applicable High Court Rules',
    ),
    pitfalls=(
        'A writ petition is a constitutional remedy. Do not cite the BNS, BNSS or BSA '
        'unless the petition arises from a criminal proceeding, and even then cite them '
        'only for the underlying matter.',
        'Article 32 lies only for enforcement of fundamental rights and only before the '
        'Supreme Court. Article 226 is wider and lies before the High Court.',
        'A writ lies against the State or an instrumentality of the State under Article 12, '
        'not ordinarily against a private party.',
        'Plead exhaustion or inadequacy of the alternative remedy — its absence is the '
        'commonest ground of dismissal at the threshold.',
        'Identify the specific writ sought. "Any appropriate writ" invites dismissal.',
    ),
    required_facts=(
        'the impugned order or action and its date',
        'the authority against whom relief is sought',
        'the fundamental or legal right said to be violated',
        'the representations made and their outcome',
    ),
    kb_doc_types=('Writ',),
    min_sections=7,
    target_tokens=8000,
)


# ---------------------------------------------------------------------------
CONSUMER_COMPLAINT = Playbook(
    doc_type='consumer_complaint',
    label='Consumer Complaint',
    branch=CIVIL,
    category='Consumer',
    aliases=('consumer complaint', 'consumer_complaint', 'consumer case'),
    keywords=(
        (r'\bconsumer\b', 8),
        (r'deficiency\s+in\s+service', 7),
        (r'unfair\s+trade\s+practice', 6),
        (r'\bconsumer\s+(forum|commission)\b', 7),
    ),
    skeleton=(
        Section(
            name='CAUSE TITLE',
            guidance=(
                'BEFORE THE [DISTRICT / STATE / NATIONAL] CONSUMER DISPUTES REDRESSAL '
                'COMMISSION AT [PLACE]. Consumer Complaint No. ____ of [YEAR]. Complainant '
                'versus Opposite Party.'
            ),
            must_contain=(('CONSUMER DISPUTES REDRESSAL', 'BEFORE THE'),),
        ),
        Section(
            name='COMPLAINT UNDER',
            guidance=(
                'Complaint under s. 35 of the Consumer Protection Act, 2019.'
            ),
            must_contain=(('Consumer Protection Act',),),
        ),
        Section(
            name='FACTS',
            guidance=(
                'Numbered "That" paragraphs: that the Complainant is a "consumer" within '
                's. 2(7); the goods bought or service availed, with date and consideration; '
                'the defect or deficiency; the complaints made and the response.'
            ),
            must_contain=('That ',),
        ),
        Section(
            name='DEFICIENCY IN SERVICE / DEFECT',
            guidance=(
                'Characterise the grievance as a defect in goods under s. 2(10), a '
                'deficiency in service under s. 2(11), or an unfair trade practice under '
                's. 2(47), and plead the facts constituting it.'
            ),
        ),
        Section(
            name='JURISDICTION AND LIMITATION',
            guidance=(
                'Plead pecuniary jurisdiction by reference to the consideration paid, '
                'territorial jurisdiction under s. 34(2), and that the complaint is within '
                'the two-year period under s. 69.'
            ),
            must_contain=(('jurisdiction',),),
        ),
        Section(
            name='RELIEF CLAIMED',
            guidance=(
                'Lettered reliefs: refund or replacement, compensation for deficiency, '
                'compensation for mental agony and harassment, and costs of the '
                'proceedings.'
            ),
            must_contain=(('prayed', 'relief'),),
        ),
        _VERIFICATION,
    ),
    conventions=PLEADING_CONVENTIONS,
    statutes_allow=(
        'Consumer Protection Act, 2019 — ss. 2(7), 2(10), 2(11), 2(47), 34, 35, 69',
        'Consumer Protection (Consumer Disputes Redressal Commissions) Rules, 2020',
        'Indian Contract Act, 1872',
    ),
    pitfalls=(
        'A consumer complaint is a civil proceeding. Do not cite the BNS, BNSS, BSA, IPC '
        'or CrPC.',
        'Pecuniary jurisdiction under the 2019 Act is determined by the CONSIDERATION '
        'PAID, not by the compensation claimed — District Commission up to Rs. 50 lakh, '
        'State Commission above Rs. 50 lakh and up to Rs. 2 crore, National Commission '
        'above Rs. 2 crore.',
        'Plead expressly that the Complainant is a "consumer" and that the goods or '
        'services were not obtained for a commercial purpose — this is the commonest '
        'threshold objection.',
        'Limitation is two years from the date the cause of action arose (s. 69); where '
        'delayed, a condonation application with sufficient cause must accompany the '
        'complaint.',
    ),
    required_facts=(
        'the date of purchase or engagement and the consideration paid',
        'the defect or deficiency complained of',
        'the complaints made to the opposite party and their outcome',
        'the place of purchase, residence or business, for territorial jurisdiction',
    ),
    min_sections=6,
    target_tokens=6000,
)


# ---------------------------------------------------------------------------
AFFIDAVIT = Playbook(
    doc_type='affidavit',
    label='Affidavit',
    branch=CIVIL,
    category='Supporting Documents',
    aliases=('affidavit', 'sworn statement'),
    keywords=(
        (r'\baffidavit\b', 9),
        (r'\bdeponent\b', 6),
        (r'\bsolemnly\s+affirm', 6),
    ),
    skeleton=(
        Section(
            name='TITLE',
            guidance=(
                'The cause title of the proceeding in which the affidavit is filed, or '
                '"AFFIDAVIT" where it is standalone.'
            ),
        ),
        Section(
            name='DEPONENT DETAILS',
            guidance=(
                'I, [FULL NAME], aged about [AGE] years, son/daughter/wife of [NAME], '
                'resident of [ADDRESS], do hereby solemnly affirm and state as under.'
            ),
            must_contain=(('solemnly affirm', 'do hereby state'),),
        ),
        Section(
            name='AVERMENTS',
            guidance=(
                'Numbered "That" paragraphs. Each must contain one fact. Facts within '
                'personal knowledge and facts on information and belief must be kept in '
                'separate paragraphs.'
            ),
            must_contain=('That ',),
        ),
        Section(
            name='VERIFICATION',
            guidance=(
                'Verified at [PLACE] on [DATE] that the contents of paragraphs [X] to [Y] '
                'are true to my personal knowledge and paragraphs [A] to [B] are believed '
                'to be true on information received and legal advice, and that nothing '
                'material has been concealed.'
            ),
            must_contain=(('Verified', 'VERIFICATION'),),
        ),
        Section(
            name='ATTESTATION',
            guidance=(
                'DEPONENT signature block, followed by the attestation of the Oath '
                'Commissioner or Notary with seal and date.'
            ),
            must_contain=(('DEPONENT',),),
        ),
    ),
    conventions=(
        'The deponent speaks in the first person — "I", "my" — unlike a plaint or notice.',
        'Every averment is a numbered paragraph beginning with "That".',
        'Never mix facts on personal knowledge with facts on information and belief in '
        'the same paragraph; the verification must be able to separate them by number.',
    ),
    statutes_allow=(
        'Code of Civil Procedure, 1908 — s. 139 and Order XIX',
        'Oaths Act, 1969',
        'Notaries Act, 1952',
        'The statute or rule requiring the affidavit',
    ),
    pitfalls=(
        'An affidavit in a civil matter must not cite the penal codes. Where it supports '
        'a criminal proceeding, cite only the provision under which it is filed.',
        'An affidavit must state facts, never argument, opinion or law.',
        'The verification clause is mandatory and must identify by paragraph number which '
        'averments are on personal knowledge and which on information and belief. A '
        'defective verification renders the affidavit liable to be ignored.',
        'Do not depose to facts the deponent cannot personally know without stating the '
        'source of the information.',
    ),
    required_facts=(
        'the deponent\'s full name, age, parentage and address',
        'the proceeding in which the affidavit is to be filed, if any',
        'which averments are within personal knowledge',
    ),
    kb_doc_types=('Affidavit', 'Rent'),
    min_sections=5,
    target_tokens=4000,
)


# ---------------------------------------------------------------------------
VAKALATNAMA = Playbook(
    doc_type='vakalatnama',
    label='Vakalatnama',
    branch=CIVIL,
    category='Supporting Documents',
    aliases=('vakalatnama', 'vakalat', 'power of attorney to advocate'),
    keywords=(
        (r'\bvakalatnama\b|\bvakalat\b', 10),
        (r'\bappoint\w*\s+.{0,20}advocate\b', 5),
    ),
    skeleton=(
        Section(
            name='TITLE AND CAUSE TITLE',
            guidance=(
                'VAKALATNAMA, followed by the court and the cause title of the proceeding '
                'with the case number.'
            ),
            must_contain=(('VAKALATNAMA',),),
        ),
        Section(
            name='APPOINTMENT',
            guidance=(
                'I/We, [NAME], the [Plaintiff/Defendant/Petitioner] in the above matter, do '
                'hereby appoint and retain [ADVOCATE NAME], Advocate, to appear, plead and '
                'act for me/us in the above proceeding.'
            ),
            must_contain=(('appoint', 'retain'), 'Advocate'),
        ),
        Section(
            name='AUTHORITY CONFERRED',
            guidance=(
                'Enumerate the authority: to appear and plead, to file and receive '
                'documents, to receive money, to compromise or withdraw with instructions, '
                'to engage another advocate, and to do all acts necessary for the conduct '
                'of the matter.'
            ),
        ),
        Section(
            name='EXECUTION AND ACCEPTANCE',
            guidance=(
                'Signature of the executant with date and place, followed by the '
                'advocate\'s acceptance, enrolment number and signature.'
            ),
            must_contain=(('Accepted', 'ACCEPTED', 'Enrolment', 'Enrollment'),),
        ),
    ),
    conventions=(
        'A vakalatnama is short and formulaic. Do not pad it with recitals.',
        'Name the specific proceeding — a vakalatnama is filed matter by matter.',
    ),
    statutes_allow=(
        'Code of Civil Procedure, 1908 — Order III Rules 1 and 4',
        'Advocates Act, 1961',
        'The applicable High Court Rules and the Court Fees / Stamp schedule',
    ),
    pitfalls=(
        'Do not cite the penal codes in a vakalatnama, in any matter.',
        'A vakalatnama must be accepted and signed by the advocate; an unaccepted '
        'vakalatnama is not on record.',
        'Where the executant is a company or a firm, the signatory\'s authority (board '
        'resolution or partnership authority) must be recited.',
    ),
    required_facts=(
        'the court and case number',
        'the executant\'s name and procedural status',
        'the advocate\'s name and enrolment number',
    ),
    kb_doc_types=('Vakalatnama',),
    min_sections=4,
    target_tokens=2500,
)


LITIGATION_PLAYBOOKS = (
    PLAINT,
    WRITTEN_STATEMENT,
    BAIL,
    ANTICIPATORY_BAIL,
    WRIT_PETITION,
    CONSUMER_COMPLAINT,
    AFFIDAVIT,
    VAKALATNAMA,
)
