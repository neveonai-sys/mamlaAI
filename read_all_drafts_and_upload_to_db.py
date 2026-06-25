import os
import pymongo
from datetime import datetime
import PyPDF2
import docx
from striprtf.striprtf import rtf_to_text
import pypandoc
from multiprocessing import Pool

# MongoDB setup
uri = ""
client = pymongo.MongoClient(uri)
db = client['legaldb']
draft_db_collection = db['draft_content_data']

# Function to extract text from PDF
def extract_pdf(file_path):
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
        return ""

# Function to extract text from DOCX
def extract_docx(file_path):
    try:
        doc = docx.Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    except Exception as e:
        print(f"Error reading DOCX {file_path}: {e}")
        return ""

# Function to extract text from RTF
def extract_rtf(file_path):
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        return rtf_to_text(content)
    except Exception as e:
        print(f"Error reading RTF {file_path}: {e}")
        return ""

# Function to extract text from DOC (using pypandoc)
def extract_doc(file_path):
    try:
        return pypandoc.convert_file(file_path, 'plain')
    except Exception as e:
        print(f"Error reading DOC {file_path}: {e}")
        return ""

# Function to extract text from TXT
def extract_txt(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading TXT {file_path}: {e}")
        return ""

# Main function to process files in a folder
def process_file(file_path):
    file_extension = file_path.split('.')[-1].lower()

    # Extract content based on file type
    if file_extension == 'pdf':
        content = extract_pdf(file_path)
    elif file_extension == 'docx':
        content = extract_docx(file_path)
    elif file_extension == 'doc':
        content = extract_doc(file_path)
    elif file_extension == 'rtf':
        content = extract_rtf(file_path)
    elif file_extension == 'txt':
        content = extract_txt(file_path)
    else:
        print(f"Unsupported file format: {file_path}")
        return

    # Store metadata and extracted content in MongoDB
    if content:
        file_path_name = file_path.replace('/home/pronoys/products/AiAdalat/draftdocs/','')
        draft_type = file_path_name.split('/')[0]
        draft_path = '/'.join(file_path_name.split('/')[1:])
        document = {
            "filename": os.path.basename(file_path).split('.')[0],
            "file_path": draft_path,
            "draft_type": draft_type,
            "content": content,
            "created_at": datetime.utcnow(),
            "file_extension": file_extension,
        }
        draft_db_collection.insert_one(document)
        print(f"Stored document: {file_path}")

def process_documents_parallel(folder_path):
    files = []
    for root, dirs, filenames in os.walk(folder_path):
        files += [os.path.join(root, file) for file in filenames]

    # Use Pool to process files in parallel
    with Pool(processes=4) as pool:
        pool.map(process_file, files)

# Example usage
process_documents_parallel('/home/pronoys/products/AiAdalat/draftdocs')
