#!/bin/bash
echo "🚀 Starting Astra Platform..."
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
