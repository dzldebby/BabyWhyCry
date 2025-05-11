#!/usr/bin/env python3
"""
Fix timezone information in the database.
This script updates all datetime fields in the database to have proper timezone information.
"""

import os
import sys
import logging
from datetime import datetime, timezone
import pytz
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from models import Base, User, Baby, Feeding, Sleep, Diaper, Crying
from utils import utc_to_sgt, get_sgt_now

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables from config/.env
config_dir = os.path.join(os.path.dirname(__file__), 'config')
env_path = os.path.join(config_dir, '.env')
if os.path.exists(env_path):
    logger.info(f"Loading environment variables from {env_path}")
    load_dotenv(dotenv_path=env_path)
    logger.info("Environment variables loaded")
else:
    logger.warning(f"Environment file not found at {env_path}, using environment variables as is")

# Get database URL from environment or use SQLite as fallback
DATABASE_URL = os.getenv("DATABASE_URL")
logger.info(f"DATABASE_URL environment variable {'found' if DATABASE_URL else 'not found'}")

# Check if we're using PostgreSQL or SQLite
is_postgres = DATABASE_URL is not None
logger.info(f"Using PostgreSQL? {is_postgres}")

# Setup proper engine based on available database
if DATABASE_URL:
    # Handle Supabase/PostgreSQL connection
    # Convert potential "postgres://" to "postgresql://" for SQLAlchemy
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        logger.info("Converted postgres:// to postgresql:// for SQLAlchemy compatibility")
    
    # Hide password in logs but show host/database
    masked_url = DATABASE_URL.replace(DATABASE_URL.split('@')[0].split(':', 2)[2], '****')
    logger.info(f"Connecting to PostgreSQL database: {masked_url}")
    
    engine = create_engine(DATABASE_URL, echo=True)
    logger.info("PostgreSQL engine created with SQL echoing enabled")
else:
    # Fallback to SQLite for local development
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, 'baby_alert.db')
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"
    logger.info(f"Using SQLite database at: {db_path}")
    
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    logger.info("SQLite engine created")

# Create a session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def fix_timezone_info():
    """Fix timezone information in all datetime fields in the database."""
    try:
        # Fix Baby birth_date
        logger.info("Fixing Baby birth_date timezone...")
        babies = db.query(Baby).all()
        for baby in babies:
            if baby.birth_date and baby.birth_date.tzinfo is None:
                logger.info(f"Fixing birth_date for baby {baby.id}: {baby.name}")
                # Assume UTC and convert to SGT
                baby.birth_date = utc_to_sgt(baby.birth_date)
        
        # Fix Feeding start_time and end_time
        logger.info("Fixing Feeding timezone...")
        feedings = db.query(Feeding).all()
        for feeding in feedings:
            if feeding.start_time and feeding.start_time.tzinfo is None:
                logger.info(f"Fixing start_time for feeding {feeding.id}")
                feeding.start_time = utc_to_sgt(feeding.start_time)
            if feeding.end_time and feeding.end_time.tzinfo is None:
                logger.info(f"Fixing end_time for feeding {feeding.id}")
                feeding.end_time = utc_to_sgt(feeding.end_time)
        
        # Fix Sleep start_time and end_time
        logger.info("Fixing Sleep timezone...")
        sleeps = db.query(Sleep).all()
        for sleep in sleeps:
            if sleep.start_time and sleep.start_time.tzinfo is None:
                logger.info(f"Fixing start_time for sleep {sleep.id}")
                sleep.start_time = utc_to_sgt(sleep.start_time)
            if sleep.end_time and sleep.end_time.tzinfo is None:
                logger.info(f"Fixing end_time for sleep {sleep.id}")
                sleep.end_time = utc_to_sgt(sleep.end_time)
        
        # Fix Diaper time
        logger.info("Fixing Diaper timezone...")
        diapers = db.query(Diaper).all()
        for diaper in diapers:
            if diaper.time and diaper.time.tzinfo is None:
                logger.info(f"Fixing time for diaper {diaper.id}")
                diaper.time = utc_to_sgt(diaper.time)
        
        # Fix Crying start_time and end_time
        logger.info("Fixing Crying timezone...")
        cryings = db.query(Crying).all()
        for crying in cryings:
            if crying.start_time and crying.start_time.tzinfo is None:
                logger.info(f"Fixing start_time for crying {crying.id}")
                crying.start_time = utc_to_sgt(crying.start_time)
            if crying.end_time and crying.end_time.tzinfo is None:
                logger.info(f"Fixing end_time for crying {crying.id}")
                crying.end_time = utc_to_sgt(crying.end_time)
        
        # Commit all changes
        logger.info("Committing changes...")
        db.commit()
        logger.info("All timezone information fixed successfully!")
        
        return True
    except Exception as e:
        logger.error(f"Error fixing timezone information: {e}")
        db.rollback()
        return False

if __name__ == "__main__":
    logger.info("Starting timezone fix script...")
    success = fix_timezone_info()
    if success:
        logger.info("Timezone fix completed successfully.")
    else:
        logger.error("Timezone fix failed.") 