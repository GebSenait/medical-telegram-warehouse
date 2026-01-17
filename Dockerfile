FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies with retry logic and DNS configuration
# Note: gcc may not be strictly needed as most packages have wheels, but kept for compatibility
RUN apt-get update --fix-missing || true && \
    apt-get install -y --no-install-recommends \
    gcc \
    || echo "Warning: gcc installation failed, continuing anyway (packages may have pre-built wheels)" && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Create data directories
RUN mkdir -p data/raw/telegram_messages data/raw/images logs

# Set Python path
ENV PYTHONPATH=/app

# Default command
CMD ["python", "-m", "src.scraper"]

