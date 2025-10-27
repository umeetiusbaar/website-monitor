#!/usr/bin/env python3
"""
Test configuration validation and loading with multiple search_text_disappears
"""
import sys
import os
import tempfile
import yaml
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from monitor import load_config


def test_config_with_multiple_disappears():
    """Test configuration with multiple items in search_text_disappears list"""
    print("\n" + "="*60)
    print("TEST: Config with multiple search_text_disappears")
    print("="*60)

    config_data = {
        "urls": [
            {
                "url": "https://example.com/tickets",
                "search_text_disappears": ["0 No results", "routine maintenance"],
                "search_text_appears": ["Add to cart"],
                "note": "Test with two disappear texts"
            }
        ]
    }

    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_file = f.name

    try:
        # Temporarily override CONFIG_FILE
        import monitor
        original_config = monitor.CONFIG_FILE
        monitor.CONFIG_FILE = temp_file

        # Load config
        config = load_config()

        # Restore original
        monitor.CONFIG_FILE = original_config

        print("\nLoaded config:")
        print(f"  URL: {config[0]['url']}")
        print(f"  search_text_disappears: {config[0]['search_text_disappears']}")
        print(f"  search_text_appears: {config[0]['search_text_appears']}")
        print(f"  note: {config[0].get('note', 'N/A')}")

        # Verify
        assert len(config) == 1, "Should have 1 URL"
        assert config[0]['search_text_disappears'] == ["0 No results", "routine maintenance"], \
            "Should have both disappear texts"
        assert config[0]['search_text_appears'] == ["Add to cart"], \
            "Should have one appear text"

        print("\n✅ TEST PASSED: Multiple search_text_disappears loaded correctly")
        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        os.unlink(temp_file)


def test_config_with_single_string_disappears():
    """Test configuration with single string search_text_disappears (should be converted to list)"""
    print("\n" + "="*60)
    print("TEST: Config with single string search_text_disappears")
    print("="*60)

    config_data = {
        "urls": [
            {
                "url": "https://example.com/product",
                "search_text_disappears": "Out of stock",
                "note": "Test with single string (not list)"
            }
        ]
    }

    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_file = f.name

    try:
        # Temporarily override CONFIG_FILE
        import monitor
        original_config = monitor.CONFIG_FILE
        monitor.CONFIG_FILE = temp_file

        # Load config
        config = load_config()

        # Restore original
        monitor.CONFIG_FILE = original_config

        print("\nLoaded config:")
        print(f"  URL: {config[0]['url']}")
        print(f"  search_text_disappears: {config[0]['search_text_disappears']}")
        print(f"  search_text_appears: {config[0]['search_text_appears']}")

        # Verify - should be converted to list
        assert len(config) == 1, "Should have 1 URL"
        assert config[0]['search_text_disappears'] == ["Out of stock"], \
            "Single string should be converted to list"
        assert config[0]['search_text_appears'] == [], \
            "Should have empty appears list"

        print("\n✅ TEST PASSED: Single string converted to list correctly")
        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        os.unlink(temp_file)


def test_config_old_format_with_list():
    """Test old format (search_text + mode) with list of texts"""
    print("\n" + "="*60)
    print("TEST: Old format with list of search_text")
    print("="*60)

    config_data = {
        "urls": [
            {
                "url": "https://example.com/product",
                "search_text": ["Sold out", "Not available"],
                "mode": "disappears",
                "note": "Old format with list"
            }
        ]
    }

    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_file = f.name

    try:
        # Temporarily override CONFIG_FILE
        import monitor
        original_config = monitor.CONFIG_FILE
        monitor.CONFIG_FILE = temp_file

        # Load config
        config = load_config()

        # Restore original
        monitor.CONFIG_FILE = original_config

        print("\nLoaded config:")
        print(f"  URL: {config[0]['url']}")
        print(f"  search_text_disappears: {config[0]['search_text_disappears']}")
        print(f"  search_text_appears: {config[0]['search_text_appears']}")

        # Verify - should be converted to new format
        assert len(config) == 1, "Should have 1 URL"
        assert config[0]['search_text_disappears'] == ["Sold out", "Not available"], \
            "Old format list should be preserved in new format"
        assert config[0]['search_text_appears'] == [], \
            "Should have empty appears list"

        print("\n✅ TEST PASSED: Old format with list converted correctly")
        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        os.unlink(temp_file)


def test_config_both_conditions():
    """Test config with both disappears AND appears conditions"""
    print("\n" + "="*60)
    print("TEST: Config with both disappears AND appears")
    print("="*60)

    config_data = {
        "urls": [
            {
                "url": "https://example.com/tickets",
                "search_text_disappears": ["0 No results", "routine maintenance"],
                "search_text_appears": ["Add to cart", "Select tickets"],
                "note": "Both conditions specified"
            }
        ]
    }

    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_file = f.name

    try:
        # Temporarily override CONFIG_FILE
        import monitor
        original_config = monitor.CONFIG_FILE
        monitor.CONFIG_FILE = temp_file

        # Load config
        config = load_config()

        # Restore original
        monitor.CONFIG_FILE = original_config

        print("\nLoaded config:")
        print(f"  URL: {config[0]['url']}")
        print(f"  search_text_disappears: {config[0]['search_text_disappears']}")
        print(f"  search_text_appears: {config[0]['search_text_appears']}")

        # Verify
        assert len(config) == 1, "Should have 1 URL"
        assert config[0]['search_text_disappears'] == ["0 No results", "routine maintenance"], \
            "Should have both disappear texts"
        assert config[0]['search_text_appears'] == ["Add to cart", "Select tickets"], \
            "Should have both appear texts"

        print("\n✅ TEST PASSED: Both conditions loaded correctly")
        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        os.unlink(temp_file)


def main():
    """Run all config tests"""
    print("="*60)
    print("CONFIGURATION TESTS")
    print("="*60)

    tests = [
        test_config_with_multiple_disappears,
        test_config_with_single_string_disappears,
        test_config_old_format_with_list,
        test_config_both_conditions,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n❌ TEST EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Tests passed: {passed}")
    print(f"Tests failed: {failed}")
    print(f"Total tests: {passed + failed}")

    if failed > 0:
        print("\n❌ Some tests failed!")
        sys.exit(1)
    else:
        print("\n✅ All configuration tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
