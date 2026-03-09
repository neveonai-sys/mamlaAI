#!/usr/bin/env python3
"""
Script to fix documents stuck in 'processing' state.
"""
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime, timedelta
import sys

def main():
    # Connect to MongoDB
    client = MongoClient("mongodb+srv://ajmrlegaly:password05092024@userdata.cshoz.mongodb.net/Userdata?retryWrites=true&w=majority")
    db = client.legaldb
    files_col = db.talkdoc_files
    
    # Find documents stuck in processing
    cutoff = datetime.utcnow() - timedelta(hours=1)
    stuck_docs = files_col.find({
        'status': 'processing',
        'created_on': {'$lt': cutoff}
    })
    
    for doc in stuck_docs:
        print(f"Found stuck document: {doc['_id']} - {doc.get('filename')}")
        print(f"Created on: {doc.get('created_on')}")
        print(f"Status: {doc.get('status')}")
        print("-" * 50)
    
    if not stuck_docs.retrieved:
        print("No stuck documents found.")
        return
    
    # Ask for confirmation
    confirm = input("\nDo you want to mark these documents as 'error'? (y/n): ")
    if confirm.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Update status to error
    result = files_col.update_many(
        {
            'status': 'processing',
            'created_on': {'$lt': cutoff}
        },
        {
            '$set': {
                'status': 'error',
                'error': 'Marked as stuck in processing',
                'last_updated': datetime.utcnow()
            }
        }
    )
    
    print(f"\nUpdated {result.modified_count} documents to 'error' status.")

if __name__ == "__main__":
    main()
