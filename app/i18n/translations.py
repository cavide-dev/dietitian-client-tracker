"""
TranslationService - Centralized multi-language support.
Handles loading and retrieving translations for the application.
Supports: English (en), Turkish (tr), Korean (ko)
"""

import json
import os
from typing import Dict, Any


class TranslationService:
    """Manages application translations."""
    
    _current_language = "en"
    _translations: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def initialize(cls, language: str = "en"):
        """
        Initialize translation service with specified language.
        
        Args:
            language: Language code ("en", "tr", "ko", etc.)
        """
        cls._load_translations()
        if language in cls._translations:
            cls._current_language = language
        else:
            print(f"Language '{language}' not found, using 'en'")
            cls._current_language = "en"
    
    @classmethod
    def _load_translations(cls):
        """Load all translation files found in i18n directory."""
        i18n_dir = os.path.dirname(__file__)
        
        # Find all .json files in directory
        for filename in os.listdir(i18n_dir):
            if filename.endswith(".json"):
                lang = filename.replace(".json", "")
                file_path = os.path.join(i18n_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        cls._translations[lang] = json.load(f)
                        print(f"✓ Loaded translation: {lang}")
                except FileNotFoundError:
                    print(f"✗ Translation file not found: {file_path}")
                except json.JSONDecodeError:
                    print(f"✗ Invalid JSON in translation file: {file_path}")
    
    @classmethod
    def get(cls, key: str, default: str = "") -> str:
        """
        Get translated string by key.
        
        Args:
            key: Translation key (e.g., "validation.phone_empty")
            default: Default value if key not found
            
        Returns:
            str: Translated string
        """
        keys = key.split(".")
        value = cls._translations.get(cls._current_language, {})
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        
        return value if value else default
    
    @classmethod
    def set_language(cls, language: str):
        """
        Switch to different language.
        
        Args:
            language: Language code ("en", "tr", "ko", etc.)
        """
        if language in cls._translations:
            cls._current_language = language
            print(f"✓ Language switched to: {language}")
        else:
            print(f"✗ Language '{language}' not available")
    
    @classmethod
    def get_current_language(cls) -> str:
        """Get current language code."""
        return cls._current_language
    
    @classmethod
    def get_available_languages(cls) -> list:
        """Get list of available languages."""
        return list(cls._translations.keys())


# Global function for easier usage
def T(key: str, default: str = "") -> str:
    """Shorthand for TranslationService.get()"""
    return TranslationService.get(key, default)
