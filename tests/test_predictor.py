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
    start_crying, end_crying
)
from src.predictor import CryingPredictor, predict_crying_reason, analyze_crying_episode

class TestPredictor(unittest.TestCase):
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
        
        # Create a predictor
        self.predictor = CryingPredictor()
    
    def tearDown(self):
        # Close the session
        self.db.close()
        
        # Remove the temporary database
        self.temp_db.close()
    
    def test_predict_hunger(self):
        """Test predicting hunger."""
        # Set up a scenario where the baby is likely hungry
        # Last feeding was more than 3 hours ago
        feeding = Feeding(
            baby_id=self.test_baby.id,
            type=FeedingType.BOTTLE,
            start_time=datetime.utcnow() - timedelta(hours=3),
            end_time=datetime.utcnow() - timedelta(hours=2, minutes=50)
        )
        self.db.add(feeding)
        
        # Recent diaper change (less likely to be diaper)
        diaper = Diaper(
            baby_id=self.test_baby.id,
            type=DiaperType.WET,
            time=datetime.utcnow() - timedelta(minutes=30)
        )
        self.db.add(diaper)
        
        # Recent sleep (less likely to be tired)
        sleep = Sleep(
            baby_id=self.test_baby.id,
            start_time=datetime.utcnow() - timedelta(hours=2),
            end_time=datetime.utcnow() - timedelta(minutes=45)
        )
        self.db.add(sleep)
        
        self.db.commit()
        
        # Make a prediction
        reason, confidence = self.predictor.predict(self.db, self.test_baby.id)
        
        # The prediction should be hunger
        self.assertEqual(reason, CryingReason.HUNGRY)
        self.assertGreater(confidence, 50)  # Should have decent confidence
    
    def test_predict_diaper(self):
        """Test predicting diaper need."""
        # Set up a scenario where the baby likely needs a diaper change
        # Recent feeding (less likely to be hungry)
        feeding = Feeding(
            baby_id=self.test_baby.id,
            type=FeedingType.BOTTLE,
            start_time=datetime.utcnow() - timedelta(minutes=45),
            end_time=datetime.utcnow() - timedelta(minutes=30)
        )
        self.db.add(feeding)
        
        # Last diaper change was more than 3 hours ago
        diaper = Diaper(
            baby_id=self.test_baby.id,
            type=DiaperType.WET,
            time=datetime.utcnow() - timedelta(hours=4)
        )
        self.db.add(diaper)
        
        # Recent sleep (less likely to be tired)
        sleep = Sleep(
            baby_id=self.test_baby.id,
            start_time=datetime.utcnow() - timedelta(hours=2),
            end_time=datetime.utcnow() - timedelta(hours=1)
        )
        self.db.add(sleep)
        
        self.db.commit()
        
        # Make a prediction
        reason, confidence = self.predictor.predict(self.db, self.test_baby.id)
        
        # The prediction should be diaper
        self.assertEqual(reason, CryingReason.DIAPER)
        self.assertGreater(confidence, 50)  # Should have decent confidence
    
    def test_predict_attention(self):
        """Test predicting need for attention."""
        # Set up a scenario where the baby likely needs attention
        # Recent feeding (less likely to be hungry)
        feeding = Feeding(
            baby_id=self.test_baby.id,
            type=FeedingType.BOTTLE,
            start_time=datetime.utcnow() - timedelta(minutes=30),
            end_time=datetime.utcnow() - timedelta(minutes=15)
        )
        self.db.add(feeding)
        
        # Recent diaper change (less likely to be diaper)
        diaper = Diaper(
            baby_id=self.test_baby.id,
            type=DiaperType.WET,
            time=datetime.utcnow() - timedelta(minutes=20)
        )
        self.db.add(diaper)
        
        # Been awake for a long time
        sleep = Sleep(
            baby_id=self.test_baby.id,
            start_time=datetime.utcnow() - timedelta(hours=4),
            end_time=datetime.utcnow() - timedelta(hours=2)
        )
        self.db.add(sleep)
        
        self.db.commit()
        
        # Make a prediction
        reason, confidence = self.predictor.predict(self.db, self.test_baby.id)
        
        # The prediction should be attention
        self.assertEqual(reason, CryingReason.ATTENTION)
        self.assertGreater(confidence, 50)  # Should have decent confidence
    
    def test_analyze_crying_episode(self):
        """Test analyzing a crying episode."""
        # Create a crying episode
        crying = start_crying(self.db, self.test_baby.id)
        
        # Set up a scenario
        feeding = Feeding(
            baby_id=self.test_baby.id,
            type=FeedingType.BOTTLE,
            start_time=datetime.utcnow() - timedelta(hours=3),
            end_time=datetime.utcnow() - timedelta(hours=2, minutes=50)
        )
        self.db.add(feeding)
        self.db.commit()
        
        # Analyze the episode
        result = analyze_crying_episode(self.db, crying.id)
        
        # Should return a result
        self.assertIsNotNone(result)
        self.assertIn("predicted_reason", result)
        self.assertIn("confidence", result)
        
        # Check the database update
        crying = self.db.query(Crying).filter(Crying.id == crying.id).first()
        self.assertIsNotNone(crying.predicted_reason)
        self.assertIsNotNone(crying.prediction_confidence)

if __name__ == '__main__':
    unittest.main() 