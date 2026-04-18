
import os
from core.init_clients import get_mongo_client, get_mongo_db
import gridfs

def upload_bytes(user_id: str, matter: dict, filename: str, data: bytes) -> dict:
    db = get_mongo_db()
    fs = gridfs.GridFS(db, collection='talkdoc_files')
    file_id = fs.put(data, filename=filename, user_id=user_id, matter=matter)
    return {"file_id": str(file_id), "filename": filename, "user_id": user_id, "matter": matter}
