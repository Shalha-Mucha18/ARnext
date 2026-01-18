# Use Python 3.10 (more stable than 3.11 for many libs)
FROM python:3.10-slim

# Environment settings
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency list first (for Docker layer caching)
COPY requirements.txt .

# Upgrade pip and install dependencies
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Ensure Python package structure (safety)
RUN test -f app/__init__.py || touch app/__init__.py

# Expose FastAPI port
EXPOSE 8000

# Healthcheck (prevents crash loops going unnoticed)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8000/docs || exit 1

# Run FastAPI with proper signal handling
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
