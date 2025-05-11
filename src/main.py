import os
import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db
import bot
from server import start_server_thread

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"baby_alert_{datetime.now().strftime('%Y%m%d')}.log")
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Run the Baby Alert application."""
    parser = argparse.ArgumentParser(description='Baby Alert - Baby Behavior Analysis Chatbot')
    parser.add_argument('--token', type=str, help='Telegram Bot Token')
    parser.add_argument('--init-db', action='store_true', help='Initialize the database')
    parser.add_argument('--openai-key', type=str, help='OpenAI API Key')
    
    args = parser.parse_args()
    
    # Initialize database if requested
    if args.init_db:
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized.")
    
    # Get the directory where main.py is located
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Try to load token from config/.env - use absolute path
    env_path = os.path.join(base_dir, 'config', '.env')
    
    # First try config/.env
    if os.path.exists(env_path):
        logger.info(f"Loading environment from {env_path}")
        load_dotenv(dotenv_path=env_path)
    else:
        logger.warning(f"Environment file not found at {env_path}")
        
        # If not found, try root directory .env
        root_env_path = os.path.join(base_dir, '.env')
        if os.path.exists(root_env_path):
            logger.info(f"Loading environment from {root_env_path}")
            load_dotenv(dotenv_path=root_env_path)
        else:
            logger.warning(f"Environment file not found at {root_env_path}")
    
    # Set token from arguments (overrides .env if both exist)
    if args.token:
        os.environ["TELEGRAM_BOT_TOKEN"] = args.token
        
    # Set OpenAI API key from arguments (overrides .env if both exist)
    if args.openai_key:
        os.environ["OPENAI_API_KEY"] = args.openai_key
    
    # Ensure we have a token
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("No TELEGRAM_BOT_TOKEN provided! Set it in config/.env file, as an environment variable, or use --token")
        sys.exit(1)
    
    # Check for OpenAI API key
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        logger.warning("No OPENAI_API_KEY provided! Natural language queries will not work.")
    
    # Start the web server for Render
    logger.info("Starting web server for Render...")
    start_server_thread()
    
    # Start the bot
    logger.info("Starting the Baby Alert bot...")
    bot.main()

if __name__ == "__main__":
    main()