"""
Edit Profile Dialog
Allows users to update their profile information (fullname, email)
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt


class EditProfileDialog(QDialog):
    def __init__(self, parent=None, user_data=None, db=None):
        """
        Args:
            parent: Parent widget
            user_data: Current user dictionary {"username": "...", "fullname": "...", "email": "..."}
            db: MongoDB database connection
        """
        super().__init__(parent)
        self.user_data = user_data
        self.db = db
        self.setWindowTitle("Edit Profile")
        self.setGeometry(0, 0, 400, 200)
        
        # Store original values
        self.original_fullname = user_data.get("fullname", "")
        self.original_email = user_data.get("email", "")
        
        self.init_ui()
        
        # Center dialog on parent window
        if parent:
            parent_geo = parent.frameGeometry()
            self.move(
                parent_geo.center().x() - self.width() // 2,
                parent_geo.center().y() - self.height() // 2
            )
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Full Name
        layout.addWidget(QLabel("Full Name:"))
        self.input_fullname = QLineEdit()
        self.input_fullname.setText(self.original_fullname)
        layout.addWidget(self.input_fullname)
        
        # Email
        layout.addWidget(QLabel("Email:"))
        self.input_email = QLineEdit()
        self.input_email.setText(self.original_email)
        layout.addWidget(self.input_email)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        btn_save = QPushButton("Save Changes")
        btn_save.clicked.connect(self.save_changes)
        button_layout.addWidget(btn_save)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("btn_cancel_dialog")
        btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancel)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def save_changes(self):
        """Save updated profile to database"""
        import re
        
        fullname = self.input_fullname.text().strip()
        email = self.input_email.text().strip()
        
        # Validation
        if not fullname:
            QMessageBox.warning(self, "Validation Error", "Full name cannot be empty")
            return
        
        if not email:
            QMessageBox.warning(self, "Validation Error", "Email cannot be empty")
            return
        
        # Validate email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            QMessageBox.warning(self, "Validation Error", "Invalid email format")
            return
        
        try:
            # Update in database
            username = self.user_data.get("username")
            self.db['dieticians'].update_one(
                {"username": username},
                {"$set": {"fullname": fullname, "email": email}}
            )
            
            # Update local user_data
            self.user_data["fullname"] = fullname
            self.user_data["email"] = email
            
            QMessageBox.information(self, "Success", "Profile updated successfully!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update profile: {str(e)}")
