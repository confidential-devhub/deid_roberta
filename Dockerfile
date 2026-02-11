# Multi-stage build to reduce final image size
# Stage 1: Build stage with build dependencies
FROM python:3.11-slim as builder

# Install only build deps (no git/curl - install from PyPI only)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Prevent bytecode; smaller image when copied to runtime
ENV PYTHONDONTWRITEBYTECODE=1

# Create HF cache dir
RUN mkdir -p /app/hf_cache
ENV HF_HOME=/app/hf_cache
ENV TRANSFORMERS_CACHE=/app/hf_cache

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Install Python deps without bytecode (.pyc); CPU-only PyTorch
RUN pip install --no-cache-dir --no-compile \
    torch --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir --no-compile \
    fastapi \
    uvicorn \
    transformers \
    jinja2 \
    azure-storage-blob

# Preload model in builder stage
RUN python - <<EOF
from transformers import AutoTokenizer, AutoModelForTokenClassification
m = "obi/deid_roberta_i2b2"
AutoTokenizer.from_pretrained(m, cache_dir="/app/hf_cache")
AutoModelForTokenClassification.from_pretrained(m, cache_dir="/app/hf_cache")
EOF

# Remove any __pycache__/.pyc and strip shared libs to shrink copied data
RUN find /usr/local -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true \
    && find /usr/local -name "*.pyc" -delete 2>/dev/null || true \
    && find /usr/local -name "*.so" -exec strip {} \; 2>/dev/null || true

# Stage 2: Runtime stage - minimal image
FROM python:3.11-slim

# Install only runtime libs (minimal set for PyTorch CPU)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 \
    libgomp1 \
    libgcc1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python environment from builder (no build tools)
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin

RUN pip install --no-cache-dir --no-compile python-multipart

# Copy model cache from builder
COPY --from=builder /app/hf_cache /app/hf_cache

# Create HF cache dir and make it writable for arbitrary OpenShift UID
RUN mkdir -p /app/hf_cache && \
    chgrp -R 0 /app/hf_cache && \
    chmod -R g+rwX /app/hf_cache

ENV HF_HOME=/app/hf_cache
ENV TRANSFORMERS_CACHE=/app/hf_cache
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copy application files
COPY app.py .
COPY templates/ templates/
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 8080

ENV UVICORN_DISABLE_IPV6=true

CMD ["/app/start.sh"]
