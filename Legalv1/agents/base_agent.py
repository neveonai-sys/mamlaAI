"""
agents/base_agent.py — BaseAgent class for all Mamla agents.

Every agent inherits from BaseAgent and implements run(inputs, db, supa_user).
BaseAgent handles:
  - Structured logging with agent identity tag
  - Exception wrapping → always returns {"ok": bool, ...}
  - Shared helpers for DB access and user context
  - Optional JSON output validation via OUTPUT_SCHEMA
"""
import logging
import traceback

logger = logging.getLogger('django')


class BaseAgent:
    """
    Base class for all Mamla agents.

    Concrete agents override _run(inputs, db, supa_user) → dict.
    The public run() method wraps _run() with exception handling.

    Optional class-level attribute:
      OUTPUT_SCHEMA: dict  — if defined, LLM JSON output will be validated
                            against this schema via output_validator.  Keys:
                            'required' (list[str]) and 'types' (dict[str, type]).
    """

    name: str = 'BaseAgent'
    OUTPUT_SCHEMA: dict | None = None

    def run(self, inputs: dict, db, supa_user: dict) -> dict:
        """
        Execute the agent safely.
        Returns {"ok": True, ...result...} on success.
        Returns {"ok": False, "error": "...", "detail": "..."} on failure.
        """
        user_id = supa_user.get('user_id', 'unknown')
        logger.info('[AGENT:%s] start user=%s inputs=%s', self.name, user_id,
                    {k: v for k, v in inputs.items() if k != 'content'})
        try:
            result = self._run(inputs, db, supa_user)
            logger.info('[AGENT:%s] done user=%s', self.name, user_id)
            return {"ok": True, **result}
        except ValueError as exc:
            logger.warning('[AGENT:%s] validation error: %s', self.name, exc)
            return {"ok": False, "error": str(exc)}
        except Exception as exc:
            logger.error('[AGENT:%s] unexpected error: %s\n%s',
                         self.name, exc, traceback.format_exc())
            return {"ok": False, "error": "Agent failed. Please try again.", "detail": str(exc)}

    def _run(self, inputs: dict, db, supa_user: dict) -> dict:
        raise NotImplementedError(f"{self.name} must implement _run()")

    def validate_json_output(self, text: str, fallback: dict | None = None) -> dict | None:
        """
        Validate LLM JSON output against self.OUTPUT_SCHEMA if defined.
        Returns validated dict on success, or *fallback* if schema is missing
        or validation fails (logs the error, does not raise).
        """
        if self.OUTPUT_SCHEMA is None:
            return safe_json_loads(text) or fallback
        try:
            from core.output_validator import LLMOutputValidationError, _extract_json, _validate_schema
            import json as _json
            json_str = _extract_json(text)
            data = _json.loads(json_str)
            validated = _validate_schema(data, self.OUTPUT_SCHEMA, self.name)
            return validated
        except Exception as exc:
            logger.warning('[AGENT:%s] output validation failed: %s', self.name, exc)
            return fallback

# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers used across multiple agents
# ─────────────────────────────────────────────────────────────────────────────

def get_case(db, case_id: str, lawyer_id: str) -> dict:
    """Load a case document; raise ValueError if not found or not owned."""
    doc = db['cases'].find_one({'_id': case_id})
    if not doc:
        raise ValueError(f"Case {case_id} not found.")
    if doc.get('lawyer_id') != lawyer_id:
        raise ValueError("Access denied to this case.")
    doc.pop('_id', None)
    doc['id'] = case_id
    return doc


def safe_json_loads(text: str) -> dict:
    """
    Very tolerant JSON extractor — finds the first {...} block in llm output.
    Falls back to empty dict if nothing parseable is found.
    """
    import json, re
    text = (text or '').strip()
    # strip markdown code fences
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
    # find first complete {...}
    match = re.search(r'\{[\s\S]+\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {}
