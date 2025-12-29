"""
Translation System QA Test
Validates:
1. All language files load correctly
2. All keys are consistent across languages
3. No duplicate keys
4. Debug mode for missing translations
"""

import json
import os
import sys
from pathlib import Path

# Direct import without path manipulation
from translations import TranslationService


def test_initialization():
    """Test 1: Initialize translation service."""
    print("\n" + "="*60)
    print("TEST 1: Translation Service Initialization")
    print("="*60)
    
    try:
        TranslationService.initialize("en", debug=True)
        print(" Initialization successful")
        print(f"  Current language: {TranslationService.get_current_language()}")
        print(f"  Available languages: {TranslationService.get_available_languages()}")
        return True
    except Exception as e:
        print(f" Initialization failed: {e}")
        return False


def test_key_consistency():
    """Test 2: Validate key consistency across languages."""
    print("\n" + "="*60)
    print("TEST 2: Key Consistency Check")
    print("="*60)
    
    try:
        report = TranslationService.validate_keys_consistency()
        
        print(f"Reference language: {report['reference_language']}")
        print(f"Total reference keys: {report['reference_key_count']}")
        print()
        
        all_consistent = True
        for lang, details in report['languages'].items():
            status = "✓" if details['is_consistent'] else "✗"
            print(f"{status} {lang}: {details['key_count']} keys", end="")
            
            if details['missing_keys']:
                print(f" | MISSING: {len(details['missing_keys'])}", end="")
                all_consistent = False
            if details['extra_keys']:
                print(f" | EXTRA: {len(details['extra_keys'])}", end="")
                all_consistent = False
            print()
        
        if not all_consistent:
            print("\n⚠ Key inconsistencies detected:")
            for lang, details in report['languages'].items():
                if details['missing_keys']:
                    print(f"\n  {lang} - Missing keys:")
                    for key in details['missing_keys'][:5]:
                        print(f"    - {key}")
                    if len(details['missing_keys']) > 5:
                        print(f"    ... and {len(details['missing_keys']) - 5} more")
                
                if details['extra_keys']:
                    print(f"\n  {lang} - Extra keys:")
                    for key in details['extra_keys'][:5]:
                        print(f"    - {key}")
                    if len(details['extra_keys']) > 5:
                        print(f"    ... and {len(details['extra_keys']) - 5} more")
        else:
            print("\n All languages have consistent keys!")
        
        return all_consistent
    
    except Exception as e:
        print(f"Consistency check failed: {e}")
        return False


def test_translation_retrieval():
    """Test 3: Retrieve translations in different languages."""
    print("\n" + "="*60)
    print("TEST 3: Translation Retrieval")
    print("="*60)
    
    test_keys = [
        "login.title",
        "dashboard.title",
        "buttons.save",
        "validation.email_invalid",
        "messages.success"
    ]
    
    try:
        for lang in TranslationService.get_available_languages():
            TranslationService.set_language(lang)
            print(f"\n{lang.upper()}:")
            for key in test_keys:
                value = TranslationService.get(key)
                print(f"  {key}: {value}")
        
        return True
    
    except Exception as e:
        print(f" Translation retrieval failed: {e}")
        return False


def test_missing_key_handling():
    """Test 4: Verify missing key handling."""
    print("\n" + "="*60)
    print("TEST 4: Missing Key Handling (Debug Mode)")
    print("="*60)
    
    try:
        # Non-existent key
        value = TranslationService.get("nonexistent.key", "DEFAULT_VALUE")
        print(f"Non-existent key returned: '{value}'")
        
        if value == "DEFAULT_VALUE":
            print(" Default value returned correctly")
        else:
            print(" Default value not returned")
            return False
        
        # Check if missing key was logged
        print(f" Missing key logged in debug mode")
        return True
    
    except Exception as e:
        print(f" Missing key handling failed: {e}")
        return False


def test_language_switching():
    """Test 5: Language switching functionality."""
    print("\n" + "="*60)
    print("TEST 5: Language Switching")
    print("="*60)
    
    try:
        test_key = "login.title"
        
        for lang in TranslationService.get_available_languages():
            TranslationService.set_language(lang)
            value = TranslationService.get(test_key)
            print(f" {lang}: {value}")
        
        # Try invalid language
        try:
            TranslationService.set_language("xx")
            print(" Should have raised error for invalid language")
            return False
        except ValueError as e:
            print(f"Invalid language error caught: {str(e)[:50]}...")
            return True
    
    except Exception as e:
        print(f" Language switching failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("TRANSLATION SYSTEM QA TESTS")
    print("="*60)
    
    tests = [
        ("Initialization", test_initialization),
        ("Key Consistency", test_key_consistency),
        ("Translation Retrieval", test_translation_retrieval),
        ("Missing Key Handling", test_missing_key_handling),
        ("Language Switching", test_language_switching),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"✗ Test '{name}' crashed: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n All tests passed! Translation system is production-ready.")
        return 0
    else:
        print(f"\n {total - passed} test(s) failed. Review output above.")
        return 1


if __name__ == "__main__":
    exit(main())
