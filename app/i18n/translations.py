"""
TranslationService - Centralized multi-language support.
Handles loading and retrieving translations for the application.
Supports: English (en), Turkish (tr), Korean (ko)

Features:
- Lazy loading: Translations loaded only once
- Flexible language detection: Auto-scans i18n/ folder
- Missing key logging: Debug mode shows untranslated keys
- Fallback: Missing keys return default value
"""

import json
import os
import logging
from typing import Dict, Any

# Configure logging
logger = logging.getLogger(__name__)


class TranslationService:
    """Manages application translations with caching and error handling."""
    
    _current_language = "en"
    _translations: Dict[str, Dict[str, Any]] = {}
    _is_loaded = False  # Track if translations are already loaded
    _debug_mode = False  # Enable debug logging for missing keys
    _missing_keys: set = set()  # Track missing keys to avoid spam logging
    
    @classmethod
    def initialize(cls, language: str = "en", debug: bool = False):
        """
        Initialize translation service with specified language.
        
        Args:
            language: Language code ("en", "tr", "ko", etc.)
            debug: If True, logs missing translation keys
        
        Raises:
            ValueError: If language not found and 'en' not available
        """
        cls._debug_mode = debug
        
        # Load translations only once (caching)
        if not cls._is_loaded:
            cls._load_translations()
            cls._is_loaded = True
        
        # Set language
        if language in cls._translations:
            cls._current_language = language
            logger.info(f"Language set to: {language}")
        else:
            if "en" in cls._translations:
                cls._current_language = "en"
                logger.warning(
                    f"Language '{language}' not found. "
                    f"Available: {list(cls._translations.keys())}. Using 'en'"
                )
            else:
                raise ValueError(
                    f"Language '{language}' not found and 'en' not available. "
                    f"Available languages: {list(cls._translations.keys())}"
                )
    
    @classmethod
    def _load_translations(cls):
        """
        Load all translation JSON files from i18n directory.
        Only called once due to _is_loaded flag.
        """
        i18n_dir = os.path.dirname(__file__)
        loaded = []
        errors = []
        
        try:
            # Find all .json files in directory
            json_files = [f for f in os.listdir(i18n_dir) if f.endswith(".json")]
            
            if not json_files:
                logger.warning("No translation files found in i18n directory")
                return
            
            for filename in json_files:
                lang = filename.replace(".json", "")
                file_path = os.path.join(i18n_dir, filename)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        cls._translations[lang] = json.load(f)
                        loaded.append(lang)
                except FileNotFoundError:
                    error = f"File not found: {file_path}"
                    logger.error(error)
                    errors.append(error)
                except json.JSONDecodeError as e:
                    error = f"Invalid JSON in {file_path}: {str(e)}"
                    logger.error(error)
                    errors.append(error)
                except Exception as e:
                    error = f"Error loading {file_path}: {str(e)}"
                    logger.error(error)
                    errors.append(error)
            
            # Log summary
            if loaded:
                logger.info(f"Loaded translations: {', '.join(loaded)}")
            if errors:
                for error in errors:
                    logger.error(error)
                    
        except Exception as e:
            logger.error(f"Failed to load translations: {str(e)}")
    
    @classmethod
    def get(cls, key: str, default: str = "", **kwargs) -> str:
        """
        Get translated string by key with proper fallback and logging.
        Supports dynamic placeholder replacement (e.g., {min}, {max}).
        
        Args:
            key: Translation key (e.g., "validation.phone_empty")
            default: Default value if key not found
            **kwargs: Format arguments for placeholders (e.g., min=3, max=50)
                     Will replace {min} with 3, {max} with 50 in the string
            
        Returns:
            str: Translated string or default value
            
        Examples:
            T("validation.age_min", min=18)
            T("validation.password_min", min=6)
            T("validation.phone_invalid", min=7, max=15)
        """
        if not cls._is_loaded:
            logger.warning("TranslationService not initialized. Call initialize() first.")
            return default
        
        keys = key.split(".")
        value = cls._translations.get(cls._current_language, {})
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    # Log missing key once per key (avoid spam)
                    if cls._debug_mode and key not in cls._missing_keys:
                        cls._missing_keys.add(key)
                        logger.warning(
                            f"Missing translation key '{key}' in language '{cls._current_language}'"
                        )
                    return default
            else:
                if cls._debug_mode and key not in cls._missing_keys:
                    cls._missing_keys.add(key)
                    logger.warning(f"Invalid path for key '{key}'")
                return default
        
        result = value if value else default
        
        # Format the string with provided kwargs if any
        if kwargs and isinstance(result, str):
            try:
                result = result.format(**kwargs)
            except KeyError as e:
                logger.warning(
                    f"Missing placeholder in translation '{key}': {str(e)}"
                )
        
        return result
    
    @classmethod
    def set_language(cls, language: str):
        """
        Switch to different language with validation.
        
        Args:
            language: Language code ("en", "tr", "ko", etc.)
            
        Raises:
            ValueError: If language not available
        """
        if not cls._is_loaded:
            logger.warning("TranslationService not initialized. Call initialize() first.")
            return
        
        if language in cls._translations:
            cls._current_language = language
            logger.info(f"Language switched to: {language}")
        else:
            available = list(cls._translations.keys())
            error_msg = (
                f"Language '{language}' not available. "
                f"Available: {available}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    @classmethod
    def get_current_language(cls) -> str:
        """Get current language code."""
        return cls._current_language
    
    @classmethod
    def get_available_languages(cls) -> list:
        """Get list of available languages."""
        return list(cls._translations.keys())
    
    @classmethod
    def validate_keys_consistency(cls) -> dict:
        """
        Validate that all language files have the same keys (for QA).
        
        Returns:
            dict: Report of inconsistencies
        """
        if not cls._translations:
            logger.warning("No translations loaded")
            return {}
        
        # Get reference language keys
        reference_lang = "en"
        if reference_lang not in cls._translations:
            reference_lang = list(cls._translations.keys())[0]
        
        reference_keys = cls._get_all_keys(
            cls._translations[reference_lang]
        )
        
        report = {
            "reference_language": reference_lang,
            "reference_key_count": len(reference_keys),
            "languages": {}
        }
        
        for lang, translations in cls._translations.items():
            lang_keys = cls._get_all_keys(translations)
            missing = reference_keys - lang_keys
            extra = lang_keys - reference_keys
            
            report["languages"][lang] = {
                "key_count": len(lang_keys),
                "missing_keys": sorted(missing) if missing else [],
                "extra_keys": sorted(extra) if extra else [],
                "is_consistent": len(missing) == 0 and len(extra) == 0
            }
        
        return report
    
    @classmethod
    def _get_all_keys(cls, obj: dict, prefix: str = "") -> set:
        """Recursively get all dot-notation keys from nested dict."""
        keys = set()
        for k, v in obj.items():
            full_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                keys.update(cls._get_all_keys(v, full_key))
            else:
                keys.add(full_key)
        return keys


# Global function for easier usage
def T(key: str, default: str = "", **kwargs) -> str:
    """
    Shorthand for TranslationService.get()
    
    Usage:
        T("login.title")
        T("validation.age_min", min=18)
        T("validation.password_min", min=6)
    """
    return TranslationService.get(key, default, **kwargs)
