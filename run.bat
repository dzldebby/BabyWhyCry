@echo off
echo Baby Alert - Starting up...

REM Check if virtual environment exists, create if not
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate

REM Install dependencies if needed
echo Installing dependencies...
pip install -r requirements.txt

REM Check if data directory exists
if not exist data (
    echo Creating data directory...
    mkdir data
)

REM Check if database needs initialization
if not exist data\baby_alert.db (
    echo Initializing database...
    python src\main.py --init-db
)

REM Check if token is set
if "%TELEGRAM_BOT_TOKEN%"=="" (
    echo.
    echo ----------------------------------------
    echo WARNING: TELEGRAM_BOT_TOKEN not set!
    echo.
    echo Please set your Telegram Bot Token:
    echo.
    set /p TOKEN="Enter your Telegram Bot Token: "
    set TELEGRAM_BOT_TOKEN=%TOKEN%
    echo.
)

REM Start the bot
echo Starting Baby Alert Bot...
python src\main.py

pause 