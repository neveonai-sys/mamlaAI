# from core.init_clients import get_mongo_client, get_mongo_db
# mongo = get_mongo_client()

# db = get_mongo_db()

# user_collection = db['user_details']
# state_district_court_collection = db["state_district_court_data"]
# existing_indexes = state_district_court_collection.index_information()
# if "state_name" not in existing_indexes:
#     state_district_court_collection.create_index([("state_name", 1)])
# if "district_name" not in existing_indexes:
#     state_district_court_collection.create_index([("district_name", 1)])
# if "court_name" not in existing_indexes:
#     state_district_court_collection.create_index([("court_name", 1)])