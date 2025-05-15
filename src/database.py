from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine import Engine
from sqlalchemy import event
import os
import sys
import datetime
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from models import Base, User, Baby, Feeding, Sleep, Diaper, Crying
from models import FeedingType, DiaperType, CryingReason
from utils import get_sgt_now, utc_to_sgt, sgt_to_utc
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)  # Ensure logging is set to INFO level

# Load environment variables from config/.env
config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
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
    original_url = DATABASE_URL
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        logger.info("Converted postgres:// to postgresql:// for SQLAlchemy compatibility")
    
    # Hide password in logs but show host/database
    masked_url = DATABASE_URL.replace(DATABASE_URL.split('@')[0].split(':', 2)[2], '****')
    logger.info(f"Connecting to PostgreSQL database: {masked_url}")
    
    engine = create_engine(DATABASE_URL, echo=True)  # Enable SQL echoing
    logger.info("PostgreSQL engine created with SQL echoing enabled")
    
    # PostgreSQL doesn't need this pragma
    @event.listens_for(Engine, "connect")
    def set_postgresql_schema(dbapi_connection, connection_record):
        # Set search path if needed - ENABLE THIS FOR SUPABASE
        cursor = dbapi_connection.cursor()
        cursor.execute("SET search_path TO public")
        cursor.close()
        logger.info("PostgreSQL schema search path set to 'public'")
else:
    # Fallback to SQLite for local development
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, 'baby_alert.db')
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"
    logger.info(f"Using SQLite database at: {db_path}")
    
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    logger.info("SQLite engine created")
    
    # Configure SQLite to enforce foreign key constraints
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        logger.info("SQLite foreign key constraints enabled")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
logger.info("Database session factory created")

def init_db():
    """Initialize the database by creating all tables."""
    logger.info("Initializing database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

def get_db():
    """Get a database session."""
    logger.info("Getting new database session")
    try:
        db = SessionLocal()
        logger.info("Database session created")
        return db
    except Exception as e:
        logger.error(f"Error creating database session: {e}")
        raise
    finally:
        logger.info("Database session will be closed when the caller is done")

# User operations
def create_user(db, username: str, email: str) -> User:
    """Create a new user."""
    user = User(username=username, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user(db, user_id: int) -> Optional[User]:
    """Get a user by ID."""
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_username(db, username: str) -> Optional[User]:
    """Get a user by username."""
    return db.query(User).filter(User.username == username).first()

# Baby operations
def create_baby(db, name: str, user_id: int, birth_date=None) -> Baby:
    """Create a new baby."""
    if birth_date is None:
        birth_date = get_sgt_now()
    baby = Baby(name=name, parent_id=user_id, birth_date=birth_date)
    db.add(baby)
    db.commit()
    db.refresh(baby)
    return baby

def get_baby(db, baby_id: int) -> Optional[Baby]:
    """Get a baby by ID."""
    return db.query(Baby).filter(Baby.id == baby_id).first()

def update_baby_name(db, baby_id: int, new_name: str) -> Optional[Baby]:
    """Update a baby's name."""
    baby = db.query(Baby).filter(Baby.id == baby_id).first()
    if baby:
        baby.name = new_name
        db.commit()
        db.refresh(baby)
    return baby

def get_babies_by_user(db, user_id: int) -> List[Baby]:
    """Get all babies for a user."""
    return db.query(Baby).filter(Baby.parent_id == user_id).all()

def get_baby_by_name(db, name: str, user_id: int) -> Optional[Baby]:
    """Get a baby by name for a specific user."""
    return db.query(Baby).filter(Baby.name == name, Baby.parent_id == user_id).first()

def delete_baby(db, baby_id: int) -> bool:
    """Delete a baby and all related data.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        baby = db.query(Baby).filter(Baby.id == baby_id).first()
        if not baby:
            return False
        
        db.delete(baby)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting baby: {e}")
        return False

# Feeding operations
def start_feeding(db, baby_id: int, feeding_type: FeedingType) -> Feeding:
    """Start a feeding session."""
    logger.info(f"Starting feeding for baby_id={baby_id}, type={feeding_type}")
    
    try:
        # When using PostgreSQL, we should NOT convert the enum to string
        # PostgreSQL's enum type will handle the conversion automatically
        # Just keep the original enum object
        feeding_type_val = feeding_type
        logger.info(f"Using feeding type: {feeding_type_val}")
            
        # Log the current time before creating the Feeding object
        current_time = get_sgt_now()
        logger.info(f"Current time for feeding start: {current_time}")
        
        feeding = Feeding(
            baby_id=baby_id,
            type=feeding_type_val,
            start_time=current_time
        )
        logger.info(f"Created feeding object with baby_id={baby_id}, type={feeding_type_val}")
        
        logger.info("Adding feeding to database session...")
        db.add(feeding)
        
        logger.info("Committing feeding to database...")
        try:
            db.commit()
            logger.info("Successfully committed feeding to database")
        except Exception as commit_error:
            logger.error(f"Error committing feeding to database: {commit_error}")
            db.rollback()
            raise
        
        logger.info("Refreshing feeding object from database...")
        try:
            db.refresh(feeding)
            logger.info(f"Successfully refreshed feeding, id={feeding.id}")
        except Exception as refresh_error:
            logger.error(f"Error refreshing feeding from database: {refresh_error}")
            raise
        
        return feeding
    except Exception as e:
        logger.error(f"Unexpected error in start_feeding: {e}")
        # Try to get a traceback
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

def end_feeding(db, feeding_id: int, amount: Optional[float] = None) -> Feeding:
    """End a feeding session."""
    feeding = db.query(Feeding).filter(Feeding.id == feeding_id).first()
    if feeding and not feeding.end_time:
        feeding.end_time = get_sgt_now()
        if amount is not None:
            feeding.amount = amount
        db.commit()
        db.refresh(feeding)
    return feeding

# Sleep operations
def start_sleep(db, baby_id: int) -> Sleep:
    """Start a sleep session."""
    sleep = Sleep(
        baby_id=baby_id,
        start_time=get_sgt_now()
    )
    db.add(sleep)
    db.commit()
    db.refresh(sleep)
    return sleep

def end_sleep(db, sleep_id: int) -> Sleep:
    """End a sleep session."""
    sleep = db.query(Sleep).filter(Sleep.id == sleep_id).first()
    if sleep and not sleep.end_time:
        sleep.end_time = get_sgt_now()
        db.commit()
        db.refresh(sleep)
    return sleep

# Diaper operations
def log_diaper_change(db, baby_id: int, diaper_type: DiaperType) -> Diaper:
    """Log a diaper change."""
    # Don't convert enum to string - use the enum directly
    diaper_type_val = diaper_type
    logger.info(f"Using diaper type: {diaper_type_val}")
        
    diaper = Diaper(
        baby_id=baby_id,
        type=diaper_type_val,
        time=get_sgt_now()
    )
    db.add(diaper)
    db.commit()
    db.refresh(diaper)
    return diaper

# Crying operations
def start_crying(db, baby_id: int) -> Crying:
    """Start tracking a crying episode."""
    crying = Crying(
        baby_id=baby_id,
        start_time=get_sgt_now()
    )
    db.add(crying)
    db.commit()
    db.refresh(crying)
    return crying

def end_crying(db, crying_id: int, actual_reason: Optional[CryingReason] = None) -> Crying:
    """End tracking a crying episode."""
    crying = db.query(Crying).filter(Crying.id == crying_id).first()
    if crying and not crying.end_time:
        crying.end_time = get_sgt_now()
        if actual_reason:
            # Don't convert enum to string - use directly
            crying.actual_reason = actual_reason
        db.commit()
        db.refresh(crying)
    return crying

# Add this helper function before get_recent_events
def safe_enum_conversion(value, enum_class):
    """
    Safely converts a value to an enum object if it's a string,
    or returns the original enum object if it already is one.
    """
    logger.info(f"Converting value: {value}, type: {type(value)}")
    
    # If it's already an enum instance, return it
    if isinstance(value, enum_class):
        logger.info(f"Value is already an enum instance: {value}")
        return value
        
    # If it's a string, try to convert it to enum
    if isinstance(value, str):
        for e in enum_class:
            if e.value == value or e.name == value:
                logger.info(f"Converted string '{value}' to enum: {e}")
                return e
                
    # Return None for null/None values
    if value is None:
        return None
        
    # If we can't convert, log error and return a default
    logger.error(f"Couldn't convert '{value}' to {enum_class.__name__} enum")
    return None

# Event retrieval
def get_recent_events(db, baby_id: int, limit: int = 10, days: int = 7) -> List[Dict[str, Any]]:
    """Get recent events for a baby."""
    logger.info(f"Retrieving recent events for baby_id={baby_id}, limit={limit}, days={days}")
    since = get_sgt_now() - timedelta(days=days)
    
    try:
        # Get recent feedings
        logger.info("Retrieving recent feedings...")
        feedings_query = db.query(Feeding).filter(
            Feeding.baby_id == baby_id,
            Feeding.start_time >= since
        ).order_by(Feeding.start_time.desc()).limit(limit)
        
        # Manually fetch and process feeding data to handle potential enum conversion issues
        raw_feedings = []
        for f in feedings_query:
            try:
                raw_feedings.append(f)
            except Exception as e:
                logger.error(f"Error processing feeding record: {e}")
        
        logger.info(f"Found {len(raw_feedings)} feeding records")
        
        # Get recent sleeps
        logger.info("Retrieving recent sleeps...")
        sleeps = db.query(Sleep).filter(
            Sleep.baby_id == baby_id,
            Sleep.start_time >= since
        ).order_by(Sleep.start_time.desc()).limit(limit).all()
        logger.info(f"Found {len(sleeps)} sleep records")
        
        # Get recent diapers
        logger.info("Retrieving recent diapers...")
        diapers_query = db.query(Diaper).filter(
            Diaper.baby_id == baby_id,
            Diaper.time >= since
        ).order_by(Diaper.time.desc()).limit(limit)
        
        # Manually fetch and process diaper data
        raw_diapers = []
        for d in diapers_query:
            try:
                raw_diapers.append(d)
            except Exception as e:
                logger.error(f"Error processing diaper record: {e}")
                
        logger.info(f"Found {len(raw_diapers)} diaper records")
        
        # Get recent crying episodes
        logger.info("Retrieving recent crying episodes...")
        cryings_query = db.query(Crying).filter(
            Crying.baby_id == baby_id,
            Crying.start_time >= since
        ).order_by(Crying.start_time.desc()).limit(limit)
        
        # Manually fetch and process crying data
        raw_cryings = []
        for c in cryings_query:
            try:
                raw_cryings.append(c)
            except Exception as e:
                logger.error(f"Error processing crying record: {e}")
                
        logger.info(f"Found {len(raw_cryings)} crying records")
        
        # Combine all events and sort by time
        events = []
        
        for feeding in raw_feedings:
            try:
                logger.info(f"Adding feeding event: id={feeding.id}, type={feeding.type}")
                events.append({
                    "type": "feeding",
                    "time": feeding.start_time,
                    "data": feeding
                })
            except Exception as e:
                logger.error(f"Error adding feeding to events: {e}")
        
        for sleep in sleeps:
            try:
                logger.info(f"Adding sleep event: id={sleep.id}")
                events.append({
                    "type": "sleep",
                    "time": sleep.start_time,
                    "data": sleep
                })
            except Exception as e:
                logger.error(f"Error adding sleep to events: {e}")
        
        for diaper in raw_diapers:
            try:
                logger.info(f"Adding diaper event: id={diaper.id}, type={diaper.type}")
                events.append({
                    "type": "diaper",
                    "time": diaper.time,
                    "data": diaper
                })
            except Exception as e:
                logger.error(f"Error adding diaper to events: {e}")
        
        for crying in raw_cryings:
            try:
                logger.info(f"Adding crying event: id={crying.id}")
                events.append({
                    "type": "crying",
                    "time": crying.start_time,
                    "data": crying
                })
            except Exception as e:
                logger.error(f"Error adding crying to events: {e}")
        
        # Sort by time (most recent first)
        events.sort(key=lambda x: x["time"], reverse=True)
        
        # Limit the number of events
        return events[:limit]
    except Exception as e:
        logger.error(f"Error retrieving recent events: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []

def get_baby_stats(db, baby_id: int, days: int = 1) -> Dict[str, Any]:
    """Get statistics for a baby over a period of days."""
    since = get_sgt_now() - timedelta(days=days)
    
    # Feeding count
    feeding_count = db.query(func.count(Feeding.id)).filter(
        Feeding.baby_id == baby_id,
        Feeding.start_time >= since
    ).scalar()
    
    # Total sleep time
    sleep_query = db.query(Sleep).filter(
        Sleep.baby_id == baby_id,
        Sleep.start_time >= since
    ).all()
    
    total_sleep_seconds = 0
    for sleep in sleep_query:
        sleep_start = sleep.start_time
        if sleep_start.tzinfo is None:
            sleep_start = utc_to_sgt(sleep_start)
            
        if sleep.end_time:
            sleep_end = sleep.end_time
            if sleep_end.tzinfo is None:
                sleep_end = utc_to_sgt(sleep_end)
                
            total_sleep_seconds += (sleep_end - sleep_start).total_seconds()
        else:
            # For ongoing sleep, count up to now
            total_sleep_seconds += (get_sgt_now() - sleep_start).total_seconds()
    
    total_sleep_hours = total_sleep_seconds / 3600
    
    # Diaper counts
    diaper_count = db.query(func.count(Diaper.id)).filter(
        Diaper.baby_id == baby_id,
        Diaper.time >= since
    ).scalar()
    
    wet_diapers = db.query(func.count(Diaper.id)).filter(
        Diaper.baby_id == baby_id,
        Diaper.time >= since,
        Diaper.type == DiaperType.WET
    ).scalar()
    
    dirty_diapers = db.query(func.count(Diaper.id)).filter(
        Diaper.baby_id == baby_id,
        Diaper.time >= since,
        Diaper.type == DiaperType.DIRTY
    ).scalar()
    
    both_diapers = db.query(func.count(Diaper.id)).filter(
        Diaper.baby_id == baby_id,
        Diaper.time >= since,
        Diaper.type == DiaperType.BOTH
    ).scalar()
    
    # Crying episodes
    crying_count = db.query(func.count(Crying.id)).filter(
        Crying.baby_id == baby_id,
        Crying.start_time >= since
    ).scalar()
    
    # Crying reasons
    crying_reasons = {}
    for reason in CryingReason:
        count = db.query(func.count(Crying.id)).filter(
            Crying.baby_id == baby_id,
            Crying.start_time >= since,
            Crying.actual_reason == reason
        ).scalar()
        crying_reasons[reason.value] = count
    
    return {
        "feeding_count": feeding_count,
        "total_sleep_hours": total_sleep_hours,
        "diaper_count": diaper_count,
        "wet_diapers": wet_diapers,
        "dirty_diapers": dirty_diapers,
        "both_diapers": both_diapers,
        "crying_count": crying_count,
        "crying_reasons": crying_reasons
    }

# NLP Query Functions
def get_last_feeding(db, baby_id: int) -> Dict[str, Any]:
    """Get the most recent feeding for a baby."""
    logger.info(f"Getting last feeding for baby_id={baby_id}")
    
    try:
        query = db.query(Feeding).filter(Feeding.baby_id == baby_id).order_by(Feeding.start_time.desc())
        logger.info(f"Query SQL: {query}")
        
        feeding = query.first()
        
        if not feeding:
            logger.warning(f"No feeding records found for baby_id={baby_id}")
            return {"found": False}
        
        logger.info(f"Found feeding record: id={feeding.id}, type={feeding.type}, time={feeding.start_time}")
        
        result = {
            "found": True,
            "type": feeding.type,
            "start_time": feeding.start_time,
            "end_time": feeding.end_time,
            "amount": feeding.amount
        }
        
        # Calculate duration if end_time exists
        if feeding.end_time:
            duration_minutes = (feeding.end_time - feeding.start_time).total_seconds() / 60
            result["duration_minutes"] = round(duration_minutes)
        
        return result
    except Exception as e:
        logger.error(f"Error getting last feeding: {e}")
        return {"found": False, "error": str(e)}

def get_last_sleep(db, baby_id: int) -> Dict[str, Any]:
    """Get the most recent sleep session for a baby."""
    sleep = db.query(Sleep).filter(
        Sleep.baby_id == baby_id
    ).order_by(Sleep.start_time.desc()).first()
    
    if not sleep:
        return {"found": False}
    
    result = {
        "found": True,
        "start_time": sleep.start_time,
        "end_time": sleep.end_time
    }
    
    # Calculate duration if end_time exists
    if sleep.end_time:
        duration_minutes = (sleep.end_time - sleep.start_time).total_seconds() / 60
        result["duration_minutes"] = round(duration_minutes)
        result["is_ongoing"] = False
    else:
        # Calculate duration up to now for ongoing sleep
        # Ensure both datetimes are timezone-aware before subtraction
        start_time = sleep.start_time
        if start_time.tzinfo is None:
            # If start_time is naive, apply timezone info using utc_to_sgt
            start_time = utc_to_sgt(start_time)
            
        duration_minutes = (get_sgt_now() - start_time).total_seconds() / 60
        result["duration_minutes"] = round(duration_minutes)
        result["is_ongoing"] = True
    
    return result

def get_last_diaper(db, baby_id: int) -> Dict[str, Any]:
    """Get the most recent diaper change for a baby."""
    diaper = db.query(Diaper).filter(
        Diaper.baby_id == baby_id
    ).order_by(Diaper.time.desc()).first()
    
    if not diaper:
        return {"found": False}
    
    return {
        "found": True,
        "type": diaper.type,
        "time": diaper.time
    }

def get_last_crying(db, baby_id: int) -> Dict[str, Any]:
    """Get the most recent crying episode for a baby."""
    crying = db.query(Crying).filter(
        Crying.baby_id == baby_id
    ).order_by(Crying.start_time.desc()).first()
    
    if not crying:
        return {"found": False}
    
    result = {
        "found": True,
        "start_time": crying.start_time,
        "end_time": crying.end_time,
        "reason": crying.actual_reason
    }
    
    # Calculate duration if end_time exists
    if crying.end_time:
        duration_minutes = (crying.end_time - crying.start_time).total_seconds() / 60
        result["duration_minutes"] = round(duration_minutes)
        result["is_ongoing"] = False
    else:
        # Calculate duration up to now for ongoing crying
        # Ensure both datetimes are timezone-aware before subtraction
        start_time = crying.start_time
        if start_time.tzinfo is None:
            # If start_time is naive, apply timezone info using utc_to_sgt
            start_time = utc_to_sgt(start_time)
            
        duration_minutes = (get_sgt_now() - start_time).total_seconds() / 60
        result["duration_minutes"] = round(duration_minutes)
        result["is_ongoing"] = True
    
    return result

def get_feeding_count(db, baby_id: int, start_time: datetime = None, end_time: datetime = None) -> Dict[str, Any]:
    """Get feeding count for a baby in a time period."""
    if not start_time:
        # Default to today
        now = get_sgt_now()
        start_time = datetime(now.year, now.month, now.day)
    
    if not end_time:
        end_time = get_sgt_now()
    
    # Count by type - use enum directly for both PostgreSQL and SQLite
    breast_count = db.query(func.count(Feeding.id)).filter(
        Feeding.baby_id == baby_id,
        Feeding.start_time >= start_time,
        Feeding.start_time <= end_time,
        Feeding.type == FeedingType.BREAST
    ).scalar()
    
    bottle_count = db.query(func.count(Feeding.id)).filter(
        Feeding.baby_id == baby_id,
        Feeding.start_time >= start_time,
        Feeding.start_time <= end_time,
        Feeding.type == FeedingType.BOTTLE
    ).scalar()
    
    solid_count = db.query(func.count(Feeding.id)).filter(
        Feeding.baby_id == baby_id,
        Feeding.start_time >= start_time,
        Feeding.start_time <= end_time,
        Feeding.type == FeedingType.SOLID
    ).scalar()
    
    total_count = breast_count + bottle_count + solid_count
    
    # Get total amount for bottle feedings
    total_amount = db.query(func.sum(Feeding.amount)).filter(
        Feeding.baby_id == baby_id,
        Feeding.start_time >= start_time,
        Feeding.start_time <= end_time,
        Feeding.type == FeedingType.BOTTLE,
        Feeding.amount != None
    ).scalar() or 0
    
    return {
        "total_count": total_count,
        "breast_count": breast_count,
        "bottle_count": bottle_count,
        "solid_count": solid_count,
        "total_amount": total_amount,
        "start_time": start_time,
        "end_time": end_time
    }

def get_sleep_duration(db, baby_id: int, start_time: datetime = None, end_time: datetime = None) -> Dict[str, Any]:
    """Get sleep duration for a baby in a time period."""
    if not start_time:
        # Default to today
        now = get_sgt_now()
        start_time = datetime(now.year, now.month, now.day, tzinfo=now.tzinfo)
    elif start_time.tzinfo is None:
        # Ensure start_time has timezone info
        start_time = utc_to_sgt(start_time)
    
    if not end_time:
        end_time = get_sgt_now()
    elif end_time.tzinfo is None:
        # Ensure end_time has timezone info
        end_time = utc_to_sgt(end_time)
    
    # Get all sleep sessions in the time period
    sleep_sessions = db.query(Sleep).filter(
        Sleep.baby_id == baby_id,
        Sleep.start_time >= start_time,
        Sleep.start_time <= end_time
    ).all()
    
    total_sleep_seconds = 0
    completed_sessions = 0
    ongoing_sessions = 0
    
    for sleep in sleep_sessions:
        sleep_start = sleep.start_time
        if sleep_start.tzinfo is None:
            sleep_start = utc_to_sgt(sleep_start)
            
        if sleep.end_time:
            sleep_end = sleep.end_time
            if sleep_end.tzinfo is None:
                sleep_end = utc_to_sgt(sleep_end)
                
            total_sleep_seconds += (sleep_end - sleep_start).total_seconds()
            completed_sessions += 1
        else:
            # For ongoing sleep, count up to now
            total_sleep_seconds += (get_sgt_now() - sleep_start).total_seconds()
            ongoing_sessions += 1
    
    total_sleep_hours = total_sleep_seconds / 3600
    
    return {
        "total_hours": round(total_sleep_hours, 1),
        "completed_sessions": completed_sessions,
        "ongoing_sessions": ongoing_sessions,
        "total_sessions": completed_sessions + ongoing_sessions,
        "start_time": start_time,
        "end_time": end_time
    }

def get_diaper_count(db, baby_id: int, start_time: datetime = None, end_time: datetime = None) -> Dict[str, Any]:
    """Get diaper count for a baby in a time period."""
    if not start_time:
        # Default to today
        now = get_sgt_now()
        start_time = datetime(now.year, now.month, now.day)
    
    if not end_time:
        end_time = get_sgt_now()
    
    # Count by type - use enum directly for both PostgreSQL and SQLite
    wet_count = db.query(func.count(Diaper.id)).filter(
        Diaper.baby_id == baby_id,
        Diaper.time >= start_time,
        Diaper.time <= end_time,
        Diaper.type == DiaperType.WET
    ).scalar()
    
    dirty_count = db.query(func.count(Diaper.id)).filter(
        Diaper.baby_id == baby_id,
        Diaper.time >= start_time,
        Diaper.time <= end_time,
        Diaper.type == DiaperType.DIRTY
    ).scalar()
    
    both_count = db.query(func.count(Diaper.id)).filter(
        Diaper.baby_id == baby_id,
        Diaper.time >= start_time,
        Diaper.time <= end_time,
        Diaper.type == DiaperType.BOTH
    ).scalar()
    
    total_count = wet_count + dirty_count + both_count
    
    return {
        "total_count": total_count,
        "wet_count": wet_count,
        "dirty_count": dirty_count,
        "both_count": both_count,
        "start_time": start_time,
        "end_time": end_time
    }

def get_crying_episodes(db, baby_id: int, start_time: datetime = None, end_time: datetime = None) -> Dict[str, Any]:
    """Get crying episodes for a baby in a time period."""
    if not start_time:
        # Default to today
        now = get_sgt_now()
        start_time = datetime(now.year, now.month, now.day)
    
    if not end_time:
        end_time = get_sgt_now()
    
    # Get all crying episodes in the time period
    crying_episodes = db.query(Crying).filter(
        Crying.baby_id == baby_id,
        Crying.start_time >= start_time,
        Crying.start_time <= end_time
    ).all()
    
    total_crying_seconds = 0
    completed_episodes = 0
    ongoing_episodes = 0
    reasons = {}
    
    for crying in crying_episodes:
        if crying.end_time:
            total_crying_seconds += (crying.end_time - crying.start_time).total_seconds()
            completed_episodes += 1
            
            # Count reasons
            if is_postgres:
                reason = crying.actual_reason if crying.actual_reason else "unknown"
            else:
                reason = crying.actual_reason.value if crying.actual_reason else "unknown"
            reasons[reason] = reasons.get(reason, 0) + 1
        else:
            # For ongoing crying, count up to now
            total_crying_seconds += (get_sgt_now() - crying.start_time).total_seconds()
            ongoing_episodes += 1
    
    total_crying_minutes = total_crying_seconds / 60
    
    return {
        "total_minutes": round(total_crying_minutes),
        "completed_episodes": completed_episodes,
        "ongoing_episodes": ongoing_episodes,
        "total_episodes": completed_episodes + ongoing_episodes,
        "reasons": reasons,
        "start_time": start_time,
        "end_time": end_time
    }

def get_baby_schedule(db, baby_id: int, days: int = 3) -> Dict[str, Any]:
    """Get a baby's schedule based on recent events."""
    end_time = get_sgt_now()
    start_time = end_time - timedelta(days=days)
    
    # Get all events in the time period
    feedings = db.query(Feeding).filter(
        Feeding.baby_id == baby_id,
        Feeding.start_time >= start_time,
        Feeding.start_time <= end_time
    ).order_by(Feeding.start_time).all()
    
    sleeps = db.query(Sleep).filter(
        Sleep.baby_id == baby_id,
        Sleep.start_time >= start_time,
        Sleep.start_time <= end_time
    ).order_by(Sleep.start_time).all()
    
    diapers = db.query(Diaper).filter(
        Diaper.baby_id == baby_id,
        Diaper.time >= start_time,
        Diaper.time <= end_time
    ).order_by(Diaper.time).all()
    
    # Calculate average intervals
    feeding_intervals = []
    for i in range(1, len(feedings)):
        prev_time = feedings[i-1].start_time
        curr_time = feedings[i].start_time
        
        # Ensure both times have timezone info
        if prev_time.tzinfo is None:
            prev_time = utc_to_sgt(prev_time)
        if curr_time.tzinfo is None:
            curr_time = utc_to_sgt(curr_time)
            
        interval = (curr_time - prev_time).total_seconds() / 3600
        feeding_intervals.append(interval)
    
    sleep_intervals = []
    for i in range(1, len(sleeps)):
        prev_time = sleeps[i-1].start_time
        curr_time = sleeps[i].start_time
        
        # Ensure both times have timezone info
        if prev_time.tzinfo is None:
            prev_time = utc_to_sgt(prev_time)
        if curr_time.tzinfo is None:
            curr_time = utc_to_sgt(curr_time)
            
        interval = (curr_time - prev_time).total_seconds() / 3600
        sleep_intervals.append(interval)
    
    diaper_intervals = []
    for i in range(1, len(diapers)):
        prev_time = diapers[i-1].time
        curr_time = diapers[i].time
        
        # Ensure both times have timezone info
        if prev_time.tzinfo is None:
            prev_time = utc_to_sgt(prev_time)
        if curr_time.tzinfo is None:
            curr_time = utc_to_sgt(curr_time)
            
        interval = (curr_time - prev_time).total_seconds() / 3600
        diaper_intervals.append(interval)
    
    # Calculate averages
    avg_feeding_interval = sum(feeding_intervals) / len(feeding_intervals) if feeding_intervals else 0
    avg_sleep_interval = sum(sleep_intervals) / len(sleep_intervals) if sleep_intervals else 0
    avg_diaper_interval = sum(diaper_intervals) / len(diaper_intervals) if diaper_intervals else 0
    
    # Calculate average sleep duration
    sleep_durations = []
    for sleep in sleeps:
        if sleep.end_time:
            start_time = sleep.start_time
            end_time = sleep.end_time
            
            # Ensure both times have timezone info
            if start_time.tzinfo is None:
                start_time = utc_to_sgt(start_time)
            if end_time.tzinfo is None:
                end_time = utc_to_sgt(end_time)
                
            duration = (end_time - start_time).total_seconds() / 3600
            sleep_durations.append(duration)
    
    avg_sleep_duration = sum(sleep_durations) / len(sleep_durations) if sleep_durations else 0
    
    return {
        "avg_feeding_interval_hours": round(avg_feeding_interval, 1),
        "avg_sleep_interval_hours": round(avg_sleep_interval, 1),
        "avg_diaper_interval_hours": round(avg_diaper_interval, 1),
        "avg_sleep_duration_hours": round(avg_sleep_duration, 1),
        "feeding_count": len(feedings),
        "sleep_count": len(sleeps),
        "diaper_count": len(diapers),
        "days_analyzed": days
    }

# Add helper functions for enum handling
def to_enum_value(enum_str, enum_class):
    """Convert string to enum value if needed"""
    if isinstance(enum_str, str):
        for enum_item in enum_class:
            if enum_str == enum_item.value:
                return enum_item
        return None
    return enum_str

def to_enum_string(enum_val):
    """Convert enum to string value if needed"""
    logger.info(f"Converting enum value: {enum_val}, type: {type(enum_val)}")
    if hasattr(enum_val, 'value'):
        result = enum_val.value
        logger.info(f"Converted enum to string: '{result}'")
        return result
    logger.info(f"Value already a string: '{enum_val}'")
    return enum_val 