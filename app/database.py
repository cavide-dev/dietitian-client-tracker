from pymongo import MongoClient
import sys

# ---------------------------------------------------------
# CONNECTION SETTINGS
# ---------------------------------------------------------
# Note: In a real production app, passwords should be in environment variables.
CONNECTION_STRING = "mongodb+srv://admin:admin4321@cluster0.skbgf4x.mongodb.net/?appName=Cluster0"

def get_database():
    """
    Establishes a connection to the MongoDB Atlas cluster
    and returns the database object.
    """
    try:
        # 1. Create the Client
        client = MongoClient(CONNECTION_STRING)
        
        # 2. Select the Database (Will be created automatically if not exists)
        db = client['diyet_app']
        
        # 3. Test Connection (Ping)
        client.admin.command('ping')
        print("SUCCESS: Connected to MongoDB Atlas successfully!")
        
        return db

    except Exception as e:
        print(f"ERROR: Connection failed. Reason: {e}")
        return None

# Test Block: Runs only when this file is executed directly
if __name__ == "__main__":
    get_database()