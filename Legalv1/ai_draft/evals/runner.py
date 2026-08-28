"""
Suite runner.

Drives golden cases through the REAL drafting engine — `start_new_session`,
the same entry point `initiate_drafting_session` uses — so the number it
produces describes the product, not a laboratory replica of it. That is the
whole point of recording a baseline before Phase 1 touches anything.

Requires Django, Mongo and a live API key, which is why this is a management
command rather than a test. The free/offline tier replays `recorded/*.json`
captured here (see `tests/test_draft_evals.py`).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import rubric
from .rubric import CaseScore, normalize_draft, score_deterministic
from .schema import GoldenCase, load_suite

logger = logging.getLogger(__name__)

RECORDED_DIR = Path(__file__).parent / 'recorded'
EVAL_USER_ID = 'eval-harness'


@dataclass
class CaseRun:
    case_id: str
    score: CaseScore
    latency_ms: int
    sections: list = field(default_factory=list)
    assumptions: list = field(default_factory=list)
    drafting_notes: list = field(default_factory=list)
    session_id: str = ''
    error: str = ''


@dataclass
class RunReport:
    label: str
    started_at: str
    runs: list[CaseRun]

    @property
    def mean(self) -> float:
        scored = [r.score.overall for r in self.runs if not r.error]
        return sum(scored) / len(scored) if scored else 0.0

    def subscore_mean(self, name: str) -> float:
        vals = [s.score for r in self.runs for s in r.score.subscores if s.name == name]
        return sum(vals) / len(vals) if vals else 0.0


# ---------------------------------------------------------------------------
# Engine invocation
# ---------------------------------------------------------------------------

def _generate(case: GoldenCase, user_id: str) -> tuple[object, str, str]:
    """
    Run one case through the production engine.

    Returns (payload, session_id, error). Never raises — a case that blows up is
    data (it scores zero), not a reason to abandon the suite.

    `payload` carries the advisories alongside the sections. Reading only
    `mssg` here is what pinned the `compliance` dimension at its baseline even
    after the advisory schema shipped: the model was returning assumptions and
    drafting notes, the engine was storing them, and the scorer never saw them.
    """
    from ai_draft.routes.creatupdateAIdrafts import CreateupdatefetchAIdrafts

    engine = CreateupdatefetchAIdrafts(user_id)
    try:
        session_id = engine.start_new_session(
            case.prompt, {}, location={}, language=case.language,
        )
    except Exception as exc:
        logger.exception('[evals] %s: start_new_session raised', case.id)
        return None, '', f'start_new_session raised: {exc}'

    if not session_id:
        # The engine swallows generation failures and returns '' — one of the
        # silent-failure modes this programme exists to remove.
        return None, '', 'start_new_session returned empty session id'

    try:
        raw = engine.retrieve_sections_of_draft(str(session_id))
    except Exception as exc:
        logger.exception('[evals] %s: retrieve_sections_of_draft raised', case.id)
        return None, str(session_id), f'retrieve failed: {exc}'

    if not isinstance(raw, dict):
        return raw, str(session_id), ''

    error = ''
    if raw.get('status') == 'failed':
        error = 'generation failed (status=failed)'

    return (
        {
            'sections': raw.get('mssg') or [],
            'assumptions': raw.get('assumptions') or [],
            'drafting_notes': raw.get('drafting_notes') or [],
        },
        str(session_id),
        error,
    )


def run_case(case: GoldenCase, *, judge: bool = False,
             user_id: str = EVAL_USER_ID) -> CaseRun:
    t0 = time.monotonic()
    raw, session_id, error = _generate(case, user_id)
    latency = int((time.monotonic() - t0) * 1000)

    draft = normalize_draft(raw)
    if error and not draft.raw_error:
        draft.raw_error = error

    score = score_deterministic(draft, case)
    if judge and draft.sections:
        # Called through the module rather than a bound import so a test (or a
        # future caller) can patch `rubric.score_judge` and actually affect this
        # — the same import-binding trap that makes `mock_chat_complete` unable
        # to reach the drafting engine.
        score.judge = rubric.score_judge(draft, case)

    return CaseRun(
        case_id=case.id,
        score=score,
        latency_ms=latency,
        sections=draft.sections,
        assumptions=draft.assumptions,
        drafting_notes=draft.drafting_notes,
        session_id=session_id,
        error=error,
    )


def run_suite(ids: tuple[str, ...] = (), *, judge: bool = False, record: bool = False,
              label: str = '', user_id: str = EVAL_USER_ID,
              out_dir: Path | None = None, progress=None) -> RunReport:
    cases = load_suite(ids)
    if not cases:
        raise ValueError(f'no golden cases matched {ids!r}')

    report = RunReport(
        label=label or 'unlabelled',
        started_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        runs=[],
    )

    for i, case in enumerate(cases, 1):
        if progress:
            progress(f'[{i}/{len(cases)}] {case.id} ...')
        run = run_case(case, judge=judge, user_id=user_id)
        report.runs.append(run)
        if progress:
            status = run.error or f'{run.score.overall:.1f}/10'
            progress(f'[{i}/{len(cases)}] {case.id} -> {status} ({run.latency_ms} ms)')
        if record:
            _record(run)

    if out_dir:
        write_report(report, out_dir)
    return report


def _record(run: CaseRun) -> None:
    """
    Freeze a generation so CI can score it again for free.

    Recorded fixtures are how the pytest tier stays deterministic and offline —
    and how the Phase 0 baseline stays reproducible after the code changes.
    """
    RECORDED_DIR.mkdir(parents=True, exist_ok=True)
    (RECORDED_DIR / f'{run.case_id}.json').write_text(
        json.dumps({
            'case_id': run.case_id,
            'recorded_at': datetime.now().isoformat(timespec='seconds'),
            'sections': run.sections,
            'assumptions': run.assumptions,
            'drafting_notes': run.drafting_notes,
            'error': run.error,
        }, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

_SUBS = ('format', 'statute', 'completeness', 'compliance')


def render_markdown(report: RunReport) -> str:
    lines = [
        f'# Drafting eval — {report.label}',
        '',
        f'Run {report.started_at} · {len(report.runs)} cases · '
        f'**mean {report.mean:.1f}/10**',
        '',
        '| case | overall | ' + ' | '.join(_SUBS) + ' | hard failures |',
        '|---|---|' + '---|' * len(_SUBS) + '---|',
    ]
    for r in report.runs:
        by = {s.name: s.score for s in r.score.subscores}
        cells = ' | '.join(f'{by.get(n, 0):.1f}' for n in _SUBS)
        fails = ', '.join(r.score.hard_failures) or '—'
        lines.append(f'| {r.case_id} | **{r.score.overall:.1f}** | {cells} | {fails} |')

    lines += ['', f'| mean | **{report.mean:.1f}** | '
                  + ' | '.join(f'{report.subscore_mean(n):.1f}' for n in _SUBS)
                  + ' | |', '']

    lines.append('## Findings')
    for r in report.runs:
        lines.append(f'\n### {r.case_id} — {r.score.overall:.1f}/10')
        if r.error:
            lines.append(f'\n> ENGINE ERROR: {r.error}\n')
        for s in r.score.subscores:
            if s.findings:
                lines.append(f'\n**{s.name}** ({s.score:.1f}/10)')
                lines += [f'- {f}' for f in s.findings]
        if r.score.judge:
            j = r.score.judge
            lines.append(f'\n**judge** overall {j.get("overall", 0):.1f}/10 — '
                         f'{j.get("rationale", "")}')
    return '\n'.join(lines) + '\n'


def write_report(report: RunReport, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'results.json').write_text(
        json.dumps({
            'label': report.label,
            'started_at': report.started_at,
            'mean': round(report.mean, 2),
            'subscore_means': {n: round(report.subscore_mean(n), 2) for n in _SUBS},
            'runs': [
                {**r.score.as_dict(), 'latency_ms': r.latency_ms,
                 'session_id': r.session_id, 'engine_error': r.error}
                for r in report.runs
            ],
        }, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    md = out_dir / 'report.md'
    md.write_text(render_markdown(report), encoding='utf-8')
    return md
