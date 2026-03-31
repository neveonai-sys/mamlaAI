import os
import pymongo
import traceback
from opensearchpy import OpenSearch
from search_facility.task import index_doc_celery
# from celery import group, chord
import logging
from bson.objectid import ObjectId
from core.init_clients import get_mongo_client

logger = logging.getLogger('django')

class Handlesearch:
    def __init__(self):
        self.opensearch_client = OpenSearch(
                                    hosts=[{'host': 'localhost', 'port': 9200}],
                                    http_compress=True,  # enables gzip compression for request bodies
                                    use_ssl=False,
                                    verify_certs=False,
                                )
        
    def get_mongo_client_db(self):
        mongo = get_mongo_client()
        if not mongo:
            return ''
        db = mongo['legaldb']
        return db

    def index_document_opensearch(self):
        try:
            index_doc_celery.delay()
            
            return {"mssg":"Indexing in Progess"}
        except Exception as err:
            logger.error(traceback.format_exc())
            return {"mssg":err}

    def search_document_by_index(self, query_string):
        try:
            response = self.opensearch_client.search(
            index=os.getenv("OPENSEARCH_INDEX_PREFIX", "") + "documents",
            body={
                "query": {
                    "multi_match": {
                        "query": query_string,
                        "fields": ["keywords", "filename", "snippet"]  # Search within content and filename
                    }
                }
                }
            )
            
            # Extract and return the matching documents
            hits = response['hits']['hits']
            results = []
            for hit in hits:
                # Extract the MongoDB _id from the first matching result
                # logger.info(f"?????????????????????????????? -------- hit snippet: {hit}\n")
                mongo_doc_id = hit['_id']
                if hit['_score']:
                    mongo_doc_id = ObjectId(mongo_doc_id)
                    # Fetch the full document from MongoDB using the MongoDB _id
                    full_document = self.get_mongo_client_db()['draft_content_data'].find_one({"_id": mongo_doc_id})
                    logger.info(f"?????????????????????????????? -------- full_document snippet: {full_document.get('filename')}\n")
                    if len(full_document):
                        source = hit['_source']
                        results.append({
                            'filename': source['filename'],
                            'file_path': source['file_path'],
                            'draft_type': source['draft_type'],
                            'content_snippet': source['snippet'],  # Show a snippet of the content
                            'score': hit['_score']  # Relevance score
                        })
            if len(results):
                results.sort(key=lambda x:x['score'], reverse=True)
            
            return results
        except Exception as err:
            logger.error(traceback.format_exc())


    def search_document_by_filename_and_draft_type(self, filename, draft_type):
        try:
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"filename": filename}},
                            {"match": {"draft_type": draft_type}}
                        ]
                    }
                }
            }
            # logger.info(f"hit found contengt ----- query == {query} ")
            # Execute the search query
            response = self.opensearch_client.search(
                index=os.getenv("OPENSEARCH_INDEX_PREFIX", "") + "documents",  # Name of your OpenSearch index
                body=query
            )

            # logger.info(f"hit found contengt ----- response == {response} ")
            # Check the results
            hits = response['hits']['hits']
            content = []
            logger.info(f"hit found contengt -----  search_document_by_filename_and_draft_type ====> {hits}")
            if hits:
                mongo_doc_id = hits[0]['_id']
                mongo_doc_id = ObjectId(mongo_doc_id)
                full_document = self.get_mongo_client_db()['draft_content_data'].find_one({"_id": mongo_doc_id})

                content = full_document.get('content')
            return content
        except Exception as err:
            logger.error(traceback.format_exc())
            return []