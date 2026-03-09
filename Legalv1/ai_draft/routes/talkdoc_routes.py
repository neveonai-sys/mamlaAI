import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from ..services.talkdoc_service import (
    process_uploaded_file,
    create_chat_session,
    process_chat_message,
    get_document,
    list_documents,
    delete_document,
)

bp = Blueprint('talkdoc', __name__, url_prefix='/api/talkdoc')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'pdf', 'doc', 'docx', 'txt'}

@bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        
        # Save file to uploads directory
        uploads_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'talkdoc')
        os.makedirs(uploads_dir, exist_ok=True)
        filepath = os.path.join(uploads_dir, f"{file_id}_{filename}")
        file.save(filepath)
        
        # Process the document
        try:
            doc_metadata = process_uploaded_file(filepath, filename)
            return jsonify({
                'id': file_id,
                'name': filename,
                'uploaded_at': datetime.utcnow().isoformat(),
                'metadata': doc_metadata
            }), 201
        except Exception as e:
            current_app.logger.error(f"Error processing file: {str(e)}")
            return jsonify({'error': 'Failed to process document'}), 500
    
    return jsonify({'error': 'File type not allowed'}), 400

@bp.route('/sessions', methods=['POST'])
def create_session():
    data = request.get_json()
    if not data or 'title' not in data:
        return jsonify({'error': 'Title is required'}), 400
    
    session = create_chat_session(data['title'], data.get('document_ids', []))
    return jsonify(session), 201

@bp.route('/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    # TODO: Implement session retrieval
    return jsonify({'error': 'Not implemented'}), 501

@bp.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    if not data or 'session_id' not in data or 'message' not in data:
        return jsonify({'error': 'Session ID and message are required'}), 400
    
    try:
        response = process_chat_message(
            session_id=data['session_id'],
            message=data['message'],
            document_ids=data.get('document_ids', [])
        )
        return jsonify(response)
    except Exception as e:
        current_app.logger.error(f"Error processing chat message: {str(e)}")
        return jsonify({'error': 'Failed to process message'}), 500

@bp.route('/files', methods=['GET'])
def list_files():
    try:
        documents = list_documents()
        return jsonify({'files': documents})
    except Exception as e:
        current_app.logger.error(f"Error listing files: {str(e)}")
        return jsonify({'error': 'Failed to list documents'}), 500

@bp.route('/files/<file_id>', methods=['GET'])
def get_file(file_id):
    try:
        document = get_document(file_id)
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        return jsonify(document)
    except Exception as e:
        current_app.logger.error(f"Error getting file: {str(e)}")
        return jsonify({'error': 'Failed to retrieve document'}), 500

@bp.route('/files/<file_id>', methods=['DELETE'])
def delete_file(file_id):
    try:
        success = delete_document(file_id)
        if not success:
            return jsonify({'error': 'Document not found'}), 404
        return jsonify({'message': 'Document deleted successfully'})
    except Exception as e:
        current_app.logger.error(f"Error deleting file: {str(e)}")
        return jsonify({'error': 'Failed to delete document'}), 500
