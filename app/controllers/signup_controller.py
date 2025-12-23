"""
Signup Window Controller
Handles user registration and account creation
"""

from PyQt5.QtWidgets import QMainWindow
from PyQt5.uic import loadUi
from PyQt5.QtCore import Qt, pyqtSignal
from pymongo import MongoClient
from dotenv import load_dotenv
import hashlib
import re
import os
import sys
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

class SignupController(QMainWindow):
    # Signal: Emitted when signup is successful
    signup_successful = pyqtSignal()  # Emits signal to go back to login
    
    def __init__(self, db_connection_string=None):
        super(SignupController, self).__init__()
        
        # Load UI from signup_window.ui
        ui_path = os.path.join(os.path.dirname(__file__), "..", "views", "signup_window.ui")
        loadUi(ui_path, self)
        
        # Setup database connection
        self.db = None
        self.init_database(db_connection_string)
        
        # Connect buttons to functions
        self.btn_signup.clicked.connect(self.handle_signup)
        self.btn_signin_link.clicked.connect(self.go_back_to_login)
        
        # Allow Enter key to signup
        self.input_confirm_password.returnPressed.connect(self.handle_signup)
    
    def init_database(self, connection_string=None):
        """
        Initialize MongoDB connection securely using .env file
        """
        try:
            # Get connection string from .env file
            if connection_string is None:
                connection_string = os.getenv("MONGO_URI")
                
            # Check if MONGO_URI exists
            if not connection_string:
                print("ERROR: 'MONGO_URI' not found in .env file!")
                self.label_error.setText("Configuration error: MONGO_URI not found")
                self.db = None
                return
            
            client = MongoClient(connection_string)
            self.db = client['diet_app']
            
            # Test connection
            self.db.command('ping')
            print("Database connected successfully!")
            
        except Exception as e:
            print(f"Database connection failed: {e}")
            self.label_error.setText("Database connection failed!")
            self.db = None
    
    def hash_password(self, password):
        """
        Hash password using SHA256 (for security)
        """
        return hashlib.sha256(password.encode()).hexdigest()
    
    def validate_email(self, email):
        """
        Validate email format
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def handle_signup(self):
        """
        Handle signup button click
        Validate and create new user account
        """
        # Get input values
        fullname = self.input_fullname.text().strip()
        email = self.input_email.text().strip()
        username = self.input_username.text().strip()
        password = self.input_password.text().strip()
        confirm_password = self.input_confirm_password.text().strip()
        
        # Clear previous error
        self.label_error.setText("")
        
        # Validation
        if not fullname or not email or not username or not password or not confirm_password:
            self.label_error.setText("All fields are required")
            return
        
        if len(fullname) < 3:
            self.label_error.setText("Full name must be at least 3 characters")
            return
        
        if not self.validate_email(email):
            self.label_error.setText("Invalid email format")
            return
        
        if len(username) < 3:
            self.label_error.setText("Username must be at least 3 characters")
            return
        
        if len(password) < 6:
            self.label_error.setText("Password must be at least 6 characters")
            return
        
        if password != confirm_password:
            self.label_error.setText("Passwords do not match")
            return
        
        if self.db is None:
            self.label_error.setText("Database connection error")
            return
        
        try:
            # Check if username already exists
            dieticians = self.db['dieticians']
            existing_user = dieticians.find_one({"username": username})
            
            if existing_user:
                self.label_error.setText("Username already exists")
                return
            
            # Check if email already exists
            existing_email = dieticians.find_one({"email": email})
            
            if existing_email:
                self.label_error.setText("Email already registered")
                return
            
            # Hash password
            hashed_password = self.hash_password(password)
            
            # Create new dietician document
            new_dietician = {
                "fullname": fullname,
                "email": email,
                "username": username,
                "password": hashed_password,
                "created_at": datetime.now()
            }
            
            # Insert into database
            result = dieticians.insert_one(new_dietician)
            
            # Show success message
            self.label_error.setText("Account created successfully! Redirecting to login...")
            
            # Emit signal to go back to login (emit after short delay for user to see message)
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(1500, self.go_back_to_login)
            
        except Exception as e:
            self.label_error.setText(f"Error: {str(e)}")
    
    def go_back_to_login(self):
        """
        Go back to login window
        """
        self.signup_successful.emit()
        self.close()
