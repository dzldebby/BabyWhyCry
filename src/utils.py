from datetime import datetime, timedelta, timezone
import pytz

# Singapore timezone
SGT = pytz.timezone('Asia/Singapore')

def get_sgt_now():
    """Get current time in Singapore timezone (SGT)"""
    return datetime.now(SGT)

def utc_to_sgt(utc_time):
    """Convert UTC datetime to Singapore timezone (SGT)"""
    if utc_time is None:
        return None
    
    # If the datetime is naive (no timezone info), assume it's UTC
    if utc_time.tzinfo is None:
        utc_time = utc_time.replace(tzinfo=timezone.utc)
    
    # Convert to SGT
    return utc_time.astimezone(SGT)

def sgt_to_utc(sgt_time):
    """Convert Singapore timezone (SGT) datetime to UTC"""
    if sgt_time is None:
        return None
    
    # If the datetime is naive (no timezone info), assume it's SGT
    if sgt_time.tzinfo is None:
        sgt_time = SGT.localize(sgt_time)
    
    # Convert to UTC
    return sgt_time.astimezone(timezone.utc)

def format_datetime(dt, include_seconds=True):
    """Format datetime in a user-friendly way"""
    if dt is None:
        return "N/A"
    
    # Convert to SGT if it has timezone info
    if dt.tzinfo is not None:
        dt = dt.astimezone(SGT)
    
    # Format with or without seconds
    if include_seconds:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        return dt.strftime("%Y-%m-%d %H:%M")
