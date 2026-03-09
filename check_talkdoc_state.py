from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv
import pprint

def check_talkdoc_state():
    # Load environment variables
    load_dotenv("Legalv1/legalenv")
    
    # Get MongoDB connection string from environment or use the same format as Django settings
    mongo_host = os.getenv('MONGO_HOSTNAME')
    mongo_pwd = os.getenv('MONGO_PWD')
    mongo_app = os.getenv('MONGO_APPNAME', 'Userdata')
    
    if all([mongo_host, mongo_pwd]):
        # Use the same connection string format as in Django settings
        mongo_uri = f"mongodb+srv://{mongo_host}:{mongo_pwd}@userdata.cshoz.mongodb.net/{mongo_app}?retryWrites=true&w=majority"
    else:
        # Fallback to local MongoDB if env vars not set
        mongo_uri = 'mongodb://localhost:27017/'
        mongo_app = 'legaldb'
    
    print(f"Connecting to MongoDB at: {mongo_uri}")
    
    try:
        # Initialize MongoDB client with more detailed connection options
        client = MongoClient(
            mongo_uri,
            maxPoolSize=100,
            minPoolSize=10,
            maxIdleTimeMS=30000,
            connectTimeoutMS=10000,
            socketTimeoutMS=30000,
            serverSelectionTimeoutMS=5000,
            retryWrites=True,
            retryReads=True,
            connect=False  # Use connect=False to handle connection manually
        )
        
        # Test the connection
        try:
            client.admin.command('ping')
            print("✅ Successfully connected to MongoDB")
            
            # List all databases
            print("\n=== Available Databases ===")
            for db_name in client.list_database_names():
                print(f"- {db_name}")
                
            # Check both potential databases
            for db_name in [mongo_app, 'legaldb', 'Userdata']:
                try:
                    db = client[db_name]
                    collections = db.list_collection_names()
                    if collections:
                        print(f"\n=== Database: {db_name} ===")
                        print("Collections:")
                        for collection_name in collections:
                            try:
                                count = db[collection_name].estimated_document_count()
                                print(f"  {collection_name}: {count} documents")
                                
                                # If this is a collection we're interested in, show some sample data
                                if collection_name in ['talkdoc_files', 'talkdoc_sessions', 'sessions', 'files']:
                                    sample = db[collection_name].find_one()
                                    if sample:
                                        print(f"  Sample document from {collection_name}:")
                                        pprint.pprint(sample, width=40)
                                        
                            except Exception as e:
                                print(f"  {collection_name}: Error - {str(e)}")
                except Exception as e:
                    print(f"\nError accessing database {db_name}: {str(e)}")
            
            # Try to find any collections that might contain our data
            all_collections = []
            for db_name in [mongo_app, 'legaldb', 'Userdata']:
                try:
                    db = client[db_name]
                    all_collections.extend([(db_name, col) for col in db.list_collection_names()])
                except:
                    continue
            
            print("\n=== All Collections Found ===")
            for db_name, col in all_collections:
                print(f"{db_name}.{col}")
        
        except Exception as e:
            print(f"❌ MongoDB connection test failed: {str(e)}")
            print("Please check your MongoDB connection string and network access.")
            return
        
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {str(e)}")
        return
    
    # Check OpenSearch connection
    try:
        from opensearchpy import OpenSearch, RequestsHttpConnection
        
        opensearch_host = os.getenv('OPENSEARCH_HOST', 'localhost')
        opensearch_port = os.getenv('OPENSEARCH_PORT', '9200')
        
        print(f"\n=== Testing OpenSearch Connection ===")
        print(f"Connecting to OpenSearch at {opensearch_host}:{opensearch_port}")
        
        # Initialize the OpenSearch client
        os_client = OpenSearch(
            [f"{opensearch_host}:{opensearch_port}"],
            use_ssl=False,
            verify_certs=False,
            connection_class=RequestsHttpConnection,
            timeout=30
        )
        
        if os_client.ping():
            print("✅ Successfully connected to OpenSearch")
            
            # List all indices
            print("\n=== OpenSearch Indices ===")
            try:
                indices = os_client.cat.indices(format="json")
                for idx in indices:
                    print(f"Index: {idx['index']}, Documents: {idx['docs.count']}")
            except Exception as e:
                print(f"Error listing indices: {str(e)}")
        else:
            print("❌ Could not connect to OpenSearch")
            
    except ImportError:
        print("\nOpenSearch client not available. Install with: pip install opensearch-py")
    except Exception as e:
        print(f"\nError checking OpenSearch: {str(e)}")

    # Check processing status of talkdoc_files
    print("\n=== Document Processing Status ===")
    files = client.legaldb.talkdoc_files.find({})
    for file in files:
        print(f"\nFile: {file.get('filename')}")
        print(f"Status: {file.get('status')}")
        print(f"Last Updated: {file.get('last_updated_on', 'N/A')}")
        print(f"Error: {file.get('error', 'None')}")
        
        # Check if there are any chunks for this file in OpenSearch
        if os_client.ping():
            try:
                res = os_client.search(
                    index='talkdoc_chunks',
                    body={
                        'query': {'term': {'doc_id': str(file['_id'])}},
                        'size': 0
                    }
                )
                print(f"Chunks in OpenSearch: {res['hits']['total']['value']}")
            except Exception as e:
                print(f"Error checking chunks: {str(e)}")
    
    # Check sessions and their document associations
    print("\n=== Session Document Associations ===")
    sessions = client.legaldb.talkdoc_sessions.find({})
    for session in sessions:
        print(f"\nSession: {session.get('title')}")
        print(f"User: {session.get('user_id')}")
        print(f"Document IDs: {session.get('doc_ids', [])}")
        
        # Check if documents in doc_ids exist
        for doc_id in session.get('doc_ids', []):
            doc = client.legaldb.talkdoc_files.find_one({'_id': ObjectId(doc_id)})
            if doc:
                print(f"  - {doc.get('filename')} (Status: {doc.get('status')})")
            else:
                print(f"  - Document {doc_id} not found")

if __name__ == "__main__":
    check_talkdoc_state()
