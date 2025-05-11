import os
import sys
import unittest
from datetime import datetime, timedelta
import tempfile

# Add parent directory to path so we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, User, Baby, Feeding, Sleep, Diaper, Crying
from src.models import FeedingType, DiaperType, CryingReason
from src.database import (
    create_user, create_baby, start_feeding, end_feeding,
    start_sleep, end_sleep, log_diaper_change,
    start_crying, end_crying, get_recent_events, get_baby_stats
)

class TestDatabase(unittest.TestCase):
    def setUp(self):
        # Create a temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db')
        
        # Create an engine and session
        self.engine = create_engine(f"sqlite:///{self.temp_db.name}")
        self.Session = sessionmaker(bind=self.engine)
        
        # Create all tables
        Base.metadata.create_all(self.engine)
        
        # Create a session
        self.db = self.Session()
        
        # Create a test user and baby
        self.test_user = create_user(self.db, "testuser", "test@example.com")
        self.test_baby = create_baby(self.db, "Test Baby", self.test_user.id)
    
    def tearDown(self):
        # Close the session
        self.db.close()
        
        # Remove the temporary database
        self.temp_db.close()
    
    def test_create_user(self):
        """Test creating a user."""
        user = create_user(self.db, "testuser2", "test2@example.com")
        self.assertIsNotNone(user.id)
        self.assertEqual(user.username, "testuser2")
        self.assertEqual(user.email, "test2@example.com")
    
    def test_create_baby(self):
        """Test creating a baby."""
        baby = create_baby(self.db, "Test Baby 2", self.test_user.id)
        self.assertIsNotNone(baby.id)
        self.assertEqual(baby.name, "Test Baby 2")
        self.assertEqual(baby.parent_id, self.test_user.id)
    
    def test_feeding(self):
        """Test feeding operations."""
        # Start feeding
        feeding = start_feeding(self.db, self.test_baby.id, FeedingType.BOTTLE)
        self.assertIsNotNone(feeding.id)
        self.assertEqual(feeding.baby_id, self.test_baby.id)
        self.assertEqual(feeding.type, FeedingType.BOTTLE)
        self.assertIsNotNone(feeding.start_time)
        self.assertIsNone(feeding.end_time)
        
        # End feeding
        feeding = end_feeding(self.db, feeding.id, 120.0)
        self.assertIsNotNone(feeding.end_time)
        self.assertEqual(feeding.amount, 120.0)
    
    def test_sleep(self):
        """Test sleep operations."""
        # Start sleep
        sleep = start_sleep(self.db, self.test_baby.id)
        self.assertIsNotNone(sleep.id)
        self.assertEqual(sleep.baby_id, self.test_baby.id)
        self.assertIsNotNone(sleep.start_time)
        self.assertIsNone(sleep.end_time)
        
        # End sleep
        sleep = end_sleep(self.db, sleep.id)
        self.assertIsNotNone(sleep.end_time)
    
    def test_diaper(self):
        """Test diaper operations."""
        # Log diaper change
        diaper = log_diaper_change(self.db, self.test_baby.id, DiaperType.WET)
        self.assertIsNotNone(diaper.id)
        self.assertEqual(diaper.baby_id, self.test_baby.id)
        self.assertEqual(diaper.type, DiaperType.WET)
        self.assertIsNotNone(diaper.time)
    
    def test_crying(self):
        """Test crying operations."""
        # Start crying
        crying = start_crying(self.db, self.test_baby.id)
        self.assertIsNotNone(crying.id)
        self.assertEqual(crying.baby_id, self.test_baby.id)
        self.assertIsNotNone(crying.start_time)
        self.assertIsNone(crying.end_time)
        
        # End crying
        crying = end_crying(self.db, crying.id, CryingReason.HUNGRY)
        self.assertIsNotNone(crying.end_time)
        self.assertEqual(crying.actual_reason, CryingReason.HUNGRY)
    
    def test_get_recent_events(self):
        """Test getting recent events."""
        # Create some events
        start_feeding(self.db, self.test_baby.id, FeedingType.BREAST)
        start_sleep(self.db, self.test_baby.id)
        log_diaper_change(self.db, self.test_baby.id, DiaperType.DIRTY)
        
        # Get recent events
        events = get_recent_events(self.db, self.test_baby.id)
        self.assertEqual(len(events), 3)
    
    def test_get_baby_stats(self):
        """Test getting baby statistics."""
        # Create some events
        start_feeding(self.db, self.test_baby.id, FeedingType.BREAST)
        sleep = start_sleep(self.db, self.test_baby.id)
        sleep.end_time = sleep.start_time + timedelta(hours=2)
        self.db.commit()
        
        log_diaper_change(self.db, self.test_baby.id, DiaperType.WET)
        log_diaper_change(self.db, self.test_baby.id, DiaperType.DIRTY)
        
        # Get stats
        stats = get_baby_stats(self.db, self.test_baby.id)
        self.assertEqual(stats["feeding_count"], 1)
        self.assertAlmostEqual(stats["total_sleep_hours"], 2.0, delta=0.1)
        self.assertEqual(stats["diaper_count"], 2)
        self.assertEqual(stats["wet_diapers"], 1)
        self.assertEqual(stats["dirty_diapers"], 1)

if __name__ == '__main__':
    unittest.main() 