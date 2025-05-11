import os
import openai
from typing import Dict, Any, List, Optional, Tuple
import json
from datetime import datetime, timedelta

# Configure OpenAI API
openai.api_key = os.environ.get("OPENAI_API_KEY")

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
        
        return result["intent"], result.get("parameters", {})
        
    except Exception as e:
        print(f"Error classifying query: {e}")
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
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Error generating response: {e}")
        return "I'm sorry, I couldn't process your question. Please try asking in a different way."

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