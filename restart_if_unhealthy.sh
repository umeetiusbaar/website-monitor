#!/bin/bash
# Script to restart the website-monitor container if it's unhealthy
# Usage: Add to crontab to run every few minutes
# Example crontab entry (check every 5 minutes):
# */5 * * * * /path/to/website-monitor/restart_if_unhealthy.sh >> /var/log/monitor-restart.log 2>&1

CONTAINER_NAME="website-monitor"

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
    echo "$(date): Container ${CONTAINER_NAME} restarted"
else
    echo "$(date): Container ${CONTAINER_NAME} is ${HEALTH:-running without healthcheck}"
fi
