#!/usr/bin/env python3
import os
import sys
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # Load environment variables from config/.env
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
    env_path = os.path.join(config_dir, '.env')
    
    if os.path.exists(env_path):
        logger.info(f"Loading environment from {env_path}")
        load_dotenv(dotenv_path=env_path)
    else:
        logger.error(f"Environment file not found at {env_path}")
        sys.exit(1)
    
    # Get database URL
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        logger.error("DATABASE_URL environment variable not set!")
        sys.exit(1)
    
    # Mask password for logging
    masked_url = DATABASE_URL
    if '@' in DATABASE_URL:
        parts = DATABASE_URL.split('@')
        auth_parts = parts[0].split(':')
        if len(auth_parts) >= 3:
            masked_url = f"{auth_parts[0]}:{auth_parts[1]}:****@{parts[1]}"
    
    logger.info(f"Using database URL: {masked_url}")
    
    # Convert postgres:// to postgresql:// if needed
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        logger.info("Converted postgres:// to postgresql:// for SQLAlchemy compatibility")
    
    try:
        # Create database engine and session
        engine = create_engine(DATABASE_URL, echo=True)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Check tables
        logger.info("Checking tables...")
        
        # Fix feedings table - convert any string values to proper enum format
        logger.info("Fixing feedings table...")
        with session.begin():
            # Using raw SQL to avoid SQLAlchemy's enum validation during query
            # This updates any string values to their corresponding enum names
            session.execute(text("""
                UPDATE feedings 
                SET type = 'BREAST'
                WHERE type = 'breast';
            """))
            
            session.execute(text("""
                UPDATE feedings 
                SET type = 'BOTTLE'
                WHERE type = 'bottle';
            """))
            
            session.execute(text("""
                UPDATE feedings 
                SET type = 'SOLID'
                WHERE type = 'solid';
            """))
        
        logger.info("Fixed feedings table.")
        
        # Fix diapers table
        logger.info("Fixing diapers table...")
        with session.begin():
            session.execute(text("""
                UPDATE diapers 
                SET type = 'WET'
                WHERE type = 'wet';
            """))
            
            session.execute(text("""
                UPDATE diapers 
                SET type = 'DIRTY'
                WHERE type = 'dirty';
            """))
            
            session.execute(text("""
                UPDATE diapers 
                SET type = 'BOTH'
                WHERE type = 'both';
            """))
        
        logger.info("Fixed diapers table.")
        
        # Fix cryings table
        logger.info("Fixing cryings table...")
        with session.begin():
            session.execute(text("""
                UPDATE cryings 
                SET reason = 'HUNGRY'
                WHERE reason = 'hungry';
            """))
            
            session.execute(text("""
                UPDATE cryings 
                SET reason = 'DIAPER'
                WHERE reason = 'diaper';
            """))
            
            session.execute(text("""
                UPDATE cryings 
                SET reason = 'ATTENTION'
                WHERE reason = 'attention';
            """))
            
            session.execute(text("""
                UPDATE cryings 
                SET reason = 'UNKNOWN'
                WHERE reason = 'unknown';
            """))
            
            # Also fix predicted_reason
            session.execute(text("""
                UPDATE cryings 
                SET predicted_reason = 'HUNGRY'
                WHERE predicted_reason = 'hungry';
            """))
            
            session.execute(text("""
                UPDATE cryings 
                SET predicted_reason = 'DIAPER'
                WHERE predicted_reason = 'diaper';
            """))
            
            session.execute(text("""
                UPDATE cryings 
                SET predicted_reason = 'ATTENTION'
                WHERE predicted_reason = 'attention';
            """))
            
            session.execute(text("""
                UPDATE cryings 
                SET predicted_reason = 'UNKNOWN'
                WHERE predicted_reason = 'unknown';
            """))
            
            # Also fix actual_reason
            session.execute(text("""
                UPDATE cryings 
                SET actual_reason = 'HUNGRY'
                WHERE actual_reason = 'hungry';
            """))
            
            session.execute(text("""
                UPDATE cryings 
                SET actual_reason = 'DIAPER'
                WHERE actual_reason = 'diaper';
            """))
            
            session.execute(text("""
                UPDATE cryings 
                SET actual_reason = 'ATTENTION'
                WHERE actual_reason = 'attention';
            """))
            
            session.execute(text("""
                UPDATE cryings 
                SET actual_reason = 'UNKNOWN'
                WHERE actual_reason = 'unknown';
            """))
        
        logger.info("Fixed cryings table.")
        
        logger.info("All enum values have been fixed!")
        
    except Exception as e:
        logger.error(f"Error fixing enum data: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main() 