#!/bin/bash
echo "Baby Alert - Starting up..."

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if data directory exists
if [ ! -d "data" ]; then
    echo "Creating data directory..."
    mkdir -p data
fi

# Check if database needs initialization
if [ ! -f "data/baby_alert.db" ]; then
    echo "Initializing database..."
    python src/main.py --init-db
fi

# Check if token is set
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo
    echo "----------------------------------------"
    echo "WARNING: TELEGRAM_BOT_TOKEN not set!"
    echo
    echo "Please set your Telegram Bot Token:"
    echo
    read -p "Enter your Telegram Bot Token: " TOKEN
    export TELEGRAM_BOT_TOKEN=$TOKEN
    echo
fi

# Start the bot
echo "Starting Baby Alert Bot..."
python src/main.py 