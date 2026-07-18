"""
MongoDB data-model helpers for MamlaAI Chat (v2).

Mirrors the existing `mamla_brain` v1 session/message pattern
(`_store_user_message` / `_store_assistant_message` in `mamla_brain/views.py`)
but uses separate collections so the new chat never collides with the v1 chat:

  brain_v2_sessions   one document per chat thread
  brain_v2_messages   one document per message; assistant messages carry a
                      `tool_trace` array (which capability fired, its args, and
                      any verified-citation payloads) for UI step chips and for
                      the audit trail behind "you own / verify the advice".
"""
import os
from datetime import datetime

from bson import ObjectId

from core.init_clients import get_mongo_db

SESSIONS = 'brain_v2_sessions'
MESSAGES = 'brain_v2_messages'

# ---------------------------------------------------------------------------
# Model tier resolution: user-facing Low/Med/High + a metered Premium toggle.
# Low/Med/High reuse the existing brain tiers (t1/t2/t3) in `llm_router`.
# Premium overrides the model with a top-tier OpenRouter slug; metering against
# the wallet/entitlements is wired in Phase 4 (feature key `MamlaAI_chat_premium`).
# ---------------------------------------------------------------------------
_TIER_BY_LEVEL = {
    'low': 't1',
    'medium': 't2',
    'high': 't3',
}
_DEFAULT_LEVEL = 'medium'


def resolve_model_selection(level: str = None, premium: bool = False) -> dict:
    """
    Map a user model choice to a call_llm() invocation.

    Returns a dict: {tier, provider, model, premium, level}. `provider`/`model`
    are None unless premium is set, in which case call_llm() uses the override.
    """
    level = (level or _DEFAULT_LEVEL).strip().lower()
    tier = _TIER_BY_LEVEL.get(level, 't2')
    if premium:
        return {
            'tier': 't3',
            'provider': 'openrouter',
            'model': os.getenv('BRAIN_PREMIUM_MODEL', 'anthropic/claude-opus-4.8'),
            'premium': True,
            'level': 'premium',
        }
    return {'tier': tier, 'provider': None, 'model': None, 'premium': False, 'level': level}


def _db():
    return get_mongo_db()


def _now():
    return datetime.utcnow()


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
def create_session(owner_id, data, app_name=''):
    matter = data.get('matter', {}) or {}
    title = data.get('title') or _default_title(matter)
    session = {
        'owner_id': owner_id,
        'title': title,
        'domain_key': (data.get('domain_key') or 'legal').strip().lower() or 'legal',
        'matter': matter,
        'doc_ids': [str(d) for d in (data.get('doc_ids') or [])],
        'model_level': (data.get('model_level') or _DEFAULT_LEVEL),
        'app_name': app_name,
        'created_at': _now(),
        'last_message_at': _now(),
        'deleted': False,
    }
    result = _db()[SESSIONS].insert_one(session)
    session['_id'] = result.inserted_id
    return session


def _default_title(matter):
    scope = 'MamlaAI Chat'
    if matter and matter.get('caseid'):
        case_id = matter['caseid'][0] if isinstance(matter['caseid'], list) else matter['caseid']
        scope = f'{scope} · {case_id}'
    return f"{scope} · {_now().strftime('%d %b %Y, %I:%M %p UTC')}"


def lookup_session(owner_id, session_id):
    try:
        object_id = ObjectId(session_id)
    except Exception:
        return None
    return _db()[SESSIONS].find_one({'_id': object_id, 'owner_id': owner_id, 'deleted': False})


def list_sessions(owner_id, page=1, page_size=20):
    page_size = min(int(page_size), 100)
    pipeline = [
        {'$match': {'owner_id': owner_id, 'deleted': False}},
        {'$sort': {'last_message_at': -1}},
        {'$facet': {
            'total': [{'$count': 'count'}],
            'items': [{'$skip': (page - 1) * page_size}, {'$limit': page_size}],
        }},
    ]
    out = list(_db()[SESSIONS].aggregate(pipeline))[0]
    total = out['total'][0]['count'] if out['total'] else 0
    return total, [serialize_session(s) for s in out['items']]


def touch_session(session_id):
    _db()[SESSIONS].update_one({'_id': session_id}, {'$set': {'last_message_at': _now()}})


def rename_session(owner_id, session_id, title):
    """Set a user-chosen title. Owner-guarded; returns the updated session or None."""
    try:
        object_id = ObjectId(session_id)
    except Exception:
        return None
    title = (title or '').strip()[:120]
    if not title:
        return None
    result = _db()[SESSIONS].find_one_and_update(
        {'_id': object_id, 'owner_id': owner_id, 'deleted': False},
        {'$set': {'title': title}},
        return_document=True,
    )
    return result


def soft_delete_session(owner_id, session_id):
    """Flag a thread deleted so list/lookup (which filter deleted=False) hide it."""
    try:
        object_id = ObjectId(session_id)
    except Exception:
        return False
    result = _db()[SESSIONS].update_one(
        {'_id': object_id, 'owner_id': owner_id, 'deleted': False},
        {'$set': {'deleted': True}},
    )
    return result.modified_count > 0


# A thread whose title still starts with this is "unnamed" — safe to auto-title
# from the first user message. A manual rename replaces it and is never clobbered.
_DEFAULT_TITLE_PREFIX = 'MamlaAI Chat'


def set_title_if_default(session_id, text):
    """Name a still-default thread after its first substantive user message.

    No-op if the user already renamed it (title no longer starts with the
    generic prefix). Only the first such call takes effect for a given thread.
    """
    session = _db()[SESSIONS].find_one({'_id': session_id}, {'title': 1})
    if not session:
        return
    if not (session.get('title', '') or '').startswith(_DEFAULT_TITLE_PREFIX):
        return
    cleaned = ' '.join((text or '').split()).strip()
    if not cleaned:
        return
    title = cleaned[:60] + ('…' if len(cleaned) > 60 else '')
    _db()[SESSIONS].update_one({'_id': session_id}, {'$set': {'title': title}})


def attach_doc(session_id, doc_id):
    """Add an uploaded document to a chat thread so doc_qa can scope to it."""
    _db()[SESSIONS].update_one(
        {'_id': session_id},
        {'$addToSet': {'doc_ids': str(doc_id)}, '$set': {'last_message_at': _now()}},
    )


# ---------------------------------------------------------------------------
# Pending draft (confirm-first drafting): the draft tool never generates on
# the first message — it records what it WOULD draft here and waits for the
# user's confirmation on the next turn.
# ---------------------------------------------------------------------------
def set_pending_draft(session_id, draft_for, query):
    _db()[SESSIONS].update_one(
        {'_id': session_id},
        {'$set': {'pending_draft': {
            'draft_for': draft_for, 'query': query, 'nudge_count': 0, 'created_at': _now(),
        }}},
    )


def clear_pending_draft(session_id):
    _db()[SESSIONS].update_one({'_id': session_id}, {'$unset': {'pending_draft': ''}})


def bump_pending_draft_nudge(session_id):
    """A bare 'yes' with no details yet — count it so a second one is read as
    consent to generate a placeholder draft rather than asking a third time."""
    _db()[SESSIONS].update_one(
        {'_id': session_id},
        {'$inc': {'pending_draft.nudge_count': 1}},
    )


def serialize_session(session):
    return {
        'id': str(session['_id']),
        'title': session.get('title', ''),
        'domain_key': session.get('domain_key', 'legal'),
        'matter': session.get('matter', {}),
        'doc_ids': session.get('doc_ids', []),
        'model_level': session.get('model_level', _DEFAULT_LEVEL),
        'created_at': str(session.get('created_at', '')),
        'last_message_at': str(session.get('last_message_at', '')),
    }


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------
def store_user_message(session, text, app_name=''):
    _db()[MESSAGES].insert_one({
        'session_id': session['_id'],
        'owner_id': session['owner_id'],
        'role': 'user',
        'content': text,
        'app_name': app_name,
        'created_at': _now(),
    })


def store_assistant_message(session, text, llm_response=None, citations=None, tool_trace=None,
                            artifacts=None, capability='', premium=False):
    llm_response = llm_response or {}
    usage = llm_response.get('usage', {}) or {}
    _db()[MESSAGES].insert_one({
        'session_id': session['_id'],
        'owner_id': session['owner_id'],
        'role': 'assistant',
        'content': text,
        'citations': citations or [],
        'tool_trace': tool_trace or [],
        'artifacts': artifacts or [],
        'capability': capability,
        'premium': bool(premium),
        'tier_used': llm_response.get('tier', ''),
        'model': llm_response.get('model', ''),
        'provider': llm_response.get('provider', ''),
        'tokens_used': usage.get('total_tokens', 0),
        'prompt_tokens': usage.get('prompt_tokens', 0),
        'completion_tokens': usage.get('completion_tokens', 0),
        'latency_ms': llm_response.get('latency_ms', 0),
        'created_at': _now(),
    })
    touch_session(session['_id'])


def history_messages(session, limit=6):
    messages = list(
        _db()[MESSAGES]
        .find({'session_id': session['_id']}, {'role': 1, 'content': 1, '_id': 0})
        .sort('created_at', -1)
        .limit(limit)
    )
    messages.reverse()
    return messages


def list_messages(session):
    messages = list(_db()[MESSAGES].find({'session_id': session['_id']}).sort('created_at', 1))
    return [serialize_message(m) for m in messages]


def serialize_message(message):
    return {
        'id': str(message['_id']),
        'role': message.get('role', ''),
        'content': message.get('content', ''),
        'citations': message.get('citations', []),
        'tool_trace': message.get('tool_trace', []),
        'artifacts': message.get('artifacts', []),
        'capability': message.get('capability', ''),
        'premium': bool(message.get('premium', False)),
        'model': message.get('model', ''),
        'tier_used': message.get('tier_used', ''),
        'tokens_used': message.get('tokens_used', 0),
        'created_at': str(message.get('created_at', '')),
    }
