"""
core/input_sanitizer.py — LLM input sanitization for Mamla.AI.

Prevents prompt injection, enforces per-tier length limits, and strips
control characters before any user text reaches the LLM.

Usage::

    from core.input_sanitizer import sanitize_user_input, LLM_INPUT_MAX_LENGTHS

    safe_text = sanitize_user_input(raw_text, tier='t2')
"""

import re
import logging
import unicodedata

logger = logging.getLogger('django')

# ---------------------------------------------------------------------------
# Per-tier max input character limits
# ---------------------------------------------------------------------------
LLM_INPUT_MAX_LENGTHS: dict = {
    't1': 512,     # query rewriting, intent classification
    't2': 2048,    # document Q&A, short answers
    't3': 4096,    # case companion, multi-doc reasoning
    'general': 2048,  # fallback for non-brain scenarios
}

# ---------------------------------------------------------------------------
# Known prompt injection patterns (case-insensitive)
# ---------------------------------------------------------------------------
_INJECTION_PATTERNS = [
    r'ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|context|messages?)',
    r'disregard\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|context)',
    r'forget\s+(everything|all|your\s+instructions?)',
    r'you\s+are\s+now\s+(a|an|the)\s+',
    r'act\s+as\s+(if\s+you\s+(are|were)\s+)?a(n)?\s+',
    r'new\s+instructions?\s*:',
    r'system\s*:\s*(you|your)',
    r'<\s*/?system\s*>',
    r'<\s*/?instructions?\s*>',
    r'\[system\]',
    r'\[instructions?\]',
    r'do\s+not\s+follow\s+(your|the)\s+(instructions?|guidelines?|rules?)',
    r'override\s+(your\s+)?(previous|prior|all)?\s*(instructions?|guidelines?|rules?|constraints?)',
    r'jailbreak',
    r'prompt\s*injection',
    r'reveal\s+(your\s+)?(system\s+)?prompt',
    r'what\s+(are|were)\s+your\s+(instructions?|guidelines?|system\s+prompt)',
    r'repeat\s+(after\s+me|your\s+(instructions?|system\s+prompt)|the\s+system\s+prompt)',
    r'print\s+(your\s+)?(system\s+prompt|instructions?|guidelines?)',
    r'ignore\s+(safety|content)\s+(filters?|guidelines?|policies)',
    r'output\s+the\s+raw\s+(prompt|system\s+message)',
    r'from\s+now\s+on\s+(you\s+(are|will|must)|ignore)',
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE | re.UNICODE) for p in _INJECTION_PATTERNS]

# Control character pattern — strip non-printable chars except standard whitespace
_CONTROL_CHAR_PATTERN = re.compile(
    r'[^\x09\x0A\x0D\x20-\x7E\x80-\xFF\u0100-\uFFFF]'
)


class PromptInjectionError(ValueError):
    """Raised when user input contains a suspected prompt injection attempt."""


def _strip_control_chars(text: str) -> str:
    """Remove non-printable control characters, keeping tabs/newlines/spaces."""
    normalized = unicodedata.normalize('NFC', text)
    return _CONTROL_CHAR_PATTERN.sub('', normalized)


def _check_injection(text: str) -> bool:
    """Return True if the text matches any known injection pattern."""
    for pattern in _COMPILED_PATTERNS:
        if pattern.search(text):
            return True
    return False


def sanitize_user_input(text: str, tier: str = 'general', raise_on_injection: bool = True) -> str:
    """
    Sanitize user text before passing it to the LLM.

    Steps:
      1. Normalize and strip control characters.
      2. Enforce per-tier maximum length (truncates with a notice).
      3. Check for prompt injection patterns.

    Args:
        text:               Raw user-supplied text.
        tier:               One of 't1', 't2', 't3', 'general'.
                            Controls the max length applied.
        raise_on_injection: If True (default), raises PromptInjectionError on
                            detection. If False, logs a warning and returns the
                            text as-is for caller to decide.

    Returns:
        Sanitized text string.

    Raises:
        PromptInjectionError: When injection is detected and raise_on_injection=True.
    """
    if not isinstance(text, str):
        text = str(text or '')

    # Step 1 — strip control characters
    cleaned = _strip_control_chars(text).strip()

    # Step 2 — enforce length limit
    max_len = LLM_INPUT_MAX_LENGTHS.get(tier, LLM_INPUT_MAX_LENGTHS['general'])
    if len(cleaned) > max_len:
        logger.warning(
            '[INPUT_SANITIZER] input truncated: tier=%s original_len=%d max_len=%d',
            tier, len(cleaned), max_len,
        )
        cleaned = cleaned[:max_len]

    # Step 3 — injection check
    if _check_injection(cleaned):
        logger.warning(
            '[INPUT_SANITIZER] prompt injection attempt detected: tier=%s snippet=%.80r',
            tier, cleaned[:80],
        )
        if raise_on_injection:
            raise PromptInjectionError(
                'Your input contains patterns that are not allowed. Please rephrase your question.'
            )

    return cleaned
