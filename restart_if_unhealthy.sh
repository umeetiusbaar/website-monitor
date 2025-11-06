#!/bin/bash
# Script to restart the website-monitor container if it's unhealthy
# Usage: Add to crontab to run every few minutes
# Example crontab entry (check every 5 minutes):
# */5 * * * * /path/to/website-monitor/restart_if_unhealthy.sh >> /var/log/monitor-restart.log 2>&1

# Set PATH to find docker and other commands (important for cron)
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

CONTAINER_NAME="website-monitor"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the script directory (where docker-compose.yml should be)
cd "$SCRIPT_DIR" || {
    echo "$(date): ERROR: Cannot change to directory $SCRIPT_DIR"
    exit 1
}

echo "$(date): Checking health of $CONTAINER_NAME (from $SCRIPT_DIR)..."

# Check if container exists
if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "$(date): Container ${CONTAINER_NAME} not found"
    exit 0
fi

# Get container health status
HEALTH=$(docker inspect --format='{{.State.Health.Status}}' ${CONTAINER_NAME} 2>/dev/null)

if [ "$HEALTH" = "unhealthy" ]; then
    echo "$(date): Container ${CONTAINER_NAME} is unhealthy, restarting..."
    docker compose restart ${CONTAINER_NAME}
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 0 ]; then
        echo "$(date): Container ${CONTAINER_NAME} restarted successfully"
    else
        echo "$(date): ERROR: Failed to restart container (exit code: $EXIT_CODE)"
    fi
else
    echo "$(date): Container ${CONTAINER_NAME} is ${HEALTH:-running without healthcheck}"
fi
