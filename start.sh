#!/bin/bash

# Check if SSL certificates are provided via environment variables or mounted volume
export SSL_CERT="${SSL_CERT:-/app/certs/tls.crt}"
export SSL_KEY="${SSL_KEY:-/app/certs/tls.key}"
export SSL_CA_CERTS="${SSL_CA_CERTS:-/app/certs/ca.crt}"


# If certificates exist, use HTTPS with optional mTLS
if [ -f "$SSL_CERT" ] && [ -f "$SSL_KEY" ] && [ -f "$SSL_CA_CERTS" ]; then
    echo "Starting server with HTTPS and mTLS (client certificate verification)..."
    exec python /app/start_mtls.py
else
    echo "Starting server with HTTP (certificates not found, using HTTP)..."
    exec python -m uvicorn app:app --host 0.0.0.0 --port 8080 --no-use-colors --loop asyncio
fi

