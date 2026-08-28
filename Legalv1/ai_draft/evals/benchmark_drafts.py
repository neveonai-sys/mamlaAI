"""
The drafts from the intern benchmark, transcribed verbatim.

Provenance: "Comparison with other AI(s)", the law interns' evaluation of
Mamla.ai against Jhana.ai and DraftBotPro. Reviewer scores for prompt 1
(rent-arrears legal notice): Mamla 3/10, Jhana 7/10.

These are kept in the repo for one reason: they are the only ground truth we
have that ties a *score* to a *document*. `tests/test_draft_evals.py` asserts
that `score_deterministic` reproduces the reviewers' ranking and rough
magnitude on them. If someone later loosens a check until our own drafts pass,
that test fails — the rubric cannot drift away from what a lawyer would say
without someone noticing.

Do not "improve" these texts. They are evidence, not examples.
"""

# ---------------------------------------------------------------------------
# Prompt 1 — rent-arrears legal notice
# ---------------------------------------------------------------------------

# What our engine produced. Reviewer: 3/10.
# Findings: BNSS cited in a civil rent dispute; no recitals, no NOW THEREFORE,
# no TAKE NOTICE; no advocate letterhead or formal closing; eviction threatened
# though only payment-in-15-days was instructed.
MAMLA_RENT_NOTICE = [
    {
        'section_name': 'LEGAL NOTICE',
        'content': (
            'To, [AKRITI SWAROOP], [ADDRESS OF AKRITI SWAROOP]. Date: [CURRENT DATE]. '
            'Subject: Legal Notice for Recovery of Outstanding Rent. Dear [AKRITI SWAROOP], '
            'This notice is being sent to you on behalf of my client, Ms. Karuna Anupam, '
            'residing at [ADDRESS OF KARUNA ANUPAM]. It has come to our attention that you '
            'have failed to pay the rent for the residential apartment leased to you under '
            'the lease agreement dated 15 January 2026, at a monthly rent of Rs 32,000.'
        ),
    },
    {
        'section_name': 'OUTSTANDING DUES',
        'content': (
            'As per the terms of the lease agreement, you are obligated to make timely '
            'payments. However, you have not paid the rent for the months of May, June, and '
            'July 2026, resulting in an outstanding total of Rs 96,000. Despite several '
            'reminders sent to you regarding this matter, you have failed to respond or make '
            'the necessary payments. This continued non-payment constitutes a breach of the '
            'lease agreement, and my client is left with no option but to take legal action.'
        ),
    },
    {
        'section_name': 'DEMAND FOR PAYMENT',
        'content': (
            'Through this legal notice, my client demands that you clear the outstanding dues '
            'of Rs 96,000 within 15 days from the date of this notice. Failure to comply with '
            'this demand will compel my client to initiate appropriate legal proceedings '
            'against you, including but not limited to filing a suit for recovery of the '
            'outstanding amount, along with any applicable interest and costs incurred in the '
            'process.'
        ),
    },
    {
        'section_name': 'CONSEQUENCES OF NON-COMPLIANCE',
        'content': (
            'Please be advised that if you do not settle the outstanding amount within the '
            'stipulated time frame, my client reserves the right to take legal action without '
            'any further notice to you. This may include eviction proceedings as per the '
            'provisions of the Bharatiya Nagarik Suraksha Sanhita 2023 (BNSS, replaced CrPC) '
            'and other applicable laws. We hope you will treat this matter with the '
            'seriousness it deserves and act accordingly.'
        ),
    },
    {
        'section_name': 'CLOSING STATEMENT',
        'content': (
            'We look forward to your prompt response and resolution of this matter. Kindly '
            'make the payment to avoid any legal complications. This notice is issued in good '
            'faith and with the intention of resolving the matter amicably. Yours sincerely, '
            '[YOUR NAME], Advocate for Ms. Karuna Anupam, [YOUR ADDRESS], '
            '[YOUR CONTACT INFORMATION].'
        ),
    },
]

# What Jhana.ai produced. Reviewer: 7/10.
# Jhana emits one flowing document; the block boundaries below are the
# document's own (header / addressee / subject / recitals / demand /
# consequences / copy-retained / closing).
JHANA_RENT_NOTICE = [
    {
        'section_name': 'LEGAL NOTICE — ADVOCATE BLOCK',
        'content': (
            "[ADVOCATE'S OFFICE ADDRESS] Email: [ADVOCATE'S EMAIL] "
            "Phone: [ADVOCATE'S PHONE] Date: [DATE] Ref. No.: [REF NO]"
        ),
    },
    {
        'section_name': 'TO',
        'content': "To, Ms. Akriti Swaroop, [TENANT'S ADDRESS]",
    },
    {
        'section_name': 'SUBJECT',
        'content': (
            'Subject: Legal Notice for the recovery of arrears of rent in respect of '
            'the property at [PROPERTY ADDRESS]'
        ),
    },
    {
        'section_name': 'RECITALS',
        'content': (
            'Madam, Under the instructions and on behalf of my client, Ms. Karuna Anupam, '
            'daughter of [FATHER\'S NAME], resident of [CLIENT\'S ADDRESS] (hereinafter '
            'referred to as "my Client"), I do hereby serve you with the following Legal '
            'Notice: '
            '1. That my Client is the absolute owner and landlord of the residential '
            'apartment located at [PROPERTY ADDRESS] (hereinafter referred to as the "Said '
            'Apartment"). '
            '2. That vide a Lease Agreement dated 15th January 2026 (the "Agreement"), you '
            'were inducted as a tenant in the Said Apartment at a monthly rent of Rs 32,000/- '
            '(Rupees Thirty-Two Thousand only), exclusive of electricity and other charges. '
            '3. That in breach of the terms of the Agreement, you have failed and neglected '
            'to pay the monthly rent for the months of May, June, and July 2026. The total '
            'outstanding arrears of rent amount to Rs 96,000/- (Rupees Ninety-Six Thousand '
            'only). '
            '4. That despite repeated oral and written reminders from my Client to clear the '
            'outstanding dues, you have failed to make the payment, which constitutes a '
            'material breach of the Agreement. '
            '5. That your failure to pay the rent is causing my Client significant financial '
            'hardship and mental anguish.'
        ),
    },
    {
        'section_name': 'DEMAND',
        'content': (
            'I, therefore, through this Legal Notice, call upon you to pay to my Client the '
            'total outstanding amount of Rs 96,000/- (Rupees Ninety-Six Thousand only) within '
            'a period of 15 (fifteen) days from the date of receipt of this notice.'
        ),
    },
    {
        'section_name': 'CONSEQUENCES',
        'content': (
            'Please note that if you fail to comply with the demand herein within the '
            'stipulated period, my Client shall be constrained to initiate appropriate legal '
            'proceedings against you for recovery of the outstanding rent, eviction from the '
            'Said Apartment, and for damages and other reliefs, entirely at your cost, risk, '
            'and consequences, which you may please note.'
        ),
    },
    {
        'section_name': 'COPY RETAINED',
        'content': 'A copy of this notice has been retained in my office for further action.',
    },
    {
        'section_name': 'CLOSING',
        'content': "Yours faithfully, [ADVOCATE'S NAME], Advocate",
    },
]


# ---------------------------------------------------------------------------
# Prompt 4 — partnership deed (the truncation case)
# ---------------------------------------------------------------------------

# Our engine's final section, verbatim. It stops mid-clause: max_tokens=4000
# cut it and nothing in the pipeline noticed. The 50:30:20 profit ratio the
# prompt expressly specified never appears anywhere in the deed.
MAMLA_PARTNERSHIP_DEED_TAIL = {
    'section_name': 'EXECUTION AND WITNESS',
    'content': (
        'IN WITNESS WHEREOF, the partners hereto have executed this Partnership Deed on '
        'this [DATE] at Kolkata, West Bengal. The partners shall sign below in the presence '
        'of the'
    ),
}
