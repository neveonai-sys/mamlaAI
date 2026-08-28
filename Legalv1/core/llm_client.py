"""
core/llm_client.py — Centralised LLM call routing for Mamla.AI.

Usage (from any Django app)::

    from core.llm_client import chat_complete

    answer = chat_complete(
        messages=[{"role": "system", "content": "..."}, {"role": "user", "content": "..."}],
        app_scenario="ai_draft:generate",
        temperature=0.3,
        max_tokens=4000,
    )

Provider selection priority
----------------------------
1. Explicit ``provider`` kwarg passed to ``chat_complete()``.
2. Django setting ``LLM_DEFAULT_PROVIDER``  (set in settings.py, default: ``'openai'``).

Model selection
---------------
* **OpenAI** path   → ``APP_OPENAI_MODELS[app_scenario]``    (env-var override supported)
* **OpenRouter** path → ``APP_OPENROUTER_MODELS[app_scenario]`` (env-var override supported)

App-scenario keys currently in use
------------------------------------
  ai_draft:generate          draft generation (Celery task)
  ai_draft:update_section    per-section AI edit (Celery task)
  talkdoc:rag                RAG document Q&A
  talkdoc:general            general legal Q&A (no docs)
  utilities:describe_draft   50-word draft description

Brain tier keys (wired ahead of the mamla_brain app landing)
--------------------------------------------------------------
  brain:t1   micro  — query rewriting, intent classification
  brain:t2   balanced — document Q&A, short answers
  brain:t3   strong  — case companion, multi-doc reasoning
"""

import os
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider constants
# ---------------------------------------------------------------------------
PROVIDER_OPENAI = "openai"
PROVIDER_OPENROUTER = "openrouter"

# ---------------------------------------------------------------------------
# Per-app model maps
# Each value is read from an env var first; falls back to a sensible default.
# For OpenRouter models use the full "<provider>/<model>" slug as shown on
# https://openrouter.ai/models
# ---------------------------------------------------------------------------

APP_OPENAI_MODELS: dict = {
    "ai_draft:generate":            os.getenv("OPENAI_AI_DRAFT_MODEL",        "gpt-4o-mini"),
    "ai_draft:update_section":      os.getenv("OPENAI_AI_DRAFT_MODEL",        "gpt-4o-mini"),
    "ai_draft:generate_from_case":  os.getenv("OPENAI_AI_DRAFT_MODEL",        "gpt-4o-mini"),
    "ai_draft:generate_from_tpl":   os.getenv("OPENAI_AI_DRAFT_MODEL",        "gpt-4o-mini"),
    "talkdoc:rag":                  os.getenv("RAG_CHAT_MODEL",               "gpt-4o"),
    "talkdoc:general":              os.getenv("RAG_CHAT_MODEL",               "gpt-4o"),
    "utilities:describe_draft":     os.getenv("OPENAI_UTILS_MODEL",           "gpt-4o-mini"),
    # create_drafts app — heavier model for field extraction / filling
    "create_drafts:extract_fields": os.getenv("OPENAI_CREATE_DRAFTS_MODEL",   "gpt-4o"),
    "create_drafts:fill_draft":     os.getenv("OPENAI_CREATE_DRAFTS_MODEL",   "gpt-4o"),
    "create_drafts:update_draft":   os.getenv("OPENAI_CREATE_DRAFTS_MODEL",   "gpt-4o"),
    # Brain tiers — all stay on stronger models; kept as OpenAI slugs
    "brain:t0":                     os.getenv("BRAIN_T0_OPENAI_MODEL",        "gpt-4o-mini"),   # intent gate fallback
    "brain:t1":                     os.getenv("BRAIN_T1_OPENAI_MODEL",        "gpt-4o-mini"),
    "brain:t2":                     os.getenv("BRAIN_T2_OPENAI_MODEL",        "gpt-4o-mini"),
    "brain:t3":                     os.getenv("BRAIN_T3_OPENAI_MODEL",        "gpt-4o"),
}

APP_OPENROUTER_MODELS: dict = {
    # Drafting is the product's core differentiator and was running on the
    # weakest model in the stack while chat got Sonnet. Benchmarked at 3/10 by
    # law interns against competitors on gpt-4o-mini; see ai_draft/evals/.
    # Reversible in one env var if cost or latency proves unacceptable.
    "ai_draft:generate":            os.getenv("OPENROUTER_AI_DRAFT_MODEL",           "anthropic/claude-sonnet-5"),
    "ai_draft:update_section":      os.getenv("OPENROUTER_AI_DRAFT_MODEL",           "anthropic/claude-sonnet-5"),
    "ai_draft:generate_from_case":  os.getenv("OPENROUTER_AI_DRAFT_MODEL",           "anthropic/claude-sonnet-5"),
    "ai_draft:generate_from_tpl":   os.getenv("OPENROUTER_AI_DRAFT_MODEL",           "anthropic/claude-sonnet-5"),
    "talkdoc:rag":                  os.getenv("OPENROUTER_TALKDOC_RAG_MODEL",         "anthropic/claude-haiku-4.5"),
    "talkdoc:general":              os.getenv("OPENROUTER_TALKDOC_GENERAL_MODEL",     "anthropic/claude-haiku-4.5"),
    "utilities:describe_draft":     os.getenv("OPENROUTER_UTILS_MODEL",               "openai/gpt-4o-mini"),
    # create_drafts app
    "create_drafts:extract_fields": os.getenv("OPENROUTER_CREATE_DRAFTS_MODEL",       "openai/gpt-4o"),
    "create_drafts:fill_draft":     os.getenv("OPENROUTER_CREATE_DRAFTS_MODEL",       "openai/gpt-4o"),
    "create_drafts:update_draft":   os.getenv("OPENROUTER_CREATE_DRAFTS_MODEL",       "openai/gpt-4o"),
    # Mamla-Brain tiers (pre-wired; activated when mamla_brain app is deployed)
    "brain:t0":                     os.getenv("BRAIN_T0_MODEL",               "meta-llama/llama-3.2-1b-instruct"),  # cheap intent gate
    "brain:t1":                     os.getenv("BRAIN_T1_MODEL",                       "meta-llama/llama-3.1-8b-instruct"),
    "brain:t2":                     os.getenv("BRAIN_T2_MODEL",                       "anthropic/claude-haiku-4.5"),
    "brain:t3":                     os.getenv("BRAIN_T3_MODEL",                       "anthropic/claude-sonnet-5"),
}

_DEFAULT_MODEL_OPENAI     = os.getenv("OPENAI_DEFAULT_MODEL",     "gpt-4o-mini")
_DEFAULT_MODEL_OPENROUTER = os.getenv("OPENROUTER_DEFAULT_MODEL", "openai/gpt-4o-mini")

# ---------------------------------------------------------------------------
# Client singletons (lazy — instantiated on first use)
# ---------------------------------------------------------------------------
_openai_instance     = None
_openrouter_instance = None


def _get_openai_client():
    global _openai_instance
    if _openai_instance is None:
        from openai import OpenAI  # noqa: PLC0415
        _openai_instance = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _openai_instance


def _get_openrouter_client():
    global _openrouter_instance
    if _openrouter_instance is None:
        from openai import OpenAI  # noqa: PLC0415
        _openrouter_instance = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
    return _openrouter_instance


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def _sampling_params(resolved_model: str, temperature: float, kwargs: dict) -> dict:
    """Return the sampling kwargs to send for *resolved_model*.

    Some models only accept default sampling settings and reject an explicit
    ``temperature`` / ``top_p`` / ``top_k`` with a 400. Every drafting call
    currently passes ``temperature``, so if we route drafting at such a model
    the request fails outright rather than degrading.

    This is provider- and version-dependent, so it is **opt-in** rather than
    guessed: set ``LLM_DEFAULT_SAMPLING_MODELS`` to a regex matching the model
    slugs that must receive defaults only. Empty (the default) preserves
    existing behaviour exactly.

    Use ``manage.py check_sampling_params`` to find out which slugs need it.
    """
    pattern = os.getenv("LLM_DEFAULT_SAMPLING_MODELS", "").strip()
    if not pattern:
        return {"temperature": temperature}

    try:
        if not re.search(pattern, resolved_model or "", re.IGNORECASE):
            return {"temperature": temperature}
    except re.error:
        logger.warning(
            "[LLM] LLM_DEFAULT_SAMPLING_MODELS is not a valid regex (%r); "
            "passing temperature through", pattern,
        )
        return {"temperature": temperature}

    dropped = [k for k in ("top_p", "top_k") if k in kwargs]
    for k in dropped:
        kwargs.pop(k)
    logger.info(
        "[LLM] model=%s requires default sampling — dropped temperature%s",
        resolved_model, f" and {', '.join(dropped)}" if dropped else "",
    )
    return {}


#: Scenarios whose token budget should go to visible output rather than to
#: model deliberation. Drafting is a format-and-knowledge task: the shape of a
#: partnership deed is not something to reason toward, it is something to know.
_REASONING_BUDGETED_SCENARIOS = frozenset({
    "ai_draft:generate",
    "ai_draft:generate_from_case",
    "ai_draft:generate_from_tpl",
    "ai_draft:update_section",
})


def _reasoning_params(app_scenario: Optional[str], provider: str, kwargs: dict) -> dict:
    """
    Cap reasoning tokens for long-form drafting on OpenRouter.

    On a reasoning model, ``max_tokens`` bounds thinking PLUS visible output. A
    16-clause partnership deed measured here spent roughly 12k of a 16k budget
    deliberating and was then truncated mid-clause — the model returned
    ``finish_reason='length'`` with ``content=None``, which the engine could only
    see as a total failure. That is defect #3a arriving by a new route.

    Off by default so nothing changes for other providers or scenarios. Set
    ``LLM_DRAFT_REASONING_TOKENS=0`` to disable reasoning entirely, or a positive
    integer to cap it; unset leaves provider defaults alone.
    """
    if provider != PROVIDER_OPENROUTER or app_scenario not in _REASONING_BUDGETED_SCENARIOS:
        return {}
    if "extra_body" in kwargs or "reasoning" in kwargs:
        return {}                      # an explicit caller wins

    raw = os.getenv("LLM_DRAFT_REASONING_TOKENS", "").strip()
    if not raw:
        return {}
    try:
        budget = int(raw)
    except ValueError:
        logger.warning("[LLM] LLM_DRAFT_REASONING_TOKENS is not an integer (%r); ignoring", raw)
        return {}

    reasoning = {"enabled": False} if budget <= 0 else {"max_tokens": budget}
    logger.info("[LLM] scenario=%s reasoning=%s", app_scenario, reasoning)
    return {"extra_body": {"reasoning": reasoning}}


def get_model(app_scenario: Optional[str], provider: str) -> str:
    """Return the model name for *app_scenario* on the given *provider*.

    Falls back to the provider-level default when the scenario is unknown.
    """
    if provider == PROVIDER_OPENROUTER:
        return (
            APP_OPENROUTER_MODELS.get(app_scenario, _DEFAULT_MODEL_OPENROUTER)
            if app_scenario
            else _DEFAULT_MODEL_OPENROUTER
        )
    return (
        APP_OPENAI_MODELS.get(app_scenario, _DEFAULT_MODEL_OPENAI)
        if app_scenario
        else _DEFAULT_MODEL_OPENAI
    )


def chat_complete(
    messages: list,
    app_scenario: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    return_usage: bool = False,
    **kwargs,
):
    """Call the LLM and return the assistant's text content.

    Args:
        messages:      OpenAI-format messages list (role/content dicts).
        app_scenario:  Key like ``'talkdoc:rag'`` or ``'ai_draft:generate'``.
                       Drives model selection when *model* is not set.
        provider:      ``'openai'`` or ``'openrouter'``.  When omitted,
                       falls back to ``settings.LLM_DEFAULT_PROVIDER``
                       (defaults to ``'openai'`` if the setting is absent).
        model:         Explicit model override; skips ``APP_*_MODELS`` lookup.
        temperature:   Sampling temperature.  Use ≤ 0.3 for JSON output.
        max_tokens:    Maximum output tokens.
        **kwargs:      Any extra keyword arguments forwarded verbatim to
                       ``chat.completions.create()``.

    Returns:
        str: The assistant message content (first choice).

    Raises:
        Exception: Propagates any OpenAI / OpenRouter API error so callers
                   can handle retries (e.g. Celery task retry logic).
    """
    from django.conf import settings

    resolved_provider = provider or getattr(settings, "LLM_DEFAULT_PROVIDER", PROVIDER_OPENAI)
    resolved_model    = model or get_model(app_scenario, resolved_provider)

    client = (
        _get_openrouter_client()
        if resolved_provider == PROVIDER_OPENROUTER
        else _get_openai_client()
    )

    logger.info(
        "[LLM] provider=%s model=%s scenario=%s max_tokens=%d",
        resolved_provider, resolved_model, app_scenario, max_tokens,
    )

    sampling = _sampling_params(resolved_model, temperature, kwargs)
    reasoning = _reasoning_params(app_scenario, resolved_provider, kwargs)

    response = client.chat.completions.create(
        model=resolved_model,
        messages=messages,
        max_tokens=max_tokens,
        **sampling,
        **reasoning,
        **kwargs,
    )
    choice = response.choices[0]
    text = choice.message.content
    if return_usage:
        usage = getattr(response, 'usage', None)
        return text, {
            'prompt_tokens':     getattr(usage, 'prompt_tokens',     0) if usage else 0,
            'completion_tokens': getattr(usage, 'completion_tokens', 0) if usage else 0,
            'model':             getattr(response, 'model', resolved_model),
            # Surfaced so callers can distinguish "the model finished" from
            # "we hit max_tokens and the document stops mid-clause". The
            # drafting validator treats 'length' as authoritative truncation.
            'finish_reason':     getattr(choice, 'finish_reason', None),
        }
    return text


def vision_complete(
    prompt: str,
    image_data_url: str,
    app_scenario: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 2048,
    **kwargs,
) -> str:
    """Call the multimodal LLM path with a single inline image data URL.

    The model resolution logic is shared with ``chat_complete()`` so existing
    OpenAI/OpenRouter configuration continues to drive provider and model choice.
    """
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ],
        }
    ]
    return chat_complete(
        messages=messages,
        app_scenario=app_scenario,
        provider=provider,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )
