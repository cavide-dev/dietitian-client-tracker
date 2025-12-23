import sys
import os

# Add parent directory to path so we can import 'app'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_database

def clear_all_data():
    """
    DANGER: Deletes ALL documents in the 'clients' and 'dieticians' collections.
    Used for resetting the database during development.
    """
    # 1. Connect to Database
    db = get_database()
    
    if db is None:
        print("Error: No connection.")
        return

    # 2. Select Collections
    clients_collection = db['clients']
    dieticians_collection = db['dieticians']

    # 3. Delete Everything from both collections
    # delete_many({}) -> Empty curly braces mean "Select ALL"
    clients_result = clients_collection.delete_many({})
    dieticians_result = dieticians_collection.delete_many({})
    
    total_deleted = clients_result.deleted_count + dieticians_result.deleted_count
    print(f"CLEARED: Deleted {total_deleted} documents from the database.")
    print(f"  - Clients: {clients_result.deleted_count}")
    print(f"  - Dieticians: {dieticians_result.deleted_count}")

if __name__ == "__main__":
    clear_all_data()