#!/bin/bash

echo "Starting server with HTTP..."
exec python -m uvicorn app:app --host 0.0.0.0 --port 8080 --no-use-colors --loop asyncio
