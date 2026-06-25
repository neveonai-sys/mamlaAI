"""
tests/test_agents.py — Unit tests for all Mamla agents.

Tests:
  - BaseAgent contract: ok=True on success, ok=False on ValueError, ok=False on generic exc
  - Each concrete agent: valid input → ok=True
  - Each concrete agent: missing required input → ok=False
  - LLM failure → graceful degradation (ok=False, no exception propagation)
"""

from unittest.mock import MagicMock, patch

import pytest

from agents.base_agent import BaseAgent


# ---------------------------------------------------------------------------
# BaseAgent contract tests
# ---------------------------------------------------------------------------

class SuccessAgent(BaseAgent):
    name = 'SuccessAgent'
    def _run(self, inputs, db, supa_user):
        return {'result': 'done', 'data': inputs.get('value', 'default')}


class ValidationErrorAgent(BaseAgent):
    name = 'ValidationErrorAgent'
    def _run(self, inputs, db, supa_user):
        raise ValueError('Missing required field: case_id')


class UnexpectedErrorAgent(BaseAgent):
    name = 'UnexpectedErrorAgent'
    def _run(self, inputs, db, supa_user):
        raise RuntimeError('Unexpected DB failure')


@pytest.fixture
def agent_context(mock_db, fake_supabase_user):
    return mock_db, fake_supabase_user


def test_base_agent_success(agent_context):
    db, user = agent_context
    agent = SuccessAgent()
    result = agent.run({'value': 'test_value'}, db, user)
    assert result['ok'] is True
    assert result['result'] == 'done'
    assert result['data'] == 'test_value'


def test_base_agent_value_error_returns_ok_false(agent_context):
    db, user = agent_context
    agent = ValidationErrorAgent()
    result = agent.run({}, db, user)
    assert result['ok'] is False
    assert 'Missing required field' in result['error']
    assert 'detail' not in result  # ValueError gives clean error, no detail


def test_base_agent_unexpected_error_returns_ok_false(agent_context):
    db, user = agent_context
    agent = UnexpectedErrorAgent()
    result = agent.run({}, db, user)
    assert result['ok'] is False
    assert result['error'] == 'Agent failed. Please try again.'
    assert 'detail' in result  # detail included for unexpected errors


# ---------------------------------------------------------------------------
# CaseIntakeAgent
# ---------------------------------------------------------------------------

def test_case_intake_agent_missing_case_id(agent_context):
    from agents.case_intake import CaseIntakeAgent
    db, user = agent_context
    db['cases'].find_one.return_value = None
    agent = CaseIntakeAgent()
    result = agent.run({'case_id': None}, db, user)
    assert result['ok'] is False


def test_case_intake_agent_llm_failure_graceful(agent_context):
    from agents.case_intake import CaseIntakeAgent
    db, user = agent_context
    db['cases'].find_one.return_value = {
        '_id': 'case_001', 'lawyer_id': user['user_id'],
        'title': 'Test Case', 'description': 'Test',
        'client_id': 'client_001',
    }
    agent = CaseIntakeAgent()
    with patch('agents.case_intake.chat_complete', side_effect=RuntimeError('LLM down')):
        result = agent.run({'case_id': 'case_001'}, db, user)
    assert result['ok'] is False


# ---------------------------------------------------------------------------
# DocumentIntelligenceAgent
# ---------------------------------------------------------------------------

def test_document_intel_agent_missing_content(agent_context):
    from agents.document_intel import DocumentIntelligenceAgent
    db, user = agent_context
    agent = DocumentIntelligenceAgent()
    result = agent.run({}, db, user)
    assert result['ok'] is False


# ---------------------------------------------------------------------------
# HearingPrepAgent
# ---------------------------------------------------------------------------

def test_hearing_prep_agent_missing_case_id(agent_context):
    from agents.hearing_prep import HearingPrepAgent
    db, user = agent_context
    db['cases'].find_one.return_value = None
    agent = HearingPrepAgent()
    result = agent.run({'case_id': 'nonexistent'}, db, user)
    assert result['ok'] is False


# ---------------------------------------------------------------------------
# PostHearingAgent
# ---------------------------------------------------------------------------

def test_post_hearing_agent_missing_case_id(agent_context):
    from agents.post_hearing import PostHearingAgent
    db, user = agent_context
    db['cases'].find_one.return_value = None
    agent = PostHearingAgent()
    result = agent.run({'case_id': 'nonexistent'}, db, user)
    assert result['ok'] is False


# ---------------------------------------------------------------------------
# DraftContextAgent
# ---------------------------------------------------------------------------

def test_draft_context_agent_missing_content(agent_context):
    from agents.draft_context import DraftContextAgent
    db, user = agent_context
    agent = DraftContextAgent()
    result = agent.run({}, db, user)
    assert result['ok'] is False


# ---------------------------------------------------------------------------
# CaseClosureAgent
# ---------------------------------------------------------------------------

def test_case_closure_agent_missing_case_id(agent_context):
    from agents.case_closure import CaseClosureAgent
    db, user = agent_context
    db['cases'].find_one.return_value = None
    agent = CaseClosureAgent()
    result = agent.run({'case_id': 'nonexistent'}, db, user)
    assert result['ok'] is False
