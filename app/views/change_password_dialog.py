"""
Change Password Dialog
Allows users to change their password securely
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt
from app.services.validation_service import ValidationService
from app.services.auth_service import AuthService


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
        self.setGeometry(0, 0, 400, 250)
        
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
        btn_cancel.setObjectName("btn_cancel_dialog")
        btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancel)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def change_password(self):
        """Validate and update password in database"""
        current_pass = self.input_current.text()
        new_pass = self.input_new.text()
        confirm_pass = self.input_confirm.text()
        
        # Validation using ValidationService
        if not current_pass:
            QMessageBox.warning(self, "Validation Error", "Current password is required")
            return
        
        is_valid_password, password_error = ValidationService.validate_password(new_pass, min_length=6)
        if not is_valid_password:
            QMessageBox.warning(self, "Validation Error", password_error)
            return
        
        if new_pass != confirm_pass:
            QMessageBox.warning(self, "Validation Error", "Passwords do not match")
            return
        
        try:
            # Use AuthService to change password (REFACTORED)
            username = self.user_data.get("username")
            success, message = AuthService.change_user_password(
                self.db, username, current_pass, new_pass, self.user_data
            )
            
            if success:
                QMessageBox.information(self, "Success", message)
                self.accept()
            else:
                QMessageBox.warning(self, "Error", message)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to change password: {str(e)}")
