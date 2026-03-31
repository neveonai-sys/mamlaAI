"""
Case CRUD operations.
Collections: cases
All functions receive the MongoDB db handle and authenticated user metadata.
"""
import uuid
import logging
from datetime import datetime, timezone

logger = logging.getLogger('django')

DB_CASES = 'cases'


def _now():
    return datetime.now(timezone.utc).isoformat()


def _serialize(doc):
    """Convert MongoDB doc to JSON-serialisable dict."""
    if doc is None:
        return None
    doc = dict(doc)
    if '_id' in doc:
        doc['_id'] = str(doc['_id'])   # keep as JSON-safe string
    return doc


# ─────────────────────────────────────────────────────────────────────────────
# CREATE
# ─────────────────────────────────────────────────────────────────────────────

def create_case(db, supa_user, payload: dict) -> dict:
    """
    Create a new internal case record.
    Required fields: title
    Optional: case_ref, case_type, court, cnr, client_ids, paralegal_ids,
              status, stage, filing_date, next_hearing, tags, brief
    """
    lawyer_id = supa_user.get('user_id', '')
    title = (payload.get('title') or '').strip()
    if not title:
        raise ValueError("'title' is required.")

    now = _now()
    doc = {
        '_id': str(uuid.uuid4()),
        'case_ref': (payload.get('case_ref') or '').strip(),
        'title': title,
        'case_type': (payload.get('case_type') or '').strip(),
        'court': payload.get('court') or {},
        'cnr': (payload.get('cnr') or '').strip(),
        'lawyer_id': lawyer_id,
        'client_ids': payload.get('client_ids') or [],
        'paralegal_ids': payload.get('paralegal_ids') or [],
        'status': payload.get('status') or 'Active',
        'stage': payload.get('stage') or 'Filing',
        'filing_date': (payload.get('filing_date') or '').strip(),
        'next_hearing': (payload.get('next_hearing') or '').strip(),
        'tags': payload.get('tags') or [],
        'brief': (payload.get('brief') or '').strip(),
        'created_at': now,
        'updated_at': now,
    }
    db[DB_CASES].insert_one(doc)
    logger.info(f"[cases] Created case {doc['_id']} for lawyer {lawyer_id}")
    return _serialize(doc)


# ─────────────────────────────────────────────────────────────────────────────
# LIST
# ─────────────────────────────────────────────────────────────────────────────

def list_cases(db, supa_user, filters: dict = None) -> list:
    """
    Return all cases visible to the authenticated user.
    - Lawyer: all cases where lawyer_id == user_id
    - Paralegal: cases where user_id in paralegal_ids
    - Client: cases where user_id in client_ids
    Optional filters dict: status, stage, search (partial title match)
    """
    filters = filters or {}
    user_id = supa_user.get('user_id', '')
    user_type = (supa_user.get('user_type') or '').lower()

    if user_type == 'lawyer':
        query = {'lawyer_id': user_id}
    elif user_type == 'paralegal':
        query = {'paralegal_ids': user_id}
    else:
        # client — only their cases
        query = {'client_ids': user_id}

    if filters.get('status'):
        query['status'] = filters['status']
    if filters.get('stage'):
        query['stage'] = filters['stage']
    if filters.get('search'):
        import re
        query['title'] = {'$regex': re.escape(filters['search']), '$options': 'i'}

    cursor = db[DB_CASES].find(query).sort('updated_at', -1).limit(200)
    return [_serialize(doc) for doc in cursor]


# ─────────────────────────────────────────────────────────────────────────────
# GET ONE
# ─────────────────────────────────────────────────────────────────────────────

def get_case(db, supa_user, case_id: str) -> dict:
    """
    Fetch a single case. Returns None if not found or not visible to user.
    """
    user_id = supa_user.get('user_id', '')
    user_type = (supa_user.get('user_type') or '').lower()
    doc = db[DB_CASES].find_one({'_id': case_id})
    if not doc:
        return None
    if not _can_access(doc, user_id, user_type):
        return None
    return _serialize(doc)


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE
# ─────────────────────────────────────────────────────────────────────────────

UPDATABLE_FIELDS = {
    'case_ref', 'title', 'case_type', 'court', 'cnr', 'client_ids',
    'paralegal_ids', 'status', 'stage', 'filing_date', 'next_hearing',
    'tags', 'brief',
}


def update_case(db, supa_user, case_id: str, payload: dict) -> dict:
    """
    Partial update of a case. Only lawyer can update.
    """
    user_id = supa_user.get('user_id', '')
    user_type = (supa_user.get('user_type') or '').lower()
    doc = db[DB_CASES].find_one({'_id': case_id})
    if not doc:
        raise LookupError('Case not found.')
    if user_type != 'lawyer' or doc.get('lawyer_id') != user_id:
        raise PermissionError('Only the case lawyer can update this case.')

    updates = {k: v for k, v in payload.items() if k in UPDATABLE_FIELDS}
    if not updates:
        raise ValueError('No valid fields to update.')
    updates['updated_at'] = _now()
    db[DB_CASES].update_one({'_id': case_id}, {'$set': updates})
    return get_case(db, supa_user, case_id)


# ─────────────────────────────────────────────────────────────────────────────
# CLOSE / ARCHIVE
# ─────────────────────────────────────────────────────────────────────────────

def close_case(db, supa_user, case_id: str, resolution_type: str, summary: str) -> dict:
    """
    Mark a case as Archived / Settled / Disposed.
    Only the case lawyer can close.
    """
    user_id = supa_user.get('user_id', '')
    user_type = (supa_user.get('user_type') or '').lower()
    doc = db[DB_CASES].find_one({'_id': case_id})
    if not doc:
        raise LookupError('Case not found.')
    if user_type != 'lawyer' or doc.get('lawyer_id') != user_id:
        raise PermissionError('Only the case lawyer can close this case.')

    valid_resolutions = {'Settled', 'Disposed', 'Appeal', 'Archived'}
    if resolution_type not in valid_resolutions:
        raise ValueError(f"resolution_type must be one of {valid_resolutions}.")

    updates = {
        'status': resolution_type,
        'stage': 'Closed',
        'brief': summary or doc.get('brief', ''),
        'updated_at': _now(),
    }
    db[DB_CASES].update_one({'_id': case_id}, {'$set': updates})
    return get_case(db, supa_user, case_id)


# ─────────────────────────────────────────────────────────────────────────────
# TIMELINE  (hearings + notes + tasks aggregated)
# ─────────────────────────────────────────────────────────────────────────────

def get_timeline(db, supa_user, case_id: str) -> dict:
    """
    Return all timeline items for a case (hearings, notes, tasks) sorted by date.
    Visibility rules applied for notes.
    """
    user_id = supa_user.get('user_id', '')
    user_type = (supa_user.get('user_type') or '').lower()
    doc = db[DB_CASES].find_one({'_id': case_id})
    if not doc:
        raise LookupError('Case not found.')
    if not _can_access(doc, user_id, user_type):
        raise PermissionError('Access denied.')

    hearings = [_serialize(d) for d in
                db['hearing_notes'].find({'case_id': case_id}).sort('hearing_date', -1)]

    note_query = {'case_id': case_id}
    if user_type == 'client':
        note_query['visibility'] = 'shared'
    notes = [_serialize(d) for d in
             db['case_notes'].find(note_query).sort('created_at', -1)]

    tasks = [_serialize(d) for d in
             db['case_tasks'].find({'case_id': case_id}).sort('due_date', 1)]

    return {
        'case': _serialize(doc),
        'hearings': hearings,
        'notes': notes,
        'tasks': tasks,
    }


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _can_access(doc, user_id: str, user_type: str) -> bool:
    if user_type == 'lawyer':
        return doc.get('lawyer_id') == user_id
    if user_type == 'paralegal':
        return user_id in (doc.get('paralegal_ids') or [])
    # client
    return user_id in (doc.get('client_ids') or [])
