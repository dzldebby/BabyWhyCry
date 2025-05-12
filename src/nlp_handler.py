import os
import openai
import logging
from typing import Dict, Any, List, Optional, Tuple
import json
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

# Configure OpenAI API
api_key = os.environ.get("OPENAI_API_KEY")
if api_key:
    logger.info(f"OpenAI API key found with length: {len(api_key)}")
    openai.api_key = api_key
else:
    logger.error("OpenAI API key not found in environment variables!")

# Test OpenAI API connection
def test_openai_connection():
    """Test if the OpenAI API connection works"""
    if not openai.api_key:
        logger.error("Cannot test OpenAI connection: No API key provided")
        return False
        
    try:
        logger.info("Testing OpenAI API connection...")
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        logger.info(f"OpenAI API connection successful: {response.choices[0].message.content}")
        return True
    except Exception as e:
        logger.error(f"OpenAI API connection test failed: {str(e)}")
        return False

# Run test on import
openai_available = test_openai_connection()
logger.info(f"OpenAI API available: {openai_available}")

# Define query intents
class QueryIntent:
    LAST_FEEDING = "last_feeding"
    LAST_SLEEP = "last_sleep"
    LAST_DIAPER = "last_diaper"
    LAST_CRYING = "last_crying"
    FEEDING_COUNT = "feeding_count"
    SLEEP_DURATION = "sleep_duration"
    DIAPER_COUNT = "diaper_count"
    CRYING_EPISODES = "crying_episodes"
    BABY_SCHEDULE = "baby_schedule"
    UNKNOWN = "unknown"

# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        return super().default(obj)

def classify_query(query_text: str) -> Tuple[str, Dict[str, Any]]:
    """
    Classify the user's query to determine the intent and extract parameters.
    
    Args:
        query_text: The user's natural language query
        
    Returns:
        Tuple containing (intent, parameters)
    """
    try:
        # First try simple rule-based classification if it's an obvious query
        simple_intent = classify_query_simple(query_text)
        if simple_intent[0] != QueryIntent.UNKNOWN:
            logger.info(f"Classified query using simple rules: {simple_intent[0]}")
            return simple_intent
            
        # If simple classification didn't work, try OpenAI
        if not openai.api_key:
            logger.warning("OpenAI API key not available, using simple classification only")
            return simple_intent
            
        # Prepare the system prompt
        system_prompt = """
        You are an AI assistant that analyzes queries about baby care events. 
        Classify the query into one of these categories:
        - last_feeding: When the user asks about the most recent feeding
        - last_sleep: When the user asks about the most recent sleep session
        - last_diaper: When the user asks about the most recent diaper change
        - last_crying: When the user asks about the most recent crying episode
        - feeding_count: When the user asks about number of feedings
        - sleep_duration: When the user asks about sleep duration
        - diaper_count: When the user asks about number of diaper changes
        - crying_episodes: When the user asks about crying episodes
        - baby_schedule: When the user asks about the baby's schedule
        - unknown: When the query doesn't match any of the above
        
        Also extract these parameters if present:
        - time_period: The time period mentioned (today, yesterday, this week, etc.)
        - baby_name: The name of the baby if mentioned
        - count: Any number mentioned in the query
        
        Return your response as a JSON object with these fields:
        {
          "intent": "intent_category",
          "parameters": {
            "time_period": "extracted time period or null",
            "baby_name": "extracted baby name or null",
            "count": "extracted count or null"
          },
          "confidence": "confidence score between 0 and 1"
        }
        """
        
        logger.info("Calling OpenAI API for query classification")
        
        # Make the API call to OpenAI
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",  # You can use a different model if needed
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query_text}
            ],
            temperature=0.1,  # Low temperature for more deterministic responses
            max_tokens=300
        )
        
        # Parse the response
        result = json.loads(response.choices[0].message.content)
        logger.info(f"Successfully classified query with OpenAI: {result['intent']}")
        
        return result["intent"], result.get("parameters", {})
        
    except Exception as e:
        logger.error(f"Error classifying query with OpenAI: {str(e)}")
        # Fall back to simple classification
        return classify_query_simple(query_text)

def classify_query_simple(query_text: str) -> Tuple[str, Dict[str, Any]]:
    """Simple rule-based classifier when OpenAI is unavailable"""
    query = query_text.lower()
    
    if any(phrase in query for phrase in ["last feeding", "recent feeding", "when feeding", "last feed"]):
        return QueryIntent.LAST_FEEDING, {}
        
    elif any(phrase in query for phrase in ["last sleep", "recent sleep", "when sleep", "last slept"]):
        return QueryIntent.LAST_SLEEP, {}
        
    elif any(phrase in query for phrase in ["last diaper", "recent diaper", "when diaper", "last change"]):
        return QueryIntent.LAST_DIAPER, {}
        
    elif any(phrase in query for phrase in ["last crying", "recent crying", "when cry", "last cried"]):
        return QueryIntent.LAST_CRYING, {}
        
    elif any(phrase in query for phrase in ["how many feeding", "feeding count", "number of feeding", "feedings"]):
        return QueryIntent.FEEDING_COUNT, {}
        
    elif any(phrase in query for phrase in ["sleep duration", "how long sleep", "sleep time"]):
        return QueryIntent.SLEEP_DURATION, {}
        
    elif any(phrase in query for phrase in ["diaper count", "how many diaper", "number of diaper"]):
        return QueryIntent.DIAPER_COUNT, {}
        
    elif any(phrase in query for phrase in ["crying episode", "how many cry", "number of cry"]):
        return QueryIntent.CRYING_EPISODES, {}
        
    elif any(phrase in query for phrase in ["schedule", "routine", "pattern"]):
        return QueryIntent.BABY_SCHEDULE, {}
    
    return QueryIntent.UNKNOWN, {}

def generate_response(intent: str, data: Dict[str, Any], query_text: str) -> str:
    """
    Generate a natural language response based on the intent and data.
    
    Args:
        intent: The classified intent of the query
        data: The data retrieved from the database
        query_text: The original query text
        
    Returns:
        A natural language response to the user's query
    """
    try:
        # Prepare the system prompt
        system_prompt = """
        You are an AI assistant for a baby tracking app. 
        Generate a natural, conversational response to the user's query based on the data provided.
        Keep your response concise, friendly, and focused on answering the question.
        Include relevant details from the data but avoid unnecessary information.
        If no data is available, politely inform the user.
        """
        
        # Convert data to a string representation using the custom encoder
        data_str = json.dumps(data, cls=DateTimeEncoder)
        
        # Prepare the user message
        user_message = f"""
        User query: {query_text}
        Query intent: {intent}
        Available data: {data_str}
        """
        
        logger.info(f"Calling OpenAI API for response generation with intent: {intent}")
        
        # Make the API call to OpenAI
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,  # Higher temperature for more natural responses
            max_tokens=200
        )
        
        result = response.choices[0].message.content.strip()
        logger.info(f"Successfully generated response from OpenAI")
        return result
        
    except Exception as e:
        logger.error(f"Error generating response with OpenAI: {str(e)}")
        
        # If we have data, provide a simple response based on the intent
        if intent == "last_feeding" and data.get("found", False):
            feeding_time = data.get("start_time")
            feeding_type = data.get("type")
            if feeding_time and feeding_type:
                if hasattr(feeding_type, 'value'):
                    type_str = feeding_type.value
                else:
                    type_str = str(feeding_type)
                return f"The last feeding ({type_str}) was at {feeding_time}."
            
        return "I'm sorry, I couldn't process your question with the AI. But I found the data you requested. Please check the history section for details."

def parse_time_period(time_period: str) -> Tuple[datetime, datetime]:
    """
    Parse a time period string into start and end datetime objects.
    
    Args:
        time_period: String describing a time period (today, yesterday, this week, etc.)
        
    Returns:
        Tuple of (start_time, end_time) in UTC
    """
    now = datetime.utcnow()
    
    if time_period in ["today", "this day"]:
        start_time = datetime(now.year, now.month, now.day)
        end_time = now
    elif time_period in ["yesterday", "last day"]:
        yesterday = now - timedelta(days=1)
        start_time = datetime(yesterday.year, yesterday.month, yesterday.day)
        end_time = datetime(now.year, now.month, now.day)
    elif time_period in ["this week", "current week"]:
        start_time = now - timedelta(days=now.weekday())
        start_time = datetime(start_time.year, start_time.month, start_time.day)
        end_time = now
    elif time_period in ["last week", "previous week"]:
        start_of_this_week = now - timedelta(days=now.weekday())
        start_time = start_of_this_week - timedelta(days=7)
        end_time = start_of_this_week
    else:
        # Default to today
        start_time = datetime(now.year, now.month, now.day)
        end_time = now
        
    return start_time, end_time

def process_query(query_text: str, current_baby_id: Optional[int] = None) -> Tuple[str, str, Dict[str, Any]]:
    """
    Process a natural language query and determine what database function to call.
    
    Args:
        query_text: The user's natural language query
        current_baby_id: The ID of the currently selected baby, if any
        
    Returns:
        Tuple containing (db_function_name, intent, parameters)
    """
    # Classify the query
    intent, parameters = classify_query(query_text)
    
    # Determine which database function to call based on intent
    if intent == QueryIntent.LAST_FEEDING:
        db_function = "get_last_feeding"
    elif intent == QueryIntent.LAST_SLEEP:
        db_function = "get_last_sleep"
    elif intent == QueryIntent.LAST_DIAPER:
        db_function = "get_last_diaper"
    elif intent == QueryIntent.LAST_CRYING:
        db_function = "get_last_crying"
    elif intent == QueryIntent.FEEDING_COUNT:
        db_function = "get_feeding_count"
    elif intent == QueryIntent.SLEEP_DURATION:
        db_function = "get_sleep_duration"
    elif intent == QueryIntent.DIAPER_COUNT:
        db_function = "get_diaper_count"
    elif intent == QueryIntent.CRYING_EPISODES:
        db_function = "get_crying_episodes"
    elif intent == QueryIntent.BABY_SCHEDULE:
        db_function = "get_baby_schedule"
    else:
        db_function = "unknown"
    
    # Add the current baby ID to parameters if not specified
    if "baby_id" not in parameters and current_baby_id is not None:
        parameters["baby_id"] = current_baby_id
        
    return db_function, intent, parameters 