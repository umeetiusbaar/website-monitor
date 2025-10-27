#!/usr/bin/env python3
"""
Test script for the enhanced monitoring logic
"""
import sys
from typing import Dict, Any, List

# Simulate the alert logic from monitor.py
def should_alert(
    disappears_list: List[str],
    appears_list: List[str],
    prev_found_disappears: List[str],
    prev_found_appears: List[str],
    curr_found_disappears: List[str],
    curr_found_appears: List[str]
) -> bool:
    """
    Returns True if an alert should be triggered.

    Alert logic:
    - ALL disappears texts must be gone (were present, now all gone)
    - At least ONE appears text must be present (was not present, now at least one is there)
    """
    # Check disappears condition (if specified)
    disappears_satisfied = True
    if disappears_list:
        # Were any disappears texts present before? Are they all gone now?
        disappears_satisfied = (len(prev_found_disappears) > 0 and
                              len(curr_found_disappears) == 0)

    # Check appears condition (if specified)
    appears_satisfied = True
    if appears_list:
        # Were all appears texts absent before? Is at least one present now?
        appears_satisfied = (len(prev_found_appears) == 0 and
                           len(curr_found_appears) > 0)

    # Alert if both conditions are satisfied
    return disappears_satisfied and appears_satisfied


def test_scenario(name: str, **kwargs):
    """Run a test scenario and print the result"""
    result = should_alert(**kwargs)
    print(f"\n{'='*60}")
    print(f"Test: {name}")
    print(f"{'='*60}")
    print(f"disappears_list: {kwargs['disappears_list']}")
    print(f"appears_list: {kwargs['appears_list']}")
    print(f"\nPREVIOUS STATE:")
    print(f"  found_disappears: {kwargs['prev_found_disappears']}")
    print(f"  found_appears: {kwargs['prev_found_appears']}")
    print(f"\nCURRENT STATE:")
    print(f"  found_disappears: {kwargs['curr_found_disappears']}")
    print(f"  found_appears: {kwargs['curr_found_appears']}")
    print(f"\nResult: {'🔔 ALERT!' if result else '⏸️  No alert'}")
    return result


def main():
    print("Testing Enhanced Monitoring Logic")
    print("="*60)

    tests_passed = 0
    tests_failed = 0

    # Test 1: Ticketmaster scenario - Should ALERT
    # Both "0 No results" and "maintenance" were there, now both gone
    # AND "Add to cart" appears
    if test_scenario(
        "Ticketmaster: Tickets available!",
        disappears_list=["0 No results", "routine maintenance"],
        appears_list=["Add to cart", "Select tickets"],
        prev_found_disappears=["0 No results", "routine maintenance"],
        prev_found_appears=[],
        curr_found_disappears=[],
        curr_found_appears=["Add to cart"]
    ):
        print("✅ Expected: ALERT - Test PASSED")
        tests_passed += 1
    else:
        print("❌ Expected: ALERT - Test FAILED")
        tests_failed += 1

    # Test 2: Maintenance only scenario - Should NOT alert
    # "0 No results" gone but "maintenance" still there
    if not test_scenario(
        "Maintenance still showing",
        disappears_list=["0 No results", "routine maintenance"],
        appears_list=["Add to cart", "Select tickets"],
        prev_found_disappears=["0 No results", "routine maintenance"],
        prev_found_appears=[],
        curr_found_disappears=["routine maintenance"],  # Still there!
        curr_found_appears=[]
    ):
        print("✅ Expected: No alert - Test PASSED")
        tests_passed += 1
    else:
        print("❌ Expected: No alert - Test FAILED")
        tests_failed += 1

    # Test 3: Texts disappeared but no "Add to cart" - Should NOT alert
    if not test_scenario(
        "Texts gone but no add to cart button",
        disappears_list=["0 No results", "routine maintenance"],
        appears_list=["Add to cart", "Select tickets"],
        prev_found_disappears=["0 No results"],
        prev_found_appears=[],
        curr_found_disappears=[],
        curr_found_appears=[]  # Nothing appeared!
    ):
        print("✅ Expected: No alert - Test PASSED")
        tests_passed += 1
    else:
        print("❌ Expected: No alert - Test FAILED")
        tests_failed += 1

    # Test 4: Old format - disappears only - Should ALERT
    if test_scenario(
        "Old format: Text disappeared",
        disappears_list=["Out of stock"],
        appears_list=[],
        prev_found_disappears=["Out of stock"],
        prev_found_appears=[],
        curr_found_disappears=[],
        curr_found_appears=[]
    ):
        print("✅ Expected: ALERT - Test PASSED")
        tests_passed += 1
    else:
        print("❌ Expected: ALERT - Test FAILED")
        tests_failed += 1

    # Test 5: Old format - appears only - Should ALERT
    if test_scenario(
        "Old format: Text appeared",
        disappears_list=[],
        appears_list=["In stock"],
        prev_found_disappears=[],
        prev_found_appears=[],
        curr_found_disappears=[],
        curr_found_appears=["In stock"]
    ):
        print("✅ Expected: ALERT - Test PASSED")
        tests_passed += 1
    else:
        print("❌ Expected: ALERT - Test FAILED")
        tests_failed += 1

    # Test 6: No change - Should NOT alert
    if not test_scenario(
        "No change in state",
        disappears_list=["0 No results"],
        appears_list=["Add to cart"],
        prev_found_disappears=["0 No results"],
        prev_found_appears=[],
        curr_found_disappears=["0 No results"],  # Still there
        curr_found_appears=[]  # Still not there
    ):
        print("✅ Expected: No alert - Test PASSED")
        tests_passed += 1
    else:
        print("❌ Expected: No alert - Test FAILED")
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
        print("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
