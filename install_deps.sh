#!/bin/bash
# Install minimal dependencies for local development

echo "Installing minimal dependencies for RAG Workspace..."

python3 -m pip install --user \
    fastapi \
    'uvicorn[standard]' \
    sqlalchemy \
    pydantic \
    pydantic-settings \
    python-multipart \
    'python-jose[cryptography]' \
    'passlib[bcrypt]' \
    email-validator

echo ""
echo "✓ Dependencies installed!"
echo ""
echo "To install all dependencies: pip install -r requirements.txt"

