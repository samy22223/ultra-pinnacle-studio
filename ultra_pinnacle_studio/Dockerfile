# Ultra Pinnacle AI Studio - Multi-stage Production Dockerfile

# Stage 1: Build web UI
FROM node:18-alpine AS web-ui-builder

WORKDIR /app/web_ui

# Copy package files
COPY web_ui/package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY web_ui/ ./

# Build the application
RUN npm run build

# Stage 2: Python dependencies
FROM python:3.12-slim AS python-deps

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Production image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ENVIRONMENT=production \
    LOG_LEVEL=INFO

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash ai-studio

# Set working directory
WORKDIR /app

# Copy Python dependencies from python-deps stage
COPY --from=python-deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=python-deps /usr/local/bin /usr/local/bin

# Copy built web UI from web-ui-builder stage
COPY --from=web-ui-builder /app/web_ui/dist ./web_ui/dist/

# Copy application code
COPY api_gateway/ ./api_gateway/
COPY encyclopedia/ ./encyclopedia/
COPY tests/ ./tests/
COPY validation_scripts/ ./validation_scripts/
COPY config.json .
COPY README.md .

# Create necessary directories
RUN mkdir -p models logs uploads && \
    chown -R ai-studio:ai-studio /app

# Switch to non-root user
USER ai-studio

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Start the application
CMD ["python", "-m", "uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]