# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python website monitoring application project.

### Key Features
- Monitor changes on specified websites
- Send notifications via Slack when changes are detected
- Program can be containerized using Docker

## Environment Setup

- **Python Version**: 3.14.0 (WSL Ubuntu)

### Activating Python Virtual Environment

```bash
source .venv/bin/activate  # On Linux/Mac
.venv\Scripts\activate     # On Windows
```

### Installing Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

## Architecture

### Core Components

**monitor.py** - Main monitoring application with the following architecture:

1. **Configuration Layer** (lines 13-48)
   - Environment-based configuration via `os.getenv()`
   - YAML-based URL configuration in `config/urls.yaml`
   - State persistence via JSON file (`tm_state.json`)

2. **Browser Automation** (lines 60-116)
   - Uses Playwright with Chromium in headless mode
   - Automatic cookie banner dismissal (`click_cookie_banners()`)
   - Text snapshot extraction from page body
   - SHA-256 hashing for content comparison

3. **Monitoring Logic** (lines 117-192)
   - Continuous polling loop with configurable interval
   - Two detection modes:
     - `appears`: Alert when search_text appears on page
     - `disappears`: Alert when search_text disappears from page
   - State tracking to detect changes between checks
   - Screenshot capture on alert conditions

4. **Notification System** (lines 50-58)
   - Slack webhook integration
   - Fallback to console output when webhook not configured

### Configuration Files

**config/urls.yaml** - Your personal URL configuration (not committed to git):
- Copy from `config/urls.yaml.example` to get started
- This file is in `.gitignore` to keep your URLs private

Expected format:
```yaml
urls:
  - url: "https://example.com"
    search_text: "Out of stock"
    mode: "disappears"  # or "appears"
    note: "Optional description"
```

### Environment Variables

- `STATE_FILE`: Path to state persistence file (default: `tm_state.json`)
- `CONFIG_FILE`: Path to URL configuration (default: `config/urls.yaml`)
- `SLACK_WEBHOOK`: Slack webhook URL for notifications
- `POLL_SECONDS`: Polling interval in seconds (default: `60`)
- `HEADLESS`: Run browser in headless mode (default: `true`)

## Running the Monitor

```bash
# Activate virtual environment first
source .venv/bin/activate

# Run with default configuration
python monitor.py

# Run with custom settings
POLL_SECONDS=120 HEADLESS=false python monitor.py
```

## Docker Deployment

### Quick Start with Docker Compose

The easiest way to run the monitor is using Docker Compose:

```bash
# 1. Create a .env file with your Slack webhook (optional)
cp .env.example .env
# Edit .env and add your SLACK_WEBHOOK URL

# 2. Make sure your config/urls.yaml is set up with URLs to monitor

# 3. Build and start the container
docker-compose up -d

# 4. View logs
docker-compose logs -f

# 5. Stop the container
docker-compose down
```

### Manual Docker Build

```bash
# Build the image
docker build -t website-monitor .

# Run the container
docker run -d \
  --name website-monitor \
  --restart unless-stopped \
  -v $(pwd)/config:/app/config:ro \
  -v $(pwd)/data:/data \
  -e SLACK_WEBHOOK="your-webhook-url" \
  -e POLL_SECONDS=60 \
  website-monitor

# View logs
docker logs -f website-monitor

# Stop and remove
docker stop website-monitor && docker rm website-monitor
```

### Docker Configuration

**Volumes:**
- `./config:/app/config:ro` - URL configuration (read-only)
- `./data:/data` - State file and screenshots (persistent)

**Environment Variables:**
- `SLACK_WEBHOOK` - Slack webhook URL for notifications
- `POLL_SECONDS` - Polling interval in seconds (default: 60)
- `HEADLESS` - Run browser in headless mode (default: true)
- `STATE_FILE` - Path to state file (default: /data/tm_state.json)
- `CONFIG_FILE` - Path to config file (default: /app/config/urls.yaml)

**Data Persistence:**
- State file: Stored in `./data/tm_state.json`
- Screenshots: Stored in `./data/screens/`

### Updating the Monitor

```bash
# Pull latest changes and rebuild
git pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```
