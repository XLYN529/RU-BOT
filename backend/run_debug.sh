#!/bin/bash
# Run the backend with detailed logging

echo "Starting RU Assistant Backend with DEBUG logging..."
echo "Watch for detailed error messages below:"
echo "=========================================="
echo ""

cd "$(dirname "$0")"
python main.py
