#!/bin/sh

# Define the certificate and key file names
CERT_FILE="./certs/nginx.crt"
KEY_FILE="./certs/nginx.key"

# Check if the certificate and key already exist
if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
    echo "Generating self-signed SSL certificate..."

    # Generate a self-signed certificate (valid for 365 days)
    openssl req -x509 -newkey rsa:2048 -nodes -days 365 -keyout $KEY_FILE -out $CERT_FILE -subj "/CN=localhost"

    echo "SSL certificate generated!"
else
    echo "SSL certificate already exists. Skipping generation."
fi
