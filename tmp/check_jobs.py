import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Legalv1.settings')
sys.path.insert(0, '/home/pronoys/products/sessioned_AiAdalat/Adalatai_ground_zero/Legalv1')
django.setup()

from core.init_clients import get_mongo_client
import json, re

db = get_mongo_client()['legaldb']

# Find completed search jobs
jobs = list(db.ecourts_scrape_jobs.find(
    {'status': 'completed', 'type': re.compile('search')}
).sort('completed_at', -1).limit(5))
print(f'Found {len(jobs)} completed search jobs')

if not jobs:
    # Try any completed job
    jobs = list(db.ecourts_scrape_jobs.find(
        {'status': 'completed'}
    ).sort('completed_at', -1).limit(5))
    print(f'Found {len(jobs)} completed jobs of any type')

if not jobs:
    # Check recent jobs regardless of status
    recent = list(db.ecourts_scrape_jobs.find().sort('created_at', -1).limit(10))
    print(f'Last {len(recent)} jobs:')
    for j in recent:
        has_result = j.get('result') is not None
        result_keys = list(j['result'].keys()) if has_result else []
        case_list_len = len(j['result'].get('case_list', [])) if has_result else 0
        print(f'  {j["_id"]} type={j.get("type")} status={j.get("status")} result_keys={result_keys} case_list_len={case_list_len}')
        if has_result and case_list_len > 0:
            first = j['result']['case_list'][0]
            print(f'    First entry keys: {list(first.keys())}')
            print(f'    First entry: {json.dumps(first, default=str, indent=4)}')
            break
else:
    for j in jobs[:1]:
        result = j.get('result', {})
        print(f'Job: {j["_id"]} type={j.get("type")}')
        print(f'Result keys: {list(result.keys())}')
        case_list = result.get('case_list', [])
        print(f'case_list length: {len(case_list)}')
        if case_list:
            first = case_list[0]
            print(f'First entry keys: {list(first.keys())}')
            print(f'First entry: {json.dumps(first, default=str, indent=2)}')
            if len(case_list) > 1:
                print(f'Second entry: {json.dumps(case_list[1], default=str, indent=2)}')

# Also check ecourts_cache for cached search results
print('\n--- Cached search results ---')
cached = list(db.ecourts_cache.find({'data_type': 'case_search'}).limit(3))
print(f'Found {len(cached)} cached search results')
for c in cached:
    data = c.get('data', {})
    case_list = data.get('case_list', [])
    print(f'  cache_key={c.get("cache_key")} case_list_len={len(case_list)}')
    if case_list:
        first = case_list[0]
        print(f'  First entry keys: {list(first.keys())}')
        print(f'  First entry: {json.dumps(first, default=str, indent=2)}')
        break
