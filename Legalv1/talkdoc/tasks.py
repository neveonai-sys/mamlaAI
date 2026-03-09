import io, os, json
import logging
from datetime import datetime
from bson import ObjectId
from celery import shared_task
from core.init_clients import get_mongo_client
# from .storage import get_signed_url
from .search import ensure_index
from .chunk import split_into_chunks
from ai_draft.routes.creatupdateAIdrafts import CreateupdatefetchAIdrafts  # reuse your text extractor
import requests

EMBED_MODEL = os.getenv("RAG_EMBED_MODEL", "text-embedding-3-large")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def _mongo():
    return get_mongo_client()['legaldb']

def embed_texts(texts):
    """
    Lightweight OpenAI embeddings call. Replace with your existing client if preferred.
    """
    from openai import OpenAI
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]

@shared_task(bind=True, max_retries=3)
def ingest_document(self, doc_id: str):
    logger = logging.getLogger('django')
    db = _mongo()
    doc = db['rag_documents'].find_one({"_id": ObjectId(doc_id)})
    if not doc:
        logger.error(f"[INGEST] Document {doc_id} not found in DB.")
        return

    import traceback
    logger.info(f"[INGEST] Starting ingestion for doc_id: {doc_id}")
    try:
        # 1) download from GridFS
        file_id = doc["storage"].get("file_id")
        if not file_id:
            logger.error(f"[INGEST][ERROR] No file_id found in document storage for doc_id: {doc_id}")
            raise Exception("No file_id found in document storage")
        logger.info(f"[INGEST] GridFS file_id: {file_id} type: {type(file_id)}")
        # Ensure file_id is ObjectId
        if not isinstance(file_id, ObjectId):
            try:
                file_id = ObjectId(file_id)
            except Exception as id_err:
                logger.error(f"[INGEST][ERROR] Could not convert file_id to ObjectId: {id_err}")
                db['rag_documents'].update_one({"_id": doc["_id"]},
                    {"$set": {"status": "failed", "error": f"objectid: {id_err}", "updated_at": datetime.utcnow()}})
                raise Exception(f"Could not convert file_id to ObjectId: {id_err}")
        from gridfs import GridFS
        gridfs_api = GridFS(get_mongo_client()["legaldb"], collection="talkdoc_files")
        try:
            file_obj = gridfs_api.get(ObjectId(file_id))
            logger.info(f"[INGEST] Successfully fetched file from GridFS for doc_id: {doc_id}")
        except Exception as gridfs_err:
            logger.error(f"[INGEST][ERROR] File with id {file_id} not found in GridFS: {gridfs_err}\n{traceback.format_exc()}")
            db['rag_documents'].update_one({"_id": doc["_id"]},
                {"$set": {"status": "failed", "error": f"gridfs: {gridfs_err}\n{traceback.format_exc()}", "updated_at": datetime.utcnow()}})
            raise Exception(f"File with id {file_id} not found in GridFS: {gridfs_err}")
        data = io.BytesIO(file_obj.read())

        # 2) extract text directly
        text = ""
        filename = doc["name_stored"]
        try:
            logger.info(f"[INGEST] Extracting text from file: {filename}")
            if filename.lower().endswith(".docx"):            
                GridFS(get_mongo_client()["legaldb"], collection="talkdoc_files")
                from docx import Document
                document = Document(data)
                text = "\n".join([p.text for p in document.paragraphs])
            elif filename.lower().endswith(".pdf"):
                import pdfplumber
                with pdfplumber.open(data) as pdf:
                    text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            elif filename.lower().endswith(".txt"):
                text = data.getvalue().decode("utf-8", errors="ignore")
            logger.info(f"[INGEST] Text extraction complete. Length: {len(text)} chars")
        except Exception as extract_err:
            logger.error(f"[INGEST][ERROR] Text extraction failed: {extract_err}\n{traceback.format_exc()}")
            db['rag_documents'].update_one({"_id": doc["_id"]},
                                           {"$set": {"status": "failed", "error": f"extract: {extract_err}\n{traceback.format_exc()}", "updated_at": datetime.utcnow()}})
            raise

        # 3) chunk
        try:
            logger.info(f"[INGEST] Chunking text for doc_id: {doc_id}")
            chunks = split_into_chunks(text, max_tokens=700, overlap=80)
            logger.info(f"[INGEST] Chunking complete. Num chunks: {len(chunks)}")
        except Exception as chunk_err:
            logger.error(f"[INGEST][ERROR] Chunking failed: {chunk_err}\n{traceback.format_exc()}")
            db['rag_documents'].update_one({"_id": doc["_id"]},
                                           {"$set": {"status": "failed", "error": f"chunk: {chunk_err}\n{traceback.format_exc()}", "updated_at": datetime.utcnow()}})
            raise

        # 4) embed
        try:
            logger.info(f"[INGEST] Embedding chunks for doc_id: {doc_id}")
            vecs = embed_texts([c["text"] for c in chunks])
            logger.info(f"[INGEST] Embedding complete. Num vectors: {len(vecs)}")
        except Exception as embed_err:
            logger.error(f"[INGEST][ERROR] Embedding failed: {embed_err}\n{traceback.format_exc()}")
            db['rag_documents'].update_one({"_id": doc["_id"]},
                                           {"$set": {"status": "failed", "error": f"embed: {embed_err}\n{traceback.format_exc()}", "updated_at": datetime.utcnow()}})
            raise

        # 5) index to OpenSearch
        try:
            logger.info(f"[INGEST] Indexing chunks to OpenSearch for doc_id: {doc_id}")
            cli = ensure_index()
            actions = []
            for i, c in enumerate(chunks):
                body = {
                    "chunk_id": f"{doc_id}_{i}",
                    "user_id": doc["user_id"],
                    "doc_id": str(doc["_id"]),
                    "matter": doc.get("matter", {}),
                    "name_stored": doc["name_stored"],
                    "page": None,
                    "text": c["text"],
                    "vector": vecs[i],
                    "created_at": datetime.utcnow()
                }
                actions.append({"index": {"_index": os.getenv("RAG_OS_INDEX","rag_chunks_v1")}})
                actions.append(body)
            if actions:
                cli.bulk(body=actions, refresh=True)
            logger.info(f"[INGEST] Indexing complete for doc_id: {doc_id}")
        except Exception as index_err:
            logger.error(f"[INGEST][ERROR] Indexing failed: {index_err}\n{traceback.format_exc()}")
            db['rag_documents'].update_one({"_id": doc["_id"]},
                                           {"$set": {"status": "failed", "error": f"index: {index_err}\n{traceback.format_exc()}", "updated_at": datetime.utcnow()}})
            raise

        db['rag_documents'].update_one({"_id": doc["_id"]},
                                       {"$set": {"status": "indexed", "pages": None, "updated_at": datetime.utcnow()}})
        logger.info(f"[INGEST] Ingestion complete for doc_id: {doc_id}")
    except Exception as e:
        logger.error(f"[INGEST][FATAL] Ingestion failed for doc_id: {doc_id}: {e}\n{traceback.format_exc()}")
        db['rag_documents'].update_one({"_id": doc["_id"]},
                                       {"$set": {"status": "failed", "error": f"fatal: {e}\n{traceback.format_exc()}", "updated_at": datetime.utcnow()}})
        raise
