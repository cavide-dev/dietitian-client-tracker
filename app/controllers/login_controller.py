"""
Login Window Controller
Handles user authentication and login/signup logic
"""

from PyQt5.QtWidgets import QMainWindow, QMessageBox, QHBoxLayout, QPushButton, QWidget, QLabel
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
        
        # Center align subtitle label
        self.label_subtitle.setAlignment(Qt.AlignCenter)
        
        # Setup language buttons
        self.setup_language_buttons()
        
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
            self.label_error.setText(TranslationService.get("login.invalid_credentials", "Please enter username and password"))
            return
        
        if self.db is None:
            self.label_error.setText(TranslationService.get("common.db_error", "Database connection error"))
            return
        
        try:
            # Check in database
            dieticians = self.db['dieticians']
            user = dieticians.find_one({"username": username})
            
            if not user:
                self.label_error.setText(TranslationService.get("login.invalid_credentials", "Invalid password or username"))
                return
            
            # Check password
            hashed_password = self.hash_password(password)
            if user['password'] != hashed_password:
                self.label_error.setText(TranslationService.get("login.invalid_credentials", "Invalid password or username"))
                return
            
            # Login successful! 
            self.current_user = user
            
            # Initialize TranslationService with user's preferred language
            user_language = user.get("preferred_language", "en")
            TranslationService.initialize(language=user_language, debug=False)
            
            # Convert user document to clean dict (remove ObjectId and other non-serializable objects)
            user_data = {
                "username": user.get("username"),
                "fullname": user.get("fullname"),
                "email": user.get("email"),
                "preferred_language": user.get("preferred_language", "en"),
                "theme_preference": user.get("theme_preference", "Light")
            }
            
            # Emit signal to notify run.py that login was successful
            # Send user data so main_window knows who's logged in
            self.login_successful.emit(user_data)
            
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
        # Show login window
        self.show()
        
        # Close signup window if still open
        if self.signup_window:
            self.signup_window.close()
        
        # Clear login form and error message
        self.input_username.setText("")
        self.input_password.setText("")
        self.label_error.setText("")
    
    def setup_language_buttons(self):
        """Add language selection text labels to login window (top right)"""
        
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
            label.mousePressEvent = lambda event, code=lang_code: self.change_login_language(code)
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
    
    def change_login_language(self, lang_code):
        """Change language on login screen"""
        # Initialize TranslationService with new language
        TranslationService.initialize(language=lang_code, debug=False)
        
        # Update all login labels
        self.label_title.setText(TranslationService.get("login.title", "Welcome Back!"))
        self.label_subtitle.setText(TranslationService.get("login.subtitle", "Sign in to your account"))
        self.label_username.setText(TranslationService.get("login.username", "Username") + ":")
        self.label_password.setText(TranslationService.get("login.password", "Password") + ":")
        self.btn_login.setText(TranslationService.get("buttons.login", "Login"))
        
        # Update combined signup text
        self.btn_signup_link.setText(TranslationService.get("login.signup_full", "Don't have an account? Sign Up"))
        
        # Update placeholder texts
        self.input_username.setPlaceholderText(TranslationService.get("login.username_placeholder", "Enter your username"))
        self.input_password.setPlaceholderText(TranslationService.get("login.password_placeholder", "Enter your password"))
        
        print(f"✓ Login language changed to: {lang_code}")
        
        # Show login window
        self.show()
