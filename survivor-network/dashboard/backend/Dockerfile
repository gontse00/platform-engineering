# Survivor Network Backend - Local Infrastructure Edition
# Optimized for Kind Cluster (Tier: Compute)

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Install system dependencies 
# libpq-dev is required for PostgreSQL connectivity
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code structure
COPY app/ ./app/

# Security: Run as non-root user
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# Expose the internal container port
EXPOSE 8080

# Health check using curl (installed above) 
# This tells Kubernetes if your 'Mission Control' is actually alive
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Launch the FastAPI app
# Add the current directory to PYTHONPATH
ENV PYTHONPATH=/app

# Run from the directory above 'app'
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]