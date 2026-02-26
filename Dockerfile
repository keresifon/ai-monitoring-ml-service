# Multi-stage build for ML Service (Alpine-based for minimal CVE surface)
FROM python:3.11-alpine AS builder

WORKDIR /app

# Install build dependencies for C extensions (numpy, scikit-learn, pandas, psycopg2)
RUN apk add --no-cache \
    gcc \
    g++ \
    musl-dev \
    linux-headers \
    libffi-dev \
    postgresql-dev \
    openblas-dev

# Upgrade pip, wheel, setuptools before installing deps
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-alpine

# Install only runtime libraries needed by compiled extensions and curl for healthcheck
RUN apk add --no-cache \
    libstdc++ \
    openblas \
    libpq \
    libffi \
    curl

# Create a non-root user for security
RUN addgroup -S appuser && adduser -S -G appuser appuser

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Remove pip/wheel/setuptools from runtime image (not needed, avoids CVE surface)
RUN rm -rf /usr/local/lib/python3.11/site-packages/pip* \
           /usr/local/lib/python3.11/site-packages/wheel* \
           /usr/local/lib/python3.11/site-packages/setuptools* \
           /usr/local/lib/python3.11/site-packages/pkg_resources* \
           /usr/local/lib/python3.11/site-packages/jaraco* \
           /usr/local/bin/pip* /usr/local/bin/pip3* \
           /usr/local/bin/wheel

# Make sure scripts in .local are usable
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy only necessary application files
COPY main.py ./
COPY app/ ./app/
COPY requirements.txt ./

# Create models directory and set proper ownership
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
