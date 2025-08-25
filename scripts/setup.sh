#!/bin/bash

set -e

echo "Setting up Agent...."

# python version check
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "[ERROR] Python 3.8 or higher is required. Found: $python_version"
    exit 1
fi

echo "[INFO] Python version: $python_version"

# Creating virtual environment
if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv venv
fi

# Activating virtual environment
echo "[INFO] Activating virtual environment..."
source venv/bin/activate

# Upgrading pip
echo "[INFO] Upgrading pip..."
pip install --upgrade pip

# Installing dependencies
echo "[INFO] Installing dependencies..."
pip install -r requirements.txt

# Checking environment file
if [ ! -f ".env" ]; then
    echo "[ERROR] .env file not found. Please create .env manually."
else
    echo "[INFO] .env file already exists."
fi

echo ""
echo "[INFO] Setup complete!"
echo ""

exit 0