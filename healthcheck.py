#!/usr/bin/env python3
"""
Health check script for Docker container.
Verifies that the monitor is still running by checking the heartbeat file.
"""
import os
import sys
from datetime import datetime, UTC, timedelta

HEARTBEAT_FILE = os.getenv("HEARTBEAT_FILE", "/data/heartbeat.txt")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "60"))

# Allow up to 3x the poll interval before considering unhealthy
# This gives time for multiple URLs to be checked and handles temporary issues
MAX_AGE_SECONDS = POLL_SECONDS * 3

try:
    # Check if heartbeat file exists
    if not os.path.exists(HEARTBEAT_FILE):
        print(f"ERROR: Heartbeat file {HEARTBEAT_FILE} does not exist")
        sys.exit(1)

    # Read the heartbeat timestamp
    with open(HEARTBEAT_FILE, "r") as f:
        timestamp_str = f.read().strip()

    # Parse the timestamp
    heartbeat_time = datetime.fromisoformat(timestamp_str)

    # Get current time
    current_time = datetime.now(UTC)

    # Calculate age
    age = (current_time - heartbeat_time).total_seconds()

    if age > MAX_AGE_SECONDS:
        print(f"ERROR: Heartbeat is too old: {age:.0f}s (max: {MAX_AGE_SECONDS}s)")
        sys.exit(1)

    print(f"OK: Heartbeat is recent ({age:.0f}s old)")
    sys.exit(0)

except Exception as e:
    print(f"ERROR: Health check failed: {e}")
    sys.exit(1)
