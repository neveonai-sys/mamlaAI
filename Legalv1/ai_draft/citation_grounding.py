"""
Citation grounding for mid-drafting chat instructions.

When a user types something like "include citation for State of UP v. Ram
Prakash Singh" while refining a draft section, the free-text instruction
goes straight into the LLM's `user` message today
(`CreateupdatefetchAIdrafts.update_content_using_AI_with_user_input` in
`ai_draft/routes/creatupdateAIdrafts.py`) with nothing stopping the LLM from
inventing a citation from memory.

This module implements fetch-then-inject grounding: resolve the real
citation from the live e-SCR portal *before* the LLM writes anything, then
hand the LLM a labeled, verified data block and instruct it to use only
that — never let it supply its own case names or citation numbers.

There is no function/tool-calling infrastructure in this codebase
(`core/llm_client.chat_complete` is single-shot prompt->completion), so this
is deliberately a plain pre-processing step, not a mid-generation tool call.
"""

import json
import logging
import re
from typing import Optional

from ecourt_scrapped.services import citation_client

logger = logging.getLogger('django')

_CITATION_INTENT_RE = re.compile(r"\b(citation|cite|precedent|case\s*law|judgm?ent)\b", re.IGNORECASE)

# Structured-citation shapes worth trying to resolve directly, mirrored from
# scrapping_codes_ecourt/sc_citation_scraper.py's classify_citation().
_NEUTRAL_SC_RE = re.compile(r"\d{4}\s*INSC\s*\d+", re.IGNORECASE)
_SCR_RE = re.compile(r"\[?\d{4}\]?\s*\d*\s*S\.?\s?C\.?\s?R\.?\s*\d+", re.IGNORECASE)
_REPORTER_RE = re.compile(r"\(?\d{4}\)?\s*\d*\s*(SCC|JT|SCALE|AIR)\s*(?:SC)?\s*\d+", re.IGNORECASE)

# "X v. Y" / "X vs Y" / "X versus Y" party-name shape. Deliberately NOT
# re.IGNORECASE as a whole — with IGNORECASE, `[A-Z]` also matches lowercase
# letters, so the leading boundary would match mid-sentence (e.g. the "i" in
# "include citation for ..."). Only the connector ("v."/"vs"/"versus") needs
# case-insensitivity, via the inline (?i:...) group.
_PARTY_RE = re.compile(r"[A-Z][\w.&' -]{2,60}\s+(?:(?i:v\.?s?\.?|versus))\s+[A-Z][\w.&' -]{2,60}")

_STRIP_PREFIX_RE = re.compile(
    r"^(please\s+)?(include|add|insert|cite|provide|find|fetch)\s+(a\s+|the\s+)?"
    r"(citation|case\s*law|precedent)s?\s*(for|of|on|about|to)?\s*",
    re.IGNORECASE,
)


def mentions_citation_intent(instruction: str) -> bool:
    return bool(_CITATION_INTENT_RE.search(instruction or ""))


def extract_candidate(instruction: str) -> Optional[str]:
    """
    Best-effort extraction of a citation string or case name from free text.

    Returns None when the instruction only names a legal *topic* ("cite a
    case on anticipatory bail") rather than a specific case or citation —
    e-SCR resolves/verifies citations you already point at, it cannot
    discover cases by topic, so there's nothing to look up.
    """
    text = (instruction or "").strip()
    if not text:
        return None
    if _NEUTRAL_SC_RE.search(text) or _SCR_RE.search(text) or _REPORTER_RE.search(text):
        return text
    if m := _PARTY_RE.search(text):
        return m.group(0)

    # Crude heuristic: strip a leading command phrase ("include citation for ...")
    # and treat what's left as a candidate case name if it still reads like one
    # (starts with a capital, isn't a long sentence).
    stripped = _STRIP_PREFIX_RE.sub("", text).strip()
    if stripped and stripped[:1].isupper() and len(stripped.split()) <= 12:
        return stripped
    return None


def build_grounding_block(instruction: str) -> Optional[str]:
    """
    If `instruction` asks for a citation, resolve it against the live e-SCR
    portal and return a labeled context block to append to the LLM system
    prompt: either verified citation data, or an explicit "could not verify"
    instruction — never a silent pass-through that lets the LLM fabricate one.

    Returns None when the instruction doesn't mention citations at all, so
    callers can fall back to the existing ungrounded prompt unchanged.
    """
    if not mentions_citation_intent(instruction):
        return None

    candidate = extract_candidate(instruction)
    if not candidate:
        return (
            "\n\nCITATION VERIFICATION NOTICE: The user asked to include a citation "
            "but did not name a specific case or citation number, so nothing could be "
            "verified against the Supreme Court's official e-SCR portal (e-SCR can "
            "verify a specific case, not search by legal topic). Do not supply any "
            "case name or citation number from memory — instead, ask the user to name "
            "the specific case or citation they want included."
        )

    try:
        result = citation_client.lookup_citation(candidate)
    except Exception as e:
        logger.warning("[citation_grounding] lookup failed for %r: %s", candidate, e)
        return (
            "\n\nCITATION VERIFICATION NOTICE: A citation lookup was attempted for "
            f'"{candidate}" against the Supreme Court\'s official e-SCR portal, but the '
            "lookup service is currently unavailable. Do not supply a case name or "
            "citation number from memory — instead, state that the citation could not "
            "be verified right now and ask the user to try again shortly."
        )

    if not result or not result.get('case_title'):
        return (
            "\n\nCITATION VERIFICATION NOTICE: A citation lookup was attempted for "
            f'"{candidate}" against the Supreme Court\'s official e-SCR portal, but no '
            "matching case was found. Do not supply a case name or citation number "
            "from memory — instead, state plainly that this citation could not be "
            "verified."
        )

    verified = {
        'case_title': result.get('case_title'),
        'neutral_citation': result.get('nc_display'),
        'scr_citation': result.get('scr_citation'),
        'cnr': result.get('cnr'),
    }
    return (
        "\n\nVERIFIED CITATION (resolved live from the Supreme Court's official "
        f"e-SCR portal): {json.dumps(verified, ensure_ascii=False)}\n"
        "Use this exact case title and citation when referring to this case. Do not "
        "invent, alter, or add any other case name, citation number, or party name "
        "from memory — only use what is given above."
    )
