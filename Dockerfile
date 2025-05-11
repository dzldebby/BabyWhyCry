FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ /app/src/

# Initialize database
RUN mkdir -p /app/data
ENV PYTHONPATH=/app

# Set environment variables
ENV TELEGRAM_BOT_TOKEN=""

# Run the application
CMD ["python", "src/main.py"] 