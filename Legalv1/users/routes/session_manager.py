# from pymongo import MongoClient
from bson.objectid import ObjectId
import os
import uuid
import traceback
import datetime
import requests
from .encryption import encrypt_data, decrypt_data
import logging
from core.init_clients import get_mongo_client, get_mongo_db
# from users.routes.usermetadata import Handleusermetadata

logger = logging.getLogger('django')

class SessionManager:
    def __init__(self):
        pass

    def get_mongo_client_db(self):
        mongo = get_mongo_client()
        if not mongo:
            return ''
        db = get_mongo_db()
        return db

    def create_session(self, user_id, access_token, refresh_token, ip_address, location, device_type):
        try:
            device_id = str(uuid.uuid4())
            encrypted_ip = encrypt_data(ip_address)
            encrypted_location = encrypt_data(location)
            encrypted_device = encrypt_data(device_type)
            session = {
                'user_id': user_id,  # Keep as string
                'access_token': access_token,
                'refresh_token': refresh_token,
                'device_id': device_id,  # New field
                'ip_address': encrypted_ip,
                'location': encrypted_location,
                'device_type': encrypted_device,
                'created_at': datetime.datetime.now(datetime.timezone.utc),
                'last_activity': datetime.datetime.now(datetime.timezone.utc)
            }
            # Check the number of active sessions
            active_sessions = list(self.get_mongo_client_db()['sessions'].find({'user_id': user_id}).sort('created_at', 1))
            if len(active_sessions) >= 4:
                
                ## not so usefull here as from supbase we can only delete tokens for latest one not the oldest one
                # supabase_obj = Handleusermetadata()
                # supabase_obj.sign_out_supabase({ "scope": "local" })

                # Invalidate the oldest session(s)
                sessions_to_invalidate = active_sessions[:len(active_sessions) - 3]  # Keep last 3, remove oldest
                for s in sessions_to_invalidate:
                    self.get_mongo_client_db()['sessions'].delete_one({'_id': s['_id']})
                    logger.info(f"Invalidated old session for user_id: {user_id}, device_id: {s['device_id']}")
            # Insert the new session
            self.get_mongo_client_db()['sessions'].insert_one(session)
            logger.debug(f"Session created for user_id: {user_id}, device_id: {device_id}")
            return device_id
        except Exception as e:
            logger.error(f"Error creating session: {traceback.format_exc()}")
            raise
    '''
    def create_session(self, user_id, access_token, refresh_token, ip_address, location, device_type):
        session = {
            'user_id': user_id,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'ip_address': encrypt_data(ip_address),
            'location': encrypt_data(location),
            'device_type': encrypt_data(device_type),
            'created_at': datetime.datetime.now(datetime.timezone.utc),
            'last_activity': datetime.datetime.now(datetime.timezone.utc)
        }
        try:
            result = self.get_mongo_client_db()['sessions'].insert_one(session)
            return str(result.inserted_id)  # Return session ID
        except Exception as e:
            logger.error(f"Failed to create session: {traceback.format_exc()}")
            raise
    '''
        
    def validate_access_token(self, token):
        try:
            session = self.get_mongo_client_db()['sessions'].find_one({'access_token': token})
            if session:
                # Update last_activity
                self.get_mongo_client_db()['sessions'].update_one(
                    {'_id': session['_id']},
                    {'$set': {'last_activity': datetime.datetime.now(datetime.timezone.utc)}}
                )
                return str(session['user_id'])
            return None
        except Exception as e:
            logger.error(f"Failed to validate access token: {traceback.format_exc()}")
            return None
    
    def validate_refresh_token(self, refresh_token):
        try:
            session = self.get_mongo_client_db()['sessions'].find_one({'refresh_token': refresh_token})
            if session:
                # Update last_activity
                self.get_mongo_client_db()['sessions'].update_one(
                    {'_id': session['_id']},
                    {'$set': {'last_activity': datetime.datetime.now(datetime.timezone.utc)}}
                )
                return str(session['user_id'])
            return None
        except Exception as e:
            logger.error(f"Failed to validate refresh token: {traceback.format_exc()}")
            return None
        
    def validate_session(self, token):
        try:
            session = self.get_mongo_client_db()['sessions'].find_one({'access_token': token})
            if session:
                # Update last_activity
                self.get_mongo_client_db()['sessions'].update_one(
                    {'_id': session['_id']},
                    {'$set': {'last_activity': datetime.datetime.now(datetime.timezone.utc)}}
                )
                decrypted_user_id = str(session['user_id'])
                return decrypted_user_id
            return None
        except Exception as e:
            logger.error(f"Error validating session: {traceback.format_exc()}")
            return None
    
    def invalidate_session(self, token):
        """only single token"""
        try:
            self.get_mongo_client_db()['sessions'].delete_one({'access_token': token})
        except Exception as e:
            logger.error(f"Failed to invalidate session: {traceback.format_exc()}")
            raise

    def invalidate_session_by_id(self, session_id):
        try:
            self.get_mongo_client_db()['sessions'].delete_one({'_id': ObjectId(session_id)})
        except Exception as e:
            logger.error(f"Failed to invalidate session by id: {traceback.format_exc()}")
            raise
        
    def invalidate_sessions(self, user_id):
        """all sessions for the user"""
        try:
            self.get_mongo_client_db()['sessions'].delete_many({'user_id': user_id})
        except Exception as e:
            logger.error(f"Failed to invalidate sessions: {traceback.format_exc()}")
            raise
    
    def invalidate_session_by_session_id(self, session_id, user_id):
        try:
            result = self.get_mongo_client_db()['sessions'].delete_one({'_id': ObjectId(session_id), 'user_id': user_id})
            if result.deleted_count > 0:
                logger.info(f"Session {session_id} invalidated for user_id: {user_id}")
                return {'message': 'Session invalidated successfully.'}
            else:
                logger.warning(f"No session found to invalidate for session_id: {session_id} and user_id: {user_id}")
                return {'error': 'Session not found or already invalidated.'}
        except Exception as e:
            logger.error(f"Error invalidating session by session_id: {traceback.format_exc()}")
            return {'error': 'Failed to invalidate session.'}

    # def get_sessions(self, user_id):
    #     try:
    #         sessions = list(self.get_mongo_client_db()['sessions'].find({'user_id': user_id}))
    #         # Decrypt sensitive data
    #         for session in sessions:
    #             session['ip_address'] = decrypt_data(session['ip_address'])
    #             session['location'] = decrypt_data(session['location'])
    #             session['device_type'] = decrypt_data(session['device_type'])
    #         logger.debug(f"Retrieved {len(sessions)} sessions for user_id: {user_id}")
    #         return sessions
    #     except Exception as e:
    #         logger.error(f"Error fetching sessions: {traceback.format_exc()}")
    #         return []
    #     except Exception as e:
    #         logger.error(f"Error decrypting session data: {traceback.format_exc()}")
    #         return []

    def get_user_by_id(self, user_id):
        try:
            logger.debug(f"Fetching user with user_id: {user_id}")
            user = self.get_mongo_client_db()['user_details'].find_one({'user_id': user_id})  # Assuming 'user_id' is the field name
            if user:
                logger.debug(f"User found: {user}")
                return user
            logger.warning(f"No user found with user_id: {user_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching user by ID: {traceback.format_exc()}")
            return None

    def update_last_activity(self, token):
        try:
            result = self.get_mongo_client_db()['sessions'].update_one(
                {'access_token': token},
                {'$set': {'last_activity': datetime.datetime.now(datetime.timezone.utc)}}
            )
            if result.matched_count:
                logger.debug(f"Updated last_activity for token: {token}")
            else:
                logger.warning(f"No session found to update for token: {token}")
        except Exception as e:
            logger.error(f"Error updating last_activity: {traceback.format_exc()}")
    
    def get_sessions(self, user_id):
        try:
            sessions = self.get_mongo_client_db()['sessions'].find({'user_id': user_id})
            session_info = []
            for session in sessions:
                session_info.append({
                    'session_id': str(session['_id']),
                    'ip_address': decrypt_data(session['ip_address']),
                    'location': decrypt_data(session['location']),
                    'device_type': decrypt_data(session['device_type']),
                    'login_time': session['created_at'],
                    'last_activity': session['last_activity'],
                    'access_token': session['access_token']
                })
            return session_info
        except Exception as e:
            logger.error(f"Failed to get sessions: {traceback.format_exc()}")
            return []
    
    def remove_inactive_sessions(self, inactivity_threshold=15):
        threshold_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=inactivity_threshold)
        try:
            result = self.get_mongo_client_db()['sessions'].delete_many({'last_activity': {'$lt': threshold_time}})
            logger.info(f"Removed {result.deleted_count} inactive sessions.")
        except Exception as e:
            logger.error(f"Failed to remove inactive sessions: {traceback.format_exc()}")

    def get_client_ip(self, request):
        """
        Retrieve client IP address from request.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def get_device_type(self, user_agent):
        """
        Determine device type using the user_agents library.
        """
        if user_agent.is_mobile:
            return 'Mobile'
        elif user_agent.is_tablet:
            return 'Tablet'
        elif user_agent.is_pc:
            return 'Desktop'
        else:
            return 'Other'

    def get_location_from_ip(self, ip_address):
        """
        Get approximate location from IP address using a geo-IP service.
        """
        # Implement using a service like ipstack, ipinfo, etc.
        # Example using ipinfo.io
        try:
            response = requests.get(f'https://ipinfo.io/{ip_address}/json')
            if response.status_code == 200:
                data = response.json()
                return f"{data.get('city', '')}, {data.get('country', '')}"
            else:
                return 'Unknown'
        except Exception:
            return 'Unknown'
