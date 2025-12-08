#!/bin/bash

# Check if SSL certificates are provided via environment variables or mounted volume
SSL_CERT="${SSL_CERT:-/app/certs/tls.crt}"
SSL_KEY="${SSL_KEY:-/app/certs/tls.key}"

# Build uvicorn command
UVICORN_CMD="python -m uvicorn app:app --host 0.0.0.0 --port 8080 --no-use-colors --loop asyncio"

# If certificates exist, use HTTPS
if [ -f "$SSL_CERT" ] && [ -f "$SSL_KEY" ]; then
    echo "Starting server with HTTPS..."
    exec $UVICORN_CMD --ssl-certfile "$SSL_CERT" --ssl-keyfile "$SSL_KEY"
else
    echo "Starting server with HTTP (certificates not found, using HTTP)..."
    exec $UVICORN_CMD
fi

