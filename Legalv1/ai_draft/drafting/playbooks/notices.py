"""
Legal-notice playbooks — demand, rent-arrears, and cheque s.138.

These three carry the most weight in the whole package. The benchmark scored our
rent-arrears notice 3/10 and called the construction recovery notice "not
litigation-ready"; our own baseline reproduced that as format 0.0 / statute 0.0
on both. Notices are also the one family with NO precedent anywhere in
`draftdocs/` — the corpus holds a single arbitrator-appointment notice — so the
`inline_exemplar` constants below are hand-authored rather than retrieved.

They are written to the form an Indian advocate actually issues: letterhead and
reference block, mode of service, subject line, numbered "That ..." recitals,
`NOW THEREFORE` operative demand, statutory compliance period, closing
`TAKE NOTICE`, and `Yours faithfully / Counsel for`. Each is a skeleton with
representative language, not a filled specimen — the model supplies facts, the
exemplar supplies register.

LEGAL REVIEW REQUIRED: these are legal work product and ship only after a
practising advocate signs off, exactly as the playbooks do.
"""

from __future__ import annotations

from .base import COMMERCIAL, CIVIL, Playbook, Section

# ---------------------------------------------------------------------------
# Shared conventions. Every notice is correspondence from an advocate to an
# opposite party — third person throughout, never "I/you" as the client.
# ---------------------------------------------------------------------------
NOTICE_CONVENTIONS = (
    'Write as the advocate, referring to the client as "my Client" throughout. '
    'Never write in the client\'s first person.',
    'Address the recipient as "you" — they are the Noticee. They are NOT a '
    '"Defendant", "Respondent", "Opposite Party" or "accused": no proceeding exists yet.',
    'Recitals are numbered paragraphs each beginning with the word "That" — '
    '"1. That my Client is ...". This is the single most recognisable feature of '
    'an Indian legal notice and its absence marks the document as not lawyer-drafted.',
    'State amounts as "Rs. 5,00,000/- (Rupees Five Lakh only)" and periods as '
    '"15 (fifteen) days", using the Indian digit grouping.',
    'Never use form-filling headings such as "TITLE OF THE NOTICE", '
    '"SENDER\'S DETAILS", "RECIPIENT DETAILS", "BODY" or "CLOSING STATEMENT". '
    'A notice is correspondence, not a form.',
    'Give the compliance period, the exact consequence of non-compliance, and '
    'reserve all rights and remedies.',
)

_SIGN_OFF = Section(
    name='SIGNATURE AND COUNSEL BLOCK',
    guidance=(
        'Close with "Yours faithfully," then the advocate name, "Advocate", and '
        '"Counsel for [CLIENT NAME]". Add the standard retention line noting that '
        'a copy of the notice is retained in the advocate\'s office.'
    ),
    must_contain=(('Yours faithfully', 'Yours truly'), 'Advocate'),
)

_LETTERHEAD = Section(
    name='ADVOCATE LETTERHEAD AND REFERENCE',
    guidance=(
        'Advocate name, chambers address, email, telephone and enrolment number, '
        'then a reference number and the date. Use ALL-CAPS bracketed placeholders.'
    ),
    must_contain=('Advocate',),
)

_SERVICE = Section(
    name='MODE OF SERVICE',
    guidance=(
        'State the mode(s) of despatch, e.g. "BY REGISTERED POST A.D. & BY EMAIL". '
        'Proof of despatch matters for limitation and for statutory notice periods.'
    ),
)

_TAKE_NOTICE = Section(
    name='TAKE NOTICE',
    guidance=(
        'Begin "TAKE NOTICE that in the event of your failure to comply ... my '
        'Client shall be constrained to initiate ..." and name the specific '
        'proceeding contemplated. State that it will be at the Noticee\'s risk as '
        'to costs and consequences, and reserve all rights and remedies.'
    ),
    must_contain=('TAKE NOTICE', ('reserves all', 'reserves its rights', 'without prejudice')),
)


# ---------------------------------------------------------------------------
# 1. Generic demand / recovery notice  (benchmark fixture 002)
# ---------------------------------------------------------------------------
DEMAND_EXEMPLAR = """\
[ADVOCATE NAME], Advocate
[CHAMBERS ADDRESS] | [EMAIL] | [PHONE] | Enrolment No. [ENROLMENT NO.]

Ref. No.: [REF]/[YYYY]                                    Date: [DD MONTH YYYY]

BY REGISTERED POST A.D. AND BY EMAIL

To,
[NOTICEE NAME], [ENTITY TYPE]
[REGISTERED OFFICE ADDRESS]

Sub: Legal notice for recovery of Rs. [AMOUNT]/- (Rupees [AMOUNT IN WORDS] only)
     towards outstanding dues under the Agreement dated [DATE], together with
     contractual interest and damages.

Sir/Madam,

Under instructions from and on behalf of my client, [CLIENT NAME], having its
registered office at [ADDRESS] (hereinafter referred to as "my Client"), I
hereby address you as under:

1. That my Client is [DESCRIPTION OF CLIENT'S BUSINESS] and you are [DESCRIPTION
   OF NOTICEE].

2. That by an Agreement dated [DATE] executed between my Client and you
   (hereinafter "the said Agreement"), my Client was engaged to [SCOPE OF WORK]
   for a total consideration of Rs. [CONTRACT VALUE]/-.

3. That my Client duly performed its obligations under the said Agreement and
   completed [EXTENT] of the contracted scope, which stands certified by
   [CERTIFYING AUTHORITY] vide certificate dated [DATE].

4. That despite such certification, a sum of Rs. [AMOUNT]/- remains outstanding
   and unpaid by you.

5. That my Client addressed reminders to you on [DATES], to none of which you
   have responded.

6. That your conduct constitutes a breach of Clause [NO.] of the said Agreement,
   entitling my Client to the outstanding sum together with interest at
   [RATE]% per annum as stipulated in Clause [NO.] thereof.

7. That the cause of action arose on [DATE] when [TRIGGERING EVENT], and
   continues from day to day.

NOW THEREFORE, I, through this legal notice, call upon you to, within 15
(fifteen) days of receipt hereof:

   (a) pay to my Client the sum of Rs. [AMOUNT]/- towards outstanding dues;
   (b) pay contractual interest at [RATE]% per annum thereon from [DATE] till
       realisation;
   (c) pay Rs. [AMOUNT]/- towards the cost of this legal notice.

You are further called upon to preserve all records, correspondence, electronic
communications, measurement books and site records relating to the said
Agreement, and not to destroy, alter or part with the same, an adverse inference
being liable to be drawn against you in the event of spoliation.

TAKE NOTICE that in the event of your failure to comply within the period
aforesaid, my Client shall be constrained to initiate such civil and/or
arbitral proceedings as it may be advised, entirely at your risk as to costs and
consequences, and my Client expressly reserves all rights and remedies available
to it in law and in equity.

A copy of this notice is retained in my office for further necessary action.

Yours faithfully,

[ADVOCATE NAME]
Advocate
Counsel for [CLIENT NAME]"""


LEGAL_NOTICE_DEMAND = Playbook(
    doc_type='legal_notice.demand',
    label='Legal Notice — Demand / Recovery',
    branch=COMMERCIAL,
    category='Notices',
    aliases=(
        'legal_notice', 'legal notice', 'demand notice', 'recovery notice',
        'legal_notice.demand', 'breach of contract notice', 'notice',
    ),
    keywords=(
        (r'\blegal\s+notice\b', 6),
        (r'\bnotice\b', 2),
        (r'\bdemand\b', 3),
        (r'\brecovery\b|\boutstanding\s+dues\b|\bunpaid\b', 3),
        (r'\bbreach\s+of\s+contract\b', 3),
    ),
    skeleton=(
        _LETTERHEAD,
        _SERVICE,
        Section(
            name='ADDRESSEE',
            guidance='"To," followed by the Noticee\'s full name, description and address.',
        ),
        Section(
            name='SUBJECT',
            guidance=(
                'One sentence beginning "Sub:" naming the relief sought, the principal '
                'amount, and the instrument or transaction relied upon.'
            ),
        ),
        Section(
            name='RECITALS',
            guidance=(
                'Numbered paragraphs, each beginning "That", setting out in chronological '
                'order: the parties, the agreement, performance by the client, the breach, '
                'the reminders, and the cause of action with its date.'
            ),
            must_contain=('That ',),
        ),
        Section(
            name='BREACH AND LIABILITY',
            guidance=(
                'Identify the specific clause breached and the legal consequence. Claim '
                'damages under ss. 73/74 of the Indian Contract Act, 1872 where the '
                'contract provides for them.'
            ),
        ),
        Section(
            name='PRESERVATION OF EVIDENCE',
            guidance=(
                'Call upon the Noticee to preserve all records, correspondence and '
                'electronic communications, and warn that an adverse inference may be '
                'drawn from spoliation.'
            ),
            must_contain=(('preserve all', 'preservation of', 'not to destroy'),),
        ),
        Section(
            name='ARBITRATION',
            guidance=(
                'Where the contract contains an arbitration clause, invoke it under s.21 '
                'of the Arbitration and Conciliation Act, 1996 in unconditional terms and '
                'call upon the Noticee to concur in the appointment of an arbitrator.'
            ),
            required=False,
        ),
        Section(
            name='NOW THEREFORE',
            guidance=(
                'The operative demand, as lettered sub-clauses: principal, interest, '
                'damages, and the cost of this notice. State the compliance period in '
                'both figures and words.'
            ),
            must_contain=(('NOW THEREFORE', 'call upon you'),
                          ('cost of this notice', 'cost of this legal notice',
                           'costs of this notice')),
        ),
        _TAKE_NOTICE,
        _SIGN_OFF,
    ),
    conventions=NOTICE_CONVENTIONS,
    statutes_allow=(
        'Indian Contract Act, 1872 (ss. 73 and 74 for damages)',
        'Arbitration and Conciliation Act, 1996 (s. 21 for invoking arbitration)',
        'Limitation Act, 1963',
        'Specific Relief Act, 1963',
        'Interest Act, 1978',
        'Code of Civil Procedure, 1908',
        'MSMED Act, 2006 — only if the client is a registered micro/small enterprise',
    ),
    pitfalls=(
        'This is a contractual money claim. It is a CIVIL/COMMERCIAL matter. Do not '
        'cite, name or allude to the BNS, BNSS, BSA, IPC, CrPC or the Indian Evidence '
        'Act, and do not characterise the Noticee\'s conduct as an "offence", "cheating" '
        'or "criminal breach of trust". The benchmark flagged exactly this as "the most '
        'serious flaw" and "a fundamental misunderstanding of the applicable legal '
        'framework".',
        'An invocation of arbitration under s.21 must be UNCONDITIONAL. Do not write '
        '"failing payment, we shall invoke arbitration" — a conditional invocation does '
        'not communicate an unequivocal intention to commence arbitration and can be '
        'challenged as an invalid s.21 notice.',
        'Never call the Noticee "the Defendant". No suit exists at notice stage.',
        'Always claim the cost of the notice itself. Omitting it was a scored defect.',
        'Do not invoke arbitration AND threaten a civil suit on the same claim without '
        'distinguishing them — where a valid arbitration clause exists, a suit is barred '
        'by s.8 of the 1996 Act.',
    ),
    required_facts=(
        'the agreement date, parties and consideration',
        'the precise outstanding amount',
        'the contractual interest rate and the clause providing for it',
        'the date and manner of prior reminders',
        'whether an arbitration clause exists and its terms',
    ),
    inline_exemplar=DEMAND_EXEMPLAR,
    min_sections=9,
    target_tokens=7000,
)


# ---------------------------------------------------------------------------
# 2. Rent arrears / eviction notice  (benchmark fixture 001 — scored 3/10)
# ---------------------------------------------------------------------------
RENT_ARREARS_EXEMPLAR = """\
[ADVOCATE NAME], Advocate
[CHAMBERS ADDRESS] | [EMAIL] | [PHONE] | Enrolment No. [ENROLMENT NO.]

Ref. No.: [REF]/[YYYY]                                    Date: [DD MONTH YYYY]

BY REGISTERED POST A.D. AND BY EMAIL

To,
[TENANT NAME]
[TENANTED PREMISES ADDRESS]

Sub: Legal notice demanding payment of arrears of rent amounting to
     Rs. [AMOUNT]/- (Rupees [AMOUNT IN WORDS] only) and for delivery of vacant
     and peaceful possession of the tenanted premises.

Sir/Madam,

Under instructions from and on behalf of my client, [LANDLORD NAME], resident of
[ADDRESS] (hereinafter referred to as "my Client"), I hereby address you as
under:

1. That my Client is the absolute owner and landlord of [FULL DESCRIPTION OF THE
   PREMISES] (hereinafter referred to as "the tenanted premises").

2. That by a Rent Agreement dated [DATE], my Client let out the tenanted premises
   to you on a monthly rent of Rs. [RENT]/- (Rupees [RENT IN WORDS] only),
   payable in advance on or before the [N]th day of each English calendar month,
   the tenancy being a month-to-month tenancy commencing on the [N]th day of each
   month.

3. That you have defaulted in payment of rent from [MONTH YYYY] to [MONTH YYYY],
   whereby a sum of Rs. [ARREARS]/- has fallen due and remains unpaid.

4. That my Client has repeatedly demanded payment of the said arrears, orally on
   [DATES] and in writing on [DATE], to which you have failed and neglected to
   respond.

5. That your continued default constitutes a ground for eviction, and my Client
   is no longer willing to continue the tenancy.

6. That the cause of action arose on [DATE] when the rent for [MONTH] fell due
   and remained unpaid, and continues from month to month.

NOW THEREFORE, I, through this legal notice, call upon you to, within 15
(fifteen) days of receipt hereof:

   (a) pay to my Client the arrears of rent amounting to Rs. [ARREARS]/-
       together with interest thereon at [RATE]% per annum;
   (b) pay mesne profits / damages for use and occupation at Rs. [AMOUNT]/- per
       month from [DATE] until delivery of vacant possession;
   (c) deliver vacant and peaceful possession of the tenanted premises to my
       Client; and
   (d) pay Rs. [AMOUNT]/- towards the cost of this legal notice.

Further, and without prejudice to the foregoing, my Client hereby determines
your tenancy in respect of the tenanted premises with effect from the expiry of
the [N]th day of [MONTH YYYY], being the last day of a month of the tenancy, and
calls upon you to deliver vacant possession on that date.

TAKE NOTICE that in the event of your failure to comply within the period
aforesaid, my Client shall be constrained to initiate appropriate proceedings for
eviction and for recovery of arrears and mesne profits before the competent
court/authority, entirely at your risk as to costs and consequences, and my
Client expressly reserves all rights and remedies available in law.

A copy of this notice is retained in my office for further necessary action.

Yours faithfully,

[ADVOCATE NAME]
Advocate
Counsel for [LANDLORD NAME]"""


LEGAL_NOTICE_RENT_ARREARS = Playbook(
    doc_type='legal_notice.rent_arrears',
    label='Legal Notice — Rent Arrears / Eviction',
    branch=CIVIL,
    category='Notices',
    aliases=(
        'rent notice', 'eviction notice', 'legal_notice.rent_arrears',
        'rent arrears notice', 'notice to quit', 'tenant notice',
    ),
    keywords=(
        # Inherits the notice-family signal so the lead window can identify the
        # DOCUMENT, while the subject-matter terms below pick the sub-variant.
        (r'\blegal\s+notice\b', 6),
        (r'\bnotice\b', 2),
        (r'\brent\b', 5),
        (r'\barrear', 6),
        (r'\btenan|\blandlord\b|\blessee\b|\blessor\b', 4),
        (r'\bevict|\bvacate\b|\bvacant\s+possession\b', 5),
        # The facts of a rent default, however the user phrases them. Fixture 001
        # says "failed to pay rent ... outstanding dues", never the word "arrears".
        (r'(?:fail|failure|default)\w*\s+to\s+pay\s+(?:the\s+)?rent|'
         r'non[-\s]payment\s+of\s+rent', 7),
        (r'\brent\b[^.]{0,60}\b(?:outstanding|unpaid|overdue|due|dues)\b|'
         r'\b(?:outstanding|unpaid|overdue)\b[^.]{0,30}\brent\b', 6),
    ),
    skeleton=(
        _LETTERHEAD,
        _SERVICE,
        Section(
            name='ADDRESSEE',
            guidance='"To," followed by the tenant\'s name and the tenanted premises address.',
        ),
        Section(
            name='SUBJECT',
            guidance=(
                'One sentence beginning "Sub:" naming the arrears claimed and the demand '
                'for vacant possession.'
            ),
        ),
        Section(
            name='RECITALS',
            guidance=(
                'Numbered "That" paragraphs: my Client\'s title, the tenancy and its terms, '
                'the rate and due date of rent, the period and quantum of default, prior '
                'demands, and the cause of action.'
            ),
            must_contain=('That ',),
        ),
        Section(
            name='DETERMINATION OF TENANCY',
            guidance=(
                'Where the tenancy is being terminated, determine it expressly and state '
                'the date of expiry. For a month-to-month tenancy the notice period under '
                's.106 of the Transfer of Property Act, 1882 is 15 days, and the notice '
                'must expire with the end of a month of the tenancy — not the calendar '
                'month, unless they coincide.'
            ),
        ),
        Section(
            name='NOW THEREFORE',
            guidance=(
                'Lettered sub-clauses: arrears, interest, mesne profits for use and '
                'occupation, delivery of vacant possession, and the cost of this notice.'
            ),
            must_contain=(('NOW THEREFORE', 'call upon you'),
                          ('vacant possession', 'vacant and peaceful possession')),
        ),
        _TAKE_NOTICE,
        _SIGN_OFF,
    ),
    conventions=NOTICE_CONVENTIONS,
    statutes_allow=(
        'Transfer of Property Act, 1882 (s. 106 notice to determine a month-to-month '
        'tenancy; s. 111(g) forfeiture)',
        'The applicable State Rent Control Act — name the State statute, and where the '
        'exact section is not certain mark it "(exact section to be confirmed)"',
        'Indian Contract Act, 1872',
        'Limitation Act, 1963',
        'Code of Civil Procedure, 1908',
        'Specific Relief Act, 1963',
    ),
    pitfalls=(
        'A landlord-tenant rent dispute is a CIVIL matter. Do not cite, name or allude '
        'to the BNSS, BNS, BSA, IPC, CrPC or the Indian Evidence Act, and never describe '
        'non-payment of rent as an "offence" or the tenant as an "accused". The benchmark '
        'scored our draft 3/10 primarily for citing the BNSS in this exact scenario.',
        'Rent control is a STATE subject. Do not assert a section of a State Rent Act '
        'unless it is given in the facts — name the statute and mark the section '
        '"(exact section to be confirmed)". Where a State Rent Act applies it may exclude '
        's.106 of the Transfer of Property Act and restrict the grounds of eviction.',
        'A notice under s.106 of the Transfer of Property Act, 1882 must expire with the '
        'end of a MONTH OF THE TENANCY, which is not necessarily the end of the calendar '
        'month. Compute it from the date the tenancy commenced.',
        'Distinguish a demand for arrears from a determination of tenancy. They are '
        'different acts with different consequences; if both are intended, say both '
        'expressly and in the alternative.',
        'Claim mesne profits / damages for use and occupation for the period after '
        'determination — rent ceases to accrue once the tenancy ends.',
        'Always claim the cost of the notice.',
    ),
    required_facts=(
        'the date and terms of the rent agreement',
        'the monthly rent and the day it falls due',
        'the exact months in default and the resulting arrears',
        'the date the tenancy commenced (needed to compute the s.106 notice expiry)',
        'the State in which the premises are situated, for the applicable Rent Act',
    ),
    inline_exemplar=RENT_ARREARS_EXEMPLAR,
    min_sections=8,
    target_tokens=7000,
)


# ---------------------------------------------------------------------------
# 3. Cheque dishonour notice — s.138 Negotiable Instruments Act, 1881
#
# Branch is COMMERCIAL, deliberately. A s.138 prosecution is quasi-criminal, but
# the NOTICE is a statutory demand under proviso (b) to s.138 and its source is
# the NI Act, not the penal codes. Setting the branch to `criminal` would switch
# off the deterministic penal-token guard and re-open the exact defect this
# package exists to close. The pitfall below states the distinction expressly.
# ---------------------------------------------------------------------------
CHEQUE_138_EXEMPLAR = """\
[ADVOCATE NAME], Advocate
[CHAMBERS ADDRESS] | [EMAIL] | [PHONE] | Enrolment No. [ENROLMENT NO.]

Ref. No.: [REF]/[YYYY]                                    Date: [DD MONTH YYYY]

BY REGISTERED POST A.D. AND BY EMAIL

To,
[DRAWER NAME]
[ADDRESS]

Sub: Statutory notice under Section 138 of the Negotiable Instruments Act, 1881
     demanding payment of Rs. [AMOUNT]/- (Rupees [AMOUNT IN WORDS] only) being
     the amount of dishonoured cheque No. [CHEQUE NO.] dated [DATE].

Sir/Madam,

Under instructions from and on behalf of my client, [PAYEE NAME], resident of
[ADDRESS] (hereinafter referred to as "my Client"), I hereby address you as
under:

1. That you were, at all material times, [RELATIONSHIP / LIABILITY] and are
   liable to my Client in the sum of Rs. [AMOUNT]/- towards [CONSIDERATION].

2. That in discharge of the said legally enforceable debt and liability, you
   issued to my Client cheque No. [CHEQUE NO.] dated [DATE] for Rs. [AMOUNT]/-
   drawn on [BANK NAME], [BRANCH].

3. That my Client presented the said cheque for encashment through its banker,
   [BANK NAME], on [DATE], within the period of its validity.

4. That the said cheque was returned unpaid vide Return Memo dated [DATE] with
   the endorsement "[REASON FOR RETURN]", information whereof was received by my
   Client on [DATE].

5. That the dishonour of the said cheque is attributable to [insufficiency of
   funds / the account having been closed / stop-payment instructions], and the
   said cheque was issued in discharge of a legally enforceable debt.

NOW THEREFORE, I, through this statutory notice issued under proviso (b) to
Section 138 of the Negotiable Instruments Act, 1881, call upon you to pay to my
Client the sum of Rs. [AMOUNT]/- being the amount of the said dishonoured
cheque, together with Rs. [AMOUNT]/- towards the cost of this notice, within 15
(fifteen) days of receipt hereof.

TAKE NOTICE that in the event of your failure to make payment of the said amount
within the period aforesaid, my Client shall be constrained to initiate criminal
proceedings against you under Section 138 read with Section 141 of the
Negotiable Instruments Act, 1881 before the competent Court, in addition to such
civil proceedings for recovery as my Client may be advised, entirely at your risk
as to costs and consequences. My Client expressly reserves all rights and
remedies available in law.

A copy of this notice is retained in my office for further necessary action.

Yours faithfully,

[ADVOCATE NAME]
Advocate
Counsel for [PAYEE NAME]"""


LEGAL_NOTICE_CHEQUE_138 = Playbook(
    doc_type='legal_notice.cheque_138',
    label='Legal Notice — Cheque Dishonour (s. 138 NI Act)',
    branch=COMMERCIAL,
    category='Notices',
    aliases=(
        'cheque bounce notice', 'cheque dishonour notice', '138 notice',
        'legal_notice.cheque_138', 'ni act notice',
    ),
    keywords=(
        (r'\bcheque\b|\bcheck\s+bounce\b', 6),
        (r'\bdishonou?r', 5),
        (r'\bsection\s*138\b|\bs\.?\s*138\b|\bu/s\s*138\b', 8),
        (r'negotiable\s+instrument', 6),
        (r'\bbounce', 4),
    ),
    skeleton=(
        _LETTERHEAD,
        _SERVICE,
        Section(
            name='ADDRESSEE',
            guidance=(
                'The drawer of the cheque. Where the drawer is a company, address the '
                'company and its directors in charge under s.141 of the Act.'
            ),
        ),
        Section(
            name='SUBJECT',
            guidance=(
                'Name the statutory provision, the cheque number and date, and the amount.'
            ),
        ),
        Section(
            name='RECITALS',
            guidance=(
                'Numbered "That" paragraphs establishing every ingredient of the offence: '
                'the legally enforceable debt, issuance of the cheque in its discharge, '
                'presentation within validity, dishonour with the bank\'s endorsement, and '
                'the date on which information of dishonour was received.'
            ),
            must_contain=('That ',),
        ),
        Section(
            name='NOW THEREFORE',
            guidance=(
                'The statutory demand, expressly stated to be issued under proviso (b) to '
                's.138, for the cheque amount and the cost of the notice, within 15 '
                '(fifteen) days of receipt.'
            ),
            must_contain=(('NOW THEREFORE', 'call upon you'),
                          'Negotiable Instruments Act',
                          ('15 (fifteen) days', 'fifteen days', '15 days')),
        ),
        _TAKE_NOTICE,
        _SIGN_OFF,
    ),
    conventions=NOTICE_CONVENTIONS,
    statutes_allow=(
        'Negotiable Instruments Act, 1881 — s. 138 (dishonour), s. 141 (offences by '
        'companies), s. 142 (cognizance), s. 143A/148 (interim compensation)',
        'Indian Contract Act, 1872',
        'Limitation Act, 1963',
    ),
    pitfalls=(
        'The source of this remedy is the Negotiable Instruments Act, 1881. Do NOT cite '
        'the BNS, BNSS, BSA, IPC or CrPC in the notice. A s.138 prosecution is '
        'quasi-criminal, but the statutory demand is made under the NI Act and citing the '
        'penal codes here is a substantive error.',
        'The notice must be issued within 30 days of RECEIPT OF INFORMATION of dishonour '
        'from the bank — not from the date of the cheque and not from the date of '
        'presentation. Plead the date of receipt expressly; it is jurisdictional.',
        'The demand period is exactly 15 days from receipt of the notice. The cause of '
        'action arises only on the expiry of those 15 days, and the complaint must then '
        'be filed within one month of that date under s.142(1)(b).',
        'Demand only the cheque amount (and the cost of the notice). A demand for a sum '
        'larger than the cheque amount has been held to vitiate the notice.',
        'Plead that the cheque was issued in discharge of a legally enforceable debt or '
        'liability — this is an essential ingredient, not boilerplate.',
        'Where the drawer is a company, the notice must also be served on the persons in '
        'charge of and responsible for its business under s.141.',
    ),
    required_facts=(
        'the cheque number, date, amount and drawee bank',
        'the date of presentation and the date of the return memo',
        'the bank\'s reason for return, verbatim',
        'the date the payee received information of dishonour',
        'the underlying debt or liability the cheque discharged',
    ),
    inline_exemplar=CHEQUE_138_EXEMPLAR,
    min_sections=7,
    target_tokens=6000,
)


NOTICE_PLAYBOOKS = (
    LEGAL_NOTICE_DEMAND,
    LEGAL_NOTICE_RENT_ARREARS,
    LEGAL_NOTICE_CHEQUE_138,
)
