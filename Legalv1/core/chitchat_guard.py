"""
core/chitchat_guard.py  —  Zero-cost chitchat detector for Mamla.AI.

Three steps, all pure-Python (zero network, zero tokens):
 1. Normalise: collapse 3+ repeated chars  hiii->hi, hellooo->hello
 2. Gibberish check: 'fa', 'ksjd', empty -> canned reply
 3. Regex: run against BOTH raw and normalised text so fuzzy variants
    are caught in one pass without extra code.

has_legal_signal(text) -> bool
    Fast keyword pre-check. When True the T0 LLM gate can be skipped
    and the message goes straight to T1/T2/T3.
"""
import re

# ---------------------------------------------------------------------------
# Canned replies
# ---------------------------------------------------------------------------
_REPLY_GREETING  = ("Hello! I'm Mamla.AI, your Indian legal research assistant. "
                    "Please share your legal question — about a case, statute, "
                    "court procedure, or document — and I'll get right to it.")
_REPLY_GRATITUDE = "You're welcome! Let me know if you have any other legal questions."
_REPLY_FAREWELL  = "Goodbye! Feel free to return whenever you need legal assistance."
_REPLY_META      = ("I'm Mamla.AI, an AI assistant focused on Indian law. "
                    "I'm not able to share details about my underlying architecture or training. "
                    "If you have a legal question, I'm here to help!")
_REPLY_ACK       = "Got it. Do you have a legal question I can help you with?"
_REPLY_GIBBERISH = ("I didn't quite catch that. Could you describe your legal question or issue? "
                    "I'm here to help with anything related to Indian law.")

# ---------------------------------------------------------------------------
# Step 1 — normalisation
# ---------------------------------------------------------------------------
_REPEAT_PAT  = re.compile(r'(.)\1{2,}')   # 3+ -> 2  (for gibberish check)
_DEDUP_PAT   = re.compile(r'(.)\1+')      # 2+ -> 1  (for regex matching)


def _normalise(text: str) -> str:
    """Collapse 3+ identical consecutive chars to 2: hiii->hi, hellooo->hello."""
    return _REPEAT_PAT.sub(r'\1\1', text)


def _dedup(text: str) -> str:
    """Collapse ALL runs of repeated chars to 1: helloo->helo, heyy->hey."""
    return _DEDUP_PAT.sub(r'\1', text)

# ---------------------------------------------------------------------------
# Step 2 — gibberish detection (zero cost)
# ---------------------------------------------------------------------------
_VOWELS        = set('aeiouAEIOU')
_LEGAL_ABBREVS = {'IPC', 'CPC', 'FIR', 'SC', 'HC', 'DC', 'MV', 'IT', 'GST', 'TDS', 'CBI', 'ED'}

def _is_gibberish(text: str) -> bool:
    s = text.strip()
    if not s:
        return True
    # 1-3 chars: allow known legal abbreviations and bare digits (section refs)
    if len(s) <= 3:
        return not (s.upper() in _LEGAL_ABBREVS or s.isdigit())
    alpha = [c for c in s if c.isalpha()]
    if not alpha:
        return True
    # Short all-consonant word -> gibberish
    if len(s) <= 7 and sum(1 for c in alpha if c in _VOWELS) == 0:
        return True
    return False

# ---------------------------------------------------------------------------
# Step 3 — regex patterns (most specific first)
# ---------------------------------------------------------------------------
_META_PAT = re.compile(
    r'^(what(\'?s)?\s+(your\s+)?(architecture|model|version|training|tech\s+stack)|'
    r'who\s+(are|r)\s+you|what\s+(are|r)\s+you|'
    r'(who|what)\s+(made|created|built|trained)\s+(you|this)|'
    r'tell\s+me\s+about\s+yourself|introduce\s+yourself|'
    r'are\s+you\s+(an?\s+)?(ai|bot|robot|machine|human|gpt|llm|claude|openai)|'
    r'which\s+(llm|model|ai)\s+(are\s+you|powers?\s+(you|this))|'
    r'what\s+(llm|model)\s+(do\s+you\s+use|are\s+you\s+based\s+on))',
    re.IGNORECASE,
)
_GREET_PAT      = re.compile(r'^(hi|hello|hey|hiya|howdy|helo|namaste|namaskar|salaam)[!.,?]*$', re.IGNORECASE)
_TIME_GREET_PAT = re.compile(r'^(good\s+)?(morning|afternoon|evening|night|day)[!.,?]*$', re.IGNORECASE)
_HOW_PAT        = re.compile(
    r'^(how\s+are\s+(you|u)|how\s+(r|are)\s+u\b|how\s+do\s+you\s+do|'
    r'what\'?s\s+up|sup\b|wassup\b|how\'?s\s+(it\s+going|everything|life|things))',
    re.IGNORECASE,
)
_THANKS_PAT = re.compile(r'^(thank(s|\s+you|u)|thx|ty|cheers|many\s+thanks)[!.,?]*$', re.IGNORECASE)
_BYE_PAT    = re.compile(r'^(bye|goodbye|good\s+bye|see\s+you|cya|later|take\s+care|ta\s*ta)[!.,?]*$', re.IGNORECASE)
_ACK_PAT    = re.compile(
    r'^(ok|okay|k|kk|fine|great|nice|cool|good|perfect|excellent|awesome|'
    r'sure|of\s+course|alright|right|noted|understood|got\s+it|'
    r'yes|no|yeah|yep|nope|nah|yup|lol|haha|ha|hehe|hmm+|uhh?|ah+|oh+)[!.,?]*$',
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Legal signal keyword scan
# ---------------------------------------------------------------------------
_LEGAL_KEYWORDS = re.compile(
    r'\b(section|article|ipc|crpc|cpc|fir|bail|petition|plea|plaint|writ|'
    r'court|judge|magistrate|tribunal|hearing|adjournment|verdict|'
    r'contract|agreement|clause|deed|affidavit|document|draft|'
    r'advocate|lawyer|attorney|counsel|litigant|plaintiff|defendant|'
    r'supreme\s+court|high\s+court|district\s+court|sessions\s+court|'
    r'property|rent|eviction|landlord|tenant|divorce|custody|alimony|'
    r'appeal|revision|review|stay|injunction|contempt|'
    r'limitation|cause\s+of\s+action|res\s+judicata|'
    r'rights?|remedies?|liability|damages?|compensation|'
    r'police|arrest|chargesheet|cognizable|bailable|'
    r'registration|stamp\s+duty|power\s+of\s+attorney|'
    r'gst|income\s+tax|tds|customs|act\b|law\b|legal|illegal|'
    r'lawful|unlawful|offence|offender)\b',
    re.IGNORECASE,
)

def has_legal_signal(text: str) -> bool:
    """
    Return True if *text* contains at least one legal domain keyword.
    When True the T0 intent gate can be skipped — go straight to T1/T2/T3.
    Cost: single compiled-regex scan, zero network calls.
    """
    return bool(_LEGAL_KEYWORDS.search(text))

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_chitchat(text: str) -> tuple[bool, str | None]:
    """
    Return (True, reply) when the input is clearly chitchat or gibberish.
    Return (False, None) for anything needing further processing.
    Zero LLM cost, zero network calls.
    """
    raw  = text.strip()
    norm = _normalise(raw)      # hiii->hi, hellooo->helloo  (for gibberish)
    dedup = _dedup(raw)         # hiii->hi, hellooo->helo    (for regex match)

    # Step 2 — regex against raw, normalised, and deduped forms. Checked BEFORE
    # the gibberish heuristic: these are precise, anchored patterns (many of the
    # ACK words — "yes", "no", "ok", "yep" — are <=3 chars and would otherwise be
    # misclassified as gibberish by the length check below).
    for candidate in (raw, norm, dedup):
        if _META_PAT.match(candidate):       return True, _REPLY_META
        if _BYE_PAT.match(candidate):        return True, _REPLY_FAREWELL
        if _THANKS_PAT.match(candidate):     return True, _REPLY_GRATITUDE
        if _GREET_PAT.match(candidate):      return True, _REPLY_GREETING
        if _TIME_GREET_PAT.match(candidate): return True, _REPLY_GREETING
        if _HOW_PAT.match(candidate):        return True, _REPLY_GREETING
        if _ACK_PAT.match(candidate):        return True, _REPLY_ACK

    # Step 3 — gibberish (only for text none of the precise patterns matched)
    if _is_gibberish(norm):
        return True, _REPLY_GIBBERISH

    return False, None


# Stub used when short-circuiting so _store_assistant_message gets a
# complete dict with tokens/latency at 0.
CHITCHAT_LLM_STUB: dict = {
    'text': '',
    'tier': 't0',
    'model': 'local',
    'provider': 'local',
    'latency_ms': 0,
    'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
}
