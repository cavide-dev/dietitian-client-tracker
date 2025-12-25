"""
AuthService - Centralized user authentication and profile management.
This service consolidates user authentication logic (password hashing, profile updates,
password changes) into a single, testable, and maintainable class.
"""

import hashlib
from typing import Optional, Tuple, Dict


class AuthService:
    """Handles all application-wide authentication and user profile operations."""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using SHA256.
        
        Args:
            password: Password to hash
            
        Returns:
            Hashed password (hex format)
        """
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def verify_password(input_password: str, stored_hash: str) -> bool:
        """
        Verify input password against stored hash.
        
        Args:
            input_password: Password entered by user
            stored_hash: Hash stored in database
            
        Returns:
            True if passwords match, False otherwise
        """
        return AuthService.hash_password(input_password) == stored_hash

    @staticmethod
    def update_user_profile(
        db,
        username: str,
        fullname: str,
        email: str,
        user_data: Dict
    ) -> Tuple[bool, str]:
        """
        Update user profile information (fullname and email).
        
        Args:
            db: MongoDB database connection
            username: Username to update
            fullname: New full name
            email: New email address
            user_data: Local user data dictionary (will be updated)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Update in database
            db['dieticians'].update_one(
                {"username": username},
                {"$set": {"fullname": fullname, "email": email}}
            )
            
            # Update local user_data
            user_data["fullname"] = fullname
            user_data["email"] = email
            
            return True, "Profil başarıyla güncellendi!"
        except Exception as e:
            return False, f"Profil güncellenemedi: {str(e)}"

    @staticmethod
    def change_user_password(
        db,
        username: str,
        current_password: str,
        new_password: str,
        user_data: Dict
    ) -> Tuple[bool, str]:
        """
        Change user password with verification.
        
        Args:
            db: MongoDB database connection
            username: Username of account to change password for
            current_password: Current password (for verification)
            new_password: New password to set
            user_data: Local user data dictionary (will be updated)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Get user from database
            user = db['dieticians'].find_one({"username": username})
            
            if not user:
                return False, "Kullanıcı bulunamadı"
            
            # Verify current password
            hashed_current = AuthService.hash_password(current_password)
            if user['password'] != hashed_current:
                return False, "Mevcut şifre yanlış"
            
            # Hash and update new password
            hashed_new = AuthService.hash_password(new_password)
            db['dieticians'].update_one(
                {"username": username},
                {"$set": {"password": hashed_new}}
            )
            
            # Update local user_data
            user_data["password"] = hashed_new
            
            return True, "Şifre başarıyla değiştirildi!"
        except Exception as e:
            return False, f"Şifre değiştirilemedi: {str(e)}"

    @staticmethod
    def get_user_by_username(db, username: str) -> Optional[Dict]:
        """
        Retrieve user from database by username.
        
        Args:
            db: MongoDB database connection
            username: Username to search for
            
        Returns:
            User data dictionary or None if not found
        """
        try:
            return db['dieticians'].find_one({"username": username})
        except Exception:
            return None

    @staticmethod
    def email_already_exists(db, email: str, exclude_username: str = None) -> bool:
        """
        Check if email is already in use by another user.
        
        Args:
            db: MongoDB database connection
            email: Email address to check
            exclude_username: Username to exclude from check (for profile updates)
            
        Returns:
            True if email already exists, False otherwise
        """
        try:
            query = {"email": email}
            if exclude_username:
                query["username"] = {"$ne": exclude_username}
            
            return db['dieticians'].find_one(query) is not None
        except Exception:
            return False

    @staticmethod
    def format_user_info(user_data: Dict) -> Dict:
        """
        Format user data for UI display.
        
        Args:
            user_data: Raw user data from database
            
        Returns:
            Formatted dictionary with display-friendly fields
        """
        return {
            'display_name': f"{user_data.get('fullname', '')} ({user_data.get('username', '')})",
            'username': user_data.get('username', ''),
            'fullname': user_data.get('fullname', ''),
            'email': user_data.get('email', ''),
        }
