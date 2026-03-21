import os
from datetime import datetime
from opensearchpy import OpenSearch

OS_HOST = os.getenv("RAG_OS_HOST") or os.getenv("OPENSEARCH_HOST", "localhost")
OS_PORT = int(os.getenv("RAG_OS_PORT") or os.getenv("OPENSEARCH_PORT", "9200"))
OS_USER = (os.getenv("RAG_OS_USER") or os.getenv("OPENSEARCH_USERNAME") or "").strip()
OS_PASS = (os.getenv("RAG_OS_PASS") or os.getenv("OPENSEARCH_PASSWORD") or "").strip()
INDEX = os.getenv("RAG_OS_INDEX", "rag_chunks_v1")

def os_client() -> OpenSearch:
    kwargs = {
        "hosts": [{"host": OS_HOST, "port": OS_PORT}],
        "use_ssl": False,
        "verify_certs": False,
    }
    if OS_USER or OS_PASS:
        kwargs["http_auth"] = (OS_USER, OS_PASS)
    return OpenSearch(**kwargs)

MAPPING = {
    "settings": {"index": {"knn": True}},
    "mappings": {
        "properties": {
            "chunk_id": {"type": "keyword"},
            "user_id": {"type": "keyword"},
            "doc_id": {"type": "keyword"},
            "matter.caseid": {"type": "keyword"},
            "matter.clientid": {"type": "keyword"},
            "matter.personal": {"type": "keyword"},
            "name_stored": {"type": "keyword"},
            "page": {"type": "integer"},
            "text": {"type": "text"},
            "vector": {"type": "knn_vector", "dimension": int(os.getenv("RAG_EMBED_DIM","3072")), "method": {"name":"hnsw","space_type":"l2"}},
            "created_at": {"type": "date"}
        }
    }
}

def ensure_index():
    cli = os_client()
    if not cli.indices.exists(INDEX):
        cli.indices.create(INDEX, body=MAPPING)
    return cli

def knn_search(cli: OpenSearch, query_vec, user_id: str, doc_ids=None, matter=None, k=24):
    must = [{"term": {"user_id": user_id}}]
    if doc_ids:
        must.append({"terms": {"doc_id": doc_ids}})
    elif matter:
        if matter.get("personal"):
            must.append({"term": {"matter.personal": matter["personal"]}})
        if matter.get("caseid"):
            must.append({"terms": {"matter.caseid": matter["caseid"]}})
        if matter.get("clientid"):
            must.append({"terms": {"matter.clientid": matter["clientid"]}})
    body = {
        "size": k,
        "query": {
            "script_score": {
                "query": {"bool": {"must": must}},
                "script": {
                    "source": "knn_score",
                    "lang": "knn",
                    "params": {
                        "field": "vector",
                        "query_value": query_vec,
                        "space_type": "l2"
                    }
                }
            }
        }
    }
    res = cli.search(index=INDEX, body=body)
    hits = res.get("hits", {}).get("hits", [])
    return [{"doc_id": h["_source"]["doc_id"], "name_stored": h["_source"]["name_stored"],
             "page": h["_source"].get("page"), "text": h["_source"]["text"], "score": h["_score"]} for h in hits]
