"""
Chat-wide citation grounding.

Generalises the fetch-then-inject pattern proven in
`ai_draft/citation_grounding.py` (which today only guards the drafting
section-refine path) so that *any* capability in MamlaAI Chat — general
answers, research, drafting — is verification-gated: if the user's turn asks
for a citation, we resolve it against the live Supreme Court e-SCR portal
*before* the model writes, and hand the model either a labelled VERIFIED
CITATION block or an explicit "could not verify — do not supply from memory"
instruction. The model is never left free to fabricate a case name or number.

We deliberately reuse the existing module rather than reimplement the regexes
and the e-SCR lookup, so there is one source of truth for citation handling.
"""
import logging

from ai_draft.citation_grounding import build_grounding_block, mentions_citation_intent

logger = logging.getLogger('django')


def augment_system_with_grounding(system_prompt: str, user_text: str) -> str:
    """
    Return `system_prompt` with a citation-grounding block appended when the
    user's turn mentions a citation/precedent/case-law, otherwise unchanged.

    Any lookup failure is swallowed (build_grounding_block already degrades to a
    "could not verify" instruction on error), so this never blocks a turn.
    """
    if not user_text or not mentions_citation_intent(user_text):
        return system_prompt
    try:
        block = build_grounding_block(user_text)
    except Exception as exc:  # defensive: grounding must never crash a turn
        logger.warning('[orchestrator.grounding] failed: %s', exc)
        return system_prompt
    return f'{system_prompt}{block}' if block else system_prompt
