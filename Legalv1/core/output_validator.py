"""
core/output_validator.py — LLM output validation for Mamla.AI.

Validates and normalises LLM responses before they are stored or returned
to callers.  JSON-schema scenarios are validated against known schemas;
free-text scenarios are validated for basic sanity only.

Usage::

    from core.output_validator import validate_llm_output, LLMOutputValidationError

    try:
        validated = validate_llm_output(raw_text, scenario='brain:t3')
    except LLMOutputValidationError as exc:
        # handle / retry
        ...
"""

import json
import logging
import re

logger = logging.getLogger('django')

# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class LLMOutputValidationError(ValueError):
    """Raised when the LLM output cannot be validated against the expected schema."""


# ---------------------------------------------------------------------------
# JSON schemas per scenario
# Each schema defines required top-level keys and their expected types.
# ---------------------------------------------------------------------------

_SCHEMAS: dict = {
    # ISSUE_CLASSIFIER_SYSTEM output
    'brain:t1:classifier': {
        'required': ['summary', 'issues', 'keywords', 'recommended_search_query'],
        'types': {
            'summary': str,
            'issues': list,
            'keywords': list,
            'recommended_search_query': str,
        },
    },
    # CASE_COMPANION_SYSTEM output
    'brain:t3': {
        'required': ['summary', 'applicable_law', 'arguments_for', 'arguments_against',
                     'weaknesses', 'recommended_steps'],
        'types': {
            'summary': str,
            'applicable_law': list,
            'arguments_for': list,
            'arguments_against': list,
            'weaknesses': list,
            'recommended_steps': list,
        },
    },
}

# Scenarios that are expected to return free-text (no JSON schema)
_FREE_TEXT_SCENARIOS = {
    'brain:t1',   # query rewrite — plain text output
    'brain:t2',   # doc Q&A — prose response
    'talkdoc:rag',
    'talkdoc:general',
    'ai_draft:generate',
    'ai_draft:update_section',
    'ai_draft:generate_from_case',
    'ai_draft:generate_from_tpl',
    'utilities:describe_draft',
    'create_drafts:extract_fields',
    'create_drafts:fill_draft',
    'create_drafts:update_draft',
}

# Minimum non-whitespace characters for a valid free-text response
_MIN_FREE_TEXT_LENGTH = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> str:
    """Extract a JSON object string from text that may contain markdown fences."""
    stripped = text.strip()
    # strip ```json … ``` fences
    fenced = re.sub(r'^```(?:json)?\s*', '', stripped, flags=re.MULTILINE)
    fenced = re.sub(r'\s*```$', '', fenced, flags=re.MULTILINE)
    # find first balanced { … }
    start = fenced.find('{')
    end = fenced.rfind('}')
    if start != -1 and end != -1 and end > start:
        return fenced[start:end + 1]
    return stripped


def _validate_schema(data: dict, schema: dict, scenario: str) -> dict:
    """Validate *data* against *schema*; fill missing optional fields with defaults."""
    required = schema.get('required', [])
    types = schema.get('types', {})

    missing = [k for k in required if k not in data]
    if missing:
        raise LLMOutputValidationError(
            f'[OUTPUT_VALIDATOR] scenario={scenario} missing required keys: {missing}'
        )

    for key, expected_type in types.items():
        if key in data and not isinstance(data[key], expected_type):
            logger.warning(
                '[OUTPUT_VALIDATOR] scenario=%s key=%s expected=%s got=%s — coercing',
                scenario, key, expected_type.__name__, type(data[key]).__name__,
            )
            # Coerce scalars to list if list is expected
            if expected_type is list:
                data[key] = [data[key]] if data[key] else []
            # Coerce list/other to str if str is expected
            elif expected_type is str:
                data[key] = str(data[key])

    return data


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_llm_output(text: str, scenario: str) -> str:
    """
    Validate and return a (possibly corrected) LLM output string.

    For JSON scenarios: parse, validate schema, return re-serialised JSON string.
    For free-text scenarios: check minimum length, return cleaned string.

    Args:
        text:     Raw string returned by the LLM.
        scenario: The ``app_scenario`` or brain tier key used for the call.

    Returns:
        Validated (and possibly coerced) output string.

    Raises:
        LLMOutputValidationError: When validation fails and cannot be auto-corrected.
    """
    if not isinstance(text, str):
        text = str(text or '')

    cleaned = text.strip()

    # Free-text path
    if scenario in _FREE_TEXT_SCENARIOS or scenario not in _SCHEMAS:
        if len(cleaned.replace(' ', '').replace('\n', '')) < _MIN_FREE_TEXT_LENGTH:
            logger.warning(
                '[OUTPUT_VALIDATOR] scenario=%s free-text response too short (%d chars)',
                scenario, len(cleaned),
            )
            raise LLMOutputValidationError(
                f'LLM returned an empty or unusable response for scenario={scenario}.'
            )
        return cleaned

    # JSON-schema path
    json_str = _extract_json(cleaned)
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        logger.error(
            '[OUTPUT_VALIDATOR] scenario=%s JSON parse failed: %s snippet=%.120r',
            scenario, exc, cleaned[:120],
        )
        raise LLMOutputValidationError(
            f'LLM returned invalid JSON for scenario={scenario}.'
        ) from exc

    if not isinstance(data, dict):
        raise LLMOutputValidationError(
            f'Expected a JSON object for scenario={scenario}, got {type(data).__name__}.'
        )

    schema = _SCHEMAS[scenario]
    validated_data = _validate_schema(data, schema, scenario)
    return json.dumps(validated_data, ensure_ascii=False)


def parse_and_validate_json(text: str, scenario: str, fallback: dict | None = None) -> dict | None:
    """
    Convenience wrapper — parses and validates JSON output, returns a dict.

    Returns *fallback* if validation fails (does not raise).
    """
    try:
        validated_str = validate_llm_output(text, scenario)
        return json.loads(validated_str)
    except (LLMOutputValidationError, json.JSONDecodeError) as exc:
        logger.warning('[OUTPUT_VALIDATOR] parse_and_validate_json failed: %s', exc)
        return fallback
