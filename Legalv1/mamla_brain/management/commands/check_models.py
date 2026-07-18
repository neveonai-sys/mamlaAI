"""
check_models — verify every OpenRouter model slug we default to actually exists
on the live OpenRouter catalog for this account.

Motivation: OpenRouter retires/renames slugs (e.g. the `:free` Llama variant that
started 404-ing the T0 intent gate). Because our model defaults are env-overridable
but hard to eyeball, this command turns silent runtime 404s into an explicit,
pre-deploy check.

Usage:
    DJANGO_MODE=dev python manage.py check_models

Exits non-zero if any configured slug is missing, so it can gate a deploy.
"""
import os

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from core.llm_client import APP_OPENROUTER_MODELS

OPENROUTER_MODELS_URL = 'https://openrouter.ai/api/v1/models'

# OpenRouter scenario keys we care about (skip OpenAI-only scenarios — those are
# validated against OpenAI, not OpenRouter).
_OPENROUTER_SCENARIOS = (
    'brain:t0', 'brain:t1', 'brain:t2', 'brain:t3',
    'talkdoc:rag', 'talkdoc:general',
)


def _configured_slugs():
    """Return {label: slug} for every OpenRouter slug we default to."""
    slugs = {key: APP_OPENROUTER_MODELS.get(key) for key in _OPENROUTER_SCENARIOS}
    # The intent gate resolves its own model independently of APP_OPENROUTER_MODELS.
    slugs['intent_gate'] = os.getenv('BRAIN_T0_MODEL', 'meta-llama/llama-3.2-1b-instruct')
    # The MamlaAI Chat premium override.
    slugs['premium'] = os.getenv('BRAIN_PREMIUM_MODEL', 'anthropic/claude-opus-4.8')
    return {label: slug for label, slug in slugs.items() if slug}


def _fetch_catalog():
    """Return (ids:set, pricing:dict) from the live OpenRouter catalog."""
    headers = {}
    if settings.OPENROUTER_API_KEY:
        headers['Authorization'] = f'Bearer {settings.OPENROUTER_API_KEY}'
    resp = requests.get(OPENROUTER_MODELS_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json().get('data', [])
    ids = set()
    pricing = {}
    for model in data:
        model_id = model.get('id')
        if not model_id:
            continue
        ids.add(model_id)
        price = model.get('pricing', {}) or {}
        pricing[model_id] = (price.get('prompt', '?'), price.get('completion', '?'))
    return ids, pricing


def _closest(slug, ids):
    """Best-effort closest-available id in the same namespace as `slug`."""
    namespace = slug.split('/', 1)[0] if '/' in slug else ''
    # Match on the model family after the namespace (e.g. "claude-haiku", "llama-3").
    stem = slug.rsplit('/', 1)[-1].split(':', 1)[0]
    family = '-'.join(stem.split('-')[:2])  # e.g. "claude-haiku", "llama-3.2"
    candidates = [
        i for i in ids
        if (not namespace or i.startswith(namespace + '/')) and family and family in i
    ]
    return sorted(candidates)[:5]


class Command(BaseCommand):
    help = 'Verify configured OpenRouter model slugs exist on the live catalog.'

    def handle(self, *args, **options):
        configured = _configured_slugs()
        try:
            ids, pricing = _fetch_catalog()
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'Could not fetch OpenRouter catalog: {exc}'))
            raise SystemExit(2)

        self.stdout.write(f'Checking {len(configured)} configured slugs against '
                          f'{len(ids)} live OpenRouter models\n')
        missing = []
        for label, slug in sorted(configured.items()):
            if slug in ids:
                p_in, p_out = pricing.get(slug, ('?', '?'))
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ {label:<14} {slug}   (in={p_in} out={p_out})'))
            else:
                missing.append((label, slug))
                self.stdout.write(self.style.ERROR(f'  ✗ {label:<14} {slug}  NOT FOUND'))
                for suggestion in _closest(slug, ids):
                    p_in, p_out = pricing.get(suggestion, ('?', '?'))
                    self.stdout.write(f'      → try {suggestion}  (in={p_in} out={p_out})')

        if missing:
            self.stdout.write('')
            self.stderr.write(self.style.ERROR(
                f'{len(missing)} slug(s) missing. Set the matching env var in '
                f'Legalv1/legalenv to a suggested id and re-run.'))
            raise SystemExit(1)
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('All configured OpenRouter slugs resolve. ✓'))
