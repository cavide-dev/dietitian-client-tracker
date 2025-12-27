"""
Edit Profile Dialog
Allows users to update their profile information (fullname, email)
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt
from app.services.validation_service import ValidationService
from app.services.auth_service import AuthService
from app.i18n.translations import TranslationService


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
        self.setWindowTitle(TranslationService.get("profile_dialogs.edit_profile_title", "Edit Profile"))
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
        layout.addWidget(QLabel(TranslationService.get("profile_dialogs.fullname_label", "Full Name") + ":"))
        self.input_fullname = QLineEdit()
        self.input_fullname.setText(self.original_fullname)
        layout.addWidget(self.input_fullname)
        
        # Email
        layout.addWidget(QLabel(TranslationService.get("clients.email", "Email") + ":"))
        self.input_email = QLineEdit()
        self.input_email.setText(self.original_email)
        layout.addWidget(self.input_email)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        btn_save = QPushButton(TranslationService.get("profile_dialogs.save_button", "Save Changes"))
        btn_save.clicked.connect(self.save_changes)
        button_layout.addWidget(btn_save)
        
        btn_cancel = QPushButton(TranslationService.get("common.cancel", "Cancel"))
        btn_cancel.setObjectName("btn_cancel_dialog")
        btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancel)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def save_changes(self):
        """Save updated profile to database"""
        
        fullname = self.input_fullname.text().strip()
        email = self.input_email.text().strip()
        
        # Validate fullname using ValidationService
        is_valid_fullname, fullname_error = ValidationService.validate_fullname(fullname)
        if not is_valid_fullname:
            QMessageBox.warning(
                self,
                TranslationService.get("dialogs.error", "Validation Error"),
                fullname_error
            )
            return
        
        # Validate email using ValidationService
        is_valid_email, email_error = ValidationService.validate_email(email)
        if not is_valid_email:
            QMessageBox.warning(
                self,
                TranslationService.get("dialogs.error", "Validation Error"),
                email_error
            )
            return
        
        try:
            # Use AuthService to update profile (REFACTORED)
            username = self.user_data.get("username")
            success, message = AuthService.update_user_profile(
                self.db, username, fullname, email, self.user_data
            )
            
            if success:
                QMessageBox.information(
                    self,
                    TranslationService.get("dialogs.success", "Success"),
                    TranslationService.get("settings.profile_updated", "Profile updated successfully!")
                )
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    TranslationService.get("dialogs.error", "Error"),
                    message
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                TranslationService.get("dialogs.error", "Error"),
                f"{TranslationService.get('dialogs.failed', 'Failed to update profile')}: {str(e)}"
            )
