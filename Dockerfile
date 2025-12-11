# Use Python 3.14 base image
FROM python:3.14-slim

# Install system dependencies required by Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxkbcommon0 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

# Copy application files
COPY monitor.py .
COPY healthcheck.py .
COPY config/ ./config/

# Create directory for screenshots and data
RUN mkdir -p /data/screens

# Set environment variables with defaults
ENV STATE_FILE=/data/tm_state.json \
    CONFIG_FILE=/app/config/urls.yaml \
    POLL_SECONDS=60 \
    HEADLESS=true \
    HEARTBEAT_FILE=/data/heartbeat.txt

# Health check: verify the app is responsive by checking heartbeat
# Check every 60s, start checking after 120s, timeout after 10s, 3 retries before unhealthy
HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=3 \
    CMD python /app/healthcheck.py || exit 1

# Run the monitor
CMD ["python", "-u", "monitor.py"]
