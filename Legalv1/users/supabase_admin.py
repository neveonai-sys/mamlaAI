from supabase import create_client
from Legalv1 import settings
from gotrue.types import AdminUserAttributes
import traceback
import logging
logger = logging.getLogger('django')

def get_supabase_admin():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

def find_user_by_username(username: str):
    """
    Use admin.list_users() and search for a user whose user_metadata.username == the given username.
    Returns the user dict if found, else None.
    """
    try:
        sb = get_supabase_admin()
        result = sb.auth.admin.list_users()
        print(f"find_user_by_username -- {type(result)} --> {result}",flush=True)
        # result["users"] is a list of user objects
        if len(result):
            users = result[0].get('users', [])
            for usr in result["users"]:
                if usr.get("user_metadata", {}).get("username", "").lower() == username.lower():
                    return usr
        return None
    except Exception as err:
        logger.error(traceback.format_exc())
        return None

def admin_update_password(user_id: str, new_password: str):
    """
    Calls supabase.auth.admin.update_user_by_id(...) with a new password.
    """
    sb = get_supabase_admin()
    attrs = AdminUserAttributes(password=new_password)
    result = sb.auth.admin.update_user_by_id(user_id, attrs)
    return result
