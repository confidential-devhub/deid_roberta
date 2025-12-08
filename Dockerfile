FROM python:3.11

# Install OS libs required by torch + tokenizers
#RUN apt-get update && apt-get install -y --no-install-recommends \
#    git curl build-essential libglib2.0-0 libstdc++6 \
 #   && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libstdc++6 \
    libgomp1 \
    libgcc1 \
    libglib2.0-0 \
    git curl \
    && rm -rf /var/lib/apt/lists/*

# Create HF cache dir
RUN mkdir -p /app/hf_cache
ENV HF_HOME=/app/hf_cache
ENV TRANSFORMERS_CACHE=/app/hf_cache

# Make it writable for arbitrary OpenShift UID
RUN chgrp -R 0 /app/hf_cache && chmod -R g+rwX /app/hf_cache

# Install Python libs
RUN pip install --no-cache-dir fastapi uvicorn transformers torch

# Preload model
RUN python - <<EOF
from transformers import AutoTokenizer, AutoModelForTokenClassification
m = "obi/deid_roberta_i2b2"
AutoTokenizer.from_pretrained(m, cache_dir="/app/hf_cache")
AutoModelForTokenClassification.from_pretrained(m, cache_dir="/app/hf_cache")
EOF

WORKDIR /app
COPY app.py .

EXPOSE 8080

ENV UVICORN_DISABLE_IPV6=true

# Create directory for SSL certificates
RUN mkdir -p /app/certs && chgrp -R 0 /app/certs && chmod -R g+rwX /app/certs

# Copy startup script that handles SSL configuration
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
