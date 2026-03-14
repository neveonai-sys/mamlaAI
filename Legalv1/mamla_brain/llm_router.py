import json
import logging

from django.conf import settings

from core.llm_client import (
    PROVIDER_OPENAI,
    PROVIDER_OPENROUTER,
    get_model,
)

logger = logging.getLogger('django')

TIER_CONFIG = {
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


def call_llm(messages, tier='t2', provider=None, model=None, temperature=None, max_tokens=None, **kwargs):
    tier_key = tier.lower()
    if tier_key not in TIER_CONFIG:
        raise ValueError(f'Unsupported Mamla Brain tier: {tier}')

    tier_config = TIER_CONFIG[tier_key]
    resolved_provider = provider or getattr(settings, 'LLM_DEFAULT_PROVIDER', PROVIDER_OPENAI)
    resolved_model = model or get_model(tier_config['app_scenario'], resolved_provider)
    resolved_temperature = tier_config['temperature'] if temperature is None else temperature
    resolved_max_tokens = tier_config['max_tokens'] if max_tokens is None else max_tokens

    logger.info(
        '[BRAIN][LLM] provider=%s model=%s tier=%s max_tokens=%s',
        resolved_provider,
        resolved_model,
        tier_key,
        resolved_max_tokens,
    )

    response = _get_client(resolved_provider).chat.completions.create(
        model=resolved_model,
        messages=messages,
        temperature=resolved_temperature,
        max_tokens=resolved_max_tokens,
        **kwargs,
    )

    usage = getattr(response, 'usage', None)
    return {
        'text': response.choices[0].message.content,
        'model': getattr(response, 'model', resolved_model),
        'provider': resolved_provider,
        'tier': tier_key,
        'usage': {
            'prompt_tokens': getattr(usage, 'prompt_tokens', 0) if usage else 0,
            'completion_tokens': getattr(usage, 'completion_tokens', 0) if usage else 0,
            'total_tokens': getattr(usage, 'total_tokens', 0) if usage else 0,
        },
    }


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
