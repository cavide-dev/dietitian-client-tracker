"""
Change Password Dialog
Allows users to change their password securely
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt
import hashlib


class ChangePasswordDialog(QDialog):
    def __init__(self, parent=None, user_data=None, db=None):
        """
        Args:
            parent: Parent widget
            user_data: Current user dictionary {"username": "...", "password": "..."}
            db: MongoDB database connection
        """
        super().__init__(parent)
        self.user_data = user_data
        self.db = db
        self.setWindowTitle("Change Password")
        self.setGeometry(100, 100, 400, 250)
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Current Password
        layout.addWidget(QLabel("Current Password:"))
        self.input_current = QLineEdit()
        self.input_current.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.input_current)
        
        # New Password
        layout.addWidget(QLabel("New Password:"))
        self.input_new = QLineEdit()
        self.input_new.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.input_new)
        
        # Confirm Password
        layout.addWidget(QLabel("Confirm Password:"))
        self.input_confirm = QLineEdit()
        self.input_confirm.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.input_confirm)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        btn_save = QPushButton("Change Password")
        btn_save.clicked.connect(self.change_password)
        button_layout.addWidget(btn_save)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancel)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def hash_password(self, password):
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def change_password(self):
        """Validate and update password in database"""
        current_pass = self.input_current.text()
        new_pass = self.input_new.text()
        confirm_pass = self.input_confirm.text()
        
        # Validation
        if not current_pass:
            QMessageBox.warning(self, "Validation Error", "Current password is required")
            return
        
        if not new_pass or not confirm_pass:
            QMessageBox.warning(self, "Validation Error", "New password cannot be empty")
            return
        
        if len(new_pass) < 6:
            QMessageBox.warning(self, "Validation Error", "Password must be at least 6 characters")
            return
        
        if new_pass != confirm_pass:
            QMessageBox.warning(self, "Validation Error", "Passwords do not match")
            return
        
        try:
            # Verify current password
            username = self.user_data.get("username")
            user = self.db['dieticians'].find_one({"username": username})
            
            hashed_current = self.hash_password(current_pass)
            if user['password'] != hashed_current:
                QMessageBox.warning(self, "Error", "Current password is incorrect")
                return
            
            # Update password in database
            hashed_new = self.hash_password(new_pass)
            self.db['dieticians'].update_one(
                {"username": username},
                {"$set": {"password": hashed_new}}
            )
            
            # Update local user_data
            self.user_data["password"] = hashed_new
            
            QMessageBox.information(self, "Success", "Password changed successfully!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to change password: {str(e)}")
