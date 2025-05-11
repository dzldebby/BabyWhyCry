from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine import Engine
from sqlalchemy import event
import os
import datetime
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from models import Base, User, Baby, Feeding, Sleep, Diaper, Crying
from models import FeedingType, DiaperType, CryingReason
from utils import get_sgt_now, utc_to_sgt, sgt_to_utc

# Configure logging
logger = logging.getLogger(__name__)

# Get database URL from environment or use SQLite as fallback
DATABASE_URL = os.getenv("DATABASE_URL")

# Check if we're using PostgreSQL or SQLite
is_postgres = DATABASE_URL is not None

# Setup proper engine based on available database
if DATABASE_URL:
    # Handle Supabase/PostgreSQL connection
    # Convert potential "postgres://" to "postgresql://" for SQLAlchemy
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    engine = create_engine(DATABASE_URL)
    
    # PostgreSQL doesn't need this pragma
    @event.listens_for(Engine, "connect")
    def set_postgresql_schema(dbapi_connection, connection_record):
        # Set search path if needed
        # cursor = dbapi_connection.cursor()
        # cursor.execute("SET search_path TO public")
        # cursor.close()
        pass
else:
    # Fallback to SQLite for local development
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, 'baby_alert.db')
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"
    
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    
    # Configure SQLite to enforce foreign key constraints
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get a database session."""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

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
    # Convert enum to string if using PostgreSQL
    if is_postgres:
        feeding_type_val = to_enum_string(feeding_type)  # Converts FeedingType.BREAST to "breast"
    else:
        feeding_type_val = feeding_type  # SQLite can store the enum object directly
        
    feeding = Feeding(
        baby_id=baby_id,
        type=feeding_type_val,  # This is either a string or enum depending on database
        start_time=get_sgt_now()
    )
    db.add(feeding)
    db.commit()
    db.refresh(feeding)
    return feeding

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
    # Convert enum to string if using PostgreSQL
    if is_postgres:
        diaper_type_val = to_enum_string(diaper_type)
    else:
        diaper_type_val = diaper_type
        
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
            # Convert enum to string if using PostgreSQL
            if is_postgres:
                crying.actual_reason = to_enum_string(actual_reason)
            else:
                crying.actual_reason = actual_reason
        db.commit()
        db.refresh(crying)
    return crying

# Event retrieval
def get_recent_events(db, baby_id: int, limit: int = 10, days: int = 7) -> List[Dict[str, Any]]:
    """Get recent events for a baby."""
    since = get_sgt_now() - timedelta(days=days)
    
    # Get recent feedings
    feedings = db.query(Feeding).filter(
        Feeding.baby_id == baby_id,
        Feeding.start_time >= since
    ).order_by(Feeding.start_time.desc()).limit(limit).all()
    
    # Get recent sleeps
    sleeps = db.query(Sleep).filter(
        Sleep.baby_id == baby_id,
        Sleep.start_time >= since
    ).order_by(Sleep.start_time.desc()).limit(limit).all()
    
    # Get recent diapers
    diapers = db.query(Diaper).filter(
        Diaper.baby_id == baby_id,
        Diaper.time >= since
    ).order_by(Diaper.time.desc()).limit(limit).all()
    
    # Get recent crying episodes
    cryings = db.query(Crying).filter(
        Crying.baby_id == baby_id,
        Crying.start_time >= since
    ).order_by(Crying.start_time.desc()).limit(limit).all()
    
    # Combine all events and sort by time
    events = []
    
    for feeding in feedings:
        events.append({
            "type": "feeding",
            "time": feeding.start_time,
            "data": feeding
        })
    
    for sleep in sleeps:
        events.append({
            "type": "sleep",
            "time": sleep.start_time,
            "data": sleep
        })
    
    for diaper in diapers:
        events.append({
            "type": "diaper",
            "time": diaper.time,
            "data": diaper
        })
    
    for crying in cryings:
        events.append({
            "type": "crying",
            "time": crying.start_time,
            "data": crying
        })
    
    # Sort by time (most recent first)
    events.sort(key=lambda x: x["time"], reverse=True)
    
    # Limit the number of events
    return events[:limit]

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
        if sleep.end_time:
            total_sleep_seconds += (sleep.end_time - sleep.start_time).total_seconds()
        else:
            # For ongoing sleep, count up to now
            total_sleep_seconds += (get_sgt_now() - sleep.start_time).total_seconds()
    
    total_sleep_hours = total_sleep_seconds / 3600
    
    # Diaper counts
    diaper_count = db.query(func.count(Diaper.id)).filter(
        Diaper.baby_id == baby_id,
        Diaper.time >= since
    ).scalar()
    
    if is_postgres:
        wet_diapers = db.query(func.count(Diaper.id)).filter(
            Diaper.baby_id == baby_id,
            Diaper.time >= since,
            Diaper.type == DiaperType.WET.value
        ).scalar()
        
        dirty_diapers = db.query(func.count(Diaper.id)).filter(
            Diaper.baby_id == baby_id,
            Diaper.time >= since,
            Diaper.type == DiaperType.DIRTY.value
        ).scalar()
        
        both_diapers = db.query(func.count(Diaper.id)).filter(
            Diaper.baby_id == baby_id,
            Diaper.time >= since,
            Diaper.type == DiaperType.BOTH.value
        ).scalar()
    else:
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
        if is_postgres:
            count = db.query(func.count(Crying.id)).filter(
                Crying.baby_id == baby_id,
                Crying.start_time >= since,
                Crying.actual_reason == reason.value
            ).scalar()
        else:
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
    feeding = db.query(Feeding).filter(
        Feeding.baby_id == baby_id
    ).order_by(Feeding.start_time.desc()).first()
    
    if not feeding:
        return {"found": False}
    
    result = {
        "found": True,
        "type": feeding.type if is_postgres else feeding.type.value,
        "start_time": feeding.start_time,
        "end_time": feeding.end_time,
        "amount": feeding.amount
    }
    
    # Calculate duration if end_time exists
    if feeding.end_time:
        duration_minutes = (feeding.end_time - feeding.start_time).total_seconds() / 60
        result["duration_minutes"] = round(duration_minutes)
    
    return result

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
        duration_minutes = (get_sgt_now() - sleep.start_time).total_seconds() / 60
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
        "type": diaper.type if is_postgres else diaper.type.value,
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
        "reason": crying.actual_reason if is_postgres else (crying.actual_reason.value if crying.actual_reason else None)
    }
    
    # Calculate duration if end_time exists
    if crying.end_time:
        duration_minutes = (crying.end_time - crying.start_time).total_seconds() / 60
        result["duration_minutes"] = round(duration_minutes)
        result["is_ongoing"] = False
    else:
        # Calculate duration up to now for ongoing crying
        duration_minutes = (get_sgt_now() - crying.start_time).total_seconds() / 60
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
    
    # Count by type
    if is_postgres:
        breast_count = db.query(func.count(Feeding.id)).filter(
            Feeding.baby_id == baby_id,
            Feeding.start_time >= start_time,
            Feeding.start_time <= end_time,
            Feeding.type == FeedingType.BREAST.value  # Use "breast" (string value)
        ).scalar()
        
        bottle_count = db.query(func.count(Feeding.id)).filter(
            Feeding.baby_id == baby_id,
            Feeding.start_time >= start_time,
            Feeding.start_time <= end_time,
            Feeding.type == FeedingType.BOTTLE.value  # Use "bottle" (string value)
        ).scalar()
        
        solid_count = db.query(func.count(Feeding.id)).filter(
            Feeding.baby_id == baby_id,
            Feeding.start_time >= start_time,
            Feeding.start_time <= end_time,
            Feeding.type == FeedingType.SOLID.value  # Use "solid" (string value)
        ).scalar()
    else:
        breast_count = db.query(func.count(Feeding.id)).filter(
            Feeding.baby_id == baby_id,
            Feeding.start_time >= start_time,
            Feeding.start_time <= end_time,
            Feeding.type == FeedingType.BREAST  # Use FeedingType.BREAST (enum object)
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
    if is_postgres:
        total_amount = db.query(func.sum(Feeding.amount)).filter(
            Feeding.baby_id == baby_id,
            Feeding.start_time >= start_time,
            Feeding.start_time <= end_time,
            Feeding.type == FeedingType.BOTTLE.value,
            Feeding.amount != None
        ).scalar() or 0
    else:
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
        start_time = datetime(now.year, now.month, now.day)
    
    if not end_time:
        end_time = get_sgt_now()
    
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
        if sleep.end_time:
            total_sleep_seconds += (sleep.end_time - sleep.start_time).total_seconds()
            completed_sessions += 1
        else:
            # For ongoing sleep, count up to now
            total_sleep_seconds += (get_sgt_now() - sleep.start_time).total_seconds()
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
    
    # Count by type
    if is_postgres:
        wet_count = db.query(func.count(Diaper.id)).filter(
            Diaper.baby_id == baby_id,
            Diaper.time >= start_time,
            Diaper.time <= end_time,
            Diaper.type == DiaperType.WET.value  # String value
        ).scalar()
        
        dirty_count = db.query(func.count(Diaper.id)).filter(
            Diaper.baby_id == baby_id,
            Diaper.time >= start_time,
            Diaper.time <= end_time,
            Diaper.type == DiaperType.DIRTY.value  # String value
        ).scalar()
        
        both_count = db.query(func.count(Diaper.id)).filter(
            Diaper.baby_id == baby_id,
            Diaper.time >= start_time,
            Diaper.time <= end_time,
            Diaper.type == DiaperType.BOTH.value  # String value
        ).scalar()
    else:
        wet_count = db.query(func.count(Diaper.id)).filter(
            Diaper.baby_id == baby_id,
            Diaper.time >= start_time,
            Diaper.time <= end_time,
            Diaper.type == DiaperType.WET  # Enum object
        ).scalar()
        
        dirty_count = db.query(func.count(Diaper.id)).filter(
            Diaper.baby_id == baby_id,
            Diaper.time >= start_time,
            Diaper.time <= end_time,
            Diaper.type == DiaperType.DIRTY  # Enum object
        ).scalar()
        
        both_count = db.query(func.count(Diaper.id)).filter(
            Diaper.baby_id == baby_id,
            Diaper.time >= start_time,
            Diaper.time <= end_time,
            Diaper.type == DiaperType.BOTH  # Enum object
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
        interval = (feedings[i].start_time - feedings[i-1].start_time).total_seconds() / 3600
        feeding_intervals.append(interval)
    
    sleep_intervals = []
    for i in range(1, len(sleeps)):
        interval = (sleeps[i].start_time - sleeps[i-1].start_time).total_seconds() / 3600
        sleep_intervals.append(interval)
    
    diaper_intervals = []
    for i in range(1, len(diapers)):
        interval = (diapers[i].time - diapers[i-1].time).total_seconds() / 3600
        diaper_intervals.append(interval)
    
    # Calculate averages
    avg_feeding_interval = sum(feeding_intervals) / len(feeding_intervals) if feeding_intervals else 0
    avg_sleep_interval = sum(sleep_intervals) / len(sleep_intervals) if sleep_intervals else 0
    avg_diaper_interval = sum(diaper_intervals) / len(diaper_intervals) if diaper_intervals else 0
    
    # Calculate average sleep duration
    sleep_durations = []
    for sleep in sleeps:
        if sleep.end_time:
            duration = (sleep.end_time - sleep.start_time).total_seconds() / 3600
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
    if hasattr(enum_val, 'value'):
        return enum_val.value
    return enum_val 