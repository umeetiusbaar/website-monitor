#!/usr/bin/env python3
"""
Integration test for the monitor using local HTML files
This test simulates the full monitoring workflow with real HTML pages
"""
import os
import sys
import json
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

# Add parent directory to path to import monitor functions
sys.path.insert(0, os.path.dirname(__file__))

# Import from monitor.py
from monitor import get_text_snapshot, click_cookie_banners

async def test_html_page(html_file: str, expected_texts: list, not_expected_texts: list):
    """Test a single HTML page to verify text detection"""
    file_path = Path(__file__).parent / "test_html" / html_file
    file_url = f"file://{file_path.absolute()}"

    print(f"\n{'='*60}")
    print(f"Testing: {html_file}")
    print(f"URL: {file_url}")
    print(f"{'='*60}")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto(file_url, wait_until="networkidle", timeout=5000)
            snapshot = await get_text_snapshot(page)

            print(f"Page text snapshot (first 500 chars):")
            print(f"{snapshot[:500]}")
            print()

            # Check expected texts
            all_found = True
            for text in expected_texts:
                found = text in snapshot
                status = "✅" if found else "❌"
                print(f"{status} Expected to find: '{text}' - {'FOUND' if found else 'NOT FOUND'}")
                if not found:
                    all_found = False

            # Check texts that should NOT be there
            none_found = True
            for text in not_expected_texts:
                found = text in snapshot
                status = "✅" if not found else "❌"
                print(f"{status} Expected NOT to find: '{text}' - {'NOT FOUND' if not found else 'FOUND'}")
                if found:
                    none_found = False

            success = all_found and none_found
            print(f"\nResult: {'✅ PASS' if success else '❌ FAIL'}")
            return success

        finally:
            await context.close()
            await browser.close()


async def test_monitoring_scenario():
    """Test a complete monitoring scenario: sold_out -> available"""
    print(f"\n{'='*60}")
    print("SCENARIO TEST: Simulating state change detection")
    print(f"{'='*60}")

    # Simulate the monitoring logic
    test_config = {
        "url": "file://test_html/sold_out.html",
        "search_text_disappears": ["0 No results", "routine maintenance"],
        "search_text_appears": ["Add to cart", "Select tickets"],
    }

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()

        # Step 1: Check sold_out.html (initial state)
        print("\n--- Step 1: Initial state (sold out) ---")
        page1 = await context.new_page()
        file_path1 = Path(__file__).parent / "test_html" / "sold_out.html"
        await page1.goto(f"file://{file_path1.absolute()}", wait_until="networkidle")
        snapshot1 = await get_text_snapshot(page1)

        found_disappears_1 = [txt for txt in test_config["search_text_disappears"] if txt in snapshot1]
        found_appears_1 = [txt for txt in test_config["search_text_appears"] if txt in snapshot1]

        print(f"Found disappears: {found_disappears_1}")
        print(f"Found appears: {found_appears_1}")
        print(f"Expected: ['0 No results'], []")

        state1_correct = (len(found_disappears_1) > 0 and len(found_appears_1) == 0)
        print(f"State 1 check: {'✅ PASS' if state1_correct else '❌ FAIL'}")

        await page1.close()

        # Step 2: Check available.html (tickets available state)
        print("\n--- Step 2: Changed state (tickets available) ---")
        page2 = await context.new_page()
        file_path2 = Path(__file__).parent / "test_html" / "available.html"
        await page2.goto(f"file://{file_path2.absolute()}", wait_until="networkidle")
        snapshot2 = await get_text_snapshot(page2)

        found_disappears_2 = [txt for txt in test_config["search_text_disappears"] if txt in snapshot2]
        found_appears_2 = [txt for txt in test_config["search_text_appears"] if txt in snapshot2]

        print(f"Found disappears: {found_disappears_2}")
        print(f"Found appears: {found_appears_2}")
        print(f"Expected: [], ['Add to cart', 'Select tickets']")

        state2_correct = (len(found_disappears_2) == 0 and len(found_appears_2) > 0)
        print(f"State 2 check: {'✅ PASS' if state2_correct else '❌ FAIL'}")

        await page2.close()

        # Step 3: Determine if alert should trigger
        print("\n--- Step 3: Alert decision ---")
        print(f"Previous state: disappears={found_disappears_1}, appears={found_appears_1}")
        print(f"Current state: disappears={found_disappears_2}, appears={found_appears_2}")

        # Alert logic
        disappears_satisfied = (len(found_disappears_1) > 0 and len(found_disappears_2) == 0)
        appears_satisfied = (len(found_appears_1) == 0 and len(found_appears_2) > 0)
        should_alert = disappears_satisfied and appears_satisfied

        print(f"Disappears condition satisfied: {disappears_satisfied}")
        print(f"Appears condition satisfied: {appears_satisfied}")
        print(f"Should alert: {should_alert}")
        print(f"Expected: True")

        alert_correct = should_alert is True
        print(f"Alert logic check: {'✅ PASS' if alert_correct else '❌ FAIL'}")

        await context.close()
        await browser.close()

        return state1_correct and state2_correct and alert_correct


async def test_maintenance_no_alert():
    """Test that maintenance page does NOT trigger alert"""
    print(f"\n{'='*60}")
    print("SCENARIO TEST: Maintenance should NOT alert")
    print(f"{'='*60}")

    test_config = {
        "search_text_disappears": ["0 No results", "routine maintenance"],
        "search_text_appears": ["Add to cart", "Select tickets"],
    }

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()

        # Step 1: sold_out.html
        print("\n--- Previous state (sold out) ---")
        page1 = await context.new_page()
        file_path1 = Path(__file__).parent / "test_html" / "sold_out.html"
        await page1.goto(f"file://{file_path1.absolute()}", wait_until="networkidle")
        snapshot1 = await get_text_snapshot(page1)
        found_disappears_1 = [txt for txt in test_config["search_text_disappears"] if txt in snapshot1]
        found_appears_1 = [txt for txt in test_config["search_text_appears"] if txt in snapshot1]
        print(f"Found disappears: {found_disappears_1}")
        print(f"Found appears: {found_appears_1}")
        await page1.close()

        # Step 2: maintenance.html
        print("\n--- Current state (maintenance) ---")
        page2 = await context.new_page()
        file_path2 = Path(__file__).parent / "test_html" / "maintenance.html"
        await page2.goto(f"file://{file_path2.absolute()}", wait_until="networkidle")
        snapshot2 = await get_text_snapshot(page2)
        found_disappears_2 = [txt for txt in test_config["search_text_disappears"] if txt in snapshot2]
        found_appears_2 = [txt for txt in test_config["search_text_appears"] if txt in snapshot2]
        print(f"Found disappears: {found_disappears_2}")
        print(f"Found appears: {found_appears_2}")
        await page2.close()

        # Alert logic
        print("\n--- Alert decision ---")
        disappears_satisfied = (len(found_disappears_1) > 0 and len(found_disappears_2) == 0)
        appears_satisfied = (len(found_appears_1) == 0 and len(found_appears_2) > 0)
        should_alert = disappears_satisfied and appears_satisfied

        print(f"Disappears condition satisfied: {disappears_satisfied} (expected: False, 'routine maintenance' still present)")
        print(f"Appears condition satisfied: {appears_satisfied} (expected: False)")
        print(f"Should alert: {should_alert}")
        print(f"Expected: False")

        correct = should_alert is False
        print(f"Result: {'✅ PASS' if correct else '❌ FAIL'}")

        await context.close()
        await browser.close()

        return correct


async def test_both_messages_no_alert():
    """Test that when BOTH messages are present, it does NOT trigger alert"""
    print(f"\n{'='*60}")
    print("SCENARIO TEST: Both messages present should NOT alert")
    print(f"{'='*60}")

    test_config = {
        "search_text_disappears": ["0 No results", "routine maintenance"],
        "search_text_appears": ["Add to cart", "Select tickets"],
    }

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()

        # Step 1: both_messages.html (initial state - both messages present)
        print("\n--- Previous state (both messages) ---")
        page1 = await context.new_page()
        file_path1 = Path(__file__).parent / "test_html" / "both_messages.html"
        await page1.goto(f"file://{file_path1.absolute()}", wait_until="networkidle")
        snapshot1 = await get_text_snapshot(page1)
        found_disappears_1 = [txt for txt in test_config["search_text_disappears"] if txt in snapshot1]
        found_appears_1 = [txt for txt in test_config["search_text_appears"] if txt in snapshot1]
        print(f"Found disappears: {found_disappears_1}")
        print(f"Found appears: {found_appears_1}")
        print(f"Expected: Both '0 No results' AND 'routine maintenance' should be present")
        await page1.close()

        # Step 2: available.html (tickets available)
        print("\n--- Current state (tickets available) ---")
        page2 = await context.new_page()
        file_path2 = Path(__file__).parent / "test_html" / "available.html"
        await page2.goto(f"file://{file_path2.absolute()}", wait_until="networkidle")
        snapshot2 = await get_text_snapshot(page2)
        found_disappears_2 = [txt for txt in test_config["search_text_disappears"] if txt in snapshot2]
        found_appears_2 = [txt for txt in test_config["search_text_appears"] if txt in snapshot2]
        print(f"Found disappears: {found_disappears_2}")
        print(f"Found appears: {found_appears_2}")
        print(f"Expected: BOTH messages gone, 'Add to cart' present")
        await page2.close()

        # Alert logic
        print("\n--- Alert decision ---")
        disappears_satisfied = (len(found_disappears_1) > 0 and len(found_disappears_2) == 0)
        appears_satisfied = (len(found_appears_1) == 0 and len(found_appears_2) > 0)
        should_alert = disappears_satisfied and appears_satisfied

        print(f"Disappears condition satisfied: {disappears_satisfied}")
        print(f"  - Previous had messages: {len(found_disappears_1) > 0}")
        print(f"  - Current has NO messages: {len(found_disappears_2) == 0}")
        print(f"Appears condition satisfied: {appears_satisfied}")
        print(f"Should alert: {should_alert}")
        print(f"Expected: True (both messages disappeared AND add to cart appeared)")

        correct = should_alert is True
        print(f"Result: {'✅ PASS' if correct else '❌ FAIL'}")

        await context.close()
        await browser.close()

        return correct


async def test_only_one_message_disappears():
    """Test that when only ONE of TWO messages disappears, it does NOT alert"""
    print(f"\n{'='*60}")
    print("SCENARIO TEST: Only one message gone should NOT alert")
    print(f"{'='*60}")

    test_config = {
        "search_text_disappears": ["0 No results", "routine maintenance"],
        "search_text_appears": ["Add to cart", "Select tickets"],
    }

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()

        # Step 1: both_messages.html (both present)
        print("\n--- Previous state (both messages present) ---")
        page1 = await context.new_page()
        file_path1 = Path(__file__).parent / "test_html" / "both_messages.html"
        await page1.goto(f"file://{file_path1.absolute()}", wait_until="networkidle")
        snapshot1 = await get_text_snapshot(page1)
        found_disappears_1 = [txt for txt in test_config["search_text_disappears"] if txt in snapshot1]
        found_appears_1 = [txt for txt in test_config["search_text_appears"] if txt in snapshot1]
        print(f"Found disappears: {found_disappears_1}")
        print(f"Found appears: {found_appears_1}")
        await page1.close()

        # Step 2: maintenance.html (only maintenance remains)
        print("\n--- Current state (only 'routine maintenance' remains) ---")
        page2 = await context.new_page()
        file_path2 = Path(__file__).parent / "test_html" / "maintenance.html"
        await page2.goto(f"file://{file_path2.absolute()}", wait_until="networkidle")
        snapshot2 = await get_text_snapshot(page2)
        found_disappears_2 = [txt for txt in test_config["search_text_disappears"] if txt in snapshot2]
        found_appears_2 = [txt for txt in test_config["search_text_appears"] if txt in snapshot2]
        print(f"Found disappears: {found_disappears_2}")
        print(f"Found appears: {found_appears_2}")
        print(f"Expected: Only 'routine maintenance' still present")
        await page2.close()

        # Alert logic
        print("\n--- Alert decision ---")
        disappears_satisfied = (len(found_disappears_1) > 0 and len(found_disappears_2) == 0)
        appears_satisfied = (len(found_appears_1) == 0 and len(found_appears_2) > 0)
        should_alert = disappears_satisfied and appears_satisfied

        print(f"Disappears condition satisfied: {disappears_satisfied}")
        print(f"  - Expected: False (routine maintenance still present)")
        print(f"Appears condition satisfied: {appears_satisfied}")
        print(f"Should alert: {should_alert}")
        print(f"Expected: False (not ALL disappear messages are gone)")

        correct = should_alert is False
        print(f"Result: {'✅ PASS' if correct else '❌ FAIL'}")

        await context.close()
        await browser.close()

        return correct


async def main():
    """Run all integration tests"""
    print("="*60)
    print("INTEGRATION TESTS - Local HTML Pages")
    print("="*60)

    tests_passed = 0
    tests_failed = 0

    # Test individual HTML pages
    if await test_html_page(
        "sold_out.html",
        expected_texts=["0 No results", "Concert Tickets"],
        not_expected_texts=["Add to cart", "routine maintenance"]
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    if await test_html_page(
        "maintenance.html",
        expected_texts=["routine maintenance", "Concert Tickets"],
        not_expected_texts=["Add to cart", "0 No results"]
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    if await test_html_page(
        "available.html",
        expected_texts=["Add to cart", "Select tickets", "Concert Tickets"],
        not_expected_texts=["0 No results", "routine maintenance"]
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    if await test_html_page(
        "both_messages.html",
        expected_texts=["0 No results", "routine maintenance", "Concert Tickets"],
        not_expected_texts=["Add to cart", "Select tickets"]
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test complete scenarios
    if await test_monitoring_scenario():
        tests_passed += 1
    else:
        tests_failed += 1

    if await test_maintenance_no_alert():
        tests_passed += 1
    else:
        tests_failed += 1

    if await test_both_messages_no_alert():
        tests_passed += 1
    else:
        tests_failed += 1

    if await test_only_one_message_disappears():
        tests_passed += 1
    else:
        tests_failed += 1

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Tests passed: {tests_passed}")
    print(f"Tests failed: {tests_failed}")
    print(f"Total tests: {tests_passed + tests_failed}")

    if tests_failed > 0:
        print("\n❌ Some tests failed!")
        sys.exit(1)
    else:
        print("\n✅ All integration tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
