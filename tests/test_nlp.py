import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import json

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from nlp_handler import classify_query, generate_response, process_query, QueryIntent

class TestNLPHandler(unittest.TestCase):
    
    @patch('nlp_handler.openai.chat.completions.create')
    def test_classify_query(self, mock_openai):
        # Mock the OpenAI API response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "intent": "last_feeding",
            "parameters": {
                "time_period": "today",
                "baby_name": None,
                "count": None
            },
            "confidence": 0.95
        })
        mock_openai.return_value = mock_response
        
        # Test the classify_query function
        intent, params = classify_query("When was the last feeding?")
        
        # Check the results
        self.assertEqual(intent, "last_feeding")
        self.assertEqual(params["time_period"], "today")
        self.assertIsNone(params["baby_name"])
        self.assertIsNone(params["count"])
        
        # Verify OpenAI API was called with correct parameters
        mock_openai.assert_called_once()
        call_args = mock_openai.call_args[1]
        self.assertEqual(call_args["messages"][1]["content"], "When was the last feeding?")
    
    @patch('nlp_handler.openai.chat.completions.create')
    def test_generate_response(self, mock_openai):
        # Mock the OpenAI API response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "The last feeding was at 2:30 PM today."
        mock_openai.return_value = mock_response
        
        # Test data
        intent = "last_feeding"
        data = {
            "found": True,
            "type": "bottle",
            "start_time": "2023-05-10 14:30:00",
            "end_time": "2023-05-10 14:45:00",
            "amount": 120,
            "baby_name": "Alex"
        }
        query = "When was the last feeding?"
        
        # Test the generate_response function
        response = generate_response(intent, data, query)
        
        # Check the results
        self.assertEqual(response, "The last feeding was at 2:30 PM today.")
        
        # Verify OpenAI API was called with correct parameters
        mock_openai.assert_called_once()
    
    @patch('nlp_handler.classify_query')
    def test_process_query(self, mock_classify):
        # Mock the classify_query function
        mock_classify.return_value = (QueryIntent.LAST_FEEDING, {"time_period": "today"})
        
        # Test the process_query function
        db_function, intent, params = process_query("When was the last feeding?", 1)
        
        # Check the results
        self.assertEqual(db_function, "get_last_feeding")
        self.assertEqual(intent, QueryIntent.LAST_FEEDING)
        self.assertEqual(params["time_period"], "today")
        self.assertEqual(params["baby_id"], 1)
        
        # Verify classify_query was called with correct parameters
        mock_classify.assert_called_once_with("When was the last feeding?")

if __name__ == '__main__':
    unittest.main() 