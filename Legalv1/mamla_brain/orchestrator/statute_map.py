"""
Bharatiya Nyaya Sanhita-era statutory correspondence map.

The 2023 codes replaced the colonial-era ones:
  IPC 1860            -> Bharatiya Nyaya Sanhita, 2023        (BNS)
  CrPC 1973           -> Bharatiya Nagarik Suraksha Sanhita   (BNSS)
  Indian Evidence Act -> Bharatiya Sakshya Adhiniyam, 2023    (BSA)

This module holds a DELIBERATELY SMALL, high-confidence set of the
most-frequently-cited section correspondences. The point of the feature is
accuracy: an incorrect mapping here would be asserted confidently by the model,
so we keep only well-established mappings and instruct the model to mark
anything NOT in this list as "to be confirmed" rather than guess a number.

Extend this list only with mappings verified against the bare acts.
"""

# --- IPC 1860 -> BNS 2023 --------------------------------------------------
IPC_TO_BNS = {
    '34': 'BNS 3(5)',      # common intention
    '120B': 'BNS 61',      # criminal conspiracy
    '149': 'BNS 190',      # unlawful assembly / common object
    '300': 'BNS 101',      # murder (definition)
    '302': 'BNS 103',      # murder (punishment)
    '304': 'BNS 105',      # culpable homicide not amounting to murder
    '304A': 'BNS 106',     # death by negligence
    '304B': 'BNS 80',      # dowry death
    '306': 'BNS 108',      # abetment of suicide
    '307': 'BNS 109',      # attempt to murder
    '375': 'BNS 63',       # rape (definition)
    '376': 'BNS 64',       # rape (punishment)
    '379': 'BNS 303',      # theft
    '392': 'BNS 309',      # robbery
    '420': 'BNS 318',      # cheating (esp. BNS 318(4))
    '498A': 'BNS 85',      # cruelty by husband/relatives (defn at BNS 86)
    '499': 'BNS 356',      # defamation (definition)
    '500': 'BNS 356',      # defamation (punishment)
}

# --- CrPC 1973 -> BNSS 2023 ------------------------------------------------
CRPC_TO_BNSS = {
    '41': 'BNSS 35',       # arrest without warrant
    '125': 'BNSS 144',     # maintenance
    '144': 'BNSS 163',     # power to issue order in urgent cases
    '154': 'BNSS 173',     # FIR
    '156(3)': 'BNSS 175(3)',  # magistrate ordering investigation
    '161': 'BNSS 180',     # examination of witnesses by police
    '164': 'BNSS 183',     # recording of confessions/statements
    '173': 'BNSS 193',     # police report / charge-sheet
    '200': 'BNSS 223',     # examination of complainant
    '437': 'BNSS 480',     # bail in non-bailable offence (Magistrate)
    '438': 'BNSS 482',     # anticipatory bail
    '439': 'BNSS 483',     # special powers of HC/Sessions re bail
    '482': 'BNSS 528',     # inherent powers of the High Court
}

# --- Indian Evidence Act 1872 -> BSA 2023 ----------------------------------
IEA_TO_BSA = {
    '3': 'BSA 2',          # interpretation clause
    '25': 'BSA 23',        # confession to police
    '27': 'BSA 23(2)',     # discovery / how much of information admissible
    '32': 'BSA 26',        # dying declaration / statements of persons who cannot testify
    '45': 'BSA 39',        # expert opinion
    '65B': 'BSA 63',       # admissibility of electronic records
    '114': 'BSA 119',      # court may presume existence of facts
}

# Keyed by UPPERCASE old-code so lookups are case-insensitive.
_OLD_CODE_LABEL = {
    'IPC': ('IPC 1860', 'BNS 2023', IPC_TO_BNS),
    'CRPC': ('CrPC 1973', 'BNSS 2023', CRPC_TO_BNSS),
    'IEA': ('Indian Evidence Act 1872', 'BSA 2023', IEA_TO_BSA),
}


def bns_equivalent(old_code: str, section: str) -> str | None:
    """Return the new-code reference for an old IPC/CrPC/IEA section, or None."""
    table = _OLD_CODE_LABEL.get((old_code or '').upper())
    if not table:
        return None
    return table[2].get((section or '').strip().upper())


def _render_map(table: dict, old_label: str) -> str:
    return '; '.join(f'{old_label} {old}→{new}' for old, new in table.items())


def build_bns_prompt_fragment() -> str:
    """Compact, injectable statutory-guidance fragment for system prompts."""
    return (
        "INDIAN STATUTORY FRAMEWORK (2023 codes are now in force):\n"
        "- Lead with the current codes: Bharatiya Nyaya Sanhita, 2023 (BNS) replaced the "
        "IPC; Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS) replaced the CrPC; "
        "Bharatiya Sakshya Adhiniyam, 2023 (BSA) replaced the Indian Evidence Act.\n"
        "- On first mention of a provision, give the current-code section with the old-code "
        "equivalent in parentheses. Use ONLY these verified correspondences:\n"
        f"  {_render_map(IPC_TO_BNS, 'IPC')}\n"
        f"  {_render_map(CRPC_TO_BNSS, 'CrPC')}\n"
        f"  {_render_map(IEA_TO_BSA, 'IEA')}\n"
        "- For ANY provision NOT in the list above, name the offence/provision in words and "
        "state that the exact BNS/BNSS/BSA section is 'to be confirmed' — do NOT guess a "
        "section number. Never assert a section number you have not verified.\n"
        "- Note: offences like sedition (old IPC 124A) have no direct one-to-one equivalent; "
        "describe the change rather than equating section numbers."
    )
