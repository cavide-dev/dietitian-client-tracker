"""
Migration Script: Add preferred_language field to existing users
This script adds the preferred_language field to all existing dietician users.
If the field already exists, it skips that user.
Default language: "en" (English)
"""

from pymongo import MongoClient
from dotenv import load_dotenv
import os
import sys

# Load environment variables from .env file
load_dotenv()

def migrate_add_language():
    """
    Add preferred_language field to all existing users in dieticians collection
    """
    # Get connection string from .env
    connection_string = os.getenv("MONGO_URI")
    
    if not connection_string:
        print("ERROR: 'MONGO_URI' not found in .env file!")
        sys.exit(1)
    
    try:
        # Connect to MongoDB
        client = MongoClient(connection_string)
        db = client['diet_app']
        
        # Test connection
        db.command('ping')
        print(" Connected to MongoDB successfully\n")
        
        dieticians = db['dieticians']
        
        # Find all users without the preferred_language field
        users_without_lang = list(dieticians.find({"preferred_language": {"$exists": False}}))
        
        if not users_without_lang:
            print("All users already have preferred_language field")
            return
        
        print(f"Found {len(users_without_lang)} user(s) without preferred_language field")
        print("Updating users...\n")
        
        # Update all users without preferred_language to default "en"
        result = dieticians.update_many(
            {"preferred_language": {"$exists": False}},
            {"$set": {"preferred_language": "en"}}
        )
        
        print(f" Successfully updated {result.modified_count} user(s)")
        print(f" Migration completed!\n")
        
        # Show updated users
        print("Updated users:")
        updated_users = dieticians.find({"preferred_language": "en"})
        for user in updated_users:
            print(f"  - {user['username']} ({user['fullname']}) - Language: {user['preferred_language']}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate_add_language()
