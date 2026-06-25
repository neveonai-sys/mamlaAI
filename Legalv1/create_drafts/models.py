# from core.init_clients import get_mongo_client, get_mongo_db

# def get_user_related_documents():
#     mongo = get_mongo_client()
#     if mongo is None:
#         raise Exception("Mongo client is not initialized.")
#     db = get_mongo_db()

#     # user_collection = db['users_user']
#     draft_collection = db['drafts_metadata'] # has required fields
#     draft_db_collection = db['draft_content_data'] # has draft content as text
#     user_draft_collection = db['user_draft_data'] # keep auto-saved drafts

#     existing_indexes = user_draft_collection.index_information()
#     if "user_id" not in existing_indexes:
#         user_draft_collection.create_index([("user_id", 1)])