FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (minimal set)
RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set environment variables to optimize PyTorch installation
# Use CPU-only PyTorch to reduce image size (saves ~2.5GB)
ENV TORCH_CUDA_ARCH_LIST=""
ENV TORCH_NVCC_FLAGS=""
ENV FORCE_CPU_ONLY=1

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies with optimizations
# Strategy: Install CPU-only PyTorch first, then install other packages
# This prevents ultralytics from pulling CUDA-enabled PyTorch (saves ~2.5GB)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt && \
    pip cache purge && \
    rm -rf /root/.cache/pip /tmp/*

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Create data directories
RUN mkdir -p data/raw/telegram_messages data/raw/images data/processed logs

# Set Python path
ENV PYTHONPATH=/app

# Default command
CMD ["python", "-m", "src.scraper"]
