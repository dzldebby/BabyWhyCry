from datetime import datetime, timedelta, timezone
import pytz
import logging

# Configure logging
logger = logging.getLogger(__name__)

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
    """Format datetime in a user-friendly way with explicit SGT conversion"""
    if dt is None:
        return "N/A"
    
    try:
        # Log the input datetime for debugging
        logger.info(f"Original datetime: {dt}, tzinfo: {dt.tzinfo}")
        
        # Always assume naive datetimes are UTC
        if dt.tzinfo is None:
            logger.info("Converting naive datetime from UTC to SGT")
            dt = datetime.replace(dt, tzinfo=timezone.utc)
            dt = dt.astimezone(SGT)
        else:
            logger.info(f"Converting aware datetime from {dt.tzinfo} to SGT")
            dt = dt.astimezone(SGT)
        
        # Log the converted datetime
        logger.info(f"Converted to SGT: {dt}")
        
        # Add SGT indicator to the format
        if include_seconds:
            return dt.strftime("%Y-%m-%d %H:%M:%S (SGT)")
        else:
            return dt.strftime("%Y-%m-%d %H:%M (SGT)")
    except Exception as e:
        logger.error(f"Error formatting datetime: {e}")
        # Fallback to simple formatting
        if include_seconds:
            return dt.strftime("%Y-%m-%d %H:%M:%S") + " (UTC)"
        else:
            return dt.strftime("%Y-%m-%d %H:%M") + " (UTC)"
