"""
Signup Window Controller
Handles user registration and account creation
"""

from PyQt5.QtWidgets import QMainWindow, QHBoxLayout, QLabel, QWidget
from PyQt5.uic import loadUi
from PyQt5.QtCore import Qt, pyqtSignal
from pymongo import MongoClient
from dotenv import load_dotenv
from app.services.validation_service import ValidationService
from app.i18n.translations import TranslationService
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
        
        # Initialize TranslationService with default language (English)
        TranslationService.initialize(language="en", debug=False)
        
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
        
        # Setup language buttons
        self.setup_language_buttons()
        
        # Initialize UI labels with translations on first load
        self.refresh_signup_ui_labels()
    
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
        
        # Validation using ValidationService
        if not fullname or not email or not username or not password or not confirm_password:
            self.label_error.setText("All fields are required")
            return
        
        is_valid_fullname, fullname_error = ValidationService.validate_fullname(fullname, min_length=3)
        if not is_valid_fullname:
            self.label_error.setText(fullname_error)
            return
        
        is_valid_email, email_error = ValidationService.validate_email(email)
        if not is_valid_email:
            self.label_error.setText(email_error)
            return
        
        is_valid_username, username_error = ValidationService.validate_username(username, min_length=3)
        if not is_valid_username:
            self.label_error.setText(username_error)
            return
        
        is_valid_password, password_error = ValidationService.validate_password(password, min_length=6)
        if not is_valid_password:
            self.label_error.setText(password_error)
            return
        
        if password != confirm_password:
            self.label_error.setText(TranslationService.get("register.password_mismatch", "Passwords do not match"))
            return
        
        if self.db is None:
            self.label_error.setText(TranslationService.get("common.db_error", "Database connection error"))
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
                "preferred_language": "en",  # Default language is English
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
        # Close this signup window
        self.close()
    
    def setup_language_buttons(self):
        """Add language selection text labels to signup window (top right)"""
        
        # Create language layout
        lang_layout = QHBoxLayout()
        lang_layout.setContentsMargins(10, 10, 10, 0)
        lang_layout.setSpacing(15)
        lang_layout.addStretch()  # Push labels to the right
        
        # Language data: (code, label)
        languages = [
            ("en", "EN"),
            ("tr", "TR"),
            ("ko", "한")
        ]
        
        # Create clickable text labels
        self.lang_labels = {}
        for lang_code, short_name in languages:
            label = QLabel(short_name)
            label.setCursor(Qt.PointingHandCursor)  # Make it look clickable
            label.setStyleSheet("color: #0066cc; text-decoration: underline; font-weight: bold;")
            label.setObjectName(f"label_lang_{lang_code}")
            
            # Store reference and connect click handler
            label.mousePressEvent = lambda event, code=lang_code: self.change_signup_language(code)
            self.lang_labels[lang_code] = label
            lang_layout.addWidget(label)
        
        # Add language layout to the main layout
        main_layout = self.centralwidget.layout()
        if main_layout and hasattr(main_layout, 'addWidget'):
            lang_widget = QWidget()
            lang_widget.setLayout(lang_layout)
            try:
                main_layout.addWidget(lang_widget, 0, 0, 1, -1)
            except TypeError:
                main_layout.insertWidget(0, lang_widget)
    
    def change_signup_language(self, lang_code):
        """Change language on signup screen"""
        # Initialize TranslationService with new language
        TranslationService.initialize(language=lang_code, debug=False)
        
        # Update all signup labels
        self.refresh_signup_ui_labels()
        
        print(f" Signup language changed to: {lang_code}")
    
    def refresh_signup_ui_labels(self):
        """Refresh all signup UI labels with current language"""
        self.label_title.setText(TranslationService.get("register.title", "Create Account"))
        self.label_subtitle.setText(TranslationService.get("register.subtitle", "Join Our Platform"))
        self.label_fullname.setText(TranslationService.get("register.fullname", "Full Name") + ":")
        self.label_username.setText(TranslationService.get("register.username", "Username") + ":")
        self.label_email.setText(TranslationService.get("register.email", "Email") + ":")
        self.label_password.setText(TranslationService.get("register.password", "Password") + ":")
        self.label_confirm_password.setText(TranslationService.get("register.confirm_password", "Confirm Password") + ":")
        self.btn_signup.setText(TranslationService.get("buttons.register", "Register"))
        
        # Update combined signin text
        self.btn_signin_link.setText(TranslationService.get("register.already_account_full", "Already have an account? Sign In"))
        
        # Update placeholder texts
        self.input_fullname.setPlaceholderText(TranslationService.get("register.fullname_placeholder", "Enter your full name"))
        self.input_username.setPlaceholderText(TranslationService.get("register.username_placeholder", "Enter your username"))
        self.input_email.setPlaceholderText(TranslationService.get("register.email_placeholder", "Enter your email"))
        self.input_password.setPlaceholderText(TranslationService.get("register.password_placeholder", "Enter your password"))
        self.input_confirm_password.setPlaceholderText(TranslationService.get("register.confirm_password_placeholder", "Confirm your password"))
