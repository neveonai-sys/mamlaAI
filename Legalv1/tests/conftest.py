"""
tests/conftest.py — Shared pytest fixtures for Mamla.AI tests.

Key fixtures:
  mock_call_llm     — patches mamla_brain.llm_router.call_llm with a deterministic stub.
  mock_chat_complete — patches core.llm_client.chat_complete with a deterministic stub.
  mock_db           — returns a MagicMock for MongoDB db handle.
  fake_supabase_user — a minimal supa_user dict for agent tests.
"""

import json
import os
from unittest.mock import MagicMock, patch

import django
import pytest

# ---------------------------------------------------------------------------
# Django setup — must happen before any Django import
# ---------------------------------------------------------------------------
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Legalv1.settings')


def pytest_configure(config):
    django.setup()


# ---------------------------------------------------------------------------
# LLM stubs
# ---------------------------------------------------------------------------

def _make_llm_response(tier='t2', text='Mocked LLM response for testing.', tokens=50):
    return {
        'text': text,
        'model': f'mock-model-{tier}',
        'provider': 'mock',
        'tier': tier,
        'latency_ms': 123,
        'usage': {
            'prompt_tokens': tokens,
            'completion_tokens': tokens // 2,
            'total_tokens': tokens + tokens // 2,
        },
    }


@pytest.fixture
def mock_call_llm():
    """
    Patches mamla_brain.llm_router.call_llm to return a deterministic response.
    Yields the mock so tests can inspect call_args.
    """
    with patch('mamla_brain.llm_router.call_llm') as mock:
        mock.side_effect = lambda messages, tier='t2', **kwargs: _make_llm_response(tier=tier)
        yield mock


@pytest.fixture
def mock_chat_complete():
    """Patches core.llm_client.chat_complete."""
    with patch('core.llm_client.chat_complete') as mock:
        mock.return_value = 'Mocked chat complete response.'
        yield mock


@pytest.fixture
def mock_draft_llm():
    """
    Patches chat_complete *as the drafting engine sees it*.

    `mock_chat_complete` above cannot reach drafting: creatupdateAIdrafts.py
    does `from core.llm_client import chat_complete` at import time, so it holds
    its own reference and patching the source module has no effect. Any drafting
    test must patch this name instead.

    Set `mock.return_value` to the JSON string the engine should parse.
    """
    with patch('ai_draft.routes.creatupdateAIdrafts.chat_complete') as mock:
        mock.return_value = json.dumps([
            {'section_name': 'RECITALS', 'content': 'That my Client is the owner.'},
        ])
        yield mock


# ---------------------------------------------------------------------------
# DB + user stubs
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    """A MagicMock that mimics the MongoDB db handle."""
    db = MagicMock()
    db['brain_messages'].insert_one.return_value = MagicMock(inserted_id='msg_001')
    db['brain_sessions'].find_one.return_value = None
    return db


@pytest.fixture
def fake_supabase_user():
    return {
        'user_id': 'test-user-uuid-1234',
        'email': 'test@mamla.ai',
        'role': 'authenticated',
    }


# ---------------------------------------------------------------------------
# Classifier JSON fixture (used in brain tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def classifier_json_text():
    return json.dumps({
        'summary': 'Test case summary',
        'issues': ['issue_a', 'issue_b'],
        'keywords': ['keyword1', 'keyword2'],
        'recommended_search_query': 'test retrieval query',
    })


# ---------------------------------------------------------------------------
# Case companion JSON fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def companion_json_text():
    return json.dumps({
        'summary': 'Test companion summary',
        'applicable_law': [{'act': 'IPC', 'section': '420', 'relevance': 'fraud'}],
        'arguments_for': ['arg1'],
        'arguments_against': ['arg2'],
        'weaknesses': ['weakness1'],
        'recommended_steps': ['step1'],
        'citations': [],
    })
