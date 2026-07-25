"""
Case notes CRUD (threaded notes with visibility).
Collection: case_notes
"""
import uuid
import logging
from datetime import datetime, timezone
from .case_crud import _serialize, _can_access
from users.routes.encryption import encrypt_field

logger = logging.getLogger('django')

DB = 'case_notes'
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

def create_note(db, supa_user, case_id: str, payload: dict) -> dict:
    """
    Add a note to a case.
    Required: content
    Optional: visibility ('internal' | 'shared') — clients default to 'shared',
              others default to 'internal'.
    """
    _assert_case_access(db, supa_user, case_id)
    content = (payload.get('content') or '').strip()
    if not content:
        raise ValueError("'content' is required.")

    user_id = supa_user.get('user_id', '')
    user_type = supa_user.get('user_type', 'Lawyer')
    lower_type = user_type.lower()

    # Clients can only write shared notes
    visibility = (payload.get('visibility') or 'internal').strip().lower()
    if lower_type == 'client':
        visibility = 'shared'

    now = _now()
    doc = {
        '_id': str(uuid.uuid4()),
        'case_id': case_id,
        'author_id': user_id,
        'author_role': user_type,
        'visibility': visibility,
        'content': encrypt_field(content),
        'attachments': payload.get('attachments') or [],
        'created_at': now,
        'updated_at': now,
    }
    db[DB].insert_one(doc)
    logger.info(f"[case_notes] Created note for case {case_id} by {user_id}")
    return _serialize(doc)


# ─────────────────────────────────────────────────────────────────────────────
# LIST
# ─────────────────────────────────────────────────────────────────────────────

def list_notes(db, supa_user, case_id: str) -> list:
    """
    List notes for a case. Clients only see 'shared' notes.
    """
    _assert_case_access(db, supa_user, case_id)
    user_type = (supa_user.get('user_type') or '').lower()

    query = {'case_id': case_id}
    if user_type == 'client':
        query['visibility'] = 'shared'

    cursor = db[DB].find(query).sort('created_at', -1)
    return [_serialize(d) for d in cursor]


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE
# ─────────────────────────────────────────────────────────────────────────────

def update_note(db, supa_user, case_id: str, note_id: str, payload: dict) -> dict:
    """
    Edit a note. Only the note author can update.
    """
    _assert_case_access(db, supa_user, case_id)
    user_id = supa_user.get('user_id', '')
    doc = db[DB].find_one({'_id': note_id, 'case_id': case_id})
    if not doc:
        raise LookupError('Note not found.')
    if doc.get('author_id') != user_id:
        raise PermissionError('Only the note author can edit this note.')

    updates = {}
    if 'content' in payload:
        updates['content'] = encrypt_field(payload['content'])
    if 'visibility' in payload:
        # clients cannot set internal visibility
        vis = payload['visibility'].lower()
        if (supa_user.get('user_type') or '').lower() == 'client':
            vis = 'shared'
        updates['visibility'] = vis
    if updates:
        updates['updated_at'] = _now()
        db[DB].update_one({'_id': note_id}, {'$set': updates})

    return _serialize(db[DB].find_one({'_id': note_id}))


# ─────────────────────────────────────────────────────────────────────────────
# DELETE
# ─────────────────────────────────────────────────────────────────────────────

def delete_note(db, supa_user, case_id: str, note_id: str) -> bool:
    _assert_case_access(db, supa_user, case_id)
    user_id = supa_user.get('user_id', '')
    user_type = (supa_user.get('user_type') or '').lower()
    doc = db[DB].find_one({'_id': note_id, 'case_id': case_id})
    if not doc:
        raise LookupError('Note not found.')
    # Lawyer can delete any note in their case; others only their own
    if user_type != 'lawyer' and doc.get('author_id') != user_id:
        raise PermissionError('You cannot delete this note.')
    db[DB].delete_one({'_id': note_id})
    return True
