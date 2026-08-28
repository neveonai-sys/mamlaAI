"""
eval_drafts — score the drafting engine against the golden set.

Motivation: law interns benchmarked our drafting at 3/10 against a competitor's
7/10. That verdict came from a human reading four drafts. This command turns it
into a number a build can compare, so every change to prompts, playbooks or
model choice is measured rather than argued about.

The golden set is seeded from the four benchmark prompts themselves, with the
reviewers' findings encoded as assertions (see `ai_draft/evals/fixtures/`).

Usage:
    # Baseline — run BEFORE changing anything. Costs money; hits the real engine.
    DJANGO_MODE=dev python manage.py eval_drafts --record --label baseline

    # After a change
    DJANGO_MODE=dev python manage.py eval_drafts --record --label phase1-playbooks

    # Re-score what was already recorded — free, no API calls, no Mongo.
    python manage.py eval_drafts --replay --label baseline

    # One case, with the LLM judge
    python manage.py eval_drafts --suite 001 --judge

Exits non-zero when a case has a hard failure (a sub-score of zero), so it can
gate a release. A penal-code citation in a civil draft is a hard failure.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from ai_draft.evals import runner
from ai_draft.evals.rubric import normalize_draft, score_deterministic
from ai_draft.evals.schema import load_suite

DEFAULT_OUT = Path(__file__).resolve().parents[3] / 'logs' / 'evals'


class Command(BaseCommand):
    help = 'Score the AI drafting engine against the golden set.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--suite', default='all',
            help="Comma-separated case ids or prefixes (e.g. '001,003'). Default: all.",
        )
        parser.add_argument(
            '--judge', action='store_true',
            help='Also run the LLM judge (one extra model call per case).',
        )
        parser.add_argument(
            '--record', action='store_true',
            help='Freeze each generation to evals/recorded/ for offline re-scoring.',
        )
        parser.add_argument(
            '--replay', action='store_true',
            help='Score evals/recorded/*.json instead of calling the engine. '
                 'Free, offline, deterministic — use after changing the rubric.',
        )
        parser.add_argument('--label', default='', help='Label for the report header.')
        parser.add_argument('--out', default='', help=f'Output dir. Default: {DEFAULT_OUT}')
        parser.add_argument(
            '--user-id', default=runner.EVAL_USER_ID,
            help='user_id the eval sessions are written under.',
        )

    def handle(self, *args, **opts):
        suite = opts['suite'].strip()
        ids = () if suite in ('all', '') else tuple(s.strip() for s in suite.split(',') if s.strip())

        if opts['record'] and opts['replay']:
            raise CommandError('--record and --replay are mutually exclusive.')

        label = opts['label'] or ('replay' if opts['replay'] else datetime.now().strftime('%Y%m%d-%H%M'))
        out_dir = Path(opts['out']) if opts['out'] else DEFAULT_OUT / f'{datetime.now():%Y%m%d-%H%M%S}-{label}'

        report = (self._replay(ids, label) if opts['replay']
                  else self._live(ids, label, opts))

        path = runner.write_report(report, out_dir)
        self._summarise(report, path)

        hard = [r.case_id for r in report.runs if r.score.hard_failures]
        if hard:
            self.stderr.write(self.style.ERROR(
                f'\nHard failures in: {", ".join(hard)}'))
            raise SystemExit(1)

    # -- modes ------------------------------------------------------------

    def _live(self, ids, label, opts):
        self.stdout.write(self.style.WARNING(
            'Running against the LIVE engine — this makes real model calls and '
            'writes eval sessions to Mongo.\n'))
        return runner.run_suite(
            ids,
            judge=opts['judge'],
            record=opts['record'],
            label=label,
            user_id=opts['user_id'],
            progress=lambda msg: self.stdout.write(f'  {msg}'),
        )

    def _replay(self, ids, label):
        """Re-score frozen generations. No API, no DB."""
        cases = load_suite(ids)
        if not cases:
            raise CommandError(f'no golden cases matched {ids!r}')

        runs = []
        for case in cases:
            path = runner.RECORDED_DIR / f'{case.id}.json'
            if not path.exists():
                self.stdout.write(self.style.WARNING(
                    f'  {case.id}: no recording — run with --record first. Skipped.'))
                continue
            blob = json.loads(path.read_text(encoding='utf-8'))
            draft = normalize_draft({
                'sections': blob.get('sections') or [],
                'assumptions': blob.get('assumptions') or [],
                'drafting_notes': blob.get('drafting_notes') or [],
            })
            draft.raw_error = blob.get('error') or ''
            score = score_deterministic(draft, case)
            runs.append(runner.CaseRun(
                case_id=case.id, score=score, latency_ms=0,
                sections=draft.sections, assumptions=draft.assumptions,
                drafting_notes=draft.drafting_notes,
                error=blob.get('error') or '',
            ))
            self.stdout.write(f'  {case.id} -> {score.overall:.1f}/10 (replay)')

        if not runs:
            raise CommandError('nothing to replay — run with --record first.')

        return runner.RunReport(
            label=f'{label} (replay)',
            started_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            runs=runs,
        )

    # -- output -----------------------------------------------------------

    def _summarise(self, report, path):
        self.stdout.write('')
        header = f'{"case":<34} {"overall":>8}  ' + '  '.join(f'{n:>12}' for n in runner._SUBS)
        self.stdout.write(self.style.MIGRATE_HEADING(header))
        self.stdout.write('-' * len(header))

        for r in report.runs:
            by = {s.name: s.score for s in r.score.subscores}
            cells = '  '.join(f'{by.get(n, 0):>12.1f}' for n in runner._SUBS)
            line = f'{r.case_id:<34} {r.score.overall:>8.1f}  {cells}'
            style = (self.style.ERROR if r.score.hard_failures
                     else self.style.SUCCESS if r.score.overall >= 7
                     else self.style.WARNING)
            self.stdout.write(style(line))
            if r.error:
                self.stdout.write(self.style.ERROR(f'{"":<34} engine error: {r.error}'))

        self.stdout.write('-' * len(header))
        means = '  '.join(f'{report.subscore_mean(n):>12.1f}' for n in runner._SUBS)
        self.stdout.write(f'{"MEAN":<34} {report.mean:>8.1f}  {means}')
        self.stdout.write(f'\nReport: {path}')
