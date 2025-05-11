# Natural Language Processing for Baby Alert

This component adds natural language query capabilities to the Baby Alert application, allowing users to ask questions about their baby's activities in plain English.

## Setup Instructions

### 1. Install Required Packages

Make sure to install the required packages:

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

You need to set up the following environment variables:

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `OPENAI_API_KEY`: Your OpenAI API key for natural language processing

You can set these variables in one of the following ways:

#### Option 1: Create a .env file

Create a `.env` file in the root directory with the following content:

```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here
```

#### Option 2: Set environment variables directly

On Windows:
```
set TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
set OPENAI_API_KEY=your_openai_api_key_here
```

On Linux/Mac:
```
export TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
export OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Run the Application

Run the application using the provided scripts:

```bash
# On Windows
run.bat

# On Linux/Mac
./run.sh
```

## Usage Examples

Users can ask questions like:

- "When was the last feeding?"
- "How long did the baby sleep today?"
- "How many diapers were changed yesterday?"
- "What's my baby's feeding schedule?"
- "When was the last diaper change?"

The bot will process these natural language queries and provide relevant information from the database.

## Supported Query Types

- Last feeding information
- Last sleep session
- Last diaper change
- Last crying episode
- Feeding count for a time period
- Sleep duration for a time period
- Diaper count for a time period
- Crying episodes for a time period
- Baby's schedule and patterns 