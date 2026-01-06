#!/usr/bin/env python3
"""
Startup script for uvicorn with mTLS support
"""
import ssl
import sys
import os
import uvicorn

def create_mtls_ssl_context(cert_file: str, key_file: str, ca_file: str) -> ssl.SSLContext:
    """Create SSL context with mTLS (mutual TLS) support"""
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    # Load server certificate and key
    ssl_context.load_cert_chain(cert_file, key_file)

    # Load CA certificate for client certificate verification
    ssl_context.load_verify_locations(ca_file)

    # Require client certificates (mTLS)
    ssl_context.verify_mode = ssl.CERT_REQUIRED

    # Set minimum TLS version (recommended: TLS 1.2 or higher)
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

    return ssl_context

if __name__ == "__main__":
    # Get certificate paths from environment or defaults
    ssl_cert = os.getenv("SSL_CERT", "/app/certs/tls.crt")
    ssl_key = os.getenv("SSL_KEY", "/app/certs/tls.key")
    ssl_ca_certs = os.getenv("SSL_CA_CERTS", "/app/certs/ca.crt")

    # Check if all required certificates exist
    if not os.path.exists(ssl_cert) or not os.path.exists(ssl_key) or os.path.exists(ssl_ca_certs):
        print("Error: Server certificate or key or CA certificatenot found", file=sys.stderr)
        sys.exit(1)

	print("Starting server with mTLS (mutual TLS)...")
	# Create mTLS SSL context
	ssl_context = create_mtls_ssl_context(ssl_cert, ssl_key, ssl_ca_certs)

	# Start uvicorn with mTLS
	uvicorn.run(
		"app:app",
		host="0.0.0.0",
		port=8080,
		ssl=ssl_context,
		log_level="info",
		use_colors=False,
		loop="asyncio"
	)

