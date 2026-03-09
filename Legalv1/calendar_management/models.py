# # from mongo_connection import db
# from core.init_clients import get_mongo_client

# mongo = get_mongo_client()
# db = mongo['legaldb']
# user_collection = db['user_details']

# existing_indexes = user_collection.index_information()
# if "user_id" not in existing_indexes:
#     user_collection.create_index([("user_id", 1)])