"""
Case tasks CRUD.
Collection: case_tasks
"""
import uuid
import logging
from datetime import datetime, timezone
from .case_crud import _serialize, _can_access

logger = logging.getLogger('django')

DB = 'case_tasks'
DB_CASES = 'cases'

VALID_STATUSES = {'Pending', 'InProgress', 'Done', 'Cancelled'}
VALID_PRIORITIES = {'High', 'Medium', 'Low'}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _assert_case_access(db, supa_user, case_id, require_lawyer=False):
    doc = db[DB_CASES].find_one({'_id': case_id})
    if not doc:
        raise LookupError('Case not found.')
    user_id = supa_user.get('user_id', '')
    user_type = (supa_user.get('user_type') or '').lower()
    if not _can_access(doc, user_id, user_type):
        raise PermissionError('Access denied.')
    if require_lawyer and (user_type != 'lawyer' or doc.get('lawyer_id') != user_id):
        raise PermissionError('Only the case lawyer can perform this action.')
    return doc


# ─────────────────────────────────────────────────────────────────────────────
# CREATE
# ─────────────────────────────────────────────────────────────────────────────

def create_task(db, supa_user, case_id: str, payload: dict) -> dict:
    """
    Create a task for a case.
    Required: title
    Optional: description, due_date, assigned_to, priority, source
    """
    _assert_case_access(db, supa_user, case_id)
    title = (payload.get('title') or '').strip()
    if not title:
        raise ValueError("'title' is required.")

    user_id = supa_user.get('user_id', '')
    priority = payload.get('priority', 'Medium')
    if priority not in VALID_PRIORITIES:
        priority = 'Medium'

    source = payload.get('source', 'manual')
    if source not in ('manual', 'agent'):
        source = 'manual'

    now = _now()
    doc = {
        '_id': str(uuid.uuid4()),
        'case_id': case_id,
        'title': title,
        'description': (payload.get('description') or '').strip(),
        'due_date': (payload.get('due_date') or '').strip(),
        'assigned_to': (payload.get('assigned_to') or user_id),
        'created_by': user_id,
        'status': 'Pending',
        'priority': priority,
        'source': source,
        'created_at': now,
    }
    db[DB].insert_one(doc)
    logger.info(f"[case_tasks] Created task '{title}' for case {case_id}")
    return _serialize(doc)


# ─────────────────────────────────────────────────────────────────────────────
# LIST
# ─────────────────────────────────────────────────────────────────────────────

def list_tasks(db, supa_user, case_id: str, filters: dict = None) -> list:
    _assert_case_access(db, supa_user, case_id)
    filters = filters or {}
    query = {'case_id': case_id}
    if filters.get('status'):
        query['status'] = filters['status']
    if filters.get('assigned_to'):
        query['assigned_to'] = filters['assigned_to']

    cursor = db[DB].find(query).sort('due_date', 1)
    return [_serialize(d) for d in cursor]


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE
# ─────────────────────────────────────────────────────────────────────────────

def update_task(db, supa_user, case_id: str, task_id: str, payload: dict) -> dict:
    """
    Update a task. Lawyers and paralegals can update. Clients cannot.
    """
    _assert_case_access(db, supa_user, case_id)
    user_type = (supa_user.get('user_type') or '').lower()
    if user_type == 'client':
        raise PermissionError('Clients cannot update tasks.')

    doc = db[DB].find_one({'_id': task_id, 'case_id': case_id})
    if not doc:
        raise LookupError('Task not found.')

    updates = {}
    if 'title' in payload:
        updates['title'] = payload['title']
    if 'description' in payload:
        updates['description'] = payload['description']
    if 'due_date' in payload:
        updates['due_date'] = payload['due_date']
    if 'assigned_to' in payload:
        updates['assigned_to'] = payload['assigned_to']
    if 'priority' in payload and payload['priority'] in VALID_PRIORITIES:
        updates['priority'] = payload['priority']
    if 'status' in payload and payload['status'] in VALID_STATUSES:
        updates['status'] = payload['status']

    if updates:
        db[DB].update_one({'_id': task_id}, {'$set': updates})

    return _serialize(db[DB].find_one({'_id': task_id}))


# ─────────────────────────────────────────────────────────────────────────────
# DELETE
# ─────────────────────────────────────────────────────────────────────────────

def delete_task(db, supa_user, case_id: str, task_id: str) -> bool:
    _assert_case_access(db, supa_user, case_id, require_lawyer=True)
    doc = db[DB].find_one({'_id': task_id, 'case_id': case_id})
    if not doc:
        raise LookupError('Task not found.')
    db[DB].delete_one({'_id': task_id})
    return True
