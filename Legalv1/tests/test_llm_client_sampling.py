"""
Tests for `core.llm_client._sampling_params` and the finish_reason surface.

`chat_complete` is on the hot path for every model call in the product, so the
default behaviour must be provably unchanged: temperature is passed through
unless an operator explicitly opts a model out via LLM_DEFAULT_SAMPLING_MODELS.

Why the opt-out exists: some models accept only default sampling settings and
answer an explicit temperature with a 400. Every drafting call passes one, so
routing drafting at such a model would fail outright rather than degrade.
"""

from unittest.mock import MagicMock, patch

import pytest

from core import llm_client


@pytest.fixture
def fake_client(monkeypatch):
    """Captures the kwargs chat_complete sends to the provider."""
    client = MagicMock()
    response = MagicMock()
    response.choices = [MagicMock(finish_reason='stop')]
    response.choices[0].message.content = 'ok'
    response.usage = MagicMock(prompt_tokens=11, completion_tokens=7)
    response.model = 'test-model'
    client.chat.completions.create.return_value = response

    monkeypatch.setattr(llm_client, '_get_openrouter_client', lambda: client)
    monkeypatch.setattr(llm_client, '_get_openai_client', lambda: client)
    return client


def _sent(client) -> dict:
    return client.chat.completions.create.call_args.kwargs


MSGS = [{'role': 'user', 'content': 'hi'}]


# ---------------------------------------------------------------------------
# Default behaviour must be unchanged
# ---------------------------------------------------------------------------

def test_temperature_is_passed_through_by_default(fake_client, monkeypatch):
    monkeypatch.delenv('LLM_DEFAULT_SAMPLING_MODELS', raising=False)
    llm_client.chat_complete(MSGS, app_scenario='ai_draft:generate', temperature=0.3)
    assert _sent(fake_client)['temperature'] == 0.3


def test_empty_env_var_is_a_no_op(fake_client, monkeypatch):
    monkeypatch.setenv('LLM_DEFAULT_SAMPLING_MODELS', '')
    llm_client.chat_complete(MSGS, temperature=0.42)
    assert _sent(fake_client)['temperature'] == 0.42


def test_extra_kwargs_still_forwarded(fake_client, monkeypatch):
    monkeypatch.delenv('LLM_DEFAULT_SAMPLING_MODELS', raising=False)
    llm_client.chat_complete(MSGS, temperature=0.1, response_format={'type': 'json_object'})
    assert _sent(fake_client)['response_format'] == {'type': 'json_object'}


# ---------------------------------------------------------------------------
# Opt-in stripping
# ---------------------------------------------------------------------------

def test_matching_model_has_temperature_dropped(fake_client, monkeypatch):
    monkeypatch.setenv('LLM_DEFAULT_SAMPLING_MODELS', r'claude-sonnet-5')
    llm_client.chat_complete(
        MSGS, model='anthropic/claude-sonnet-5', provider='openrouter', temperature=0.3)
    assert 'temperature' not in _sent(fake_client)


def test_non_matching_model_is_unaffected(fake_client, monkeypatch):
    monkeypatch.setenv('LLM_DEFAULT_SAMPLING_MODELS', r'claude-sonnet-5')
    llm_client.chat_complete(
        MSGS, model='openai/gpt-4o-mini', provider='openrouter', temperature=0.3)
    assert _sent(fake_client)['temperature'] == 0.3


def test_top_p_and_top_k_are_dropped_together(fake_client, monkeypatch):
    monkeypatch.setenv('LLM_DEFAULT_SAMPLING_MODELS', r'strict-model')
    llm_client.chat_complete(
        MSGS, model='vendor/strict-model', temperature=0.3, top_p=0.9, top_k=40)
    sent = _sent(fake_client)
    assert 'temperature' not in sent and 'top_p' not in sent and 'top_k' not in sent


def test_invalid_regex_fails_open(fake_client, monkeypatch):
    """A malformed env var must not break every model call in the product."""
    monkeypatch.setenv('LLM_DEFAULT_SAMPLING_MODELS', '[unclosed')
    llm_client.chat_complete(MSGS, temperature=0.3)
    assert _sent(fake_client)['temperature'] == 0.3


# ---------------------------------------------------------------------------
# finish_reason — the authoritative truncation signal
# ---------------------------------------------------------------------------

def test_return_usage_now_surfaces_finish_reason(fake_client, monkeypatch):
    monkeypatch.delenv('LLM_DEFAULT_SAMPLING_MODELS', raising=False)
    text, usage = llm_client.chat_complete(MSGS, temperature=0.3, return_usage=True)
    assert text == 'ok'
    assert usage['finish_reason'] == 'stop'
    assert usage['prompt_tokens'] == 11 and usage['completion_tokens'] == 7


def test_length_finish_reason_reaches_the_caller(fake_client, monkeypatch):
    """This is what lets the validator call truncation authoritatively."""
    monkeypatch.delenv('LLM_DEFAULT_SAMPLING_MODELS', raising=False)
    fake_client.chat.completions.create.return_value.choices[0].finish_reason = 'length'
    _, usage = llm_client.chat_complete(MSGS, return_usage=True)
    assert usage['finish_reason'] == 'length'


def test_plain_call_still_returns_a_bare_string(fake_client, monkeypatch):
    """Existing callers pass no return_usage and expect str, not a tuple."""
    monkeypatch.delenv('LLM_DEFAULT_SAMPLING_MODELS', raising=False)
    assert llm_client.chat_complete(MSGS) == 'ok'
