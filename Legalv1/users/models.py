# from core.init_clients import get_mongo_client, get_mongo_db

# def get_user_related_documents():
#     mongo = get_mongo_client()
#     if mongo is None:
#         raise Exception("Mongo client is not initialized.")
#     db = get_mongo_db()
#     user_collection = db['user_details']
#     feedback_collection = db['user_feedback']
#     sessions_collection = db['sessions']
#     signup_tokens_collection = db['signup_tokens']
#     temporary_signup_otp_verfication = db['signup_otp_store']
#     state_district_court_collection = db["state_district_court_data"]