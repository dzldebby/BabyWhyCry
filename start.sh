#!/bin/bash

# Install NLTK data
python -m nltk.downloader punkt stopwords wordnet averaged_perceptron_tagger

# Fix timezone information in the database
echo "Fixing timezone information in the database..."
python fix_timezone.py

# Run the main application
python src/main.py 