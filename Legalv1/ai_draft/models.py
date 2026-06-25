# from pymongo import ASCENDING, DESCENDING
# from core.init_clients import get_mongo_client, get_mongo_db

# mongo = get_mongo_client()
# db = get_mongo_db()

# class Session:
#     collection = db['aidrafts_complete_data']
#     existing_indexes = collection.index_information()
#     if "user_id" not in existing_indexes:
#         # user_collection.create_index([("user_id", 1)])
#         collection.create_index([('user_id', 1)])
#     if "draft_name_index" not in existing_indexes:
#         collection.create_index([('saved_drafts.draft_name', ASCENDING)], name='draft_name_index')
#     if "personal_index" not in existing_indexes:
#         collection.create_index([('draft_for.personal', ASCENDING)], name='personal_index')
#     if "caseid_index" not in existing_indexes:
#         collection.create_index([('draft_for.caseid', ASCENDING)], name='caseid_index')
#     if "clientid_index" not in existing_indexes:
#         collection.create_index([('draft_for.clientid', ASCENDING)], name='clientid_index')
#     if "caseid_with_clientid_index" not in existing_indexes:
#         collection.create_index([('draft_for.caseid_with_clientid', ASCENDING)], name='caseid_with_clientid_index')
#     if "created_on_index" not in existing_indexes:
#         collection.create_index([('created_on', DESCENDING)], name='created_on_index')
#     if "last_updated_on_index" not in existing_indexes:
#         collection.create_index([('last_updated_on', DESCENDING)], name='last_updated_on_index')