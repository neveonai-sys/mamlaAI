from celery import shared_task, group
# import requests
import os
import traceback
# from io import BytesIO
# import base64
import logging
# import datetime
from opensearchpy import OpenSearch
# import pymongo
import nltk
from nltk.corpus import stopwords
from collections import Counter
import re
from utilities.routes.utils import Handutilities
from core.init_clients import get_mongo_client

nltk.download('stopwords')
STOPWORDS = set(stopwords.words('english'))

logger = logging.getLogger('django')

opensearch_client = OpenSearch(
                                hosts=[{'host': 'localhost', 'port': 9200}],
                                http_compress=True,  # enables gzip compression for request bodies
                                use_ssl=False,
                                verify_certs=False,
                                )

def get_mongo_client_db():
    mongo = get_mongo_client()
    if not mongo:
        return ''
    db = mongo['legaldb']
    return db

@shared_task
def index_doc_celery():
    """Task to update content of documents."""
    try:
        page_size = 500  # Number of documents to process in each batch
        page_num = 0

        while True:
            documents = get_mongo_client_db()['draft_content_data'].find({}).skip(page_num * page_size).limit(page_size)
            documents_list = list(documents)
            if not documents_list:
                break  # Exit the loop if no more documents are found

            updated_docs = []
            obj = Handutilities()

            for doc in documents_list:
                try:
                    logger.info(f"--------- creating snippet ---> {doc.get('_id')}")
                    content = doc.get('content')
                    keywords = extract_keywords(content)
                    snippet = obj.openai_create_data(content)  # Modify content
                    doc['snippet'] = snippet  # Add updated content
                    doc['keywords'] = keywords
                    updated_docs.append(doc)
                except Exception as e:
                    logger.warning(f"Error processing doc {doc.get('_id')}: {str(e)}")
                    obj = Handutilities()  # Reset Handutilities object if necessary

            page_num += 1

        # Now index updated documents
        # index_documents.delay(updated_docs)
        task_group = group(index_documents.s( {
                    'filename': doc.get('filename'),
                    'file_path': doc.get('file_path'),
                    'draft_type': doc.get('draft_type'),
                    'keywords': doc.get('keywords'),
                    'snippet': doc.get('snippet'),
                    '_id': str(doc.get('_id'))
                })for doc in updated_docs)
                        # Trigger the tasks
        result = task_group.apply_async()
    except Exception as err:
        logger.error(traceback.format_exc())

@shared_task
def index_documents(doc):
    """Task to index updated documents in OpenSearch."""
    try:
        # for doc in updated_docs:
        document_data = {
                    'filename': doc.get('filename'),
                    'file_path': doc.get('file_path'),
                    'draft_type': doc.get('draft_type'),
                    'keywords': doc.get('keywords'),
                    'snippet': doc.get('snippet')
                }
                # Index document in OpenSearch
        opensearch_client.index(
            index=os.getenv("OPENSEARCH_INDEX_PREFIX", "") + "documents",  # The name of the OpenSearch index
            body=document_data,
                id=doc.get('_id') # Use MongoDB's _id as the document ID
        )
        logger.info(f"Indexed document: {doc['filename']}")
    except Exception as err:
        logger.error(traceback.format_exc())

# Function to clean and extract keywords from the content
def extract_keywords(content, num_keywords=50):
    # Remove non-alphabetic characters and tokenize
    tokens = re.findall(r'\b\w+\b', content.lower())
    
    # Remove stopwords and short words, then count frequency
    filtered_tokens = [word for word in tokens if word not in STOPWORDS and len(word) > 2]
    frequency = Counter(filtered_tokens)
    
    # Extract the most common unique keywords
    keywords = [word for word, count in frequency.most_common(num_keywords)]
    return keywords