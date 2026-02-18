# Multi-stage build for ML Service
FROM python:3.11-slim AS builder

WORKDIR /app

# Apply OS security patches and install build dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, wheel, setuptools to fix known CVEs before installing deps
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

# Apply all available OS security patches (glibc, util-linux, libtasn1, sqlite, curl)
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy Python dependencies from builder to user's home directory
COPY --from=builder /root/.local /home/appuser/.local

# Upgrade base image Python tools to fix CVEs (wheel, jaraco.context, pip),
# then remove them from the runtime image since they are not needed
RUN pip install --no-cache-dir --upgrade pip wheel setuptools jaraco.context && \
    rm -rf /usr/local/lib/python3.11/site-packages/pip* \
           /usr/local/lib/python3.11/site-packages/wheel* \
           /usr/local/lib/python3.11/site-packages/setuptools* \
           /usr/local/lib/python3.11/site-packages/pkg_resources* \
           /usr/local/lib/python3.11/site-packages/jaraco* \
           /usr/local/bin/pip* /usr/local/bin/pip3* \
           /usr/local/bin/wheel

# Make sure scripts in .local are usable
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy only necessary application files (explicit copy to avoid sensitive data)
# .dockerignore provides additional protection
COPY main.py ./
COPY app/ ./app/
COPY requirements.txt ./

# Create models directory and set proper ownership for all files
RUN mkdir -p models && \
    chown -R appuser:appuser /app /home/appuser/.local

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/v1/health')" || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]