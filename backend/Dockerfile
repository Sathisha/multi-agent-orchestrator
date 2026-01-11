# Multi-stage Dockerfile for optimized builds
FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies (this layer rarely changes)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Dependencies layer - only rebuilds when requirements.txt changes
FROM base as dependencies

# Copy requirements first (separate layer for caching)
COPY requirements.txt .

# Install CPU-only PyTorch first to avoid pulling CUDA dependencies (saves ~6GB)
# This is sufficient since the backend delegates all GPU work to Ollama/external APIs
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt && \
    pip cache purge

# Application layer - rebuilds when code changes
FROM dependencies as application

# Copy application code
COPY . .

# Create non-root user for production (but use root for development)
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5.0)" || exit 1

# Create startup script that initializes database then runs the application
COPY docker-entrypoint.sh /usr/local/bin/
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh && \
    chmod +x /usr/local/bin/docker-entrypoint.sh

# Run the application with database initialization
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "main.py"]