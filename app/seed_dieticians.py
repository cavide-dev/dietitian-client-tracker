"""
Seed dietician data to MongoDB
Creates test dietician account for login testing
"""

from pymongo import MongoClient
from dotenv import load_dotenv
import hashlib
import os
import sys

# Load environment variables from .env file
load_dotenv()

def seed_dieticians():
    """
    Add test dietician to database
    Uses MONGO_URI from .env file for security
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
        print("Connected to MongoDB successfully")
        
        dieticians = db['dieticians']
        
        # Check if already exists
        if dieticians.find_one({"username": "admin"}):
            print("Admin user already exists")
            return
        
        # Hash password
        password = "admin4321"  # Default password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        # Create admin user
        admin_user = {
            "username": "admin",
            "password": hashed_password,
            "email": "admin@dietician.com",
            "full_name": "Administrator",
            "created_at": None  # Will be set by MongoDB
        }
        
        result = dieticians.insert_one(admin_user)
        print(f"Admin user created with ID: {result.inserted_id}")
        print(f"   Username: admin")
        print(f"   Password: admin4321")
        
        # Check if testuser exists
        if dieticians.find_one({"username": "testuser"}):
            print("Testuser already exists")
            return
        
        # Create test user for checking filtering
        test_user = {
            "username": "testuser",
            "password": hashed_password,
            "email": "test@dietician.com",
            "full_name": "Test Dietician",
            "created_at": None
        }
        
        result2 = dieticians.insert_one(test_user)
        print(f"Testuser created with ID: {result2.inserted_id}")
        print(f"   Username: testuser")
        print(f"   Password: admin4321")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    seed_dieticians()

