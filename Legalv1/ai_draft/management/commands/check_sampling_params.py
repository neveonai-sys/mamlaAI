"""
check_sampling_params — find out which model slugs reject an explicit
``temperature``, before we route real traffic at them.

Motivation: every drafting call passes ``temperature`` (0.3 for generation,
0.4 for section refine). Some models accept only default sampling settings and
answer a non-default ``temperature`` with a 400. If we move drafting onto such
a model, generation does not degrade — it stops working.

Rather than guess, probe. This sends a 5-token request to each candidate twice
(with and without ``temperature``) and reports what happened. Feed the result
into ``LLM_DEFAULT_SAMPLING_MODELS`` (a regex) so ``core.llm_client`` drops the
parameter for exactly those slugs and nothing else.

Usage:
    DJANGO_MODE=dev python manage.py check_sampling_params
    DJANGO_MODE=dev python manage.py check_sampling_params --models anthropic/claude-sonnet-5

Cost: a handful of tokens per model. Exits non-zero if any candidate cannot be
reached at all, so it can gate a model migration.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from core.llm_client import (
    APP_OPENAI_MODELS,
    APP_OPENROUTER_MODELS,
    PROVIDER_OPENROUTER,
    _get_openai_client,
    _get_openrouter_client,
)

# The slugs drafting could plausibly move to, plus whatever the app already
# points at for the heavier tiers.
_DEFAULT_CANDIDATES = (
    'anthropic/claude-sonnet-5',
    'anthropic/claude-haiku-4.5',
    'openai/gpt-4o-mini',
)

_PROBE = [{'role': 'user', 'content': 'Reply with the single word: ok'}]


class Command(BaseCommand):
    help = 'Probe which model slugs reject an explicit temperature.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--models', default='',
            help='Comma-separated slugs to probe. Default: the drafting migration candidates.',
        )
        parser.add_argument(
            '--provider', default=PROVIDER_OPENROUTER,
            choices=['openai', 'openrouter'],
            help='Which client to probe through. Default: openrouter.',
        )
        parser.add_argument(
            '--include-configured', action='store_true',
            help='Also probe every slug in the app model maps.',
        )

    def handle(self, *args, **opts):
        provider = opts['provider']
        client = (_get_openrouter_client() if provider == PROVIDER_OPENROUTER
                  else _get_openai_client())

        models = [m.strip() for m in opts['models'].split(',') if m.strip()]
        if not models:
            models = list(_DEFAULT_CANDIDATES)
        if opts['include_configured']:
            configured = (APP_OPENROUTER_MODELS if provider == PROVIDER_OPENROUTER
                          else APP_OPENAI_MODELS)
            models += [m for m in dict.fromkeys(configured.values()) if m not in models]

        self.stdout.write(f'Probing {len(models)} model(s) via {provider}\n')

        needs_default, unreachable = [], []

        for slug in models:
            with_temp = self._probe(client, slug, {'temperature': 0.3})
            without = self._probe(client, slug, {})

            if with_temp is True:
                verdict, style = 'accepts temperature', self.style.SUCCESS
            elif without is True:
                verdict, style = 'REJECTS temperature — needs defaults only', self.style.WARNING
                needs_default.append(slug)
            else:
                verdict, style = f'unreachable: {without or with_temp}', self.style.ERROR
                unreachable.append(slug)

            self.stdout.write(style(f'  {slug:<38} {verdict}'))
            if with_temp is not True and without is True:
                self.stdout.write(f'{"":<40} (error was: {with_temp})')

        self._advise(needs_default)

        if unreachable:
            self.stderr.write(self.style.ERROR(
                f'\nUnreachable slugs: {", ".join(unreachable)}'))
            raise SystemExit(1)

    def _probe(self, client, slug, extra) -> object:
        """Return True on success, else a short error string."""
        try:
            client.chat.completions.create(
                model=slug, messages=_PROBE, max_tokens=5, **extra,
            )
            return True
        except Exception as exc:
            return f'{type(exc).__name__}: {str(exc)[:160]}'

    def _advise(self, needs_default):
        self.stdout.write('')
        if not needs_default:
            self.stdout.write(self.style.SUCCESS(
                'All probed models accept an explicit temperature. '
                'Leave LLM_DEFAULT_SAMPLING_MODELS unset.'))
            return

        pattern = '|'.join(re_escape(s) for s in needs_default)
        self.stdout.write(self.style.WARNING(
            'Add this to your env file so core.llm_client drops the parameter '
            'for these slugs only:\n'))
        self.stdout.write(f'    LLM_DEFAULT_SAMPLING_MODELS={pattern}\n')
        self.stdout.write(
            'Note: brain:t3 and the premium chat path also pass a temperature, '
            'so a rejection here affects chat as well as drafting.')


def re_escape(s: str) -> str:
    import re
    return re.escape(s)
