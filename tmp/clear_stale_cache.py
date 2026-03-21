"""Clear stale eCourts search cache and completed scrape jobs with old data format."""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Legalv1.settings')
sys.path.insert(0, '/home/pronoys/products/sessioned_AiAdalat/Adalatai_ground_zero/Legalv1')
django.setup()

from core.init_clients import get_mongo_client
import re

db = get_mongo_client()['legaldb']

# Clear cached search results (they have old unparsed format)
result = db.ecourts_cache.delete_many({'data_type': 'case_search'})
print(f'Deleted {result.deleted_count} cached search results')

# Clear cached search results by key pattern
result2 = db.ecourts_cache.delete_many({'cache_key': re.compile(r':search:')})
print(f'Deleted {result2.deleted_count} additional search cache entries')

# Clear completed search jobs (they store old format in result field)
result3 = db.ecourts_scrape_jobs.delete_many({
    'status': 'completed',
    'type': re.compile(r'search'),
})
print(f'Deleted {result3.deleted_count} completed search jobs')

print('Done. Stale cache cleared.')
