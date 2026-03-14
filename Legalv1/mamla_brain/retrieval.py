import os
from pathlib import Path

from talkdoc.search import INDEX as TALKDOC_INDEX
from talkdoc.search import ensure_index as ensure_talkdoc_index
from talkdoc.search import knn_search, os_client
from talkdoc.tasks import embed_texts

from .prompts import get_domain_profile

KNOWLEDGE_BASE_MAPPING = {
    'settings': {'index': {'knn': True}},
    'mappings': {
        'properties': {
            'chunk_id': {'type': 'keyword'},
            'domain_key': {'type': 'keyword'},
            'source_id': {'type': 'keyword'},
            'source_name': {'type': 'keyword'},
            'title': {'type': 'text'},
            'text': {'type': 'text'},
            'act': {'type': 'keyword'},
            'section_number': {'type': 'keyword'},
            'section_title': {'type': 'text'},
            'jurisdiction': {'type': 'keyword'},
            'source_url': {'type': 'keyword'},
            'vector': {
                'type': 'knn_vector',
                'dimension': int(os.getenv('RAG_EMBED_DIM', '3072')),
                'method': {'name': 'hnsw', 'space_type': 'l2'},
            },
            'created_at': {'type': 'date'},
        }
    },
}


def get_knowledge_index(domain_key='legal'):
    return get_domain_profile(domain_key)['knowledge_index']


def ensure_knowledge_index(domain_key='legal'):
    client = os_client()
    index_name = get_knowledge_index(domain_key)
    if not client.indices.exists(index_name):
        client.indices.create(index_name, body=KNOWLEDGE_BASE_MAPPING)
    return client, index_name


def search_user_docs(query, owner_id, doc_ids=None, matter=None, k=10):
    if not owner_id or not query:
        return []
    query_vector = embed_texts([query])[0]
    client = ensure_talkdoc_index()
    hits = knn_search(client, query_vector, user_id=owner_id, doc_ids=doc_ids, matter=matter, k=k)
    results = []
    for rank, hit in enumerate(hits, start=1):
        results.append({
            'source_type': 'document',
            'source_id': hit['doc_id'],
            'source_name': hit.get('name_stored', ''),
            'page': hit.get('page'),
            'text': hit.get('text', ''),
            'score': hit.get('score', 0),
            'rank': rank,
            'citation': {
                'source': hit.get('name_stored', ''),
                'page': hit.get('page'),
                'snippet': (hit.get('text', '')[:320] + '...') if hit.get('text') else '',
            },
        })
    return results


def search_knowledge_base(query, domain_key='legal', k=8):
    if not query:
        return []

    client = os_client()
    index_name = get_knowledge_index(domain_key)
    if not client.indices.exists(index_name):
        return []

    query_vector = embed_texts([query])[0]
    body = {
        'size': k,
        'query': {
            'script_score': {
                'query': {'bool': {'must': [{'term': {'domain_key': domain_key}}]}},
                'script': {
                    'source': 'knn_score',
                    'lang': 'knn',
                    'params': {
                        'field': 'vector',
                        'query_value': query_vector,
                        'space_type': 'l2',
                    },
                },
            }
        },
    }
    response = client.search(index=index_name, body=body)
    results = []
    for rank, hit in enumerate(response.get('hits', {}).get('hits', []), start=1):
        source = hit.get('_source', {})
        label = source.get('section_title') or source.get('title') or source.get('source_name') or 'knowledge-base'
        results.append({
            'source_type': 'knowledge_base',
            'source_id': source.get('source_id') or source.get('chunk_id') or label,
            'source_name': label,
            'page': None,
            'text': source.get('text', ''),
            'score': hit.get('_score', 0),
            'rank': rank,
            'act': source.get('act', ''),
            'section_number': source.get('section_number', ''),
            'section_title': source.get('section_title', ''),
            'source_url': source.get('source_url', ''),
            'citation': {
                'source': label,
                'page': None,
                'snippet': (source.get('text', '')[:320] + '...') if source.get('text') else '',
            },
        })
    return results


def merge_context(kb_hits, doc_hits, max_items=8):
    merged = []
    seen = set()

    for collection_name, hits, weight in (
        ('document', doc_hits or [], 1.0),
        ('knowledge_base', kb_hits or [], 0.9),
    ):
        for item in hits:
            dedupe_key = (collection_name, item.get('source_id'), item.get('page'), item.get('text', '')[:160])
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            rank = max(item.get('rank', 1), 1)
            item['merged_rank_score'] = weight / rank
            merged.append(item)

    merged.sort(key=lambda item: item.get('merged_rank_score', 0), reverse=True)
    return merged[:max_items]


def render_context(context_items, max_items=5):
    parts = []
    for item in (context_items or [])[:max_items]:
        if item.get('source_type') == 'knowledge_base':
            heading = item.get('source_name') or 'knowledge-base'
        else:
            page = item.get('page') or '?'
            heading = f"{item.get('source_name') or 'document'} p.{page}"
        parts.append(f'[{heading}]\n{item.get("text", "")}')
    return '\n\n'.join(parts)


def knowledge_source_dir(domain_key='legal'):
    app_dir = Path(__file__).resolve().parent
    if domain_key == 'legal':
        return app_dir / 'legal_kb_sources'
    return app_dir / 'knowledge_sources' / domain_key


def knowledge_index_stats(domain_key='legal'):
    client = os_client()
    index_name = get_knowledge_index(domain_key)
    if not client.indices.exists(index_name):
        return {'index': index_name, 'exists': False, 'count': 0}
    count = client.count(index=index_name).get('count', 0)
    return {'index': index_name, 'exists': True, 'count': count, 'doc_index': TALKDOC_INDEX}
