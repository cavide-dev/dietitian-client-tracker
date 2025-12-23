import sys
import os

# Add parent directory to path so we can import 'app'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_database

def add_fake_data():
    """
    Populates the MongoDB database with dummy client data for testing purposes.
    """
    
    # 1. Retrieve Database Connection
    db = get_database()
    
    if db is None:
        print("ERROR: Database connection failed!")
        return

    # 2. Select the Collection
    # In MongoDB, tables are called 'Collections'. 
    # We are accessing the 'clients' collection here.
    clients_collection = db['clients']

    # 3. Prepare Dummy Data
    # Creating a list of dictionaries (JSON-like objects) representing clients.
    fake_clients = [
        {
            "full_name": "John Doe",
            "phone": "+1 555 0199",
            "email": "johndoe@example.com",
            "gender": "Male",
            "notes": "Type 2 Diabetes patient. Needs low sugar diet.",
            "dietician_username": "admin"
        },
        {
            "full_name": "Jane Smith",
            "phone": "+1 555 0200",
            "email": "janesmith@example.com",
            "gender": "Female",
            "notes": "Vegan diet. Prefers plant-based proteins.",
            "dietician_username": "admin"
        },
        {
            "full_name": "Ali Yilmaz",
            "phone": "+90 555 123 45 67",
            "email": "ali@example.com",
            "gender": "Male",
            "notes": "Gluten intolerant (Celiac).",
            "dietician_username": "admin"
        },
        {
            "full_name": "Maria Garcia",
            "phone": "+34 666 123 456",
            "email": "maria@example.com",
            "gender": "Female",
            "notes": "High cholesterol. Needs low-fat diet.",
            "dietician_username": "testuser"
        },
        {
            "full_name": "Ahmed Hassan",
            "phone": "+20 100 123 4567",
            "email": "ahmed@example.com",
            "gender": "Male",
            "notes": "Weight loss program. 30 lbs target.",
            "dietician_username": "testuser"
        }
    ]
    
    # 4. Insert Data into Database
    # 'insert_many' is more efficient than looping with 'insert_one'.
    try:
        result = clients_collection.insert_many(fake_clients)
        count = len(result.inserted_ids)
        print(f"SUCCESS: {count} dummy clients added to MongoDB successfully!")
    except Exception as e:
        print(f"ERROR: Failed to add data. Reason: {e}")

if __name__ == "__main__":
    add_fake_data()