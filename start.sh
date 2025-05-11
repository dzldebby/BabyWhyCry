#!/bin/bash

# Install NLTK data
python -m nltk.downloader punkt stopwords wordnet averaged_perceptron_tagger

# Run the main application
python src/main.py 