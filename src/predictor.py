import datetime
from sqlalchemy.orm import Session
from models import Baby, Feeding, Sleep, Diaper, Crying, CryingReason
from database import get_recent_events

class CryingPredictor:
    """
    Predicts the reason a baby is crying based on recent history.
    Uses a simple rule-based approach initially, but could be expanded
    to use machine learning in the future.
    """
    
    def __init__(self):
        # Configuration constants
        self.HUNGER_THRESHOLD_HOURS = 2.5  # Hours since last feeding to consider hunger
        self.DIAPER_THRESHOLD_HOURS = 3.0  # Hours since last diaper to consider dirty diaper
        self.ATTENTION_THRESHOLD_MINUTES = 90  # Minutes awake to consider needing attention
    
    def predict(self, db: Session, baby_id: int):
        """
        Predict the most likely reason for crying based on recent events.
        Returns a tuple of (predicted_reason, confidence)
        """
        now = datetime.datetime.utcnow()
        
        # Get recent events for analysis
        recent_events = self._get_relevant_events(db, baby_id)
        
        # Extract the most recent events by type
        last_feeding = self._get_last_event_by_type(recent_events, "feeding")
        last_diaper = self._get_last_event_by_type(recent_events, "diaper")
        last_sleep = self._get_last_event_by_type(recent_events, "sleep")
        
        # Initialize scores for each reason
        hunger_score = 0
        diaper_score = 0
        attention_score = 0
        
        # Calculate time since last feeding
        if last_feeding:
            time_since_feeding = (now - last_feeding["time"]).total_seconds() / 3600  # hours
            # The longer since feeding, the higher the hunger score
            if time_since_feeding > self.HUNGER_THRESHOLD_HOURS:
                hunger_score = min(100, (time_since_feeding / self.HUNGER_THRESHOLD_HOURS) * 70)
            else:
                hunger_score = max(0, (time_since_feeding / self.HUNGER_THRESHOLD_HOURS) * 40)
        else:
            # If no feeding record found, assume high hunger score
            hunger_score = 90
        
        # Calculate time since last diaper change
        if last_diaper:
            time_since_diaper = (now - last_diaper["time"]).total_seconds() / 3600  # hours
            if time_since_diaper > self.DIAPER_THRESHOLD_HOURS:
                diaper_score = min(90, (time_since_diaper / self.DIAPER_THRESHOLD_HOURS) * 70)
            else:
                diaper_score = max(0, (time_since_diaper / self.DIAPER_THRESHOLD_HOURS) * 30)
        else:
            # If no diaper record found, assume medium-high diaper score
            diaper_score = 80
        
        # Calculate time since waking up
        if last_sleep:
            sleep_data = last_sleep["data"]
            # If baby is still sleeping (unlikely as they're crying)
            if not sleep_data.end_time:
                attention_score = 10
            else:
                time_awake = (now - sleep_data.end_time).total_seconds() / 60  # minutes
                if time_awake > self.ATTENTION_THRESHOLD_MINUTES:
                    attention_score = min(85, (time_awake / self.ATTENTION_THRESHOLD_MINUTES) * 65)
                else:
                    attention_score = max(10, (time_awake / self.ATTENTION_THRESHOLD_MINUTES) * 50)
        else:
            # If no sleep record found, assume medium attention score
            attention_score = 50
        
        # Adjust scores based on historical data patterns
        self._adjust_scores_from_history(db, baby_id, 
                                        hunger_score, diaper_score, attention_score)
        
        # Get the highest scoring reason
        scores = {
            CryingReason.HUNGRY: hunger_score,
            CryingReason.DIAPER: diaper_score,
            CryingReason.ATTENTION: attention_score
        }
        
        predicted_reason = max(scores, key=scores.get)
        max_score = scores[predicted_reason]
        
        # Calculate confidence based on how much this reason outscores others
        second_max = max([s for r, s in scores.items() if r != predicted_reason], default=0)
        confidence = min(95, max(30, (max_score - second_max) + (max_score / 2)))
        
        return predicted_reason, confidence
    
    def _get_relevant_events(self, db, baby_id):
        """Get the most recent events needed for analysis"""
        # Get more events than strictly needed for accuracy
        return get_recent_events(db, baby_id, limit=20)
    
    def _get_last_event_by_type(self, events, event_type):
        """Find the most recent event of a specific type"""
        for event in events:
            if event["type"] == event_type:
                return event
        return None
    
    def _adjust_scores_from_history(self, db, baby_id, hunger_score, diaper_score, attention_score):
        """
        Adjust prediction scores based on historical crying episodes and feedback.
        This would analyze past crying incidents and user feedback to improve predictions.
        Would be implemented in a more advanced version.
        """
        # This is where a machine learning model could be implemented
        # For now, we'll leave this as a placeholder
        return hunger_score, diaper_score, attention_score
    
    def analyze_crying(self, db, crying_id):
        """
        Analyze a crying episode and update the database with prediction.
        """
        # Get the crying episode
        crying = db.query(Crying).filter(Crying.id == crying_id).first()
        if not crying:
            return None
        
        # Get the prediction
        predicted_reason, confidence = self.predict(db, crying.baby_id)
        
        # Update the crying record
        crying.predicted_reason = predicted_reason
        crying.prediction_confidence = confidence
        db.commit()
        
        return {
            "predicted_reason": predicted_reason,
            "confidence": confidence
        }

# Create a singleton instance
predictor = CryingPredictor()

def predict_crying_reason(db, baby_id):
    """
    Predict the reason a baby is crying.
    Returns a dictionary with the predicted reason and confidence.
    """
    reason, confidence = predictor.predict(db, baby_id)
    return {
        "predicted_reason": reason,
        "confidence": confidence
    }

def analyze_crying_episode(db, crying_id):
    """
    Analyze a crying episode and update the database.
    Returns the analysis results.
    """
    return predictor.analyze_crying(db, crying_id) 