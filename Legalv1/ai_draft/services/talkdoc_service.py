import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
from PyPDF2 import PdfReader
import docx2txt

# In-memory storage (replace with database in production)
_documents = {}
_sessions = {}

def process_uploaded_file(filepath: str, filename: str) -> Dict[str, Any]:
    """Process an uploaded file and extract text content."""
    file_ext = os.path.splitext(filename)[1].lower()
    
    try:
        if file_ext == '.pdf':
            text = extract_text_from_pdf(filepath)
        elif file_ext in ['.doc', '.docx']:
            text = docx2txt.process(filepath)
        elif file_ext == '.txt':
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        # Create document metadata
        doc_id = str(uuid.uuid4())
        doc_metadata = {
            'id': doc_id,
            'name': filename,
            'path': filepath,
            'size': os.path.getsize(filepath),
            'uploaded_at': datetime.utcnow().isoformat(),
            'content': text[:10000],  # Store first 10k chars for preview
            'full_content': text
        }
        
        _documents[doc_id] = doc_metadata
        return doc_metadata
        
    except Exception as e:
        # Clean up the file if processing fails
        if os.path.exists(filepath):
            os.remove(filepath)
        raise e

def extract_text_from_pdf(filepath: str) -> str:
    """Extract text from a PDF file."""
    text = []
    with open(filepath, 'rb') as f:
        reader = PdfReader(f)
        for page in reader.pages:
            text.append(page.extract_text())
    return '\n'.join(text)

def create_chat_session(title: str, document_ids: List[str] = None) -> Dict[str, Any]:
    """Create a new chat session."""
    if document_ids is None:
        document_ids = []
        
    # Verify all documents exist
    for doc_id in document_ids:
        if doc_id not in _documents:
            raise ValueError(f"Document not found: {doc_id}")
    
    session_id = str(uuid.uuid4())
    session = {
        'id': session_id,
        'title': title,
        'document_ids': document_ids.copy(),
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
        'messages': []
    }
    
    _sessions[session_id] = session
    return session

def process_chat_message(session_id: str, message: str, document_ids: List[str] = None) -> Dict[str, Any]:
    """Process a chat message and generate a response."""
    if session_id not in _sessions:
        raise ValueError("Session not found")
    
    if document_ids is None:
        document_ids = _sessions[session_id]['document_ids']
    
    # Get relevant document content
    context = []
    for doc_id in document_ids:
        if doc_id in _documents:
            context.append(f"Document: {_documents[doc_id]['name']}\n{_documents[doc_id]['full_content']}")
    
    # TODO: Integrate with actual AI/ML model for response generation
    # This is a placeholder response
    response_text = f"You asked: {message}\n\n"
    if context:
        response_text += "I'll analyze the provided documents and get back to you with a detailed response."
    else:
        response_text += "Please upload documents to get more specific answers based on their content."
    
    # Add message to session history
    user_message = {
        'id': str(uuid.uuid4()),
        'content': message,
        'role': 'user',
        'timestamp': datetime.utcnow().isoformat()
    }
    
    bot_message = {
        'id': str(uuid.uuid4()),
        'content': response_text,
        'role': 'assistant',
        'timestamp': datetime.utcnow().isoformat()
    }
    
    _sessions[session_id]['messages'].extend([user_message, bot_message])
    _sessions[session_id]['updated_at'] = datetime.utcnow().isoformat()
    
    return {
        'response': response_text,
        'message_id': bot_message['id']
    }

def get_document(doc_id: str) -> Optional[Dict[str, Any]]:
    """Get a document by ID."""
    return _documents.get(doc_id)

def list_documents() -> List[Dict[str, Any]]:
    """List all documents."""
    return list(_documents.values())

def delete_document(doc_id: str) -> bool:
    """Delete a document."""
    if doc_id in _documents:
        # Remove file from disk
        doc = _documents[doc_id]
        if 'path' in doc and os.path.exists(doc['path']):
            try:
                os.remove(doc['path'])
            except Exception as e:
                print(f"Warning: Failed to delete file {doc['path']}: {e}")
        
        # Remove from documents
        del _documents[doc_id]
        
        # Remove from any sessions
        for session in _sessions.values():
            if doc_id in session['document_ids']:
                session['document_ids'].remove(doc_id)
        
        return True
    return False
