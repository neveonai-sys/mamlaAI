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
    "ai_draft:generate":            os.getenv("OPENROUTER_AI_DRAFT_MODEL",           "openai/gpt-4o-mini"),
    "ai_draft:update_section":      os.getenv("OPENROUTER_AI_DRAFT_MODEL",           "openai/gpt-4o-mini"),
    "ai_draft:generate_from_case":  os.getenv("OPENROUTER_AI_DRAFT_MODEL",           "openai/gpt-4o-mini"),
    "ai_draft:generate_from_tpl":   os.getenv("OPENROUTER_AI_DRAFT_MODEL",           "openai/gpt-4o-mini"),
    "talkdoc:rag":                  os.getenv("OPENROUTER_TALKDOC_RAG_MODEL",         "anthropic/claude-3-haiku"),
    "talkdoc:general":              os.getenv("OPENROUTER_TALKDOC_GENERAL_MODEL",     "anthropic/claude-3-haiku"),
    "utilities:describe_draft":     os.getenv("OPENROUTER_UTILS_MODEL",               "openai/gpt-4o-mini"),
    # create_drafts app
    "create_drafts:extract_fields": os.getenv("OPENROUTER_CREATE_DRAFTS_MODEL",       "openai/gpt-4o"),
    "create_drafts:fill_draft":     os.getenv("OPENROUTER_CREATE_DRAFTS_MODEL",       "openai/gpt-4o"),
    "create_drafts:update_draft":   os.getenv("OPENROUTER_CREATE_DRAFTS_MODEL",       "openai/gpt-4o"),
    # Mamla-Brain tiers (pre-wired; activated when mamla_brain app is deployed)
    "brain:t0":                     os.getenv("BRAIN_T0_MODEL",               "meta-llama/llama-3.2-1b-instruct:free"),  # free intent gate
    "brain:t1":                     os.getenv("BRAIN_T1_MODEL",                       "meta-llama/llama-3.1-8b-instruct"),
    "brain:t2":                     os.getenv("BRAIN_T2_MODEL",                       "anthropic/claude-3-haiku"),
    "brain:t3":                     os.getenv("BRAIN_T3_MODEL",                       "anthropic/claude-sonnet-4-5"),
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

    response = client.chat.completions.create(
        model=resolved_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )
    text = response.choices[0].message.content
    if return_usage:
        usage = getattr(response, 'usage', None)
        return text, {
            'prompt_tokens':     getattr(usage, 'prompt_tokens',     0) if usage else 0,
            'completion_tokens': getattr(usage, 'completion_tokens', 0) if usage else 0,
            'model':             getattr(response, 'model', resolved_model),
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
