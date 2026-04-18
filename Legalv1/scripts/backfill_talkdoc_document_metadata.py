import os
import sys
from datetime import datetime
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
LEGALV1_DIR = CURRENT_DIR.parent
PROJECT_DIR = LEGALV1_DIR.parent

if str(LEGALV1_DIR) not in sys.path:
    sys.path.insert(0, str(LEGALV1_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Legalv1.settings')

import django  # noqa: E402

django.setup()

from core.init_clients import get_mongo_client, get_mongo_db  # noqa: E402


def matter_list(matter, key):
    value = (matter or {}).get(key)
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    normalized = str(value).strip()
    return [normalized] if normalized else []


def timestamped_filename(filename, created_at=None):
    original_name = Path(filename or 'document').name or 'document'
    stem = Path(original_name).stem or 'document'
    suffix = Path(original_name).suffix

    if hasattr(created_at, 'strftime'):
        timestamp = created_at.strftime('%Y%m%d-%H%M%S-%f')
    else:
        timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f')

    return f'{stem}_{timestamp}{suffix}'


def main():
    db = get_mongo_db()
    collection = db['rag_documents']

    updated = 0
    scanned = 0

    cursor = collection.find({}, {
        'name_original': 1,
        'name_display': 1,
        'name_stored': 1,
        'matter': 1,
        'created_at': 1,
        'case_ids': 1,
        'client_ids': 1,
        'primary_case_id': 1,
        'primary_client_id': 1,
    })

    for document in cursor:
        scanned += 1
        matter = document.get('matter') or {}
        case_ids = matter_list(matter, 'caseid')
        client_ids = matter_list(matter, 'clientid')

        original_name = document.get('name_original') or document.get('name_display') or document.get('name_stored') or 'document'
        display_name = document.get('name_display') or document.get('name_stored') or ''

        update_fields = {}

        if not display_name:
            update_fields['name_display'] = timestamped_filename(original_name, document.get('created_at'))

        if document.get('case_ids') != case_ids:
            update_fields['case_ids'] = case_ids

        if document.get('client_ids') != client_ids:
            update_fields['client_ids'] = client_ids

        primary_case_id = case_ids[0] if case_ids else ''
        if document.get('primary_case_id', '') != primary_case_id:
            update_fields['primary_case_id'] = primary_case_id

        primary_client_id = client_ids[0] if client_ids else ''
        if document.get('primary_client_id', '') != primary_client_id:
            update_fields['primary_client_id'] = primary_client_id

        if update_fields:
            collection.update_one({'_id': document['_id']}, {'$set': update_fields})
            updated += 1

    print(f'Scanned {scanned} TalkDoc documents')
    print(f'Updated {updated} TalkDoc documents')


if __name__ == '__main__':
    main()