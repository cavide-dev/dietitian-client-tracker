"""
ValidationService - Centralized validation for all application forms.
This service consolidates all validation logic from scattered locations
into a single, testable, and maintainable class.
"""

import re
from datetime import datetime, date
from typing import Tuple


class ValidationService:
    """Handles all application-wide validation."""

    # Regex patterns
    PHONE_PATTERN = re.compile(r"^\d{7,15}$")  # 7-15 digits
    EMAIL_PATTERN = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )

    # Ranges
    HEIGHT_MIN, HEIGHT_MAX = 100, 250  # cm
    WEIGHT_MIN, WEIGHT_MAX = 20, 500  # kg
    BODY_FAT_MIN, BODY_FAT_MAX = 0, 100  # %
    MIN_AGE, MAX_AGE = 8, 120  # years

    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, str]:
        """
        Validate phone number.
        
        Args:
            phone: Phone number string
            
        Returns:
            Tuple: (is_valid, error_message)
        """
        phone = phone.strip()
        
        if not phone:
            return False, "Telefon numarası boş olamaz"
        
        if not ValidationService.PHONE_PATTERN.match(phone):
            return False, "Telefon numarası 7-15 rakam olmalıdır"
        
        return True, ""

    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """
        Validate email address.
        
        Args:
            email: Email string
            
        Returns:
            Tuple: (is_valid, error_message)
        """
        email = email.strip()
        
        if not email:
            return False, "E-posta boş olamaz"
        
        if not ValidationService.EMAIL_PATTERN.match(email):
            return False, "Geçerli bir e-posta adresi giriniz"
        
        return True, ""

    @staticmethod
    def validate_birth_date(birth_date: str) -> Tuple[bool, str]:
        """
        Validate birth date.
        - Must not be in the future
        - Age must be between 8 and 120
        
        Args:
            birth_date: Birth date string (YYYY-MM-DD format)
            
        Returns:
            Tuple: (is_valid, error_message)
        """
        try:
            # Handle both string and date object
            if isinstance(birth_date, str):
                birth_date_obj = datetime.strptime(birth_date, "%Y-%m-%d").date()
            else:
                birth_date_obj = birth_date
            
            # Check if future
            if birth_date_obj > date.today():
                return False, "Doğum tarihi günümüzden sonra olamaz"
            
            # Calculate age
            today = date.today()
            age = today.year - birth_date_obj.year
            
            # Adjust for month/day
            if (today.month, today.day) < (birth_date_obj.month, birth_date_obj.day):
                age -= 1
            
            # Check age range
            if age < ValidationService.MIN_AGE:
                return False, f"Yaş en az {ValidationService.MIN_AGE} olmalıdır"
            
            if age > ValidationService.MAX_AGE:
                return False, f"Yaş {ValidationService.MAX_AGE} yaşından fazla olamaz"
            
            return True, ""
        
        except (ValueError, AttributeError) as e:
            return False, f"Geçerli bir tarih formatı giriniz (YYYY-MM-DD): {str(e)}"

    @staticmethod
    def validate_measurement_values(
        height: float, weight: float, body_fat: float
    ) -> Tuple[bool, str]:
        """
        Validate measurement values (height, weight, body fat %).
        
        Args:
            height: Height in cm
            weight: Weight in kg
            body_fat: Body fat percentage
            
        Returns:
            Tuple: (is_valid, error_message)
        """
        # Height validation
        if height:
            if height < ValidationService.HEIGHT_MIN or height > ValidationService.HEIGHT_MAX:
                return (
                    False,
                    f"Boy {ValidationService.HEIGHT_MIN}-{ValidationService.HEIGHT_MAX} cm arasında olmalıdır",
                )
        
        # Weight validation (allow 0)
        if weight is not None:
            if weight < ValidationService.WEIGHT_MIN or weight > ValidationService.WEIGHT_MAX:
                return (
                    False,
                    f"Kilo {ValidationService.WEIGHT_MIN}-{ValidationService.WEIGHT_MAX} kg arasında olmalıdır",
                )
        
        # Body fat validation
        if body_fat is not None:
            if body_fat < ValidationService.BODY_FAT_MIN or body_fat > ValidationService.BODY_FAT_MAX:
                return (
                    False,
                    f"Vücut yağ oranı {ValidationService.BODY_FAT_MIN}-{ValidationService.BODY_FAT_MAX}% arasında olmalıdır",
                )
        
        return True, ""

    @staticmethod
    def validate_diet_plan(
        title: str, min_characters: int = 3
    ) -> Tuple[bool, str]:
        """
        Validate diet plan title.
        
        Args:
            title: Diet plan title
            min_characters: Minimum character count (default: 3)
            
        Returns:
            Tuple: (is_valid, error_message)
        """
        title = title.strip()
        
        if not title:
            return False, "Diyet planı başlığı boş olamaz"
        
        if len(title) < min_characters:
            return False, f"Başlık en az {min_characters} karakter olmalıdır"
        
        return True, ""

    @staticmethod
    def validate_client_name(name: str, min_characters: int = 2) -> Tuple[bool, str]:
        """
        Validate client/person name.
        
        Args:
            name: Person's name
            min_characters: Minimum character count (default: 2)
            
        Returns:
            Tuple: (is_valid, error_message)
        """
        name = name.strip()
        
        if not name:
            return False, "İsim boş olamaz"
        
        if len(name) < min_characters:
            return False, f"İsim en az {min_characters} karakter olmalıdır"
        
        return True, ""

    @staticmethod
    def calculate_age(birth_date) -> int:
        """
        Calculate age from birth date.
        
        Args:
            birth_date: Birth date (string YYYY-MM-DD or date object)
            
        Returns:
            int: Age in years
        """
        try:
            if isinstance(birth_date, str):
                birth_date_obj = datetime.strptime(birth_date, "%Y-%m-%d").date()
            else:
                birth_date_obj = birth_date
            
            today = date.today()
            age = today.year - birth_date_obj.year
            
            if (today.month, today.day) < (birth_date_obj.month, birth_date_obj.day):
                age -= 1
            
            return age
        except Exception:
            return 0

    @staticmethod
    def validate_password(password: str, min_length: int = 6) -> Tuple[bool, str]:
        """
        Validate password strength.
        
        Args:
            password: Password string
            min_length: Minimum password length (default: 6)
            
        Returns:
            Tuple: (is_valid, error_message)
        """
        if not password:
            return False, "Şifre boş olamaz"
        
        if len(password) < min_length:
            return False, f"Şifre en az {min_length} karakter olmalıdır"
        
        return True, ""

    @staticmethod
    def validate_username(username: str, min_length: int = 3) -> Tuple[bool, str]:
        """
        Validate username.
        
        Args:
            username: Username string
            min_length: Minimum username length (default: 3)
            
        Returns:
            Tuple: (is_valid, error_message)
        """
        username = username.strip()
        
        if not username:
            return False, "Kullanıcı adı boş olamaz"
        
        if len(username) < min_length:
            return False, f"Kullanıcı adı en az {min_length} karakter olmalıdır"
        
        return True, ""

    @staticmethod
    def validate_fullname(fullname: str, min_length: int = 2) -> Tuple[bool, str]:
        """
        Validate full name.
        
        Args:
            fullname: Person's full name
            min_length: Minimum name length (default: 2)
            
        Returns:
            Tuple: (is_valid, error_message)
        """
        fullname = fullname.strip()
        
        if not fullname:
            return False, "Ad Soyad boş olamaz"
        
        if len(fullname) < min_length:
            return False, f"Ad Soyad en az {min_length} karakter olmalıdır"
        
        return True, ""

    @staticmethod
    def validate_meals(meal_text: str, min_length: int = 5) -> Tuple[bool, str]:
        """
        Validate meal description.
        
        Args:
            meal_text: Meal description text
            min_length: Minimum text length (default: 5)
            
        Returns:
            Tuple: (is_valid, error_message)
        """
        meal_text = meal_text.strip()
        
        if not meal_text:
            return False, "Öğün boş olamaz"
        
        if len(meal_text) < min_length:
            return False, f"Öğün açıklaması en az {min_length} karakter olmalıdır"
        
        return True, ""

