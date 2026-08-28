"""
Runner plumbing tests — engine mocked, no Mongo, no API calls.

The `--record` baseline run costs real money and writes real sessions. If the
runner is broken, that is discovered expensively. These tests exercise the wiring
(engine -> normalize -> score -> report -> record) for free.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from ai_draft.evals import runner
from ai_draft.evals.benchmark_drafts import MAMLA_RENT_NOTICE


@pytest.fixture
def fake_engine():
    """Stands in for CreateupdatefetchAIdrafts at the point runner imports it."""
    engine = MagicMock()
    engine.start_new_session.return_value = 'sess-abc123'
    engine.retrieve_sections_of_draft.return_value = {'mssg': MAMLA_RENT_NOTICE}
    with patch('ai_draft.routes.creatupdateAIdrafts.CreateupdatefetchAIdrafts',
               return_value=engine):
        yield engine


def _case():
    from ai_draft.evals.schema import load_suite
    return {c.id: c for c in load_suite()}['001_rent_arrears_notice']


def test_run_case_scores_engine_output(fake_engine):
    run = runner.run_case(_case())
    assert run.session_id == 'sess-abc123'
    assert not run.error
    assert len(run.sections) == len(MAMLA_RENT_NOTICE)
    assert 'statute' in run.score.hard_failures     # the BNSS citation


def test_run_case_passes_the_prompt_to_the_engine(fake_engine):
    case = _case()
    runner.run_case(case)
    args, kwargs = fake_engine.start_new_session.call_args
    assert args[0] == case.prompt
    assert kwargs.get('language') == case.language


def test_empty_session_id_is_recorded_as_an_error(fake_engine):
    """The engine returns '' when generation fails — a silent failure today."""
    fake_engine.start_new_session.return_value = ''
    run = runner.run_case(_case())
    assert 'empty session id' in run.error
    assert run.score.overall == 0.0


def test_engine_exception_does_not_abort_the_suite(fake_engine):
    fake_engine.start_new_session.side_effect = RuntimeError('mongo down')
    run = runner.run_case(_case())
    assert 'mongo down' in run.error
    assert run.score.overall == 0.0


def test_retrieve_returning_bare_list_is_accepted(fake_engine):
    """retrieve_sections_of_draft returns {'mssg': [...]}, but tolerate a list."""
    fake_engine.retrieve_sections_of_draft.return_value = MAMLA_RENT_NOTICE
    run = runner.run_case(_case())
    assert len(run.sections) == len(MAMLA_RENT_NOTICE)


def test_judge_is_invoked_through_the_module_so_it_stays_patchable(fake_engine):
    """
    Guards the import-binding trap: `runner` must call `rubric.score_judge`,
    not a name bound at import, or patching it silently does nothing.
    """
    with patch('ai_draft.evals.rubric.score_judge', return_value={'overall': 6.0}) as mj:
        run = runner.run_case(_case(), judge=True)
    assert mj.called
    assert run.score.judge == {'overall': 6.0}


def test_judge_outage_degrades_rather_than_crashing(fake_engine):
    """An API failure in the judge must never take down a deterministic run."""
    with patch('core.llm_client.chat_complete', side_effect=RuntimeError('api down')):
        run = runner.run_case(_case(), judge=True)
    assert run.score.judge is None
    assert run.score.hard_failures        # deterministic scoring still happened


def test_judge_is_skipped_when_no_sections_came_back(fake_engine):
    """No point paying for a judge call on an empty draft."""
    fake_engine.retrieve_sections_of_draft.return_value = {'mssg': []}
    with patch('ai_draft.evals.rubric.score_judge') as mj:
        run = runner.run_case(_case(), judge=True)
    assert not mj.called
    assert run.score.overall == 0.0


def test_run_suite_writes_report_and_recordings(fake_engine, tmp_path):
    with patch.object(runner, 'RECORDED_DIR', tmp_path / 'recorded'):
        report = runner.run_suite(
            ('001',), record=True, label='wiring-test', out_dir=tmp_path / 'out',
        )
        recorded = tmp_path / 'recorded' / '001_rent_arrears_notice.json'
        assert recorded.exists()
        blob = json.loads(recorded.read_text())
        assert blob['case_id'] == '001_rent_arrears_notice'
        assert len(blob['sections']) == len(MAMLA_RENT_NOTICE)

    assert len(report.runs) == 1
    assert (tmp_path / 'out' / 'results.json').exists()

    md = (tmp_path / 'out' / 'report.md').read_text()
    assert 'Drafting eval — wiring-test' in md
    assert '001_rent_arrears_notice' in md
    assert 'BNSS' in md            # the finding surfaces in the report


def test_report_mean_ignores_errored_runs():
    from ai_draft.evals.rubric import CaseScore, SubScore
    ok = runner.CaseRun('a', CaseScore('a', 8.0, [SubScore('format', 8.0, 1.0)], 3), 10)
    bad = runner.CaseRun('b', CaseScore('b', 0.0, [], 0, error='boom'), 10, error='boom')
    report = runner.RunReport('x', 'now', [ok, bad])
    assert report.mean == 8.0


def test_unknown_suite_id_raises():
    with pytest.raises(ValueError, match='no golden cases matched'):
        runner.run_suite(('nonexistent-case',))
