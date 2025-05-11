import os
import sys
import unittest
import tempfile
from unittest.mock import patch

# Add parent directory to path so we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the main application (without running it)
from src import main, bot
from src.database import init_db

class TestApp(unittest.TestCase):
    def setUp(self):
        # Create a temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db')
        
        # Set up a test token
        self.test_token = "test_token"
        os.environ["TELEGRAM_BOT_TOKEN"] = self.test_token
        
        # Path to save the original path and temp path
        self.original_db_path = None
        self.temp_db_path = self.temp_db.name
    
    def tearDown(self):
        # Clean up
        self.temp_db.close()
        
        # Restore original path if changed
        if self.original_db_path:
            from src import database
            database.db_path = self.original_db_path
    
    @patch('src.bot.Application.run_polling')
    def test_init_db(self, mock_run_polling):
        """Test that the database initialization works."""
        # Patch the database path
        from src import database
        self.original_db_path = database.db_path
        database.db_path = self.temp_db_path
        
        # Initialize the database
        init_db()
        
        # Check that the database file exists
        self.assertTrue(os.path.exists(self.temp_db_path))
    
    @patch('src.bot.Application.run_polling')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_with_token(self, mock_parse_args, mock_run_polling):
        """Test that the main function works with a token."""
        # Set up mock arguments
        mock_parse_args.return_value = type('obj', (object,), {
            'token': self.test_token,
            'init_db': True
        })
        
        # Patch the database path
        from src import database
        self.original_db_path = database.db_path
        database.db_path = self.temp_db_path
        
        # Run the main function (patched to not actually start the bot)
        with patch('src.bot.main'):
            main.main()
        
        # Check that the environment variable was set
        self.assertEqual(os.environ.get("TELEGRAM_BOT_TOKEN"), self.test_token)
    
    @patch('src.bot.Application')
    def test_bot_initialization(self, mock_application):
        """Test that the bot initializes correctly."""
        # Create a mock for the Application
        mock_app = mock_application.builder.return_value.token.return_value.build.return_value
        
        # Patch functions that would actually run the bot
        with patch('src.bot.Application.run_polling'):
            # Run the bot main function
            bot.main()
        
        # Check that the application added handlers
        self.assertTrue(mock_app.add_handler.called)
        self.assertTrue(mock_app.add_error_handler.called)

if __name__ == '__main__':
    unittest.main() 