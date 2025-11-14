#!/bin/bash
# Script: generate-encryption-key.sh
# Purpose: Generate Fernet encryption key for database credential encryption
# Date: 2025-11-14

set -e

echo "=== Generating Fernet Encryption Key ==="
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 is required but not found"
    exit 1
fi

# Check if cryptography package is installed
python3 -c "import cryptography.fernet" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "ERROR: cryptography package not installed"
    echo "Please install it with: pip install cryptography"
    exit 1
fi

# Generate Fernet key
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

if [ -z "$ENCRYPTION_KEY" ]; then
    echo "ERROR: Failed to generate encryption key"
    exit 1
fi

echo "✅ Fernet encryption key generated successfully"
echo
echo "Add the following line to your .env file:"
echo
echo "ENCRYPTION_KEY=${ENCRYPTION_KEY}"
echo
echo "⚠️  IMPORTANT:"
echo "- Keep this key secret and secure"
echo "- Never commit this key to version control"
echo "- If lost, encrypted passwords cannot be recovered"
echo "- Store a backup copy in a secure location"
