#!/bin/bash

# Load from .env if exists
if [ -f .env ]; then
  export $(cat .env | xargs)
fi

# Default values
DB_PASSWORD=${DB_PASSWORD:-"postgres"}
GEMINI_API_KEY=${GEMINI_API_KEY:-""}

if [ -z "$GEMINI_API_KEY" ]; then
  echo "⚠️  GEMINI_API_KEY is not set. You will need to edit the 'llm-secrets' secret manually later."
  echo "   Use: export GEMINI_API_KEY='your-key' before running this script."
fi

echo "🔐 Creating Kubernetes Secrets..."

# 1. Database Credentials
kubectl create secret generic db-credentials \
  --from-literal=password="$DB_PASSWORD" \
  --dry-run=client -o yaml | kubectl apply -f -

# 2. LLM/Gemini Credentials
kubectl create secret generic llm-secrets \
  --from-literal=api-key="$GEMINI_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "✅ Secrets created (db-credentials, llm-secrets)."
