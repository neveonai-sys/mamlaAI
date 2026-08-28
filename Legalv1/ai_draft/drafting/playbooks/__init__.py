"""
Playbook registry.

Import-time invariants are enforced here rather than in a test, because a
duplicate alias or a colliding doc_type silently mis-routes drafts in production
and the failure looks like "the model got it wrong". Better to refuse to start.

`GENERIC` is the fallback for anything unclassified. It is the ONLY playbook
whose branch is `unknown`, and therefore the only one that still carries the old
conditional statute wording — which the whole package exists to stop relying on.
Every classified type gets an explicit allow-list or an explicit prohibition.
"""

from __future__ import annotations

from .base import (
    BRANCHES,
    CIVIL,
    COMMERCIAL,
    CONSTITUTIONAL,
    CRIMINAL,
    FAMILY,
    NON_PENAL_BRANCHES,
    TESTAMENTARY,
    UNKNOWN,
    Playbook,
    Section,
)
from .instruments import INSTRUMENT_PLAYBOOKS
from .litigation import LITIGATION_PLAYBOOKS
from .notices import NOTICE_PLAYBOOKS

# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------
GENERIC = Playbook(
    doc_type='generic',
    label='Legal Document',
    branch=UNKNOWN,
    category='Other',
    aliases=('generic', 'other', 'document'),
    keywords=(),
    skeleton=(
        Section(
            name='TITLE',
            guidance='The name of the instrument and, where it is filed in court, the cause title.',
        ),
        Section(
            name='PARTIES',
            guidance='Every party with full name, description and address.',
        ),
        Section(
            name='BODY',
            guidance=(
                'The substantive content, in numbered paragraphs. Where the document is a '
                'pleading or a notice, each paragraph begins with the word "That".'
            ),
        ),
        Section(
            name='OPERATIVE PART',
            guidance='The demand, prayer, or operative covenants, as the document requires.',
        ),
        Section(
            name='EXECUTION',
            guidance='Signature, date, place and witness or attestation blocks as applicable.',
        ),
    ),
    conventions=(
        'Follow Indian drafting convention: numbered paragraphs, formal register, '
        'third person for pleadings and notices, first person for affidavits and wills.',
        'State amounts as "Rs. 5,00,000/- (Rupees Five Lakh only)".',
        'Use ALL-CAPS bracketed placeholders such as [CLIENT NAME] for anything not supplied.',
    ),
    statutes_allow=(),
    pitfalls=(
        'Identify the branch of law that actually governs this document before citing '
        'anything. The penal codes (BNS, BNSS, BSA) apply ONLY to criminal matters. Do '
        'not cite them in a civil, commercial, testamentary or family matter.',
        'Never assert a section number you have not verified. Name the provision in words '
        'and mark it "(exact section to be confirmed)".',
    ),
    min_sections=5,
    target_tokens=6000,
)


ALL_PLAYBOOKS: tuple[Playbook, ...] = (
    NOTICE_PLAYBOOKS + LITIGATION_PLAYBOOKS + INSTRUMENT_PLAYBOOKS + (GENERIC,)
)

# ---------------------------------------------------------------------------
# Indexes, built once and validated at import.
# ---------------------------------------------------------------------------
_BY_TYPE: dict[str, Playbook] = {}
_BY_ALIAS: dict[str, Playbook] = {}

for _pb in ALL_PLAYBOOKS:
    if _pb.doc_type in _BY_TYPE:
        raise RuntimeError(f'duplicate playbook doc_type: {_pb.doc_type}')
    _BY_TYPE[_pb.doc_type] = _pb

    for _alias in (_pb.doc_type,) + _pb.aliases:
        _key = _alias.strip().lower()
        _existing = _BY_ALIAS.get(_key)
        if _existing is not None and _existing.doc_type != _pb.doc_type:
            raise RuntimeError(
                f'alias {_alias!r} claimed by both {_existing.doc_type} and {_pb.doc_type}'
            )
        _BY_ALIAS[_key] = _pb

del _pb, _alias, _key, _existing


def get(doc_type: str | None) -> Playbook:
    """Look up by doc_type or alias. Never raises — unknown types get GENERIC."""
    if not doc_type:
        return GENERIC
    return _BY_ALIAS.get(str(doc_type).strip().lower(), GENERIC)


def exists(doc_type: str | None) -> bool:
    return bool(doc_type) and str(doc_type).strip().lower() in _BY_ALIAS


def all_playbooks(include_generic: bool = False) -> tuple[Playbook, ...]:
    if include_generic:
        return ALL_PLAYBOOKS
    return tuple(p for p in ALL_PLAYBOOKS if p.doc_type != GENERIC.doc_type)


def aliases() -> dict[str, str]:
    """alias -> doc_type, for the classifier."""
    return {k: v.doc_type for k, v in _BY_ALIAS.items()}


def ui_categories() -> list[dict]:
    """
    Payload for `users/supabase_views.py`'s `document_categories` key.

    The drafting workspace's type picker gates on this key and has therefore
    never rendered — the backend has never returned it. Shape is
    `[{category, types: [{value, label}]}]`, grouped and alphabetised.
    """
    grouped: dict[str, list[dict]] = {}
    for pb in all_playbooks():
        grouped.setdefault(pb.category, []).append({'value': pb.doc_type, 'label': pb.label})
    return [
        {'category': category, 'types': sorted(types, key=lambda t: t['label'])}
        for category, types in sorted(grouped.items())
    ]


__all__ = [
    'ALL_PLAYBOOKS', 'GENERIC', 'Playbook', 'Section',
    'BRANCHES', 'NON_PENAL_BRANCHES',
    'CIVIL', 'CRIMINAL', 'COMMERCIAL', 'TESTAMENTARY', 'FAMILY', 'CONSTITUTIONAL', 'UNKNOWN',
    'get', 'exists', 'all_playbooks', 'aliases', 'ui_categories',
]
