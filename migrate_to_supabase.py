#!/usr/bin/env python
import os
import sqlite3
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database connection parameters
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL environment variable not set")
    exit(1)

# Convert postgres:// to postgresql:// if needed
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Get path to SQLite database
data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
db_path = os.path.join(data_dir, 'baby_alert.db')

if not os.path.exists(db_path):
    print(f"Error: SQLite database not found at {db_path}")
    exit(1)

print(f"Migrating data from {db_path} to Supabase...")

# Connect to SQLite database
sqlite_conn = sqlite3.connect(db_path)
sqlite_conn.row_factory = sqlite3.Row
sqlite_cursor = sqlite_conn.cursor()

# Connect to PostgreSQL database
pg_conn = psycopg2.connect(DATABASE_URL)
pg_cursor = pg_conn.cursor()

try:
    # Migrate users
    print("Migrating users...")
    sqlite_cursor.execute("SELECT id, username, email, role, department FROM users")
    users = sqlite_cursor.fetchall()
    
    for user in users:
        pg_cursor.execute(
            "INSERT INTO users (id, username, email, role, department) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (user['id'], user['username'], user['email'], user['role'], user['department'])
        )
    
    # Migrate babies
    print("Migrating babies...")
    sqlite_cursor.execute("SELECT id, name, birth_date, parent_id FROM babies")
    babies = sqlite_cursor.fetchall()
    
    for baby in babies:
        pg_cursor.execute(
            "INSERT INTO babies (id, name, birth_date, parent_id) VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (baby['id'], baby['name'], baby['birth_date'], baby['parent_id'])
        )
    
    # Migrate feedings
    print("Migrating feedings...")
    sqlite_cursor.execute("SELECT id, baby_id, type, start_time, end_time, amount, notes FROM feedings")
    feedings = sqlite_cursor.fetchall()
    
    for feeding in feedings:
        # Convert enum to string value
        feeding_type = feeding['type']
        if isinstance(feeding_type, int):  # SQLite might store enum as int
            feeding_types = ["breast", "bottle", "solid"]
            feeding_type = feeding_types[feeding_type - 1] if 0 < feeding_type <= 3 else "unknown"
        
        pg_cursor.execute(
            "INSERT INTO feedings (id, baby_id, type, start_time, end_time, amount, notes) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (feeding['id'], feeding['baby_id'], feeding_type, feeding['start_time'], feeding['end_time'], feeding['amount'], feeding['notes'])
        )
    
    # Migrate sleeps
    print("Migrating sleeps...")
    sqlite_cursor.execute("SELECT id, baby_id, start_time, end_time, notes FROM sleeps")
    sleeps = sqlite_cursor.fetchall()
    
    for sleep in sleeps:
        pg_cursor.execute(
            "INSERT INTO sleeps (id, baby_id, start_time, end_time, notes) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (sleep['id'], sleep['baby_id'], sleep['start_time'], sleep['end_time'], sleep['notes'])
        )
    
    # Migrate diapers
    print("Migrating diapers...")
    sqlite_cursor.execute("SELECT id, baby_id, type, time, notes FROM diapers")
    diapers = sqlite_cursor.fetchall()
    
    for diaper in diapers:
        # Convert enum to string value
        diaper_type = diaper['type']
        if isinstance(diaper_type, int):  # SQLite might store enum as int
            diaper_types = ["wet", "dirty", "both"]
            diaper_type = diaper_types[diaper_type - 1] if 0 < diaper_type <= 3 else "unknown"
        
        pg_cursor.execute(
            "INSERT INTO diapers (id, baby_id, type, time, notes) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (diaper['id'], diaper['baby_id'], diaper_type, diaper['time'], diaper['notes'])
        )
    
    # Migrate crying episodes
    print("Migrating crying episodes...")
    sqlite_cursor.execute("SELECT id, baby_id, start_time, end_time, reason, predicted_reason, prediction_confidence, actual_reason, notes FROM cryings")
    cryings = sqlite_cursor.fetchall()
    
    for crying in cryings:
        # Convert enum values to string values
        reason = crying['reason']
        if isinstance(reason, int) and reason > 0:
            crying_reasons = ["hungry", "diaper", "attention", "unknown"]
            reason = crying_reasons[reason - 1] if 0 < reason <= 4 else "unknown"
        
        predicted_reason = crying['predicted_reason']
        if isinstance(predicted_reason, int) and predicted_reason > 0:
            crying_reasons = ["hungry", "diaper", "attention", "unknown"]
            predicted_reason = crying_reasons[predicted_reason - 1] if 0 < predicted_reason <= 4 else "unknown"
        
        actual_reason = crying['actual_reason']
        if isinstance(actual_reason, int) and actual_reason > 0:
            crying_reasons = ["hungry", "diaper", "attention", "unknown"]
            actual_reason = crying_reasons[actual_reason - 1] if 0 < actual_reason <= 4 else "unknown"
        
        pg_cursor.execute(
            "INSERT INTO cryings (id, baby_id, start_time, end_time, reason, predicted_reason, prediction_confidence, actual_reason, notes) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (crying['id'], crying['baby_id'], crying['start_time'], crying['end_time'], reason, predicted_reason, crying['prediction_confidence'], actual_reason, crying['notes'])
        )
    
    # Commit the transaction
    pg_conn.commit()
    print("Migration completed successfully!")

except Exception as e:
    pg_conn.rollback()
    print(f"Error during migration: {e}")

finally:
    # Close connections
    sqlite_cursor.close()
    sqlite_conn.close()
    pg_cursor.close()
    pg_conn.close() 