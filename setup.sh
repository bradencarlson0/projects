#!/bin/bash

# Redfin CMA Tool - Setup Script
# ===============================
# Automated setup for the Redfin CMA Tool on Unix-like systems

set -e  # Exit on any error

echo "🏡 Redfin CMA Tool - Setup Script"
echo "=================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
    echo "✅ Python $PYTHON_VERSION detected"
else
    echo "❌ Python $PYTHON_VERSION is too old. Requires Python 3.8 or higher."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip3."
    exit 1
fi

echo "✅ pip3 detected"

# Create virtual environment (optional but recommended)
read -p "📦 Create a virtual environment? (recommended) [Y/n]: " create_venv
create_venv=${create_venv:-Y}

if [[ $create_venv =~ ^[Yy]$ ]]; then
    echo "🔧 Creating virtual environment..."
    
    if ! command -v python3 -m venv &> /dev/null; then
        echo "Installing python3-venv..."
        sudo apt-get update && sudo apt-get install -y python3-venv 2>/dev/null || echo "⚠️  Could not install python3-venv automatically. Please install it manually."
    fi
    
    python3 -m venv venv
    echo "✅ Virtual environment created"
    
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
    echo "✅ Virtual environment activated"
    
    # Upgrade pip in virtual environment
    echo "🔧 Upgrading pip..."
    pip install --upgrade pip
fi

# Install required packages
echo "📥 Installing required packages..."
pip3 install -r requirements.txt

echo "✅ Packages installed successfully"

# Run installation test
echo "🧪 Running installation tests..."
python3 test_installation.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Setup completed successfully!"
    echo ""
    echo "To start the application:"
    if [[ $create_venv =~ ^[Yy]$ ]]; then
        echo "  1. Activate the virtual environment: source venv/bin/activate"
        echo "  2. Start the app: streamlit run redfinwebapp_optimized.py"
    else
        echo "  streamlit run redfinwebapp_optimized.py"
    fi
    echo ""
    echo "The app will open in your browser at http://localhost:8501"
    echo ""
    echo "For more information, see README.md"
else
    echo "❌ Setup encountered issues. Please check the error messages above."
    exit 1
fi