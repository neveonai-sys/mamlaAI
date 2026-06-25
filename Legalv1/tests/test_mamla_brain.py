"""
tests/test_mamla_brain.py — Unit tests for Mamla Brain LLM routing.

Tests:
  - TIER_CONFIG values (max_tokens, history_limit, context_items)
  - call_llm dispatches to correct tier config
  - call_llm retry logic on retryable errors
  - call_llm fallback to alternate provider on exhausted retries
  - parse_json_response handles valid JSON, fenced JSON, and fallback
"""

import json
from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Tier config correctness
# ---------------------------------------------------------------------------

def test_tier_config_t1():
    from mamla_brain.llm_router import TIER_CONFIG
    cfg = TIER_CONFIG['t1']
    assert cfg['max_tokens'] == 256
    assert cfg['history_limit'] == 2
    assert cfg['context_items'] == 0
    assert cfg['temperature'] <= 0.2


def test_tier_config_t2():
    from mamla_brain.llm_router import TIER_CONFIG
    cfg = TIER_CONFIG['t2']
    assert cfg['max_tokens'] == 1024
    assert cfg['history_limit'] == 6
    assert cfg['context_items'] == 5


def test_tier_config_t3():
    from mamla_brain.llm_router import TIER_CONFIG
    cfg = TIER_CONFIG['t3']
    assert cfg['max_tokens'] == 2048
    assert cfg['history_limit'] == 6
    assert cfg['context_items'] == 8


def test_invalid_tier_raises():
    from mamla_brain.llm_router import call_llm
    with pytest.raises(ValueError, match='Unsupported Mamla Brain tier'):
        call_llm([], tier='t99')


# ---------------------------------------------------------------------------
# call_llm — successful path
# ---------------------------------------------------------------------------

def _mock_response(model='mock', text='Answer'):
    response = MagicMock()
    response.choices[0].message.content = text
    response.model = model
    response.usage.prompt_tokens = 10
    response.usage.completion_tokens = 5
    response.usage.total_tokens = 15
    return response


def test_call_llm_returns_expected_structure():
    from mamla_brain.llm_router import call_llm

    mock_resp = _mock_response(text='Test answer')
    with patch('mamla_brain.llm_router._get_client') as mock_client, \
         patch('mamla_brain.llm_router.get_circuit_breaker') as mock_cb:
        mock_cb.return_value = MagicMock()  # circuit always closed
        mock_client.return_value.chat.completions.create.return_value = mock_resp

        result = call_llm([{'role': 'user', 'content': 'Test'}], tier='t2')

    assert result['text'] == 'Test answer'
    assert result['tier'] == 't2'
    assert 'usage' in result
    assert 'latency_ms' in result
    assert isinstance(result['latency_ms'], (int, float))
    assert result['usage']['total_tokens'] == 15


# ---------------------------------------------------------------------------
# call_llm — retry logic
# ---------------------------------------------------------------------------

def test_call_llm_retries_on_rate_limit():
    from openai import RateLimitError
    from mamla_brain.llm_router import call_llm, _MAX_RETRIES

    mock_resp = _mock_response(text='Retry success')
    call_count = {'n': 0}

    def side_effect(*args, **kwargs):
        call_count['n'] += 1
        if call_count['n'] < _MAX_RETRIES:
            raise RateLimitError('rate limited', response=MagicMock(), body={})
        return mock_resp

    with patch('mamla_brain.llm_router._get_client') as mock_client, \
         patch('mamla_brain.llm_router.get_circuit_breaker') as mock_cb, \
         patch('mamla_brain.llm_router.time.sleep'):  # skip actual sleep
        mock_cb.return_value = MagicMock()
        mock_client.return_value.chat.completions.create.side_effect = side_effect

        result = call_llm([{'role': 'user', 'content': 'Q'}], tier='t2')

    assert result['text'] == 'Retry success'
    assert call_count['n'] == _MAX_RETRIES


def test_call_llm_falls_back_after_max_retries():
    """After primary provider exhausts retries, falls back to alternate provider."""
    from openai import APIConnectionError
    from mamla_brain.llm_router import call_llm

    mock_resp = _mock_response(text='Fallback answer')
    primary_calls  = {'n': 0}
    fallback_calls = {'n': 0}

    def primary_side_effect(*args, **kwargs):
        primary_calls['n'] += 1
        raise APIConnectionError(request=MagicMock())

    def fallback_side_effect(*args, **kwargs):
        fallback_calls['n'] += 1
        return mock_resp

    clients = {'openrouter': MagicMock(), 'openai': MagicMock()}
    clients['openrouter'].chat.completions.create.side_effect = primary_side_effect
    clients['openai'].chat.completions.create.side_effect = fallback_side_effect

    def get_client_stub(provider):
        return clients.get(provider, clients['openai'])

    with patch('mamla_brain.llm_router._get_client', side_effect=get_client_stub), \
         patch('mamla_brain.llm_router.get_circuit_breaker') as mock_cb, \
         patch('mamla_brain.llm_router.time.sleep'), \
         patch('django.conf.settings') as mock_settings:
        mock_settings.LLM_DEFAULT_PROVIDER = 'openrouter'
        mock_cb.return_value = MagicMock()

        result = call_llm([{'role': 'user', 'content': 'Q'}], tier='t2', provider='openrouter')

    assert result['text'] == 'Fallback answer'
    assert fallback_calls['n'] == 1


# ---------------------------------------------------------------------------
# parse_json_response
# ---------------------------------------------------------------------------

def test_parse_json_response_valid():
    from mamla_brain.llm_router import parse_json_response
    data = {'key': 'value', 'number': 42}
    assert parse_json_response(json.dumps(data)) == data


def test_parse_json_response_with_fences():
    from mamla_brain.llm_router import parse_json_response
    text = '```json\n{"key": "val"}\n```'
    result = parse_json_response(text, fallback={})
    # parse_json_response in llm_router extracts first {...}
    assert result == {'key': 'val'}


def test_parse_json_response_returns_fallback_on_invalid():
    from mamla_brain.llm_router import parse_json_response
    result = parse_json_response('not valid json at all !!!', fallback={'default': True})
    assert result == {'default': True}


def test_parse_json_response_empty_string_returns_fallback():
    from mamla_brain.llm_router import parse_json_response
    assert parse_json_response('', fallback=None) is None
