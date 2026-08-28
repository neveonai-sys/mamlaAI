"""
Instrument playbooks — will, partnership deed, rent/lease agreement, sale deed.

These four are the types the baseline already handles least badly (will and deed
both scored 6.8 against human 6 and 7). The generic prompt happens to suit long
structured instruments, so the job here is to lift the *substance* without
disturbing the structure that already works: the reviewers' complaints about
these documents were about missing operative provisions, not missing headings.

Every `pitfalls` entry below is traceable to a specific finding in the benchmark.
`target_tokens` is raised well above the old global 4000 because the partnership
deed truncated mid-sentence at that ceiling.
"""

from __future__ import annotations

from .base import COMMERCIAL, CIVIL, TESTAMENTARY, Playbook, Section

# An instruction to draft a NOTICE or a PLEADING *about* an instrument is not an
# instruction to draft the instrument itself. Every notice recites the agreement
# it complains of, so without this the underlying instrument out-scores the
# document actually requested — which is exactly how the benchmark's rent-arrears
# notice first classified as a lease agreement.
_NOT_THE_INSTRUMENT = (
    (r'\b(?:draft|issue|send|prepare|serve)\s+(?:a\s+|the\s+)?legal\s+notice\b', -12),
    (r'\b(?:draft|file|prepare)\s+(?:a\s+|the\s+)?(?:plaint|suit|petition|complaint)\b', -8),
)

DEED_CONVENTIONS = (
    'Open with the nature of the instrument, its date, and the parties with full '
    'description, followed by defined terms in the form '
    '"(hereinafter referred to as \\"the Vendor\\", which expression shall, unless '
    'repugnant to the context, include his heirs, executors, administrators and '
    'assigns)".',
    'Recitals begin with "WHEREAS" and establish the background and the parties\' '
    'title or capacity.',
    'The operative part begins "NOW THIS DEED WITNESSETH AS FOLLOWS:" and is set out '
    'in numbered clauses with headings.',
    'Close with "IN WITNESS WHEREOF the parties hereto have set their respective '
    'hands ..." followed by signature and witness blocks and, where applicable, a '
    'Schedule of property.',
    'State amounts as "Rs. 5,00,000/- (Rupees Five Lakh only)" and shares as both '
    'figure and words.',
)


# ---------------------------------------------------------------------------
# WILL  (benchmark fixture 003 — scored 6/10, "facially complete but
# substantively incomplete")
# ---------------------------------------------------------------------------
WILL = Playbook(
    doc_type='will',
    label='Last Will and Testament',
    branch=TESTAMENTARY,
    category='Testamentary',
    aliases=('will', 'last will', 'testament', 'last will and testament', 'codicil'),
    keywords=(
        (r'\bwill\b(?!\s+(be|not|have|need|you|he|she|they|it|we))', 6),
        (r'last\s+will|testament', 9),
        (r'\btestator|\btestatrix|\bbequeath|\blegatee\b', 8),
        (r'\bcodicil\b', 7),
        (r'\bexecutor\b|\bexecutrix\b', 5),
    ) + _NOT_THE_INSTRUMENT,
    skeleton=(
        Section(
            name='DECLARATION',
            guidance=(
                'I, [FULL NAME], son/daughter of [NAME], aged [AGE] years, resident of '
                '[ADDRESS], declare this to be my last Will and Testament.'
            ),
            must_contain=(('last Will', 'Last Will'),),
        ),
        Section(
            name='TESTAMENTARY CAPACITY AND FREE VOLITION',
            guidance=(
                'Declare sound mind, sound memory and sound understanding, and that the '
                'Will is made voluntarily, without coercion, undue influence or persuasion '
                'from any person.'
            ),
            must_contain=(('sound mind',), ('own free will', 'free volition', 'voluntarily')),
        ),
        Section(
            name='REVOCATION',
            guidance=(
                'Revoke all wills, codicils and testamentary dispositions PREVIOUSLY made '
                'by the testator. Confine the revocation to earlier instruments.'
            ),
            must_contain=(('revoke',),),
        ),
        Section(
            name='FAMILY AND DEPENDANTS',
            guidance='Identify the spouse and each child by name, and any other dependant.',
        ),
        Section(
            name='SCHEDULE OF ASSETS',
            guidance=(
                'Enumerate each asset with sufficient particularity to identify it — '
                'immovable property by description and location, bank and demat accounts '
                'by institution, shares by company and holding.'
            ),
        ),
        Section(
            name='BEQUESTS',
            guidance=(
                'One numbered clause per bequest, naming the beneficiary, the asset, and '
                'the nature of the interest given (absolute, or life interest with a named '
                'remainder).'
            ),
            must_contain=(('bequeath', 'give, devise and bequeath'),),
        ),
        Section(
            name='LIFE INTEREST AND REMAINDER',
            guidance=(
                'Where a life interest is created, state expressly: who holds it; the right '
                'to possession, income, rents and profits; the obligation to pay outgoings; '
                'whether the life tenant may alienate, mortgage or encumber the property '
                '(ordinarily expressly restrained); who takes the remainder and in what '
                'shares; and what happens if the life tenant predeceases the testator.'
            ),
            required=False,
        ),
        Section(
            name='SUBSTITUTIONARY AND SURVIVORSHIP PROVISIONS',
            guidance=(
                'Provide for each beneficiary predeceasing the testator, naming the '
                'substituted takers and the shares in which they take, and provide a '
                'fallback where a predeceasing beneficiary leaves no descendants.'
            ),
            must_contain=(('predecease',),),
        ),
        Section(
            name='DEBTS, TAXES AND TESTAMENTARY EXPENSES',
            guidance=(
                'Direct payment of all just debts, funeral expenses, taxes and testamentary '
                'expenses out of the estate before distribution, and identify the fund out '
                'of which they are payable.'
            ),
        ),
        Section(
            name='RESIDUARY ESTATE',
            guidance=(
                'Dispose of all property not otherwise specifically bequeathed, whether '
                'acquired before or after the execution of the Will.'
            ),
            must_contain=(('residue', 'residuary'),),
        ),
        Section(
            name='APPOINTMENT AND POWERS OF EXECUTOR',
            guidance=(
                'Appoint the executor and an alternate. Enumerate powers: to collect and '
                'get in the estate, to pay debts, to sell or realise assets for that '
                'purpose, to distribute in specie, and to obtain probate. Any exoneration '
                'clause must be limited to acts done in good faith.'
            ),
            must_contain=(('Executor', 'Executrix'),),
        ),
        Section(
            name='ATTESTATION AND EXECUTION',
            guidance=(
                'IN WITNESS WHEREOF I have hereunto set my hand at [PLACE] on [DATE]. '
                'Testator signature block, then the attestation clause reciting that the '
                'testator signed in the presence of two witnesses present at the same time, '
                'each of whom then signed in the presence of the testator. Witness blocks '
                'with names and addresses.'
            ),
            must_contain=(('IN WITNESS WHEREOF', 'hereunto set my hand'), ('witness', 'WITNESS')),
        ),
    ),
    conventions=(
        'The testator speaks in the first person throughout — "I give, devise and '
        'bequeath".',
        'Each bequest is a separate numbered clause. Do not merge bequests.',
        'Name every beneficiary in full with their relationship to the testator.',
        'Use "[PLACEHOLDER]" in ALL CAPS for any particular not supplied. Never invent '
        'a name, date, account number or valuation.',
    ),
    statutes_allow=(
        'Indian Succession Act, 1925 — s. 59 (capacity), s. 63 (execution and '
        'attestation), s. 70 (revocation), ss. 213 and 57 (probate)',
        'Hindu Succession Act, 1956 — for a Hindu testator',
        'Registration Act, 1908 — s. 18 (registration of a Will is optional)',
        'Transfer of Property Act, 1882 — for the nature of the interests created',
    ),
    pitfalls=(
        'A Will is a TESTAMENTARY instrument. No penal code has any application. Do not '
        'cite or name the BNS, BNSS, BSA, IPC, CrPC or the Indian Evidence Act.',
        'The revocation clause must revoke only EARLIER wills and codicils. A clause '
        'purporting to revoke wills made "before or after" this one, or any future will, '
        'is void — a testator cannot fetter the power to make a later will. This exact '
        'error was found in the benchmark draft.',
        'A life interest is not created by the words "for her lifetime" alone. State who '
        'holds it, the right to possession and income, liability for outgoings, whether '
        'alienation is permitted (ordinarily expressly restrained), who takes the '
        'remainder, and what happens if the life tenant predeceases the testator. The '
        'benchmark draft failed on every one of these.',
        'Provide expressly for the spouse predeceasing the testator where a life interest '
        'is given to the spouse. Without it the bequest lapses and the asset falls into '
        'residue or intestacy.',
        'A substitutionary gift to "their children, if any" is inadequate. Name the class, '
        'state the shares, state whether they take per stirpes or per capita, and provide '
        'a fallback where a predeceasing beneficiary leaves no descendants.',
        'An executor exoneration clause must be limited to acts done in good faith. A '
        'blanket clause excluding liability for "any loss or damage" is overbroad and '
        'liable to be read down.',
        'Execution requires the testator\'s signature and attestation by TWO witnesses, '
        'each of whom saw the testator sign and signed in the testator\'s presence '
        '(s. 63). A beneficiary or a beneficiary\'s spouse should not attest.',
        'Probate is NOT universally mandatory. Under s. 213 read with s. 57 of the Indian '
        'Succession Act, 1925, probate is required for a Hindu\'s Will only where the Will '
        'was made within the local limits of the ordinary original civil jurisdiction of '
        'the High Courts at Calcutta, Madras or Bombay, or relates to immovable property '
        'situate within those limits. State the position for the actual facts rather than '
        'asserting a blanket rule either way.',
        'Where shares in a private limited company are bequeathed, the transmission is '
        'subject to the Articles of Association, which commonly contain pre-emption '
        'rights. Flag this rather than assuming a clean transmission.',
    ),
    required_facts=(
        'the testator\'s full name, age, parentage and address',
        'the name and relationship of every beneficiary',
        'a sufficient description of every asset',
        'the intended nature of each interest — absolute or life interest',
        'the executor and the alternate executor',
    ),
    kb_doc_types=('Will', 'TWILLS', 'Conveyancing'),
    min_sections=11,
    target_tokens=9000,
)


# ---------------------------------------------------------------------------
# PARTNERSHIP DEED  (benchmark fixture 004 — scored 7/10, truncated mid-sentence)
# ---------------------------------------------------------------------------
PARTNERSHIP_DEED = Playbook(
    doc_type='partnership_deed',
    label='Partnership Deed',
    branch=COMMERCIAL,
    category='Commercial',
    aliases=('partnership deed', 'partnership_deed', 'partnership agreement', 'deed of partnership'),
    keywords=(
        (r'partnership\s+(deed|agreement)', 10),
        (r'\bpartnership\b', 6),
        (r'\bpartners?\b.{0,30}\b(capital|profit|firm)\b', 4),
        (r'\bfirm\b', 2),
    ) + _NOT_THE_INSTRUMENT,
    skeleton=(
        Section(
            name='PARTIES AND DATE',
            guidance=(
                'THIS DEED OF PARTNERSHIP made at [PLACE] on [DATE] between the partners, '
                'each with full name, age, parentage and address, described as parties of '
                'the first, second and third part.'
            ),
            must_contain=(('DEED OF PARTNERSHIP', 'THIS DEED'),),
        ),
        Section(
            name='FIRM NAME, BUSINESS AND OFFICE',
            guidance=(
                'The firm name, the nature of the business, the principal place of business, '
                'and the date of commencement. State whether the partnership is at will or '
                'for a fixed term.'
            ),
        ),
        Section(
            name='CAPITAL CONTRIBUTION',
            guidance=(
                'The capital contributed by each partner, in figures and words, and whether '
                'interest is payable on capital and at what rate.'
            ),
            must_contain=(('capital',),),
        ),
        Section(
            name='PROFIT AND LOSS SHARING',
            guidance=(
                'The ratio in which profits AND losses are shared, stated in the exact ratio '
                'instructed. If the client supplied a ratio such as 50:30:20, reproduce it '
                'in that form and also name each partner\'s share.'
            ),
            must_contain=(('profit',), ('loss', 'losses')),
        ),
        Section(
            name='DRAWINGS, REMUNERATION AND INTEREST',
            guidance=(
                'Permitted drawings, working-partner remuneration, and interest on capital '
                'and on current accounts, each within the limits of s. 40(b) of the Income '
                'Tax Act, 1961 if the deduction is to be available.'
            ),
        ),
        Section(
            name='MANAGEMENT, AUTHORITY AND DUTIES',
            guidance=(
                'Which partners manage, what acts require unanimous consent, and the duties '
                'of good faith, true accounts and diligence under ss. 9 and 10 of the Act.'
            ),
        ),
        Section(
            name='BANK ACCOUNTS AND BOOKS OF ACCOUNT',
            guidance=(
                'Operation of bank accounts and signing authority; maintenance of books at '
                'the principal place of business and every partner\'s right of access under '
                's. 12(d).'
            ),
        ),
        Section(
            name='ADMISSION, RETIREMENT AND EXPULSION',
            guidance=(
                'Terms for introducing a new partner (s. 31), retirement and notice (s. 32), '
                'and expulsion in good faith under an express power (s. 33).'
            ),
        ),
        Section(
            name='DEATH AND INSOLVENCY OF A PARTNER',
            guidance=(
                'State whether the firm continues; how the outgoing partner\'s or deceased '
                'partner\'s share is valued and paid out, over what period; the rights of '
                'the legal heirs or legal representatives; and the effect of adjudication '
                'of a partner as insolvent under s. 34.'
            ),
            must_contain=(('death',), ('insolven',),
                          ('legal heirs', 'legal representatives', 'outgoing partner')),
        ),
        Section(
            name='TRANSFER OF PARTNERSHIP INTEREST',
            guidance=(
                'Restrictions on transfer or assignment of a partner\'s interest, and the '
                'limited rights of a transferee under s. 29.'
            ),
        ),
        Section(
            name='CONFIDENTIALITY AND NON-COMPETE',
            guidance=(
                'Confidentiality obligations, and any restraint on competing business. Note '
                'that a restraint operating after dissolution is valid only within the '
                'narrow limits of s. 27 of the Indian Contract Act, 1872 read with ss. 11(2), '
                '36(2) and 54 of the Partnership Act.'
            ),
        ),
        Section(
            name='INDEMNITY AND PARTNER LIABILITY',
            guidance=(
                'Indemnity between partners, and an accurate statement of liability to third '
                'parties: every partner is liable jointly and severally for all acts of the '
                'firm done while a partner.'
            ),
        ),
        Section(
            name='DISPUTE RESOLUTION',
            guidance=(
                'Arbitration under the Arbitration and Conciliation Act, 1996 — number of '
                'arbitrators, seat, venue and language.'
            ),
            must_contain=(('arbitration',),),
        ),
        Section(
            name='DISSOLUTION AND SETTLEMENT OF ACCOUNTS',
            guidance=(
                'Grounds and mode of dissolution, and the settlement of accounts in the '
                'statutory order under s. 48: first the debts of the firm to third parties, '
                'then rateable repayment of partners\' advances, then repayment of capital, '
                'and only the residue divided in the PROFIT-SHARING ratio.'
            ),
            must_contain=(('dissolution', 'dissolved'),),
        ),
        Section(
            name='AMENDMENT, NOTICES AND GOVERNING LAW',
            guidance='Amendment only in writing signed by all partners; addresses for notices; governing law and jurisdiction.',
        ),
        Section(
            name='EXECUTION AND WITNESSES',
            guidance=(
                'IN WITNESS WHEREOF the partners have set their hands on the date first '
                'above written, followed by signature blocks for every partner and two '
                'witnesses, each with name and address.'
            ),
            must_contain=(('IN WITNESS WHEREOF',), ('WITNESS', 'Witnesses')),
        ),
    ),
    conventions=DEED_CONVENTIONS,
    statutes_allow=(
        'Indian Partnership Act, 1932 — ss. 4, 9, 10, 11, 12, 13, 14, 18 to 27 (mutual '
        'agency and liability), 29, 30 to 38, 39 to 44 (dissolution), 48 (settlement of '
        'accounts), 58 and 59 (registration), 69 (effect of non-registration)',
        'Indian Contract Act, 1872 — including s. 27 on restraint of trade',
        'Arbitration and Conciliation Act, 1996',
        'Income Tax Act, 1961 — s. 40(b) for remuneration and interest limits',
        'Indian Stamp Act, 1899 and the applicable State schedule',
    ),
    pitfalls=(
        'A partnership deed is a COMMERCIAL instrument. Do not cite or name the BNS, '
        'BNSS, BSA, IPC, CrPC or the Indian Evidence Act.',
        'Reproduce the profit-sharing ratio EXACTLY as instructed. The benchmark draft '
        'silently omitted an expressly instructed 50:30:20 ratio. If for any reason a '
        'given instruction cannot be followed, say so expressly in the document — '
        'silently dropping it is a defect.',
        'Never write that "no partner shall be liable for the acts of another partner". '
        'That contradicts mutual agency: under ss. 18 to 27 of the Indian Partnership Act, '
        '1932 every partner is an agent of the firm and is liable jointly and severally '
        'for all acts of the firm done while a partner. An internal indemnity may allocate '
        'the burden between partners, but it cannot limit liability to third parties — '
        'draft it as an indemnity and say so.',
        'On dissolution, assets are applied in the statutory order under s. 48 — outside '
        'debts first, then partners\' advances, then capital, and only the RESIDUE in the '
        'profit-sharing ratio. Distributing surplus by capital contribution alone '
        'contradicts both the agreed ratio and the statute.',
        'Death and insolvency of a partner must each be addressed substantively, with the '
        'mechanism for valuing and paying out the outgoing partner\'s interest. The '
        'benchmark draft omitted both despite an express instruction.',
        'A non-compete operating during the partnership is generally valid; one operating '
        'after a partner leaves is void under s. 27 of the Contract Act except within the '
        'narrow savings in ss. 36(2) and 54 of the Partnership Act. Flag any clause that '
        'goes further.',
        'Registration under s. 58 is optional but s. 69 bars the firm from suing to enforce '
        'a contractual right if unregistered. Note this rather than leaving it silent.',
    ),
    required_facts=(
        'the full name, age, parentage and address of every partner',
        'each partner\'s capital contribution',
        'the profit and loss sharing ratio, exactly as instructed',
        'the firm name, business and principal place of business',
        'the commencement date and whether the term is fixed or at will',
    ),
    kb_doc_types=('Appointment', 'Release'),
    min_sections=14,
    target_tokens=10000,
)


# ---------------------------------------------------------------------------
RENT_LEASE_AGREEMENT = Playbook(
    doc_type='rent_lease_agreement',
    label='Rent / Lease Agreement',
    branch=CIVIL,
    category='Property',
    aliases=(
        'rent agreement', 'lease agreement', 'rent_lease_agreement',
        'leave and licence', 'leave and license', 'tenancy agreement',
    ),
    keywords=(
        (r'(rent|lease|tenancy|licence|license)\s+agreement', 10),
        (r'leave\s+and\s+licen[cs]e', 9),
        (r'\blessor\b|\blessee\b|\blicensor\b|\blicensee\b', 6),
        (r'\blease\b|\btenancy\b', 4),
        (r'\barrear|\bevict', -5),          # steer to the notice playbook
    ) + _NOT_THE_INSTRUMENT,
    skeleton=(
        Section(
            name='PARTIES AND DATE',
            guidance=(
                'THIS AGREEMENT made at [PLACE] on [DATE] between [LESSOR] and [LESSEE], '
                'with full description and the standard inclusive-of-successors formula.'
            ),
            must_contain=(('THIS AGREEMENT', 'THIS DEED'),),
        ),
        Section(
            name='RECITALS',
            guidance='WHEREAS clauses establishing the lessor\'s title and the lessee\'s requirement.',
            must_contain=(('WHEREAS',),),
        ),
        Section(
            name='DESCRIPTION OF THE PREMISES',
            guidance=(
                'Full description with address, built-up area, floor, and boundaries; a '
                'detailed description may be placed in a Schedule.'
            ),
        ),
        Section(
            name='TERM AND COMMENCEMENT',
            guidance=(
                'The duration, the commencement date, and any renewal option with the '
                'mechanism and notice period for exercising it.'
            ),
            must_contain=(('term', 'period'),),
        ),
        Section(
            name='RENT, ESCALATION AND DEPOSIT',
            guidance=(
                'The monthly rent in figures and words, the due date, the mode of payment, '
                'the escalation rate and interval, the interest-free security deposit, and '
                'the terms and timeline for its refund.'
            ),
            must_contain=(('rent',), ('deposit',)),
        ),
        Section(
            name='OUTGOINGS, TAXES AND UTILITIES',
            guidance=(
                'Allocation of municipal taxes, maintenance charges, electricity, water and '
                'any society charges between lessor and lessee.'
            ),
        ),
        Section(
            name='USE AND RESTRICTIONS',
            guidance=(
                'Permitted use, and restraints on subletting, assignment, structural '
                'alteration and unlawful use.'
            ),
        ),
        Section(
            name='REPAIRS AND MAINTENANCE',
            guidance='Allocation of structural and day-to-day repairs.',
        ),
        Section(
            name='OBLIGATIONS OF THE PARTIES',
            guidance=(
                'Covenants of the lessor including quiet enjoyment, and covenants of the '
                'lessee including payment, care and yielding up.'
            ),
        ),
        Section(
            name='TERMINATION AND LOCK-IN',
            guidance=(
                'Notice period for termination by each party, any lock-in and its '
                'consequence, and the grounds for termination for breach.'
            ),
            must_contain=(('terminat',),),
        ),
        Section(
            name='HANDOVER AND DELIVERY OF POSSESSION',
            guidance=(
                'Condition in which the premises are to be yielded up, and the consequence '
                'of holding over, including mesne profits for use and occupation.'
            ),
        ),
        Section(
            name='DISPUTE RESOLUTION AND GOVERNING LAW',
            guidance='Arbitration or the jurisdiction of the courts at [PLACE].',
        ),
        Section(
            name='EXECUTION AND WITNESSES',
            guidance=(
                'IN WITNESS WHEREOF, followed by signature blocks for both parties and two '
                'witnesses, and a Schedule describing the premises.'
            ),
            must_contain=(('IN WITNESS WHEREOF',), ('WITNESS', 'Witnesses')),
        ),
    ),
    conventions=DEED_CONVENTIONS,
    statutes_allow=(
        'Transfer of Property Act, 1882 — ss. 105 to 117 (ss. 106, 107, 108 in particular)',
        'Registration Act, 1908 — s. 17(1)(d) and s. 49',
        'Indian Easements Act, 1882 — ss. 52 to 64, where the transaction is a licence',
        'The applicable State Rent Control Act, and the applicable Stamp Act schedule',
        'Indian Contract Act, 1872',
    ),
    pitfalls=(
        'A lease is a CIVIL instrument. Do not cite or name the BNS, BNSS, BSA, IPC, '
        'CrPC or the Indian Evidence Act.',
        'Distinguish a LEASE from a LEAVE AND LICENCE. A lease transfers an interest in '
        'the property and exclusive possession; a licence confers only permission to use. '
        'The label the parties choose does not decide it — the substance does. Draft '
        'consistently with the transaction actually intended and flag any mismatch.',
        'A lease from year to year, or for a term exceeding one year, or reserving a '
        'yearly rent, must be made by a REGISTERED instrument under s. 107 of the Transfer '
        'of Property Act read with s. 17(1)(d) of the Registration Act, 1908. This is why '
        'agreements are commonly made for 11 months. State the registration requirement '
        'for the actual term rather than leaving it implicit.',
        'Stamp duty is a State subject and varies. Do not assert a rate — state that stamp '
        'duty is payable as per the applicable State schedule and mark the rate '
        '"(to be confirmed)".',
        'Where a State Rent Control Act applies it may override the agreed terms on rent, '
        'eviction and notice. Identify the State and flag the possibility.',
        'Provide expressly for the refund timeline of the security deposit and for '
        'permitted deductions — its absence is the commonest source of dispute.',
    ),
    required_facts=(
        'the parties\' full names and addresses',
        'a full description of the premises',
        'the rent, deposit and term',
        'the State in which the premises are situated',
    ),
    kb_doc_types=('Rent', 'Agreement', 'Easements'),
    min_sections=11,
    target_tokens=8000,
)


# ---------------------------------------------------------------------------
SALE_DEED = Playbook(
    doc_type='sale_deed',
    label='Sale Deed',
    branch=CIVIL,
    category='Property',
    aliases=('sale deed', 'sale_deed', 'conveyance deed', 'deed of sale'),
    keywords=(
        (r'sale\s+deed|deed\s+of\s+sale|conveyance\s+deed', 10),
        (r'\bvendor\b.{0,40}\bvendee\b|\bvendee\b.{0,40}\bvendor\b', 7),
        (r'\bsale\b.{0,30}\b(property|land|flat|plot)\b', 5),
        (r'\bconveyanc', 5),
    ) + _NOT_THE_INSTRUMENT,
    skeleton=(
        Section(
            name='PARTIES AND DATE',
            guidance=(
                'THIS DEED OF SALE made at [PLACE] on [DATE] between [VENDOR] and [VENDEE], '
                'with full description and the inclusive-of-successors formula.'
            ),
            must_contain=(('DEED OF SALE', 'THIS DEED'),),
        ),
        Section(
            name='RECITALS AND DEVOLUTION OF TITLE',
            guidance=(
                'WHEREAS clauses tracing how the Vendor acquired title — the prior deed, '
                'its date, registration particulars, and any intervening devolution by '
                'inheritance, partition or succession.'
            ),
            must_contain=(('WHEREAS',),),
        ),
        Section(
            name='AGREEMENT TO SELL AND CONSIDERATION',
            guidance=(
                'The agreed sale consideration in figures and words, the mode and schedule '
                'of payment, and an acknowledgement of receipt.'
            ),
            must_contain=(('consideration',),),
        ),
        Section(
            name='OPERATIVE CONVEYANCE',
            guidance=(
                'NOW THIS DEED WITNESSETH that in consideration of the sum paid, the Vendor '
                'doth hereby grant, convey, transfer and assign unto the Vendee all that '
                'the property described in the Schedule, together with all rights, '
                'easements and appurtenances, to hold the same absolutely and forever.'
            ),
            must_contain=(('WITNESSETH', 'doth hereby', 'hereby grant, convey'),),
        ),
        Section(
            name='DELIVERY OF POSSESSION',
            guidance='The date and manner of delivery of vacant possession.',
            must_contain=(('possession',),),
        ),
        Section(
            name='COVENANTS FOR TITLE',
            guidance=(
                'The Vendor covenants that the Vendor has a clear and marketable title, '
                'full power to convey, that the property is free from encumbrances, charges '
                'and litigation, and that the Vendee shall quietly enjoy the property. '
                'Include an indemnity for breach.'
            ),
            must_contain=(('encumbrance',), ('covenant', 'covenants')),
        ),
        Section(
            name='TAXES, OUTGOINGS AND APPORTIONMENT',
            guidance='Apportionment of municipal taxes and outgoings as on the date of transfer.',
        ),
        Section(
            name='STAMP DUTY AND REGISTRATION',
            guidance=(
                'Who bears stamp duty and registration charges, and the parties\' obligation '
                'to appear before the Sub-Registrar for registration.'
            ),
            must_contain=(('registration', 'registered'),),
        ),
        Section(
            name='SCHEDULE OF PROPERTY',
            guidance=(
                'Full description: survey or plot number, area, boundaries on all four '
                'sides, and the property\'s municipal particulars.'
            ),
            must_contain=(('SCHEDULE', 'Schedule'),),
        ),
        Section(
            name='EXECUTION AND WITNESSES',
            guidance=(
                'IN WITNESS WHEREOF, signature blocks for Vendor and Vendee, and two '
                'witnesses with names and addresses.'
            ),
            must_contain=(('IN WITNESS WHEREOF',), ('WITNESS', 'Witnesses')),
        ),
    ),
    conventions=DEED_CONVENTIONS,
    statutes_allow=(
        'Transfer of Property Act, 1882 — s. 54 (sale), s. 55 (rights and liabilities of '
        'buyer and seller)',
        'Registration Act, 1908 — s. 17(1)(b) and s. 49',
        'Indian Stamp Act, 1899 and the applicable State schedule',
        'Indian Contract Act, 1872',
        'Real Estate (Regulation and Development) Act, 2016, where applicable',
    ),
    pitfalls=(
        'A sale deed is a CIVIL instrument. Do not cite or name the BNS, BNSS, BSA, IPC, '
        'CrPC or the Indian Evidence Act.',
        'A sale of immovable property of the value of Rs. 100 or more can be made only by '
        'a REGISTERED instrument under s. 54 of the Transfer of Property Act, 1882. An '
        'unregistered sale deed conveys nothing.',
        'The recitals must trace devolution of title with the prior deed and its '
        'registration particulars. A conveyance that does not show how the Vendor got '
        'title is not a marketable one.',
        'Stamp duty is a State subject and rates differ. Never assert a rate — state that '
        'it is payable as per the applicable State schedule and mark it '
        '"(to be confirmed)".',
        'The Schedule must describe the property with boundaries on all four sides. A '
        'vague description defeats identification and registration.',
        'Do not draft the receipt of consideration as acknowledged unless the facts say it '
        'was received. Where payment is deferred, say so and provide for the consequence '
        'of default.',
    ),
    required_facts=(
        'the parties\' full names, ages, parentage and addresses',
        'the prior deed by which the Vendor acquired title, with registration particulars',
        'the sale consideration and the mode of payment',
        'a full description of the property with boundaries',
    ),
    kb_doc_types=('SALES', 'Conveyancing', 'Gift'),
    min_sections=9,
    target_tokens=8000,
)


INSTRUMENT_PLAYBOOKS = (
    WILL,
    PARTNERSHIP_DEED,
    RENT_LEASE_AGREEMENT,
    SALE_DEED,
)
