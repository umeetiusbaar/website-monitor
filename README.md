# Website Monitor

A containerized Python application that monitors websites for content changes and sends Slack notifications.

## Features

- 🔍 Monitor multiple websites for content changes
- 🔔 Slack notifications when changes are detected
- 📸 Automatic screenshot capture on alerts
- 🐳 Fully containerized with Docker
- 🔄 Persistent state tracking between restarts
- ⚙️ Two monitoring modes: `appears` and `disappears`

## Quick Start

1. **Configure URLs to monitor:**

   Copy the example config and edit it:
   ```bash
   cp config/urls.yaml.example config/urls.yaml
   # Edit config/urls.yaml with your URLs
   ```

   Example configuration:
   ```yaml
   urls:
     - url: "https://example.com"
       search_text: "Out of stock"
       mode: "disappears"
       note: "Product availability"
   ```

2. **Set up Slack webhook (optional):**

   ```bash
   cp .env.example .env
   # Edit .env and add your SLACK_WEBHOOK URL
   ```

3. **Run with Docker Compose:**

   ```bash
   docker-compose up -d
   ```

4. **View logs:**

   ```bash
   docker-compose logs -f
   ```

## Configuration

### Monitoring Modes

- **`appears`**: Alerts when `search_text` appears on the page
- **`disappears`**: Alerts when `search_text` disappears from the page

### Environment Variables

- `SLACK_WEBHOOK` - Slack webhook URL for notifications
- `POLL_SECONDS` - Check interval in seconds (default: 60)
- `HEADLESS` - Run browser in headless mode (default: true)

## Local Development

```bash
# Set up virtual environment
python3.14 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run locally
python monitor.py
```

## Data Persistence

- **State file**: `./data/tm_state.json` - Tracks previous states
- **Screenshots**: `./data/screens/` - Alert screenshots

## Stopping the Monitor

```bash
docker-compose down
```

## License

Private project
