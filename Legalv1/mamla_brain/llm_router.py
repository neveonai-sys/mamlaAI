import json
import logging
import time

from django.conf import settings

from core.circuit_breaker import CircuitOpenError, get_circuit_breaker
from core.llm_client import (
    PROVIDER_OPENAI,
    PROVIDER_OPENROUTER,
    get_model,
)

logger = logging.getLogger('django')

# ---------------------------------------------------------------------------
# Retry configuration
# ---------------------------------------------------------------------------
_MAX_RETRIES    = 3
_BACKOFF_BASE   = 1.0   # seconds; doubles each attempt: 1 → 2 → 4
_FALLBACK_MAP   = {
    PROVIDER_OPENROUTER: PROVIDER_OPENAI,
    PROVIDER_OPENAI:     PROVIDER_OPENROUTER,
}

# openai error classes that are safe to retry
def _is_retryable(exc) -> bool:
    try:
        from openai import RateLimitError, APIConnectionError, APITimeoutError
        return isinstance(exc, (RateLimitError, APIConnectionError, APITimeoutError))
    except ImportError:
        return False

TIER_CONFIG = {
    't0': {
        'app_scenario': 'brain:t0',
        'temperature': 0.0,
        'max_tokens': 20,
        'history_limit': 0,
        'context_items': 0,
    },
    't1': {
        'app_scenario': 'brain:t1',
        'temperature': 0.1,
        'max_tokens': 256,
        'history_limit': 2,
        'context_items': 0,
    },
    't2': {
        'app_scenario': 'brain:t2',
        'temperature': 0.2,
        'max_tokens': 1024,
        'history_limit': 6,
        'context_items': 5,
    },
    't3': {
        'app_scenario': 'brain:t3',
        'temperature': 0.2,
        'max_tokens': 2048,
        'history_limit': 6,
        'context_items': 8,
    },
}

_openai_instance = None
_openrouter_instance = None


def _get_openai_client():
    global _openai_instance
    if _openai_instance is None:
        from openai import OpenAI  # noqa: PLC0415

        _openai_instance = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_instance


def _get_openrouter_client():
    global _openrouter_instance
    if _openrouter_instance is None:
        from openai import OpenAI  # noqa: PLC0415

        _openrouter_instance = OpenAI(
            base_url='https://openrouter.ai/api/v1',
            api_key=settings.OPENROUTER_API_KEY,
        )
    return _openrouter_instance


def _get_client(provider):
    if provider == PROVIDER_OPENROUTER:
        return _get_openrouter_client()
    return _get_openai_client()


def _call_provider(provider, resolved_model, messages, temperature, max_tokens, tier_key, **kwargs):
    """
    Make a single LLM call to *provider* with circuit-breaker + latency tracking.
    Returns the standard llm_router response dict.
    Raises on any error so the caller can retry or fall back.
    """
    cb = get_circuit_breaker(provider)
    cb.before_call()

    t_start = time.perf_counter()
    try:
        response = _get_client(provider).chat.completions.create(
            model=resolved_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
    except Exception as exc:
        cb.on_failure(exc)
        raise
    finally:
        latency_ms = round((time.perf_counter() - t_start) * 1000)

    cb.on_success()
    usage = getattr(response, 'usage', None)
    result = {
        'text': response.choices[0].message.content,
        'model': getattr(response, 'model', resolved_model),
        'provider': provider,
        'tier': tier_key,
        'latency_ms': latency_ms,
        'usage': {
            'prompt_tokens':     getattr(usage, 'prompt_tokens',     0) if usage else 0,
            'completion_tokens': getattr(usage, 'completion_tokens', 0) if usage else 0,
            'total_tokens':      getattr(usage, 'total_tokens',      0) if usage else 0,
        },
    }
    logger.info(
        '[BRAIN][LLM] provider=%s model=%s tier=%s latency_ms=%d '
        'prompt_tokens=%d completion_tokens=%d',
        provider, resolved_model, tier_key, latency_ms,
        result['usage']['prompt_tokens'], result['usage']['completion_tokens'],
    )
    return result


def call_llm(messages, tier='t2', provider=None, model=None, temperature=None, max_tokens=None, **kwargs):
    """
    Call the LLM for the given Brain tier with automatic retry and cross-provider
    fallback.

    Retry policy:
      - Up to _MAX_RETRIES attempts with exponential back-off (1 s → 2 s → 4 s).
      - Retries on: RateLimitError, APIConnectionError, APITimeoutError.
      - Does not retry on: AuthenticationError, BadRequestError.
      - CircuitOpenError from the circuit breaker triggers immediate fallback.

    Fallback:
      - If the primary provider fails after all retries, one attempt is made on
        the alternate provider (openrouter ↔ openai).
    """
    tier_key = tier.lower()
    if tier_key not in TIER_CONFIG:
        raise ValueError(f'Unsupported Mamla Brain tier: {tier}')

    tier_config          = TIER_CONFIG[tier_key]
    primary_provider     = provider or getattr(settings, 'LLM_DEFAULT_PROVIDER', PROVIDER_OPENAI)
    resolved_model       = model or get_model(tier_config['app_scenario'], primary_provider)
    resolved_temperature = tier_config['temperature'] if temperature is None else temperature
    resolved_max_tokens  = tier_config['max_tokens']  if max_tokens  is None else max_tokens

    logger.info(
        '[BRAIN][LLM] provider=%s model=%s tier=%s max_tokens=%d',
        primary_provider, resolved_model, tier_key, resolved_max_tokens,
    )

    last_exc = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return _call_provider(
                primary_provider, resolved_model, messages,
                resolved_temperature, resolved_max_tokens, tier_key, **kwargs,
            )
        except CircuitOpenError as exc:
            logger.warning('[BRAIN][LLM] circuit open provider=%s — falling back', primary_provider)
            last_exc = exc
            break  # go straight to fallback
        except Exception as exc:
            last_exc = exc
            if not _is_retryable(exc):
                logger.error(
                    '[BRAIN][LLM] non-retryable error provider=%s attempt=%d: %s',
                    primary_provider, attempt, exc,
                )
                break  # don't waste retries on auth/bad-request errors
            backoff = _BACKOFF_BASE * (2 ** (attempt - 1))
            logger.warning(
                '[BRAIN][LLM] retryable error provider=%s attempt=%d/%d backoff=%.1fs: %s',
                primary_provider, attempt, _MAX_RETRIES, backoff, exc,
            )
            if attempt < _MAX_RETRIES:
                time.sleep(backoff)

    # --- Cross-provider fallback ---
    fallback_provider = _FALLBACK_MAP.get(primary_provider)
    if fallback_provider:
        fallback_model = get_model(tier_config['app_scenario'], fallback_provider)
        logger.warning(
            '[BRAIN][LLM] falling back provider=%s model=%s tier=%s',
            fallback_provider, fallback_model, tier_key,
        )
        try:
            return _call_provider(
                fallback_provider, fallback_model, messages,
                resolved_temperature, resolved_max_tokens, tier_key, **kwargs,
            )
        except Exception as fallback_exc:
            logger.error(
                '[BRAIN][LLM] fallback also failed provider=%s: %s',
                fallback_provider, fallback_exc,
            )
            raise fallback_exc from last_exc

    raise last_exc


def get_tier_config(tier='t2'):
    tier_key = tier.lower()
    if tier_key not in TIER_CONFIG:
        raise ValueError(f'Unsupported Mamla Brain tier: {tier}')
    return TIER_CONFIG[tier_key]


def parse_json_response(text, fallback=None):
    payload = (text or '').strip()
    if not payload:
        return fallback

    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        start = payload.find('{')
        end = payload.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(payload[start:end + 1])
            except json.JSONDecodeError:
                pass
    return fallback
