"""
Hearing notes CRUD (prep + outcome).
Collection: hearing_notes
"""
import uuid
import logging
from datetime import datetime, timezone
from .case_crud import _serialize, _can_access

logger = logging.getLogger('django')

DB = 'hearing_notes'
DB_CASES = 'cases'


def _now():
    return datetime.now(timezone.utc).isoformat()


def _assert_case_access(db, supa_user, case_id):
    doc = db[DB_CASES].find_one({'_id': case_id})
    if not doc:
        raise LookupError('Case not found.')
    user_id = supa_user.get('user_id', '')
    user_type = (supa_user.get('user_type') or '').lower()
    if not _can_access(doc, user_id, user_type):
        raise PermissionError('Access denied.')
    return doc


# ─────────────────────────────────────────────────────────────────────────────
# CREATE
# ─────────────────────────────────────────────────────────────────────────────

def create_hearing_note(db, supa_user, case_id: str, payload: dict) -> dict:
    """
    Create a hearing note of type 'prep' or 'outcome'.
    Required: hearing_date, type ('prep' | 'outcome')
    """
    _assert_case_access(db, supa_user, case_id)
    lawyer_id = supa_user.get('user_id', '')
    note_type = payload.get('type', '').strip()
    if note_type not in ('prep', 'outcome'):
        raise ValueError("'type' must be 'prep' or 'outcome'.")

    hearing_date = (payload.get('hearing_date') or '').strip()
    if not hearing_date:
        raise ValueError("'hearing_date' is required.")

    now = _now()
    doc = {
        '_id': str(uuid.uuid4()),
        'case_id': case_id,
        'lawyer_id': lawyer_id,
        'hearing_date': hearing_date,
        'calendar_event_id': (payload.get('calendar_event_id') or '').strip(),
        'type': note_type,
        'content': (payload.get('content') or '').strip(),
        'ai_brief': payload.get('ai_brief') or {},
        'purpose': (payload.get('purpose') or '').strip(),
        'outcome': (payload.get('outcome') or '').strip(),
        'next_date': (payload.get('next_date') or '').strip(),
        'tasks_generated': payload.get('tasks_generated') or [],
        'created_at': now,
    }
    db[DB].insert_one(doc)
    logger.info(f"[hearing_notes] Created {note_type} note for case {case_id}")
    return _serialize(doc)


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE OUTCOME
# ─────────────────────────────────────────────────────────────────────────────

def update_hearing_outcome(db, supa_user, case_id: str, note_id: str, payload: dict) -> dict:
    """
    Record or update the outcome of a hearing note.
    """
    _assert_case_access(db, supa_user, case_id)
    doc = db[DB].find_one({'_id': note_id, 'case_id': case_id})
    if not doc:
        raise LookupError('Hearing note not found.')

    updates = {}
    if 'outcome' in payload:
        updates['outcome'] = payload['outcome']
    if 'next_date' in payload:
        updates['next_date'] = payload['next_date']
    if 'content' in payload:
        updates['content'] = payload['content']
    if 'tasks_generated' in payload:
        updates['tasks_generated'] = payload['tasks_generated']
    if 'ai_brief' in payload:
        updates['ai_brief'] = payload['ai_brief']

    if updates:
        db[DB].update_one({'_id': note_id}, {'$set': updates})
        # Also update case next_hearing if next_date provided
        if updates.get('next_date'):
            db[DB_CASES].update_one({'_id': case_id}, {'$set': {
                'next_hearing': updates['next_date'],
                'updated_at': _now(),
            }})

    updated = db[DB].find_one({'_id': note_id})
    return _serialize(updated)


# ─────────────────────────────────────────────────────────────────────────────
# LIST
# ─────────────────────────────────────────────────────────────────────────────

def list_hearing_notes(db, supa_user, case_id: str) -> list:
    _assert_case_access(db, supa_user, case_id)
    cursor = db[DB].find({'case_id': case_id}).sort('hearing_date', -1)
    return [_serialize(d) for d in cursor]


# ─────────────────────────────────────────────────────────────────────────────
# GET ONE
# ─────────────────────────────────────────────────────────────────────────────

def get_hearing_note(db, supa_user, case_id: str, note_id: str) -> dict:
    _assert_case_access(db, supa_user, case_id)
    doc = db[DB].find_one({'_id': note_id, 'case_id': case_id})
    if not doc:
        raise LookupError('Hearing note not found.')
    return _serialize(doc)
