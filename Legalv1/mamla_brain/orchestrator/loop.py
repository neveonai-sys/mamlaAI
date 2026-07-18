"""
The MamlaAI Chat orchestration loop.

`run_turn` is a generator that yields event dicts (the same event stream the SSE
endpoint forwards to the browser and the non-streaming endpoint collects):

    {'type': 'tool_call',   'capability': ...}
    {'type': 'tool_result', 'capability': ..., 'artifacts': [...]}
    {'type': 'token',       'text': '...'}          # streamed answer chunks
    {'type': 'done',        'text', 'tool_trace', 'citations', 'artifacts', 'capability'}
    {'type': 'error',       'message': '...'}

The final 'done' event carries the fully-assembled assistant turn so the caller
can persist it once, regardless of streaming vs non-streaming.

Phase 1: DRAFT is a real tool (synchronous, returns a deep-link card); every
other capability is answered through the grounded orchestrator persona (tokens
streamed). Dedicated doc_qa / citation / research tools slot in at the marked
dispatch point in later phases.
"""
import logging

from . import router, tools
from .grounding import augment_system_with_grounding
from .prompts_v2 import build_orchestrator_system

logger = logging.getLogger('django')


def _resolved_model_name(selection, tier_cfg):
    """The model this turn will use — for UI badges and the audit trail."""
    from django.conf import settings
    from core.llm_client import PROVIDER_OPENAI, get_model

    if selection.get('model'):
        return selection['model']
    provider = selection.get('provider') or getattr(settings, 'LLM_DEFAULT_PROVIDER', PROVIDER_OPENAI)
    return get_model(tier_cfg['app_scenario'], provider)


def _stream_chat(messages, selection, tier_cfg):
    """
    Yield answer text chunks from the LLM (stream=True), reusing the llm_router
    client pool + model resolution. Raises on error so run_turn can fall back.
    """
    from ..llm_router import _get_client
    from core.llm_client import PROVIDER_OPENAI, get_model

    provider = selection.get('provider') or PROVIDER_OPENAI
    model = selection.get('model') or get_model(tier_cfg['app_scenario'], provider)
    client = _get_client(provider)
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=tier_cfg['temperature'],
        max_tokens=tier_cfg['max_tokens'],
        stream=True,
    )
    for chunk in stream:
        try:
            delta = chunk.choices[0].delta.content
        except (AttributeError, IndexError):
            delta = None
        if delta:
            yield delta


def run_turn(session, text, selection, history, tier_cfg):
    """Generator of orchestration events for one user turn."""
    resolved_model = _resolved_model_name(selection, tier_cfg)
    premium = bool(selection.get('premium'))

    # --- Pending draft confirmation (confirm-first, detail-gathering) -----
    # A draft is never generated off a bare "yes" with no facts. See
    # tools.classify_pending_reply for the full decision table.
    if session.get('pending_draft'):
        from . import store

        pending = session.get('pending_draft') or {}
        decision = tools.classify_pending_reply(text)

        if decision == 'placeholder' or (decision == 'affirm_only' and pending.get('nudge_count', 0) >= 1):
            yield {'type': 'tool_call', 'capability': 'draft', 'confidence': 'high'}
            result = tools.run_draft_generate(session, text, history, tier_cfg, use_placeholders=True)
            if result.get('artifacts'):
                yield {'type': 'tool_result', 'capability': 'draft', 'artifacts': result['artifacts']}
            yield {'type': 'token', 'text': result['answer']}
            yield {
                'type': 'done', 'text': result['answer'],
                'tool_trace': result['tool_trace'], 'citations': result.get('citations', []),
                'artifacts': result.get('artifacts', []), 'capability': 'draft',
                'model': resolved_model, 'premium': premium,
            }
            return

        if decision == 'affirm_only':
            store.bump_pending_draft_nudge(session['_id'])
            draft_for = pending.get('draft_for', 'document')
            hint = tools.field_hint_for(draft_for)
            answer = (
                f"Sure — whenever you're ready, share {hint} and I'll draft the **{draft_for}** from it. "
                "Or say **use placeholders** for a generic version to start from."
            )
            yield {'type': 'token', 'text': answer}
            yield {
                'type': 'done', 'text': answer,
                'tool_trace': [{'capability': 'draft', 'status': 'awaiting_details'}],
                'citations': [], 'artifacts': [], 'capability': 'draft',
                'model': resolved_model, 'premium': premium,
            }
            return

        if decision == 'cancel':
            store.clear_pending_draft(session['_id'])
            answer = "No problem — let me know if you'd like that draft later."
            yield {'type': 'token', 'text': answer}
            yield {
                'type': 'done', 'text': answer,
                'tool_trace': [{'capability': 'draft', 'status': 'cancelled'}],
                'citations': [], 'artifacts': [], 'capability': 'draft',
                'model': resolved_model, 'premium': premium,
            }
            return

        if decision == 'question':
            store.clear_pending_draft(session['_id'])
            session.pop('pending_draft', None)
            # falls through to normal routing below — treated as a new turn
        else:  # 'details' — substantive facts supplied; draft from them now
            yield {'type': 'tool_call', 'capability': 'draft', 'confidence': 'high'}
            result = tools.run_draft_generate(session, text, history, tier_cfg)
            if result.get('artifacts'):
                yield {'type': 'tool_result', 'capability': 'draft', 'artifacts': result['artifacts']}
            yield {'type': 'token', 'text': result['answer']}
            yield {
                'type': 'done', 'text': result['answer'],
                'tool_trace': result['tool_trace'], 'citations': result.get('citations', []),
                'artifacts': result.get('artifacts', []), 'capability': 'draft',
                'model': resolved_model, 'premium': premium,
            }
            return

    has_docs = bool(session.get('doc_ids'))
    routing = router.classify_capability(text, has_docs=has_docs)
    capability = routing['capability']
    yield {'type': 'tool_call', 'capability': capability, 'confidence': routing['confidence']}

    # === Dispatch =========================================================
    # draft (confirm-first) / research / doc_qa / citation / meta are dedicated
    # tools; general falls through to the grounded general path below.
    result = tools.dispatch(capability, session, text, history, tier_cfg)

    if result and result.get('artifacts'):
        yield {'type': 'tool_result', 'capability': capability, 'artifacts': result['artifacts']}

    if result and result['kind'] == 'answer':
        yield {'type': 'token', 'text': result['answer']}
        yield {
            'type': 'done', 'text': result['answer'],
            'tool_trace': result['tool_trace'], 'citations': result.get('citations', []),
            'artifacts': result.get('artifacts', []), 'capability': capability,
            'model': resolved_model, 'premium': premium,
        }
        return

    if result and result['kind'] == 'stream':
        messages = result['messages']
        tool_trace = result['tool_trace']
        citations = result.get('citations', [])
    else:
        # Grounded general path (citation / general)
        system = build_orchestrator_system(session.get('domain_key', 'legal'))
        system = augment_system_with_grounding(system, text)  # verification-gated citations
        messages = [{'role': 'system', 'content': system}]
        for turn in history:
            messages.append({'role': turn['role'], 'content': turn['content']})
        messages.append({'role': 'user', 'content': text})
        tool_trace = [{'capability': capability, 'status': 'ok', 'method': routing['method']}]
        citations = []

    full = []
    try:
        for delta in _stream_chat(messages, selection, tier_cfg):
            full.append(delta)
            yield {'type': 'token', 'text': delta}
    except Exception as exc:
        logger.warning('[orchestrator.loop] stream failed, falling back: %s', exc)
        from ..llm_router import call_llm
        try:
            response = call_llm(
                messages, tier=selection['tier'],
                provider=selection['provider'], model=selection['model'],
            )
            text_out = response.get('text') or ''
            if not full:  # nothing streamed yet — emit whole answer
                full.append(text_out)
                yield {'type': 'token', 'text': text_out}
        except Exception as exc2:
            logger.error('[orchestrator.loop] fallback failed: %s', exc2)
            yield {'type': 'error', 'message': 'the assistant is temporarily unavailable, please retry'}
            return

    answer = ''.join(full).strip()
    yield {
        'type': 'done',
        'text': answer,
        'tool_trace': tool_trace,
        'citations': citations,
        'artifacts': [],
        'capability': capability,
        'model': resolved_model,
        'premium': premium,
    }
