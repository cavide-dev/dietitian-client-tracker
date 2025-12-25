"""
Login Window Controller
Handles user authentication and login/signup logic
"""

from PyQt5.QtWidgets import QMainWindow, QMessageBox
from PyQt5.uic import loadUi
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from pymongo import MongoClient
from dotenv import load_dotenv
import hashlib
import os
import sys

# Load environment variables from .env file
load_dotenv()

# Import SignupController for signup functionality
from app.controllers.signup_controller import SignupController
from app.i18n.translations import TranslationService

class LoginController(QMainWindow):
    # Signal: Emitted when login is successful
    # This allows run.py to know when user has logged in successfully
    login_successful = pyqtSignal(dict)  # Emits user data
    
    def __init__(self, db_connection_string=None):
        super(LoginController, self).__init__()
        
        # Load UI from login_window.ui
        # UI files are in app/views/ directory, so we go up one level (..)
        ui_path = os.path.join(os.path.dirname(__file__), "..", "views", "login_window.ui")
        loadUi(ui_path, self)
        
        # Setup database connection
        self.db = None
        self.init_database(db_connection_string)
        
        # Connect buttons to functions
        self.btn_login.clicked.connect(self.handle_login)
        self.btn_signup_link.clicked.connect(self.open_signup)
        
        # Allow Enter key to login
        self.input_password.returnPressed.connect(self.handle_login)
        
        # Store current user (for later)
        self.current_user = None
        
        # Set error label objectName for QSS styling
        self.label_error.setObjectName("label_error_login")
        
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
    
    def handle_login(self):
        """
        Handle login button click
        Validate username and password
        """
        username = self.input_username.text().strip()
        password = self.input_password.text().strip()
        
        # Clear previous error
        self.label_error.setText("")
        
        # Validation
        if not username or not password:
            self.label_error.setText("Please enter username and password")
            return
        
        if self.db is None:
            self.label_error.setText("Database connection error")
            return
        
        try:
            # Check in database
            dieticians = self.db['dieticians']
            user = dieticians.find_one({"username": username})
            
            if not user:
                self.label_error.setText("Invalid password or username")
                return
            
            # Check password
            hashed_password = self.hash_password(password)
            if user['password'] != hashed_password:
                self.label_error.setText("Invalid password or username")
                return
            
            # Login successful! 
            self.current_user = user
            
            # Initialize TranslationService with user's preferred language
            user_language = user.get("preferred_language", "en")
            TranslationService.initialize(language=user_language, debug=False)
            
            # Emit signal to notify run.py that login was successful
            # Send user data so main_window knows who's logged in
            self.login_successful.emit(user)
            
            # Close this window
            self.close()
            
        except Exception as e:
            self.label_error.setText(f"Error: {str(e)}")
    
    def open_signup(self):
        """
        Open signup window for new user registration
        """
        # Create signup window
        self.signup_window = SignupController()
        
        # When signup is successful, connect signal to refresh login
        self.signup_window.signup_successful.connect(self.on_signup_complete)
        
        # Show signup window
        self.signup_window.show()
        
        # Hide login window (optional - keeps it in background)
        self.hide()
    
    def on_signup_complete(self):
        """
        Called when signup is completed
        Show login window again
        """
        # Clear login form
        self.input_username.setText("")
        self.input_password.setText("")
        self.label_error.setText("Account created! Please sign in.")
        
        # Show login window
        self.show()
