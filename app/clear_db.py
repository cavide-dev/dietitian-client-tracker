from app.database import get_database

def clear_all_data():
    """
    DANGER: Deletes ALL documents in the 'clients' collection.
    Used for resetting the database during development.
    """
    # 1. Connect to Database
    db = get_database()
    
    if db is None:
        print("Error: No connection.")
        return

    # 2. Select Collection
    clients_collection = db['clients']

    # 3. Delete Everything
    # delete_many({}) -> Empty curly braces mean "Select ALL"
    result = clients_collection.delete_many({})
    
    print(f"CLEARED: Deleted {result.deleted_count} documents from the database.")

if __name__ == "__main__":
    clear_all_data()