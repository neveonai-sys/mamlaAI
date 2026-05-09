"""
core/intent_gate.py
===================
T0 intent gate for Mamla.AI.

Uses meta-llama/llama-3.2-1b-instruct:free on OpenRouter (free tier).
Max 20 output tokens -> {"intent": "legal"} or {"intent": "chitchat"}.

Only call this when ALL of the following are true:
  - check_chitchat() returned False   (not caught by regex/gibberish)
  - has_legal_signal() returned False (no obvious legal keyword present)
  - should_use_gate(text) is True     (text shorter than T0_MAX_LEN)

On any failure the gate returns "legal" so the normal pipeline runs —
fail open, never fail closed.
"""
import json
import logging
import os
import time

logger = logging.getLogger("django")

# Inputs >= this length are almost certainly substantive; skip the gate
T0_MAX_LEN = 120

_T0_SYSTEM = (
    "You are an intent classifier for an Indian legal AI assistant. "
    "Classify the user message into exactly one category:\n"
    "- legal: any legal question, court matter, statute, rights, document, case\n"
    "- chitchat: greeting, small talk, joke, unrelated question, gibberish\n\n"
    'Respond with ONLY valid JSON: {"intent": "legal"} or {"intent": "chitchat"}. '
    "No other text."
)

_client = None


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY", ""),
        )
    return _client


def classify_intent(text: str) -> str:
    """
    Return 'legal' or 'chitchat'.
    Fails open ('legal') on any error so the normal pipeline still runs.
    """
    t_start = time.perf_counter()
    try:
        model = os.getenv("BRAIN_T0_MODEL", "meta-llama/llama-3.2-1b-instruct:free")
        response = _get_client().chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _T0_SYSTEM},
                {"role": "user",   "content": text},
            ],
            temperature=0.0,
            max_tokens=20,
        )
        raw     = (response.choices[0].message.content or "").strip()
        payload = json.loads(raw)
        intent  = payload.get("intent", "legal").lower()
        latency_ms = round((time.perf_counter() - t_start) * 1000)
        logger.info(
            "[BRAIN][T0] intent=%s latency_ms=%d text_len=%d",
            intent, latency_ms, len(text),
        )
        return intent if intent in ("legal", "chitchat") else "legal"
    except Exception as exc:
        logger.warning("[BRAIN][T0] gate failed (fail-open): %s", exc)
        return "legal"


def should_use_gate(text: str) -> bool:
    """
    Return True when calling the T0 gate is worthwhile.
    Long / clearly substantive messages skip it to save latency.
    """
    return len(text.strip()) < T0_MAX_LEN
