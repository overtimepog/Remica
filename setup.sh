#!/bin/bash

echo "Real Estate Market Insights Chat Agent - Setup Script"
echo "====================================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then 
    echo " Python $python_version is installed (>= $required_version required)"
else
    echo " Python $python_version is too old. Please install Python $required_version or higher."
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo " Virtual environment created"
else
    echo " Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo " Dependencies installed"

# Create .env file if it doesn't exist
echo ""
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo " .env file created"
    echo ""
    echo "IMPORTANT: Please edit .env and add your OpenRouter API key"
    echo "You can get a free API key at https://openrouter.ai/"
else
    echo " .env file already exists"
fi

# Test connections
echo ""
echo "Testing connections..."
python main.py --test

echo ""
echo "Setup complete! To start the application, run:"
echo "  source venv/bin/activate"
echo "  python main.py"
echo ""
echo "For help, run: python main.py --help"