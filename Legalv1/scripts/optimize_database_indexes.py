"""
Comprehensive database optimization for MongoDB collections.
Run this script to ensure all indexes are created for optimal performance.
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Legalv1.settings')
django.setup()

from pymongo import ASCENDING, DESCENDING, TEXT, IndexModel
from core.init_clients import get_mongo_client, get_mongo_db
import logging

logger = logging.getLogger('django')


def optimize_aidrafts_indexes():
    """Optimize indexes for AI drafts collection"""
    mongo = get_mongo_client()
    if not mongo:
        logger.error("MongoDB client not available")
        return False
    
    collection = get_mongo_db()['aidrafts_complete_data']
    
    # Define comprehensive indexes (excluding text index that conflicts with Bengali data)
    indexes = [
        IndexModel([('user_id', ASCENDING)], name='user_id_idx'),
        IndexModel([('user_id', ASCENDING), ('created_on', DESCENDING)], name='user_created_idx'),
        IndexModel([('user_id', ASCENDING), ('status', ASCENDING)], name='user_status_idx'),
        IndexModel([('draft_for.personal', ASCENDING)], name='personal_idx'),
        IndexModel([('draft_for.caseid', ASCENDING)], name='caseid_idx'),
        IndexModel([('draft_for.clientid', ASCENDING)], name='clientid_idx'),
        IndexModel([('draft_for.caseid_with_clientid', ASCENDING)], name='caseid_clientid_idx'),
        IndexModel([('created_on', DESCENDING)], name='created_on_idx'),
        IndexModel([('last_updated_on', DESCENDING)], name='last_updated_idx'),
        IndexModel([('status', ASCENDING), ('last_updated_on', DESCENDING)], name='status_updated_idx'),
        # Text index on draft_name — language_override set to '_text_lang_override' (a field that never
        # exists in our documents) so MongoDB never tries to interpret our 'language' field as a
        # MongoDB text-search language token (which would reject values like 'Hindi', 'Bengali', etc.)
        IndexModel(
            [('draft_name', TEXT)],
            name='draft_name_text_index',
            default_language='english',
            language_override='_text_lang_override'
        ),
    ]
    
    try:
        # Drop existing indexes except _id_ before recreating
        existing_indexes = list(collection.list_indexes())
        for idx in existing_indexes:
            if idx['name'] != '_id_':
                try:
                    collection.drop_index(idx['name'])
                except Exception:
                    pass  # Index might not exist
        
        collection.create_indexes(indexes)
        logger.info("AI drafts indexes optimized successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating AI drafts indexes: {e}")
        return False


def optimize_talkdoc_indexes():
    """Optimize indexes for TalkDoc RAG collections"""
    mongo = get_mongo_client()
    if not mongo:
        return False
    
    db = get_mongo_db()
    
    # RAG documents indexes
    doc_indexes = [
        IndexModel([('user_id', ASCENDING), ('created_at', DESCENDING)], name='user_created_idx'),
        IndexModel([('user_id', ASCENDING), ('status', ASCENDING)], name='user_status_idx'),
        IndexModel([('matter.personal', ASCENDING)], name='matter_personal_idx'),
        IndexModel([('matter.caseid', ASCENDING)], name='matter_caseid_idx'),
        IndexModel([('matter.clientid', ASCENDING)], name='matter_clientid_idx'),
        IndexModel([('status', ASCENDING)], name='status_idx'),
        IndexModel([('name_original', TEXT)], name='name_text_idx'),
    ]
    
    # RAG chat sessions indexes
    session_indexes = [
        IndexModel([('user_id', ASCENDING), ('deleted', ASCENDING), ('last_message_at', DESCENDING)], 
                   name='user_deleted_lastmsg_idx'),
        IndexModel([('user_id', ASCENDING), ('has_docs', ASCENDING)], name='user_hasdocs_idx'),
        IndexModel([('doc_ids', ASCENDING)], name='docids_idx'),
    ]
    
    # RAG messages indexes
    message_indexes = [
        IndexModel([('session_id', ASCENDING), ('created_at', ASCENDING)], name='session_created_idx'),
        IndexModel([('role', ASCENDING)], name='role_idx'),
    ]
    
    # RAG chunks indexes (for vector search)
    chunk_indexes = [
        IndexModel([('doc_id', ASCENDING)], name='docid_idx'),
        IndexModel([('session_id', ASCENDING)], name='sessionid_idx'),
    ]
    
    try:
        db['rag_documents'].create_indexes(doc_indexes)
        db['rag_chat_sessions'].create_indexes(session_indexes)
        db['rag_messages'].create_indexes(message_indexes)
        db['rag_chunks'].create_indexes(chunk_indexes)
        logger.info("TalkDoc indexes optimized successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating TalkDoc indexes: {e}")
        return False


def optimize_user_indexes():
    """Optimize indexes for user-related collections"""
    mongo = get_mongo_client()
    if not mongo:
        return False
    
    db = get_mongo_db()
    
    # User sessions indexes
    session_indexes = [
        IndexModel([('user_id', ASCENDING), ('is_active', ASCENDING)], name='user_active_idx'),
        IndexModel([('session_token', ASCENDING)], name='session_token_idx', unique=True, sparse=True),
        IndexModel([('last_activity', DESCENDING)], name='last_activity_idx'),
        IndexModel([('created_at', DESCENDING)], name='created_at_idx'),
    ]
    
    try:
        if 'user_sessions' in db.list_collection_names():
            db['user_sessions'].create_indexes(session_indexes)
            logger.info("User sessions indexes optimized successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating user indexes: {e}")
        return False


def optimize_all_indexes():
    """Run all index optimizations"""
    logger.info("Starting database index optimization...")
    
    results = {
        'aidrafts': optimize_aidrafts_indexes(),
        'talkdoc': optimize_talkdoc_indexes(),
        'users': optimize_user_indexes(),
    }
    
    success_count = sum(1 for v in results.values() if v)
    logger.info(f"Index optimization complete: {success_count}/{len(results)} collections optimized")
    
    return all(results.values())


if __name__ == '__main__':
    optimize_all_indexes()
